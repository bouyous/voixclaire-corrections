# VoixClaire

**Reconnaissance vocale adaptative pour les personnes ayant des difficultes d'elocution.**

VoixClaire est un logiciel de dictee vocale qui **apprend** a comprendre la voix de chaque utilisateur. Plus on l'utilise, mieux il comprend.

## Comment ca marche

1. On lance le logiciel (double-clic sur `VoixClaire.bat`)
2. Au premier lancement, on entre son prenom (ex: "Liam")
3. Une petite barre apparait en haut de l'ecran avec un bouton micro
4. On clique sur le micro, on parle, on reclique pour arreter
5. Le texte reconnu apparait dans une bulle. On peut le corriger si besoin
6. Le texte est ecrit automatiquement dans la fenetre active (Word, navigateur, etc.)

**L'apprentissage** : si le logiciel comprend "fuit" au lieu de "oui", on corrige dans la bulle. VoixClaire apprend la correction, mais les petits mots ambigus comme "je", "tu", "jeu" ne sont appliques automatiquement qu'apres plusieurs confirmations pour eviter les remplacements en boucle.

**Correction vocale** : apres une mauvaise transcription, on peut aussi redicter une correction en disant par exemple : "stop, tu ne m'as pas compris, je voulais dire ...".

**Entrainement guide** : au premier demarrage d'un profil, VoixClaire propose quelques phrases cles a lire. On peut aussi relancer cet entrainement depuis le bouton `Entrainement` de la barre.

## Installation portable (sans droits admin)

**Aucune installation necessaire.** Le dossier fonctionne tel quel sur n'importe quel PC Windows 64 bits avec un microphone.

### Preparer le dossier portable

Sur un PC ou vous avez les droits (maison par exemple) :

1. Installer Python 3.11+ depuis https://www.python.org/downloads/
2. Ouvrir un terminal dans le dossier du projet
3. Lancer `build_portable.bat`
4. Le dossier `VoixClaire_Portable` est cree (~2-3 Go)

### Creer un .exe

Pour generer un executable Windows direct :

1. Ouvrir un terminal dans le dossier du projet
2. Lancer `build_release.bat`
3. Recuperer `dist\VoixClaire.exe`

Le modele vocal par defaut est maintenant `medium` pour privilegier la comprehension. Le premier lancement peut donc telecharger un modele plus gros.

### Utiliser sur un PC (college, maison, etc.)

1. Copier le dossier `VoixClaire_Portable` sur une cle USB ou un partage reseau
2. Double-cliquer sur `VoixClaire.bat`
3. C'est tout !

- Pas d'installation requise
- Pas de droits administrateur
- Pas d'alerte antivirus (Python est signe par python.org)
- Fonctionne sur Windows 10 et 11

## Profils utilisateur

Chaque personne a son propre profil d'apprentissage. Au premier lancement, on choisit son prenom ou on en cree un nouveau. Les corrections sont enregistrees par profil.

Les profils sont synchronises via GitHub entre tous les postes, donc les corrections apprises a la maison fonctionnent aussi au college.

## Configuration minimum

- Windows 10 ou 11 (64 bits)
- 4 coeurs CPU minimum
- 4 Go de RAM
- Un microphone
- ~3 Go d'espace disque

## Structure du depot

```
VoixClaire_Portable/
  VoixClaire.bat          <- Double-clic pour lancer
  python/                 <- Python embarque (pas besoin d'installer)
  app/                    <- Code source de VoixClaire
```

Les corrections apprises sont stockees dans `%APPDATA%\VoixClaire\` sur chaque poste.

## Licence

Logiciel libre, usage educatif et personnel.
