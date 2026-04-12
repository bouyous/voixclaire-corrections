"""Overlay flottant pour afficher/corriger la transcription."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QCursor


OVERLAY_STYLE = """
QWidget#overlay {
    background-color: rgba(30, 30, 46, 245);
    border: 2px solid #89b4fa;
    border-radius: 16px;
}

QLabel {
    color: #cdd6f4;
    font-family: 'Segoe UI', sans-serif;
}

QLabel#overlay_title {
    font-size: 12px;
    color: #89b4fa;
    font-weight: bold;
}

QLabel#hint_label {
    font-size: 11px;
    color: #a6adc8;
}

QTextEdit#overlay_text {
    background-color: #313244;
    border: 2px solid #45475a;
    border-radius: 10px;
    padding: 10px;
    color: #cdd6f4;
    font-size: 18px;
    font-family: 'Segoe UI', sans-serif;
    selection-background-color: #89b4fa;
}

QTextEdit#overlay_text:focus {
    border-color: #89b4fa;
}

QPushButton {
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 20px;
    border-radius: 10px;
    border: none;
}

QPushButton#btn_ok {
    background-color: #a6e3a1;
    color: #1e1e2e;
}

QPushButton#btn_ok:hover {
    background-color: #94e2d5;
}

QPushButton#btn_correct {
    background-color: #89b4fa;
    color: #1e1e2e;
}

QPushButton#btn_correct:hover {
    background-color: #74c7ec;
}

QPushButton#btn_cancel {
    background-color: #45475a;
    color: #cdd6f4;
}

QPushButton#btn_cancel:hover {
    background-color: #585b70;
}
"""


class TranscriptionOverlay(QWidget):
    """
    Popup qui apparait apres une dictee.

    Affiche le texte reconnu. L'utilisateur peut:
    - Appuyer Entree ou cliquer "OK" → injecte le texte tel quel
    - Modifier le texte puis "Corriger" → apprend la correction + injecte
    - Echap ou "Annuler" → annule
    """

    text_validated = pyqtSignal(str, str)   # (original, corrected)
    text_injected = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_text = ""
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._on_auto_inject)
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setStyleSheet(OVERLAY_STYLE)
        self.setFixedWidth(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Titre
        title = QLabel("J'ai compris :")
        title.setObjectName("overlay_title")
        layout.addWidget(title)

        # Zone de texte
        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("overlay_text")
        self.text_edit.setMaximumHeight(120)
        self.text_edit.setFont(QFont("Segoe UI", 16))
        self.text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_edit)

        # Indication
        self.hint = QLabel("Modifie le texte si c'est pas bon, puis clique 'Corriger'")
        self.hint.setObjectName("hint_label")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        # Boutons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_ok = QPushButton("OK - Ecrire")
        self.btn_ok.setObjectName("btn_ok")
        self.btn_ok.clicked.connect(self._on_inject)

        self.btn_correct = QPushButton("Corriger + Ecrire")
        self.btn_correct.setObjectName("btn_correct")
        self.btn_correct.clicked.connect(self._on_correct)
        self.btn_correct.setVisible(False)

        self.btn_cancel = QPushButton("Annuler")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.clicked.connect(self._on_cancel)

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_correct)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def show_transcription(self, text: str, auto_inject_seconds: int = 0):
        """Affiche la transcription dans l'overlay."""
        self.original_text = text
        self.text_edit.setPlainText(text)
        self.btn_correct.setVisible(False)
        self.hint.setText("C'est bon ? Appuie sur Entree ou clique OK")

        # Centrer sous la barre flottante
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        self.move(x, 70)

        self.show()
        self.raise_()
        self.text_edit.setFocus()
        self.text_edit.selectAll()

        if auto_inject_seconds > 0:
            self._auto_timer.start(auto_inject_seconds * 1000)

    def _on_text_changed(self):
        current = self.text_edit.toPlainText().strip()
        modified = current != self.original_text
        self.btn_correct.setVisible(modified)
        if modified:
            self.hint.setText("Tu as corrige le texte - clique 'Corriger' pour que j'apprenne !")
            self.hint.setStyleSheet("font-size: 11px; color: #a6e3a1; font-weight: bold;")
        else:
            self.hint.setText("C'est bon ? Appuie sur Entree ou clique OK")
            self.hint.setStyleSheet("font-size: 11px; color: #a6adc8;")
        self._auto_timer.stop()

    def _on_inject(self):
        self._auto_timer.stop()
        text = self.text_edit.toPlainText().strip()
        # Si le texte a ete modifie, apprendre quand meme
        if text != self.original_text:
            self.text_validated.emit(self.original_text, text)
        self.text_injected.emit(text)
        self.hide()

    def _on_correct(self):
        self._auto_timer.stop()
        corrected = self.text_edit.toPlainText().strip()
        self.text_validated.emit(self.original_text, corrected)
        self.text_injected.emit(corrected)
        self.hide()

    def _on_auto_inject(self):
        text = self.text_edit.toPlainText().strip()
        self.text_injected.emit(text)
        self.hide()

    def _on_cancel(self):
        self._auto_timer.stop()
        self.cancelled.emit()
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            if self.btn_correct.isVisible():
                self._on_correct()
            else:
                self._on_inject()
        elif event.key() == Qt.Key.Key_Escape:
            self._on_cancel()
        else:
            super().keyPressEvent(event)
