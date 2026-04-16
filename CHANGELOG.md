# VoixClaire - Historique des versions

## v1.1.1 (2026-04-16)
- **Fix:** Import `Qt` manquant dans `main_window.py` — les boutons Historique et Mots appris ne s'ouvraient pas (NameError)

## v1.1.0 (2026-04-16)
### Stabilite
- Tous les dialogues (Historique, Dictionnaire, Parametres) sont maintenant **non-modaux** (`show()` au lieu de `exec()`) — plus de blocage avec bip d'erreur Windows
- Ajout `WindowStaysOnTopHint` + `WindowCloseButtonHint` sur tous les dialogues
- Protection `try/except` sur cancel recording, injection, ouverture dialogues
- Overlay: `clearFocus()` explicite a la fermeture

### Demarrage
- **Updater en thread daemon** — ne bloque plus le demarrage (DNS lent = freeze avant)
- **Logs diagnostiques** a chaque etape (`[MAIN] Init QApplication...`, etc.) dans `voixclaire.log`
- **Detection zombie** avec force-kill: si mutex deja pris, proposer de tuer les `pythonw.exe` zombies
- **Auto-selection profil unique** — plus de dialogue "premier lancement" inutile si un seul profil existe

### Updater
- **Fix URL critique**: les fichiers sont a la racine du repo GitHub, pas dans `voix_claire/`. L'updater disait TOUJOURS "Pas de version.json distant" avant ce fix.
- Timeouts reduits a 2s (au lieu de 3-5s)
- `urlretrieve` remplace par `urlopen(timeout=5) + read()` (urlretrieve ignorait les timeouts)
- Suppression du sync GitHub bloquant au premier lancement

### Historique
- HistoryDialog "Coller": ferme d'abord le dialogue, attend 200ms, PUIS colle
- HistoryDialog "Copier": utilise `pyperclip` au lieu de `_set_clipboard` (compatible Qt)

## v1.0.0 (2026-04-14)
### Fonctionnalites
- Reconnaissance vocale adaptative (faster-whisper, model "small", CPU int8)
- Barre flottante en haut de l'ecran avec micro, profils, statut
- Overlay de correction: modifier le texte avant collage, apprentissage automatique
- Injection de texte dans n'importe quelle fenetre (keybd_event + pyperclip)
- Suivi de la fenetre cible en arriere-plan (thread 300ms)
- Affichage "Sera colle dans: [nom fenetre]" dans l'overlay
- Historique des 4 dernieres dictees avec Copier/Coller
- Anti-double-clic sur le micro (1.5s lockout)
- Bouton "Annuler" rouge pendant l'enregistrement
- Boutons Minimiser et Fermer sur la barre
- Dictionnaire des mots appris
- Parametres (modele, micro, demarrage auto)
- Synchronisation des corrections via GitHub
- Protection single-instance via Windows Mutex (CreateMutexW)
- Crash log dans %LOCALAPPDATA%\VoixClaire\voixclaire.log
- Auto-update depuis GitHub a chaque lancement
- Distribution: installable (INSTALLER.bat) + portable USB (INSTALLER_USB.bat)
