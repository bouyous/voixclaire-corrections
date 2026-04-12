"""VoixClaire - Point d'entree principal.

Reconnaissance vocale adaptative pour les personnes
ayant des difficultes d'elocution.
"""

import sys
import os

# Ajouter le repertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from config import load_config, save_config, APP_NAME, GITHUB_REPO
from sync import GitHubSync, _sanitize_name
from database import CorrectionDB


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    config = load_config()

    # Premier lancement ? Demander le prenom
    user_name = config.get("user_name", "").strip()
    if not user_name:
        # Essayer de lister les profils existants sur GitHub
        existing_profiles = []
        try:
            db = CorrectionDB()
            sync = GitHubSync(GITHUB_REPO, db, "temp")
            sync.setup()
            existing_profiles = sync.list_profiles()
        except Exception:
            pass

        from ui.first_run import FirstRunDialog
        dialog = FirstRunDialog(existing_profiles)
        if dialog.exec():
            user_name = dialog.user_name
        else:
            sys.exit(0)

    # Lancer le controleur principal
    from ui.main_window import AppController
    controller = AppController(user_name)
    controller.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
