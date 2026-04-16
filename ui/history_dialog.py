"""Historique des dernieres transcriptions avec possibilite de recoller."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer


HISTORY_STYLE = """
QDialog {
    background-color: #1e1e2e;
}
QLabel {
    color: #cdd6f4;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#title {
    font-size: 22px;
    font-weight: bold;
    color: #89b4fa;
}
QLabel#empty {
    font-size: 16px;
    color: #a6adc8;
    padding: 40px;
}
QLabel#entry_text {
    font-size: 16px;
    color: #cdd6f4;
    padding: 12px;
    background-color: #313244;
    border-radius: 8px;
}
QLabel#entry_time {
    font-size: 11px;
    color: #a6adc8;
}
QLabel#entry_status {
    font-size: 11px;
    color: #a6adc8;
    font-style: italic;
}
QPushButton#paste_btn {
    background-color: #a6e3a1;
    color: #1e1e2e;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton#paste_btn:hover {
    background-color: #94e2d5;
}
QPushButton#copy_btn {
    background-color: #89b4fa;
    color: #1e1e2e;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton#copy_btn:hover {
    background-color: #74c7ec;
}
QPushButton#close_btn {
    background-color: #45475a;
    color: #cdd6f4;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton#close_btn:hover {
    background-color: #585b70;
}
QFrame#separator {
    background-color: #45475a;
    max-height: 1px;
}
"""


class HistoryDialog(QDialog):
    """Affiche les 4 dernieres transcriptions avec bouton pour recoller."""

    paste_requested = pyqtSignal(str)  # texte a coller

    def __init__(self, history: list[dict], parent=None):
        """
        history: liste de dict avec cles:
            - text: str (texte final)
            - original: str (texte brut whisper)
            - timestamp: str
            - injected: bool (True si deja colle)
        """
        super().__init__(parent)
        self.setWindowTitle("VoixClaire - Historique")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumWidth(520)
        self.setMinimumHeight(300)
        self.setStyleSheet(HISTORY_STYLE)
        self.history = history
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Historique des dictees")
        title.setObjectName("title")
        layout.addWidget(title)

        if not self.history:
            empty = QLabel("Aucune dictee pour l'instant.\nParle dans le micro !")
            empty.setObjectName("empty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty)
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(12)

            for i, entry in enumerate(reversed(self.history)):
                frame = self._create_entry(entry, i + 1)
                container_layout.addWidget(frame)

            container_layout.addStretch()
            scroll.setWidget(container)
            layout.addWidget(scroll)

        # Bouton fermer
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("Fermer")
        btn_close.setObjectName("close_btn")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _create_entry(self, entry: dict, num: int) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("QWidget { background-color: #181825; border-radius: 10px; }")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # En-tete: numero + heure + statut
        header = QHBoxLayout()
        time_label = QLabel(f"#{num}  -  {entry.get('timestamp', '?')}")
        time_label.setObjectName("entry_time")
        header.addWidget(time_label)
        header.addStretch()

        status = entry.get("injected", False)
        status_label = QLabel("Colle" if status else "Non colle")
        status_label.setObjectName("entry_status")
        if not status:
            status_label.setStyleSheet("font-size: 11px; color: #f38ba8; font-weight: bold;")
        header.addWidget(status_label)
        layout.addLayout(header)

        # Texte
        text = entry.get("text", entry.get("original", ""))
        text_label = QLabel(text)
        text_label.setObjectName("entry_text")
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(text_label)

        # Boutons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_copy = QPushButton("Copier")
        btn_copy.setObjectName("copy_btn")
        btn_copy.clicked.connect(lambda checked, t=text: self._copy_text(t))
        btn_layout.addWidget(btn_copy)

        btn_paste = QPushButton("Coller dans la fenetre")
        btn_paste.setObjectName("paste_btn")
        btn_paste.clicked.connect(lambda checked, t=text: self._paste_text(t))
        btn_layout.addWidget(btn_paste)

        layout.addLayout(btn_layout)
        return widget

    def _copy_text(self, text: str):
        """Copie le texte dans le presse-papier."""
        try:
            import pyperclip
            pyperclip.copy(text)
        except Exception:
            try:
                from text_injector import _set_clipboard
                _set_clipboard(text)
            except Exception:
                pass
        self.setWindowTitle("VoixClaire - Copie !")
        QTimer.singleShot(1500, lambda: self.setWindowTitle("VoixClaire - Historique"))

    def _paste_text(self, text: str):
        """Ferme le dialogue et demande au controleur de coller."""
        self.close()
        # Emettre le signal APRES fermeture pour eviter les conflits de focus
        QTimer.singleShot(200, lambda: self.paste_requested.emit(text))
