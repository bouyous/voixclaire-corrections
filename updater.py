"""Mise a jour automatique du code VoixClaire depuis GitHub."""

import os
import sys
import json
import urllib.request
import shutil
from pathlib import Path

# URL brutes des fichiers sur GitHub (branche main)
GITHUB_RAW = "https://raw.githubusercontent.com/bouyous/voixclaire-corrections/main"

# Liste des fichiers a mettre a jour
APP_FILES = [
    "main.py",
    "config.py",
    "database.py",
    "audio_engine.py",
    "transcriber.py",
    "adaptive_learner.py",
    "text_injector.py",
    "sync.py",
    "updater.py",
    "verifier_integrite.py",
]

UI_FILES = [
    "ui/__init__.py",
    "ui/floating_bar.py",
    "ui/overlay.py",
    "ui/main_window.py",
    "ui/dictionary_dialog.py",
    "ui/settings_dialog.py",
    "ui/first_run.py",
    "ui/history_dialog.py",
]

ALL_FILES = APP_FILES + UI_FILES

# Fichier local qui stocke le hash de la derniere version
VERSION_FILE = "version.json"


def _has_internet() -> bool:
    """Verifie si GitHub est accessible."""
    try:
        urllib.request.urlopen("https://raw.githubusercontent.com", timeout=2)
        return True
    except Exception:
        return False


def _get_remote_version() -> dict:
    """Recupere le fichier version.json depuis GitHub."""
    try:
        url = f"{GITHUB_RAW}/voix_claire/{VERSION_FILE}"
        req = urllib.request.urlopen(url, timeout=2)
        return json.loads(req.read().decode("utf-8"))
    except Exception:
        return {}


def _get_local_version(app_dir: Path) -> dict:
    """Lit le fichier version.json local."""
    version_path = app_dir / VERSION_FILE
    if version_path.exists():
        try:
            return json.loads(version_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _download_file(filename: str, dest: Path) -> bool:
    """Telecharge un fichier depuis GitHub."""
    url = f"{GITHUB_RAW}/voix_claire/{filename}"
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        # urlretrieve sans timeout peut bloquer - utiliser urlopen avec timeout
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = resp.read()
        dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"[UPDATE] Echec telechargement {filename}: {e}", flush=True)
        return False


def check_and_update(app_dir: str | Path, callback=None) -> str:
    """
    Verifie et met a jour le code depuis GitHub.

    Args:
        app_dir: chemin du dossier app/ contenant le code
        callback: fonction(message: str) pour informer l'utilisateur

    Returns:
        "updated" si mis a jour, "current" si deja a jour, "offline" si pas de reseau
    """
    app_dir = Path(app_dir)

    if not _has_internet():
        if callback:
            callback("Pas de connexion - demarrage hors ligne")
        print("[UPDATE] Pas de connexion internet", flush=True)
        return "offline"

    if callback:
        callback("Verification des mises a jour...")

    remote_version = _get_remote_version()
    if not remote_version:
        print("[UPDATE] Pas de version.json distant", flush=True)
        if callback:
            callback("Pas de mise a jour disponible")
        return "current"

    local_version = _get_local_version(app_dir)

    remote_v = remote_version.get("version", "0")
    local_v = local_version.get("version", "0")

    print(f"[UPDATE] Version locale: {local_v}, distante: {remote_v}", flush=True)

    if remote_v == local_v:
        if callback:
            callback("Logiciel a jour")
        return "current"

    # Mise a jour necessaire
    if callback:
        callback(f"Mise a jour v{remote_v}...")
    print(f"[UPDATE] Mise a jour vers v{remote_v}", flush=True)

    updated = 0
    failed = 0
    for filename in ALL_FILES:
        dest = app_dir / filename
        if _download_file(filename, dest):
            updated += 1
        else:
            failed += 1

    # Sauver la nouvelle version
    (app_dir / VERSION_FILE).write_text(
        json.dumps(remote_version, indent=2),
        encoding="utf-8",
    )

    msg = f"Mis a jour ! ({updated} fichiers)"
    if failed:
        msg += f" ({failed} echecs)"
    if callback:
        callback(msg)
    print(f"[UPDATE] {msg}", flush=True)

    return "updated"
