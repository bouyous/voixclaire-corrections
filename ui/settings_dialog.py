"""Dialogue des parametres."""

import os
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QSpinBox, QCheckBox, QHBoxLayout,
)
from PyQt6.QtCore import Qt
from config import load_config, save_config, IS_PORTABLE
from audio_engine import AudioEngine


SETTINGS_STYLE = """
QDialog {
    background-color: #1e1e2e;
}
QLabel {
    color: #cdd6f4;
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}
QLabel#title {
    font-size: 22px;
    font-weight: bold;
    color: #89b4fa;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 20px;
    font-weight: bold;
    color: #89b4fa;
    font-family: 'Segoe UI', sans-serif;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
}
QComboBox {
    background-color: #313244;
    border: 2px solid #45475a;
    border-radius: 6px;
    padding: 8px 12px;
    color: #cdd6f4;
    font-size: 14px;
}
QSpinBox {
    background-color: #313244;
    border: 2px solid #45475a;
    border-radius: 6px;
    padding: 8px 12px;
    color: #cdd6f4;
    font-size: 14px;
}
QCheckBox {
    color: #cdd6f4;
    font-size: 14px;
    spacing: 8px;
}
QPushButton {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 10px 20px;
    color: #cdd6f4;
    font-size: 14px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}
QPushButton#save_btn {
    background-color: #a6e3a1;
    color: #1e1e2e;
    font-weight: bold;
    border: none;
}
"""


class SettingsDialog(QDialog):
    """Fenetre des parametres de VoixClaire."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VoixClaire - Parametres")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumWidth(480)
        self.setStyleSheet(SETTINGS_STYLE)
        self.config = load_config()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Parametres")
        title.setObjectName("title")
        layout.addWidget(title)

        # Profil
        profile_label = QLabel(f"Profil actuel : {self.config.get('user_name', '?')}")
        profile_label.setStyleSheet("color: #94e2d5; font-size: 15px;")
        layout.addWidget(profile_label)

        # --- Modele ---
        model_group = QGroupBox("Reconnaissance vocale")
        model_layout = QFormLayout(model_group)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText(self.config.get("whisper_model", "medium"))
        model_layout.addRow("Modele :", self.model_combo)

        info = QLabel(
            "tiny/base = rapide | small = leger | medium = recommande "
            "pour mieux comprendre | large-v3 = tres precis mais lent"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #a6adc8; font-size: 11px;")
        model_layout.addRow(info)

        self.beam_spin = QSpinBox()
        self.beam_spin.setRange(1, 10)
        self.beam_spin.setValue(self.config.get("beam_size", 3))
        model_layout.addRow("Precision (beam) :", self.beam_spin)

        layout.addWidget(model_group)

        # --- Micro ---
        audio_group = QGroupBox("Microphone")
        audio_layout = QFormLayout(audio_group)

        self.device_combo = QComboBox()
        self.device_combo.addItem("Par defaut", None)
        try:
            for dev in AudioEngine.list_devices():
                self.device_combo.addItem(dev["name"], dev["index"])
        except Exception:
            pass
        current = self.config.get("device_index")
        if current is not None:
            idx = self.device_combo.findData(current)
            if idx >= 0:
                self.device_combo.setCurrentIndex(idx)
        audio_layout.addRow("Micro :", self.device_combo)
        layout.addWidget(audio_group)

        # --- Comportement ---
        behavior_group = QGroupBox("Comportement")
        behavior_layout = QFormLayout(behavior_group)

        self.overlay_cb = QCheckBox("Afficher la popup de confirmation")
        self.overlay_cb.setChecked(self.config.get("show_overlay", True))
        behavior_layout.addRow(self.overlay_cb)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(0, 30)
        self.timeout_spin.setValue(self.config.get("overlay_timeout", 5))
        self.timeout_spin.setSuffix(" sec")
        behavior_layout.addRow("Delai avant ecriture auto :", self.timeout_spin)

        # Option demarrage automatique (uniquement en mode installe)
        if not IS_PORTABLE:
            self.startup_cb = QCheckBox("Lancer VoixClaire au demarrage de Windows")
            self.startup_cb.setChecked(self._is_startup_enabled())
            behavior_layout.addRow(self.startup_cb)
        else:
            self.startup_cb = None

        layout.addWidget(behavior_group)

        # Boutons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Annuler")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Enregistrer")
        btn_save.setObjectName("save_btn")
        btn_save.clicked.connect(self._save)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _save(self):
        self.config["whisper_model"] = self.model_combo.currentText()
        self.config["beam_size"] = self.beam_spin.value()
        self.config["device_index"] = self.device_combo.currentData()
        self.config["show_overlay"] = self.overlay_cb.isChecked()
        self.config["overlay_timeout"] = self.timeout_spin.value()
        save_config(self.config)

        # Gerer le demarrage automatique
        if self.startup_cb is not None:
            if self.startup_cb.isChecked():
                self._enable_startup()
            else:
                self._disable_startup()

        self.accept()

    # --- Demarrage automatique Windows ---

    @staticmethod
    def _startup_shortcut_path() -> Path:
        """Chemin du raccourci dans le dossier Demarrage de Windows."""
        startup_dir = Path(os.environ.get("APPDATA", "")) / \
            "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return startup_dir / "VoixClaire.lnk"

    @staticmethod
    def _is_startup_enabled() -> bool:
        return SettingsDialog._startup_shortcut_path().exists()

    @staticmethod
    def _enable_startup():
        """Cree un raccourci dans le dossier Demarrage."""
        install_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "VoixClaire"
        vbs_path = install_dir / "VoixClaire.vbs"
        icon_path = install_dir / "voixclaire.ico"
        shortcut_path = SettingsDialog._startup_shortcut_path()

        if not vbs_path.exists():
            return

        try:
            import subprocess
            ps_cmd = (
                f'$ws = New-Object -ComObject WScript.Shell; '
                f'$s = $ws.CreateShortcut("{shortcut_path}"); '
                f'$s.TargetPath = "wscript.exe"; '
                f'$s.Arguments = \'"{vbs_path}"\'; '
                f'$s.WorkingDirectory = "{install_dir}"; '
                f'$s.Description = "VoixClaire - Demarrage automatique"; '
            )
            if icon_path.exists():
                ps_cmd += f'$s.IconLocation = "{icon_path},0"; '
            ps_cmd += '$s.Save()'
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, timeout=10,
            )
        except Exception:
            pass

    @staticmethod
    def _disable_startup():
        """Supprime le raccourci du dossier Demarrage."""
        shortcut = SettingsDialog._startup_shortcut_path()
        try:
            if shortcut.exists():
                shortcut.unlink()
        except Exception:
            pass
