# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format se base sur [Keep a Changelog](https://keepachangelog.com/fr/),
et ce projet suit [Semantic Versioning](https://semver.org/lang/fr/).

## [1.0.0] - 2026-09-10

### Ajouté
- Génération automatique de questions de compréhension basée sur des documents PDF et DOCX
- Système de correction automatique avec score et feedback
- Interface Streamlit moderne avec thème personnalisé
- Extraction aléatoire d'extraits du document pour performance optimale
- Système de filtrage des questions pour éviter les questions sur la structure du document
- Prévention de la répétition de questions au sein d'une même session
- Support du caching Streamlit pour optimiser les performances
- Mise en page réactive avec animations CSS
- Intégration avec une API de modèle de langage pour la génération et la correction
- Documentation complète et guide de contribution

### Fonctionnalités
- ✅ Upload de documents (PDF, DOCX)
- ✅ Génération de questions avec contexte intelligent
- ✅ Correction des réponses avec score (0-10)
- ✅ Feedback détaillé et explicatif
- ✅ Interface intuitive et moderne
- ✅ Performance optimisée (< 5s par question)
- ✅ Questions uniques par session
- ✅ Génération assistée par modèle de langage avec configuration par API

## Versions futures envisagées

### [1.1.0] - Planifié
- [ ] Support de formats additionnels (TXT, EPUB)
- [ ] Export des sessions en PDF ou CSV
- [ ] Historique des performances
- [ ] Sélection du modèle IA via UI
- [ ] Ajustement de la difficulté des questions

### [2.0.0] - Planifié
- [ ] Mode multi-utilisateurs avec base de données
- [ ] Authentification des utilisateurs
- [ ] Statistiques et analytics
- [ ] Support du multi-langue
- [ ] API REST pour intégration externe

---

**Note** : Les versions futures ne sont pas confirmées et peuvent changer en fonction des contributions et des retours utilisateurs.
