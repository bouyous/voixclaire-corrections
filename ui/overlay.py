"""Overlay flottant pour afficher/corriger la transcription."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QCursor


OVERLAY_STYLE = """
QWidget#overlay {
    background-color: #1e1e2e;
    border: 2px solid #89b4fa;
    border-radius: 16px;
}

QLabel {
    color: #cdd6f4;
    font-family: 'Segoe UI', sans-serif;
}

QLabel#overlay_title {
    font-size: 14px;
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

    L'utilisateur peut:
    - Modifier le texte puis "Corriger + Ecrire" pour apprendre
    - Cliquer "OK" pour ecrire tel quel
    - Echap ou "Annuler" pour annuler
    """

    text_validated = pyqtSignal(str, str)
    text_injected = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_text = ""
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("overlay")
        # Fenetre normale (pas Tool) pour accepter le focus proprement
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(OVERLAY_STYLE)
        self.setFixedWidth(500)
        # S'assurer que la fenetre accepte le focus
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Titre + croix fermer
        header = QHBoxLayout()
        title = QLabel("J'ai compris :")
        title.setObjectName("overlay_title")
        header.addWidget(title)
        header.addStretch()
        btn_close = QPushButton("X")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet(
            "QPushButton { background-color: #45475a; color: #cdd6f4; "
            "border-radius: 14px; font-size: 12px; font-weight: bold; border: none; }"
            "QPushButton:hover { background-color: #f38ba8; color: #1e1e2e; }"
        )
        btn_close.clicked.connect(self._on_cancel)
        header.addWidget(btn_close)
        layout.addLayout(header)

        # Zone de texte editable
        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("overlay_text")
        self.text_edit.setMaximumHeight(120)
        self.text_edit.setFont(QFont("Segoe UI", 16))
        self.text_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_edit)

        # Indication
        self.hint = QLabel("")
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

    def show_transcription(self, text: str, bar_geometry=None):
        """Affiche la transcription pres de la barre flottante.

        bar_geometry: QRect de la barre, pour savoir ou se placer.
        """
        self.original_text = text

        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(text)
        self.text_edit.blockSignals(False)

        self.btn_correct.setVisible(False)
        self.hint.setText("Clique dans le texte pour le corriger, ou clique OK")
        self.hint.setStyleSheet("font-size: 11px; color: #a6adc8;")

        # Positionner la popup
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2

        if bar_geometry:
            bar_bottom = bar_geometry.y() + bar_geometry.height()
            bar_top = bar_geometry.y()
            screen_mid = screen.height() // 2

            if bar_top > screen_mid:
                # Barre en bas de l'ecran → popup AU-DESSUS
                self.adjustSize()
                y = bar_top - self.height() - 10
            else:
                # Barre en haut → popup EN-DESSOUS
                y = bar_bottom + 10
        else:
            y = 70

        self.move(x, max(0, y))

        self.show()
        self.raise_()
        self.activateWindow()

        # Mettre le focus sur le texte apres un petit delai
        # (pour que la fenetre soit bien affichee avant)
        QTimer.singleShot(100, self._focus_text)

    def _focus_text(self):
        """Donne le focus au champ texte."""
        self.activateWindow()
        self.text_edit.setFocus(Qt.FocusReason.OtherFocusReason)
        # Placer le curseur a la fin (pas de selectAll pour eviter
        # que le texte disparaisse quand on clique)
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)

    def _on_text_changed(self):
        current = self.text_edit.toPlainText().strip()
        modified = current != self.original_text
        self.btn_correct.setVisible(modified)
        if modified:
            self.hint.setText("Tu as corrige le texte - clique 'Corriger + Ecrire' pour que j'apprenne !")
            self.hint.setStyleSheet("font-size: 11px; color: #a6e3a1; font-weight: bold;")
        else:
            self.hint.setText("Clique dans le texte pour le corriger, ou clique OK")
            self.hint.setStyleSheet("font-size: 11px; color: #a6adc8;")

    def _on_inject(self):
        text = self.text_edit.toPlainText().strip()
        if text != self.original_text:
            self.text_validated.emit(self.original_text, text)
        self.text_injected.emit(text)
        self.hide()

    def _on_correct(self):
        corrected = self.text_edit.toPlainText().strip()
        self.text_validated.emit(self.original_text, corrected)
        self.text_injected.emit(corrected)
        self.hide()

    def _on_cancel(self):
        self.cancelled.emit()
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._on_cancel()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Entree = valider (seulement si pas Shift+Entree pour saut de ligne)
            if event.modifiers() != Qt.KeyboardModifier.ShiftModifier:
                if self.btn_correct.isVisible():
                    self._on_correct()
                else:
                    self._on_inject()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)
