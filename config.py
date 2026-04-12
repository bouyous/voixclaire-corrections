"""Configuration de VoixClaire."""

import os
import sys
import json
from pathlib import Path

APP_NAME = "VoixClaire"
APP_VERSION = "1.0.0"

# Determiner le repertoire de donnees:
# - Mode portable (cle USB): les donnees sont DANS le dossier de l'app
#   On detecte le mode portable si un dossier "python" existe a cote
# - Mode installe: les donnees vont dans %APPDATA%

def _find_app_root() -> Path:
    """Trouve la racine de l'application."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def _detect_data_dir() -> Path:
    """
    Detecte ou stocker les donnees.

    Mode portable (cle USB):
        VoixClaire_Portable/
            VoixClaire.lnk       <- seul fichier visible
            _engine/             <- cache
                python/
                app/
                data/
                    liam/
                        voixclaire.db

    Mode installe:
        %APPDATA%/VoixClaire/
    """
    app_root = _find_app_root()

    # Mode portable: chercher _engine/python ou python a cote/au-dessus
    portable_root = app_root.parent  # remonte de app/ vers _engine/
    engine_root = portable_root.parent  # remonte de _engine/ vers VoixClaire_Portable/

    if (portable_root / "python").exists():
        # Structure _engine/app/ et _engine/python/
        data_dir = portable_root / "data"
    elif (engine_root / "python").exists():
        data_dir = engine_root / "data"
    elif (app_root / "python").exists():
        data_dir = app_root / "data"
    else:
        # Mode installe classique
        data_dir = Path(os.environ.get("APPDATA", Path.home())) / "VoixClaire"

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


DATA_DIR = _detect_data_dir()
IS_PORTABLE = DATA_DIR.name == "data"

# Chemins (seront mis a jour avec le profil utilisateur)
DB_PATH = DATA_DIR / "voixclaire.db"
CONFIG_PATH = DATA_DIR / "config.json"
AUDIO_SAMPLES_DIR = DATA_DIR / "audio_samples"
AUDIO_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# Le cache du modele Whisper est toujours dans le dossier portable
# pour qu'il voyage avec la cle USB
if IS_PORTABLE:
    MODEL_CACHE_DIR = DATA_DIR.parent / "models"
else:
    MODEL_CACHE_DIR = DATA_DIR / "models"
MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# URL du depot GitHub pour les corrections partagees
GITHUB_REPO = "https://github.com/bouyous/voixclaire-corrections.git"

# Valeurs par defaut
DEFAULTS = {
    "whisper_model": "small",
    "language": "fr",
    "sample_rate": 16000,
    "channels": 1,
    "auto_inject": True,
    "show_overlay": True,
    "overlay_timeout": 5,
    "confidence_threshold": 0.6,
    "device_index": None,
    "beam_size": 3,
    "compute_type": "int8",
    "user_name": "",
    "bar_position": "top",
}


def set_user_profile(user_name: str):
    """
    Configure les chemins pour un profil utilisateur specifique.

    En mode portable, chaque profil a son propre sous-dossier:
        data/liam/voixclaire.db
        data/liam/config.json
    """
    global DB_PATH, CONFIG_PATH, AUDIO_SAMPLES_DIR

    if user_name:
        profile_dir = DATA_DIR / _sanitize(user_name)
        profile_dir.mkdir(parents=True, exist_ok=True)
        DB_PATH = profile_dir / "voixclaire.db"
        CONFIG_PATH = profile_dir / "config.json"
        AUDIO_SAMPLES_DIR = profile_dir / "audio_samples"
        AUDIO_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize(name: str) -> str:
    """Nom de dossier safe."""
    import re
    name = name.strip().lower()
    name = re.sub(r'[^a-z0-9_\-]', '_', name)
    return re.sub(r'_+', '_', name).strip('_') or "default"


def load_config() -> dict:
    """Charge la configuration depuis le fichier JSON."""
    config = DEFAULTS.copy()
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            config.update(user_config)
        except (json.JSONDecodeError, IOError):
            pass
    return config


def save_config(config: dict):
    """Sauvegarde la configuration."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def list_local_profiles() -> list[str]:
    """Liste les profils disponibles localement (sur la cle USB ou en local)."""
    profiles = []
    if DATA_DIR.exists():
        for d in DATA_DIR.iterdir():
            if d.is_dir() and (d / "voixclaire.db").exists():
                profiles.append(d.name)
    return profiles
