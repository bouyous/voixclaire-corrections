"""Dialogue de premier lancement - demande le prenom."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


FIRST_RUN_STYLE = """
QDialog {
    background-color: #1e1e2e;
}
QLabel {
    color: #cdd6f4;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#welcome {
    font-size: 28px;
    font-weight: bold;
    color: #89b4fa;
}
QLabel#desc {
    font-size: 15px;
    color: #a6adc8;
    line-height: 1.5;
}
QLineEdit {
    background-color: #313244;
    border: 2px solid #45475a;
    border-radius: 12px;
    padding: 16px 20px;
    color: #cdd6f4;
    font-size: 22px;
    font-family: 'Segoe UI', sans-serif;
}
QLineEdit:focus {
    border-color: #89b4fa;
}
QPushButton#start_btn {
    background-color: #a6e3a1;
    color: #1e1e2e;
    font-size: 18px;
    font-weight: bold;
    padding: 16px 40px;
    border-radius: 12px;
    border: none;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#start_btn:hover {
    background-color: #94e2d5;
}
QPushButton#start_btn:disabled {
    background-color: #45475a;
    color: #6c7086;
}
QComboBox {
    background-color: #313244;
    border: 2px solid #45475a;
    border-radius: 8px;
    padding: 10px 16px;
    color: #cdd6f4;
    font-size: 16px;
}
"""


class FirstRunDialog(QDialog):
    """Dialogue affiche au premier lancement pour entrer le prenom."""

    def __init__(self, existing_profiles: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.user_name = ""
        self.existing_profiles = existing_profiles or []
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("VoixClaire")
        self.setFixedSize(500, 420)
        self.setStyleSheet(FIRST_RUN_STYLE)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        # Bienvenue
        welcome = QLabel("VoixClaire")
        welcome.setObjectName("welcome")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome)

        desc = QLabel(
            "Bonjour ! Ce logiciel va apprendre a comprendre ta voix.\n"
            "Plus tu l'utilises, mieux il te comprendra."
        )
        desc.setObjectName("desc")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(10)

        # Choix: nouveau profil ou existant
        if self.existing_profiles:
            choose_label = QLabel("Choisis ton profil ou crees-en un nouveau :")
            choose_label.setStyleSheet("font-size: 14px; color: #cdd6f4;")
            layout.addWidget(choose_label)

            self.profile_combo = QComboBox()
            self.profile_combo.addItem("-- Nouveau profil --", "")
            for p in self.existing_profiles:
                self.profile_combo.addItem(p, p)
            self.profile_combo.currentIndexChanged.connect(self._on_profile_selected)
            layout.addWidget(self.profile_combo)
        else:
            self.profile_combo = None

        # Champ prenom
        name_label = QLabel("Comment tu t'appelles ?")
        name_label.setStyleSheet("font-size: 16px; color: #cdd6f4;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ton prenom...")
        self.name_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_input.textChanged.connect(self._on_name_changed)
        self.name_input.returnPressed.connect(self._on_start)
        layout.addWidget(self.name_input)

        layout.addSpacing(10)

        # Bouton demarrer
        self.btn_start = QPushButton("C'est parti !")
        self.btn_start.setObjectName("start_btn")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._on_start)
        layout.addWidget(self.btn_start, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

    def _on_profile_selected(self, index):
        if self.profile_combo:
            selected = self.profile_combo.currentData()
            if selected:
                self.name_input.setText(selected)
                self.name_input.setEnabled(False)
            else:
                self.name_input.clear()
                self.name_input.setEnabled(True)

    def _on_name_changed(self, text):
        self.btn_start.setEnabled(len(text.strip()) >= 1)

    def _on_start(self):
        name = self.name_input.text().strip()
        if name:
            # Nettoyer le nom pour en faire un identifiant
            self.user_name = name
            self.accept()
