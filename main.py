"""VoixClaire - Point d'entree principal.

Reconnaissance vocale adaptative pour les personnes
ayant des difficultes d'elocution.
"""

import sys
import os
import ctypes
import threading
import traceback
from datetime import datetime
from pathlib import Path

# Ajouter le repertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _setup_crash_log():
    """Redirige les erreurs vers un fichier log pour debugger."""
    log_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "VoixClaire"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "voixclaire.log"
    try:
        f = open(log_file, "a", encoding="utf-8")
        f.write(f"\n--- Lancement {datetime.now().isoformat()} ---\n")
        f.flush()
        sys.stderr = f
        sys.stdout = f
    except Exception:
        pass


_setup_crash_log()


def _log(msg):
    print(f"[MAIN] {msg}", flush=True)


_log("Imports Qt...")
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QTimer

_log("Imports config...")
from config import (
    load_config, save_config, set_user_profile,
    list_local_profiles, APP_NAME, GITHUB_REPO, IS_PORTABLE,
)


def _kill_previous_instances():
    """Force la fermeture des processus pythonw.exe zombies de VoixClaire."""
    try:
        import subprocess
        my_pid = os.getpid()
        # Lister les pythonw.exe avec leur ligne de commande
        result = subprocess.run(
            ["wmic", "process", "where", "name='pythonw.exe'",
             "get", "processid,commandline", "/format:csv"],
            capture_output=True, text=True, timeout=5,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
        killed = 0
        for line in result.stdout.splitlines():
            if "voix_claire" in line.lower() or "voixclaire" in line.lower():
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    try:
                        pid = int(parts[-1])
                        if pid != my_pid:
                            subprocess.run(
                                ["taskkill", "/F", "/PID", str(pid)],
                                capture_output=True, timeout=3,
                                creationflags=0x08000000,
                            )
                            killed += 1
                    except (ValueError, subprocess.SubprocessError):
                        pass
        _log(f"Zombies tues: {killed}")
        return killed
    except Exception as e:
        _log(f"Erreur kill zombies: {e}")
        return 0


def main():
    try:
        _main_inner()
    except Exception as e:
        print(f"ERREUR FATALE: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)


def _main_inner():
    _log("Init QApplication...")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    # Protection anti-double-lancement via mutex Windows
    _log("Verification mutex...")
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, True, "VoixClaire_SingleInstance")
    last_error = kernel32.GetLastError()
    _log(f"Mutex: last_error={last_error}")
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        _log("Deja lance - proposer de forcer l'arret.")
        reply = QMessageBox.question(
            None, APP_NAME,
            "VoixClaire semble deja lance.\n\n"
            "Si tu vois l'icone en bas a droite, clique sur OUI pour annuler.\n\n"
            "Si tu ne vois rien (logiciel bloque), clique sur NON pour "
            "forcer l'arret et redemarrer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            sys.exit(0)
        # Forcer l'arret du zombie
        _log("Kill zombies demande par utilisateur")
        # Liberer notre mutex avant de tuer
        kernel32.ReleaseMutex(mutex)
        kernel32.CloseHandle(mutex)
        _kill_previous_instances()
        # Attendre un peu puis recreer le mutex
        import time
        time.sleep(1)
        mutex = kernel32.CreateMutexW(None, True, "VoixClaire_SingleInstance")
        last_error = kernel32.GetLastError()
        _log(f"Mutex apres kill: last_error={last_error}")
        if last_error == 183:
            QMessageBox.warning(
                None, APP_NAME,
                "Impossible de liberer VoixClaire.\n"
                "Redemarre l'ordinateur et reessaie.",
            )
            sys.exit(1)

    _log("Demarrage...")

    # Mise a jour en arriere-plan, NON-BLOQUANTE
    def _bg_update():
        try:
            from updater import check_and_update
            app_dir = os.path.dirname(os.path.abspath(__file__))
            check_and_update(app_dir)
        except Exception as e:
            _log(f"Erreur mise a jour: {e}")

    threading.Thread(target=_bg_update, daemon=True).start()
    _log("Updater lance en background")

    # Chercher un profil existant
    _log("Liste profils locaux...")
    local_profiles = list_local_profiles()
    _log(f"Profils locaux: {len(local_profiles)}")

    _log("Lecture config...")
    config = load_config()
    last_user = config.get("user_name", "").strip()
    _log(f"Dernier utilisateur: '{last_user}'")

    # Si pas de user_name en config mais un seul profil local, l'utiliser
    if not last_user and len(local_profiles) == 1:
        last_user = local_profiles[0]
        _log(f"Auto-selection unique profil: '{last_user}'")
        config["user_name"] = last_user
        try:
            save_config(config)
        except Exception as e:
            _log(f"Save config failed: {e}")

    if last_user:
        set_user_profile(last_user)
    else:
        # Premier lancement: demander le prenom
        _log("Premier lancement - dialog")
        existing = list(local_profiles)
        # PAS de sync GitHub bloquante au premier lancement
        from ui.first_run import FirstRunDialog
        dialog = FirstRunDialog(existing)
        if dialog.exec():
            last_user = dialog.user_name
            set_user_profile(last_user)
            cfg = load_config()
            cfg["user_name"] = last_user
            save_config(cfg)
        else:
            sys.exit(0)

    # Lancer le controleur principal
    _log("Chargement controleur...")
    from ui.main_window import AppController
    _log(f"Init AppController pour '{last_user}'...")
    controller = AppController(last_user)
    _log("Start controleur...")
    controller.start()
    _log("Entree event loop")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
