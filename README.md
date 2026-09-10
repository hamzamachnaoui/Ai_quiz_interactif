# Quiz Interactif - Ollama & Streamlit

Une application web de génération automatique de questions de compréhension basée sur vos documents (PDF ou DOCX). Utilisez cette application pour tester votre compréhension de n'importe quel document, avec correction intelligente de vos réponses.

## Fonctionnalités

- ✅ **Upload de documents** : Chargez des fichiers PDF ou DOCX
- ✅ **Génération automatique de questions** : Questions créées dynamiquement basées sur le contenu
- ✅ **Correction intelligente** : Les réponses sont évaluées avec score et feedback détaillé
- ✅ **Pas de répétition** : Chaque question n'est posée qu'une seule fois par session
- ✅ **Performance optimisée** : Utilise des extraits aléatoires du document pour une génération rapide
- ✅ **Interface moderne** : Design réactif avec animations et thème personnalisé

## Prérequis

- Python 3.10+
- Ollama exécuté localement sur le port par défaut (11434)
- Modèle Mistral téléchargé dans Ollama

## Installation

### 1. Cloner ou créer le projet

```bash
git clone <votre-repo>
cd Ai_Learning
```

### 2. Créer un environnement virtuel

**Windows** :
```powershell
python -m venv .venv
.\.venv\Scripts\Activate
```

**macOS/Linux** :
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Vérifier qu'Ollama est en cours d'exécution

```bash
ollama serve  # Dans un autre terminal
ollama pull mistral  # Si Mistral n'est pas téléchargé
```

## Utilisation

### Lancer l'application

```bash
streamlit run app.py
```

L'application s'ouvre automatiquement dans votre navigateur (généralement à `http://localhost:8501`).

### Workflow

1. **Télécharger un document** : Cliquez sur "Parcourir les fichiers" et sélectionnez un PDF ou DOCX
2. **Générer une question** : Cliquez sur "Générer une question" - une question sera créée à partir du document
3. **Répondre** : Tapez votre réponse dans le champ texte
4. **Soumettre et recevoir une correction** : Cliquez sur "Soumettre la réponse" pour obtenir un score et un feedback détaillé
5. **Continuer** : Cliquez sur "Question suivante" pour une nouvelle question

## Architecture

### Fichiers principaux

```
.
├── app.py                    # Application Streamlit principale
├── .streamlit/
│   └── config.toml          # Configuration du thème et des fonts
├── requirements.txt         # Dépendances Python
└── README.md               # Ce fichier
```

### Flux de données

```
Document Upload
    ↓
Extract Focus Text (extrait aléatoire)
    ↓
Split Document (chunks pour contexte)
    ↓
Generate Question (Ollama/Mistral)
    ↓
User Answer
    ↓
Correct Answer (évaluation + feedback)
    ↓
Track in Session State (pour éviter répétitions)
```

### Technologies utilisées

| Composant | Rôle |
|-----------|------|
| **Streamlit** | Framework web interactif |
| **LangChain** | Orchestration LLM et text splitting |
| **Ollama** | Moteur LLM local |
| **Mistral** | Modèle de langage |
| **pypdf** | Extraction de texte des PDF |
| **python-docx** | Traitement des documents Word |

## Configuration

Éditez `.streamlit/config.toml` pour personnaliser :

```toml
[theme]
primaryColor = "#d85a2d"      # Couleur des boutons
backgroundColor = "#fffaf3"   # Fond de page
font = "IBM Plex Sans"        # Police principale
headingFont = "Space Grotesk" # Police des titres
```

## Optimisations de performance

- **Extraits aléatoires** : Sélectionne une page PDF aléatoire ou un bloc de paragraphes DOCX au lieu du document entier
- **Contexte limité** : Utilise 2 chunks maximum pour chaque génération de question
- **Caching Streamlit** : Les extractions de texte et splits sont mis en cache
- **Questions uniques** : Chaque session évite de poser deux fois la même question
- **Filtrage intelligent** : Rejette automatiquement les questions portant sur la structure du document

## Dépannage

### L'app se lance mais reste bloquée

Vérifiez qu'Ollama est en cours d'exécution :
```bash
ollama serve
```

Testez la connexion :
```bash
curl http://localhost:11434/api/tags
```

### "Modèle non trouvé"

Téléchargez Mistral :
```bash
ollama pull mistral
```

Listez les modèles disponibles :
```bash
ollama list
```

### Questions mal formées ou répétitives

L'app dispose d'un système de filtrage pour rejeter les questions sur la structure du document. Si une question est rejetée, l'app la régénère automatiquement (jusqu'à 6 tentatives).

### Erreurs JSON

L'app dispose de multiples stratégies de fallback pour extraire du JSON valide à partir des réponses du modèle.

## Développement futur

- [ ] Support de formats additionnels (TXT, EPUB, Markdown)
- [ ] Export des sessions (questions + réponses + scores)
- [ ] Historique des performances par utilisateur
- [ ] Sélection dynamique du modèle Ollama via UI
- [ ] Ajustement de la difficulté des questions
- [ ] Mode multi-utilisateurs avec base de données
- [ ] Support du multi-langue

## Contribution

Les contributions sont bienvenues ! Pour contribuer :

1. Forkez le projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/NouvelleFeature`)
3. Committez vos changements (`git commit -m 'Add: Nouvelle fonctionnalité'`)
4. Poussez vers la branche (`git push origin feature/NouvelleFeature`)
5. Ouvrez une Pull Request

## Licence

À définir selon votre préférence (MIT, Apache 2.0, etc.)

## Ressources utiles

- [Documentation Streamlit](https://docs.streamlit.io/)
- [Documentation LangChain](https://docs.langchain.com/)
- [Ollama - Site officiel](https://ollama.ai/)
- [Modèle Mistral](https://mistral.ai/)

---

**Note** : Cette application nécessite une connexion locale à Ollama. Elle ne fonctionne pas sans un moteur LLM local en cours d'exécution.
- Les documents très volumineux peuvent demander plus de temps de traitement.
