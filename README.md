# AI Quiz Interactif

> Générateur intelligent de questions de compréhension à partir de vos documents

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red?style=flat-square)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=flat-square)](https://github.com/hamzamachnaoui/Ai_quiz_interactif)

Transformez vos documents en quiz pédagogique interactif avec correction automatique et feedback intelligent.

### 🚀 [Essayez l'application en ligne →](https://aiquizinteractif-yixus6eyaappmvfcdgvrvs9.streamlit.app/)

---

## Vue d'ensemble

**AI Quiz Interactif** est une application web qui transforme automatiquement vos documents PDF ou DOCX en quiz pédagogique interactif. L'application génère des questions de compréhension intelligentes, corrige les réponses en temps réel, et fournit des explications détaillées.

### Cas d'usage

- 📚 **Enseignants** : Créer rapidement des évaluations formatives
- 🎓 **Étudiants** : Auto-évaluer sa compréhension de documents complexes  
- 💼 **Formation d'entreprise** : Tester la compréhension des supports de formation
- 🔍 **QA/Éditorial** : Valider la qualité et la clarté d'une documentation

---

## Fonctionnalités

✨ **Génération Intelligente**
- Questions générées automatiquement basées sur le contenu réel du document
- Filtrage actif pour éviter les questions hors contexte
- Variation des questions à chaque session

🎯 **Correction Automatique**
- Évaluation instantanée avec score (0-10)
- Feedback détaillé et pédagogique
- Affichage de la réponse correcte et explication

📄 **Multi-format**
- Supports PDF et DOCX
- Extraction intelligente du texte
- Gestion des documents longs avec optimisation

⚡ **Performance**
- Première question en ~2-3 secondes
- Questions suivantes en ~1-2 secondes
- Interface réactive sans lag

🎨 **UX Moderne**
- Interface épurée et intuitive
- Animations fluides
- Responsive sur tous les appareils

---

## Installation Rapide

### Prérequis

- Python 3.10 ou supérieur
- pip
- Clé API gratuite (voir section Configuration)

### Étapes

**1. Cloner le projet**
```bash
git clone https://github.com/hamzamachnaoui/Ai_quiz_interactif.git
cd Ai_quiz_interactif
```

**2. Créer un environnement virtuel**

*Sur Windows :*
```powershell
python -m venv .venv
.\.venv\Scripts\Activate
```

*Sur macOS/Linux :*
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Installer les dépendances**
```bash
pip install -r requirements.txt
```

**4. Configurer la clé API**

Créez un fichier `.env` à la racine du projet :
```bash
cp .env.example .env
```

Éditez `.env` et ajoutez votre clé API :
```
GROQ_API_KEY=votre_clé_ici
GROQ_MODEL=mixtral-8x7b-32768
```

**5. Lancer l'application**
```bash
streamlit run app.py
```

L'app s'ouvre automatiquement à `http://localhost:8501`

---

## Configuration

### Obtenir une clé API gratuite

L'application utilise une API de modèle de langage pour générer les questions. Vous avez besoin d'une clé API :

1. Allez sur [console.groq.com](https://console.groq.com)
2. Inscrivez-vous (gratuit)
3. Créez une clé API dans la section Keys
4. Copiez-la dans votre fichier `.env`

### Modèles disponibles

L'application supporte plusieurs modèles. Modifiez `GROQ_MODEL` dans `.env` :

- `mixtral-8x7b-32768` ⭐ **Recommandé** (meilleur rapport qualité/vitesse)
- `llama-2-70b-chat` (plus puissant, un peu plus lent)
- `gemma-7b-it` (plus léger, réponses rapides)

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `GROQ_API_KEY` | Clé API (obligatoire) | - |
| `GROQ_MODEL` | Modèle à utiliser | `mixtral-8x7b-32768` |
| `DEBUG` | Mode debug | `false` |

---

## Utilisation

### Workflow

1. **Importer un document** → Cliquez sur "Sélectionnez un fichier PDF ou DOCX"
2. **Analyser** → Cliquez sur "Lancer l'analyse"
3. **Répondre** → Saisissez votre réponse à la question affichée
4. **Soumettre** → Cliquez sur "Soumettre et obtenir la correction"
5. **Continuer** → Passez à la question suivante

### Conseils

- **Documents optimaux** : 5-50 pages avec du contenu pédagogique clair
- **Formats** : PDF ou DOCX (protégés par mot de passe non supportés)
- **Qualité** : Plus le document est structuré, meilleures les questions
- **Session** : Chaque session démarre avec un document frais

---

## Architecture

```
┌─────────────────────────────────────┐
│     Interface Streamlit             │
│   (Upload, Affichage Questions)     │
└──────────────┬──────────────────────┘
               │
        ┌──────▼──────┐
        │  Extraction │
        │  (PDF/DOCX) │
        └──────┬──────┘
               │
        ┌──────▼──────────────┐
        │ Segmentation Texte  │
        │ (RecursiveSplitter) │
        └──────┬──────────────┘
               │
        ┌──────▼──────────────────┐
        │  Génération Questions   │
        │  (LLM via API)          │
        └──────┬──────────────────┘
               │
        ┌──────▼──────────────────┐
        │  Évaluation Réponses    │
        │  (LLM + Scoring)        │
        └─────────────────────────┘
```

### Technologie

| Composant | Rôle |
|-----------|------|
| **Streamlit** | Framework web interactif |
| **LangChain** | Orchestration LLM et text processing |
| **API LLM** | Génération et évaluation automatiques |
| **pypdf** | Extraction de PDFs |
| **python-docx** | Traitement de fichiers Word |

---

## Dépannage

### "Clé API non configurée"
→ Créez un fichier `.env` et ajoutez votre `GROQ_API_KEY`

### "Le document ne contient pas de texte exploitable"
→ Vérifiez que le PDF n'est pas une image scannée (OCR nécessaire)

### Questions génériques ou de faible qualité
→ Utilisez un document avec du contenu pédagogique clair et structuré

### "Impossible de générer une autre question"
→ Le document n'a pas assez de contenu exploitable. Essayez un autre document.

### L'app est lente
→ Vérifiez votre connexion Internet (utilisée pour l'API)

---

## Contribuer

Les contributions sont les bienvenues ! 

1. **Fork** le projet
2. **Créez une branche** (`git checkout -b feature/VotreFonctionnalite`)
3. **Committez** vos changements (`git commit -m 'Add: Description'`)
4. **Poussez** (`git push origin feature/VotreFonctionnalite`)
5. **Ouvrez une Pull Request**

### Types de contributions

- 🐛 **Signaler un bug** → Issues
- 💡 **Proposer une amélioration** → Issues avec tag "enhancement"
- 🔧 **Améliorer le code** → Pull Requests
- 📝 **Améliorer la documentation** → PRs bienvenues

---

## Feuille de route

### Version 1.1 (Q4 2026)
- [ ] Support de formats supplémentaires (TXT, EPUB)
- [ ] Export des sessions (PDF, CSV)
- [ ] Historique des performances
- [ ] Sélection du modèle via UI

### Version 2.0 (2027)
- [ ] Mode multi-utilisateurs
- [ ] Statistiques d'apprentissage
- [ ] Authentification utilisateurs
- [ ] API REST pour intégration

---

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour les détails.

---

## Support

Besoin d'aide ?

- 📖 Consultez la [Documentation Complète](docs/) (si disponible)
- 🐛 Signalez un bug : [Créez une issue](https://github.com/hamzamachnaoui/Ai_quiz_interactif/issues)
- 💬 Discussions : [GitHub Discussions](https://github.com/hamzamachnaoui/Ai_quiz_interactif/discussions)

---

**Fait avec ❤️ pour les étudiants et les formateurs**

[🚀 Essayez l'app en ligne](https://aiquizinteractif-yixus6eyaappmvfcdgvrvs9.streamlit.app/) | [⭐ Star le projet](https://github.com/hamzamachnaoui/Ai_quiz_interactif) | [📧 Nous contacter](mailto:hamza@example.com) | [🔗 Portfolio](https://github.com/hamzamachnaoui)
