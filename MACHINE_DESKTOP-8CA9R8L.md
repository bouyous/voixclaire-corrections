# Notes machine : DESKTOP-8CA9R8L (PC de Liam)

## Identité
- **Nom** : DESKTOP-8CA9R8L
- **OS** : Windows 10 Famille — 10.0.19045 build 19045
- **Utilisateur Windows** : liam (dossier C:\Users\liam0\)
- **Profil VoixClaire** : liam
- **VoixClaire version installée** : 1.1.1 (mis à jour 16/04/2026)

## Bugs rencontrés et corrigés

### 1. `updater.py` manquant
- **Log** : `[MAIN] Erreur mise a jour: No module named 'updater'`
- **Cause** : Ancien INSTALLER.bat ne copiait pas updater.py
- **Statut** : ✅ Corrigé en copiant updater.py dans app/

### 2. `Qt` non importé dans main_window.py
- **Symptôme** : Crash NameError au clic sur Historique/Mots appris
- **Cause** : Import manquant dans l'ancienne version
- **Statut** : ✅ Corrigé par mise à jour v1.1.1

### 3. Processus zombie
- **Symptôme** : `Mutex: last_error=183` — app "déjà lancée" mais invisible
- **Cause** : Instance crashée restait en mémoire
- **Statut** : ✅ Corrigé dans v1.1.1 (boîte de dialogue + kill automatique)

### 4. user_name vide au démarrage
- **Symptôme** : `[MAIN] Dernier utilisateur: ''`
- **Cause** : config.json racine vide, profil dans data/liam/config.json
- **Statut** : ✅ Corrigé dans v1.1.1 (auto-sélection profil unique)

## Installation

```
C:\Users\liam0\AppData\Local\VoixClaire\
  python\         Python 3.11.9 embarqué
  app\            Code VoixClaire v1.1.1
    ui\
  data\
    liam\         Profil de Liam (DB + config)
  models\         Modèle Whisper small
  sync_repo\      Clone git pour sync corrections
  VoixClaire.vbs  Lanceur sans fenêtre noire
  voixclaire.log  Log de lancement (consulter en cas de bug)
```

## Micros disponibles
- [0] Microsoft Sound Mapper - Input
- [1] Microphone (High Definition Audio Device) ← principal
- [4] Pilote de capture audio principal
- [5] Microphone (High Definition Audio Device)
- [9] Microphone (High Definition Audio Device)
- [11] Microphone (HD Audio Microphone)

## Commandes de dépannage

```batch
REM Voir le log
type %LOCALAPPDATA%\VoixClaire\voixclaire.log

REM Tuer VoixClaire
taskkill /F /IM pythonw.exe

REM Lancer avec erreurs visibles
%LOCALAPPDATA%\VoixClaire\python\python.exe %LOCALAPPDATA%\VoixClaire\app\main.py
```
