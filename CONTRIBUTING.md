# Guide de contribution

Merci d'être intéressé par la contribution à ce projet ! Voici comment vous pouvez aider.

## Comment contribuer

### Signaler un bug

1. Vérifiez que le bug n'a pas déjà été rapporté en parcourant les [issues](../../issues)
2. Ouvrez une nouvelle issue avec un titre descriptif
3. Décrivez le comportement attendu et le comportement actuel
4. Incluez des exemples de code ou des captures d'écran si pertinent
5. Indiquez votre environnement (OS, version Python, version Ollama)

### Proposer une amélioration

1. Ouvrez une issue avec le titre commençant par `[FEATURE]`
2. Décrivez clairement la fonctionnalité proposée et ses avantages
3. Expliquez comment cela améliorerait l'application

### Soumettre une Pull Request

1. **Fork le projet** et créez une branche pour votre fonctionnalité
   ```bash
   git checkout -b feature/ma-nouvelle-fonctionnalite
   ```

2. **Travaillez sur votre branche**
   - Respectez le style de code existant
   - Ajoutez des commentaires explicatifs si nécessaire
   - Testez votre code localement avec `streamlit run app.py`

3. **Committez vos changements** avec des messages clairs
   ```bash
   git commit -m "Add: Description claire de la fonctionnalité"
   ```

4. **Poussez votre branche** vers votre fork
   ```bash
   git push origin feature/ma-nouvelle-fonctionnalite
   ```

5. **Ouvrez une Pull Request**
   - Décrivez vos changements de manière claire
   - Référencez les issues associées (ex: `Fixes #123`)
   - Incluez des tests ou des captures d'écran si pertinent

## Standards de code

- **Python** : Suivez [PEP 8](https://pep8.org/)
- **Noms** : Utilisez des noms clairs et explicites en français ou en anglais (cohérent avec le codebase)
- **Commentaires** : Écrivez des commentaires en français pour rester cohérent avec le code existant
- **Fonctions** : Documentez les fonctions avec docstrings

Exemple :
```python
def ma_fonction(param1: str, param2: int) -> bool:
    """
    Fait quelque chose d'utile.
    
    Args:
        param1: Description du paramètre 1
        param2: Description du paramètre 2
    
    Returns:
        Résultat de l'opération
    """
    pass
```

## Processus de review

Avant qu'une PR soit acceptée :
1. Au moins une review positive est requise
2. Tous les tests doivent passer
3. Aucun conflit de merge
4. Le code respecte les standards du projet

## Questions ?

Ouvrez une discussion en créant une issue ou contactez le mainteneur du projet.

Merci pour votre contribution ! 🎉
