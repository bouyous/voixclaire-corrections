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

from config import (
    load_config, save_config, set_user_profile,
    list_local_profiles, APP_NAME, GITHUB_REPO, IS_PORTABLE,
)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    # Chercher un profil existant
    local_profiles = list_local_profiles()

    # Essayer de charger le dernier profil utilise
    # (on regarde s'il y a un config.json a la racine data/)
    last_user = ""
    config = load_config()
    last_user = config.get("user_name", "").strip()

    if last_user:
        # On a un profil sauvegarde, l'utiliser
        set_user_profile(last_user)
    else:
        # Premier lancement: demander le prenom
        # Aussi recuperer les profils GitHub si possible
        existing = list(local_profiles)
        try:
            from database import CorrectionDB
            from sync import GitHubSync
            db_temp = CorrectionDB()
            sync_temp = GitHubSync(GITHUB_REPO, db_temp, "temp")
            sync_temp.setup()
            remote_profiles = sync_temp.list_profiles()
            for p in remote_profiles:
                if p not in existing:
                    existing.append(p)
        except Exception:
            pass

        from ui.first_run import FirstRunDialog
        dialog = FirstRunDialog(existing)
        if dialog.exec():
            last_user = dialog.user_name
            set_user_profile(last_user)
            # Sauvegarder le profil choisi
            cfg = load_config()
            cfg["user_name"] = last_user
            save_config(cfg)
        else:
            sys.exit(0)

    # Lancer le controleur principal
    from ui.main_window import AppController
    controller = AppController(last_user)
    controller.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
