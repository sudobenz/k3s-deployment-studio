# Installation et lancement sous Windows

## Prérequis

- Windows 10/11 64 bits.
- Python 3.11 ou supérieur. Le lanceur tente de détecter `py`, `python` ou `python3`.
- Si Python est absent, `packaging/launch-windows.ps1` propose une installation utilisateur de Python 3.12 via `winget` (aucun droit administrateur n'est normalement requis).
- Terraform doit être installé et accessible dans `PATH` pour utiliser le backend Proxmox.
- Ansible s'exécute dans WSL2. Le MVP ne transforme pas automatiquement les commandes Windows en commandes WSL : utiliser le wrapper/documentation Ansible fournis.

## Démarrage

Depuis la racine du projet, ouvrir PowerShell :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\packaging\launch-windows.ps1
```

Le script :

1. recherche un Python 3.11+ sans imposer une version mineure précise ;
2. propose `winget install Python.Python.3.12` si aucun interpréteur adapté n'est trouvé ;
3. crée `.venv` dans le dossier du projet ;
4. installe `requirements.txt` dans cet environnement isolé ;
5. lance l'application avec `.venv\Scripts\python.exe`.

Si Python vient d'être installé et n'est pas détecté, fermer PowerShell, ouvrir une nouvelle session et relancer le script. Installation manuelle possible depuis https://www.python.org/downloads/windows/ (activer l'ajout au PATH).

## Dépannage

- Vérifier `py -0p`, `python --version` et `where.exe python`.
- Une entrée `python.exe` pointant vers un alias Microsoft Store n'est pas un interpréteur utilisable : installer Python depuis python.org ou winget.
- Pour reconstruire l'environnement : supprimer `.venv`, puis relancer le script.
