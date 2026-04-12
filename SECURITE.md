# VoixClaire - Note de securite

Ce document est destine aux responsables informatiques (college, etablissement)
qui voudraient evaluer VoixClaire avant de l'autoriser sur un poste.

## Ce que fait le logiciel

1. **Capture audio** via le microphone (uniquement quand l'utilisateur clique)
2. **Transcription locale** via le modele Whisper (aucun envoi reseau)
3. **Injection de texte** dans la fenetre active via le presse-papier (Ctrl+V)
4. **Stockage local** des corrections dans une base SQLite sur la cle USB

## Ce que le logiciel ne fait PAS

- Il n'envoie AUCUN audio sur internet
- Il n'enregistre PAS en continu (uniquement sur action de l'utilisateur)
- Il ne capture PAS les frappes clavier (pas de keylogger)
- Il ne modifie PAS le systeme (pas d'installation, pas de registre)
- Il ne necessite PAS de droits administrateur
- Il n'ouvre PAS de port reseau
- Il ne telecharge PAS de code executable

## Acces reseau

Le seul acces reseau est la synchronisation Git (optionnelle) :
- Protocole : HTTPS vers github.com
- Donnees echangees : fichiers JSON contenant des paires de corrections
  (exemple : {"wrong_text": "fuit", "correct_text": "oui", "count": 5})
- Aucune donnee personnelle, aucun audio, aucun identifiant

Si le reseau est bloque ou filtre, le logiciel fonctionne
normalement en mode hors-ligne.

## Composants utilises

| Composant | Source | Usage |
|---|---|---|
| Python 3.11 embedded | python.org (signe PSF) | Interpreteur |
| faster-whisper | PyPI (open source) | Reconnaissance vocale locale |
| PyQt6 | PyPI (Qt Company) | Interface graphique |
| sounddevice | PyPI (open source) | Capture microphone |
| pynput | PyPI (open source) | Simulation Ctrl+V uniquement |
| SQLite | Integre a Python | Base de donnees locale |

## Mode portable (cle USB)

- Aucun fichier n'est ecrit sur le PC hote
- Tout est contenu dans le dossier de la cle USB
- Aucune trace apres retrait de la cle
- Pas de modification du registre Windows
- Pas d'installation de service ou pilote

## Verification

Le code source est integralement disponible et auditable :
https://github.com/bouyous/voixclaire-corrections

Les dependances Python sont toutes issues de PyPI et peuvent etre
verifiees avec `pip show <package>`.
