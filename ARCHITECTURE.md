# Architecture de l'application

Ce document décrit l'architecture générale de l'application Quiz Interactif.

## Vue d'ensemble

L'application est une interface web Streamlit qui permet de générer et corriger des questions de compréhension basées sur des documents. Elle fonctionne entièrement localement, sans connexion Internet requise (sauf pour les dépendances initiales).

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Streamlit                         │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  Upload UI       │  │  Question UI     │  │  Correction  │  │
│  │  (Sidebar)       │  │  (Main)          │  │  UI (Form)   │  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬───────┘  │
│           │                     │                    │           │
└───────────┼─────────────────────┼────────────────────┼───────────┘
            │                     │                    │
            ▼                     ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Session State Management                      │
│  (chunks, question_index, asked_questions, current_question)   │
└─────────────────────────────────────────────────────────────────┘
            │                     │                    │
            ▼                     ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │Extract Focus │  │Split Docs    │  │Generate Questions    │  │
│  │Text          │  │(Chunks)      │  │& Correct Answers     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
            │                                        │
            ▼                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Processing Layer                         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │PDF Parser    │  │DOCX Parser   │  │Text Splitter         │  │
│  │(pypdf)       │  │(python-docx) │  │(RecursiveCharSplit)  │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
            │                                        │
            ▼                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Integration Layer                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ LangChain + fournisseur LLM distant                      │  │
│  │ - JSON Mode pour réponses structurées                    │  │
│  │ - Temperature control (0.2 general, 0.1 JSON)           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Service LLM externe                           │
│                                                                  │
│  Modèle: configurable via variable d'environnement              │
│  Accès: via clé API                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Flux de données détaillé

### 1. Upload et extraction du document

```
User Upload (PDF/DOCX)
        │
        ▼
extract_focus_text()
        │
        ├─── PDF: 
        │    ├─ Récupère les pages non vides
        │    └─ Sélectionne UNE page aléatoire
        │
        └─── DOCX:
             ├─ Récupère tous les paragraphes
             └─ Sélectionne UN bloc de 8 paragraphes aléatoires
        │
        ▼
(text, label) tuple
        │
        ▼
Cache (avec @st.cache_data)
```

### 2. Split du document en chunks

```
Texte extrait
        │
        ▼
RecursiveCharacterTextSplitter
        │
        ├─ Chunk size: 1200 caractères
        ├─ Overlap: 150 caractères
        │
        ▼
Lista[Chunk]
        │
        ▼
Session State (conservé pour la durée de la session)
```

### 3. Génération de question

```
Chunks + Contexte
        │
        ▼
generate_question()
        │
        ├─ Sélectionne MAX_CONTEXT_CHUNKS (2) chunks
        │
        ▼
Prompt + Contexte
        │
        ▼
get_json_llm() → client LLM JSON (temperature=0.1)
        │
        ▼
LLM Response (JSON)
        │
        ▼
_extract_json()
        │
        ├─ Essaie de parser directement
        ├─ Strip markdown fences si présents
        ├─ Recherche plusieurs candidats JSON valides
        │
        ▼
Question Dict: {question, answer, explanation}
        │
        ▼
is_question_acceptable()
        │
        ├─ Vérifie absence de bannies fraases
        │  (chapitre, section, page, titre, etc.)
        │
        ├─ Acceptée: retour au UI
        └─ Rejetée: retry jusqu'à 6 fois
```

### 4. Correction de réponse

```
User Answer + Question + Expected Answer
        │
        ▼
correct_answer()
        │
        ▼
Correction Prompt + Contexte
        │
        ▼
get_json_llm() → client LLM JSON (temperature=0.1)
        │
        ▼
LLM Response: {is_correct, score, feedback, correct_answer, explanation}
        │
        ▼
_extract_json() → Parsing similaire
        │
        ▼
Correction affichée à l'utilisateur
        │
        ▼
set_current_question()
        │
        └─ Ajoute à st.session_state.asked_questions
```

## Composants clés

### Session State

Gère l'état persistant durant une session Streamlit:

```python
st.session_state = {
    "chunks": List[str],                    # Chunks du document
    "question_index": int,                  # Index actuel
    "asked_questions": List[str],           # Questions posées (déduplication)
    "current_question": Dict,               # Question actuelle
    "last_correction": Dict,                # Dernière correction
    "source_name": str,                     # Nom du fichier
    "source_focus_label": str              # Label de l'extrait (ex: "Page 5/10")
}
```

### Caching Streamlit

- `@st.cache_resource`: LLM instances (`get_llm`, `get_json_llm`)
- `@st.cache_data`: Extraction de texte (`extract_focus_text`)

Cela réduit les recalculs inutiles entre les reruns.

### Filtrage des questions

L'application rejette automatiquement les questions sur :
- Structure du document (chapitre, section, page, titre)
- Organisation (composant, indice, numéro)
- Références non-pédagogiques

List de bannies phrases dans `is_question_acceptable()`.

## Configuration

### `.streamlit/config.toml`

Configure :
- **Thème**: Couleurs (primaryColor, backgroundColor)
- **Typographie**: Polices (font, headingFont, codeFont)
- **UI**: Rayons (baseRadius, buttonRadius)

### `.env.example`

Variables d'environnement optionnelles :
- `GROQ_API_KEY`: Clé API du fournisseur LLM
- `GROQ_MODEL`: Modèle à utiliser
- `STREAMLIT_PORT`: Port Streamlit

## Points de performance

### Optimisations appliquées

1. **Extrait aléatoire** : Une page PDF au lieu du document entier
2. **Chunks limités** : 2 chunks maximum pour contexte (au lieu de 4+)
3. **Caching agressif** : Réutilisation du texte et splits extraits
4. **JSON mode** : Le client LLM force un format structuré exploitable
5. **Température basse** : 0.1 pour JSON (meilleure cohérence)
6. **Retry intelligente** : Si question rejetée, régénère (pas re-requête entière)

### Résultats

- **First question** : ~2-3 secondes
- **Next questions** : ~1-2 secondes
- **Correction** : ~2-3 secondes

## Dépendances externes

| Paquet | Rôle | Version |
|--------|------|---------|
| streamlit | UI & orchestration | Latest |
| langchain | LLM orchestration | Latest |
| langchain-groq | LLM API integration | Latest |
| pypdf | PDF parsing | Latest |
| python-docx | DOCX parsing | Latest |
| langchain-text-splitters | Text chunking | Latest |

## Extensibilité future

### Ajout d'un nouveau format de document

1. Créer `extract_[format]()` dans `app.py`
2. L'ajouter à `extract_focus_text()`
3. Tester le parsing

Exemple EPUB :
```python
def extract_epub(file_bytes: bytes) -> str:
    import ebooklib
    # ... logique d'extraction
    return text
```

### Ajout d'un nouveau modèle LLM

Modifi `get_json_llm()` ou créer `get_custom_llm()`:

```python
def get_custom_llm() -> ChatGroq:
        return ChatGroq(model="mixtral-8x7b-32768", temperature=0.1)
```

### Support de plusieurs utilisateurs

Ajouter une base de données (SQLite, PostgreSQL) pour :
- Persister les sessions
- Tracker les scores par utilisateur
- Générer des statistiques

## Sécurité

- **Aucune donnée cloud** : Tout reste local
- **Aucune authentification** : À ajouter si déploiement multi-utilisateurs
- **Fichiers temporaires** : Stockés en mémoire, pas sur disque (via BytesIO)

---

**Dernière mise à jour** : 2026-09-10
