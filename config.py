"""Configuration de VoixClaire."""

import os
import json
from pathlib import Path

APP_NAME = "VoixClaire"
APP_VERSION = "1.0.0"

# Repertoire de donnees utilisateur
DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "VoixClaire"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "voixclaire.db"
CONFIG_PATH = DATA_DIR / "config.json"
AUDIO_SAMPLES_DIR = DATA_DIR / "audio_samples"
AUDIO_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
MODEL_CACHE_DIR = DATA_DIR / "models"
MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# URL du depot GitHub pour les corrections partagees
GITHUB_REPO = "https://github.com/bouyous/voixclaire-corrections.git"

# Valeurs par defaut
DEFAULTS = {
    "whisper_model": "small",       # small (~500Mo) ou medium (~1.5Go)
    "language": "fr",
    "sample_rate": 16000,
    "channels": 1,
    "auto_inject": True,            # Injecter automatiquement dans la fenetre active
    "show_overlay": True,           # Afficher l'overlay de confirmation
    "overlay_timeout": 5,           # Secondes avant injection automatique
    "confidence_threshold": 0.6,    # Seuil de confiance pour les corrections auto
    "device_index": None,           # None = micro par defaut
    "beam_size": 3,
    "compute_type": "int8",         # int8 pour CPU, float16 pour GPU
    "user_name": "",                # Nom du profil (ex: "Liam", "Jean-Pascal")
    "bar_position": "top",          # Position de la barre: "top" ou "bottom"
}


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
