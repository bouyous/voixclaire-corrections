"""Fenetre d'entrainement guide pour apprendre la voix de l'utilisateur."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QListWidget, QListWidgetItem, QProgressBar,
)
from PyQt6.QtCore import Qt, pyqtSignal


TRAINING_PHRASES = [
    "Bonjour, je m'appelle Liam.",
    "Je veux boire de l'eau.",
    "Je voudrais jouer maintenant.",
    "Tu peux m'aider s'il te plait ?",
    "J'ai fini mon travail.",
    "Je ne comprends pas.",
    "Oui, je suis d'accord.",
    "Non, je ne veux pas.",
    "Aujourd'hui je vais bien.",
    "Stop, tu ne m'as pas compris, je voulais dire bonjour.",
]


TRAINING_STYLE = """
QDialog { background-color: #1e1e2e; color: #cdd6f4; }
QLabel { color: #cdd6f4; font-family: 'Segoe UI', sans-serif; }
QLabel#title { font-size: 22px; font-weight: bold; color: #89b4fa; }
QLabel#phrase {
    background-color: #313244; border: 2px solid #89b4fa;
    border-radius: 8px; padding: 14px; font-size: 22px;
}
QLabel#hint { color: #a6adc8; font-size: 12px; }
QListWidget {
    background-color: #181825; border: 1px solid #45475a;
    border-radius: 8px; color: #cdd6f4; font-size: 13px;
}
QListWidget::item { padding: 8px; }
QListWidget::item:selected { background-color: #313244; color: #89b4fa; }
QTextEdit {
    background-color: #313244; border: 1px solid #45475a;
    border-radius: 8px; padding: 10px; color: #cdd6f4;
    font-size: 16px; font-family: 'Segoe UI', sans-serif;
}
QPushButton {
    background-color: #313244; border: 1px solid #45475a;
    border-radius: 8px; padding: 10px 16px; color: #cdd6f4;
    font-size: 13px; font-weight: bold;
}
QPushButton:hover { background-color: #45475a; }
QPushButton#record_btn { background-color: #a6e3a1; color: #1e1e2e; border: none; }
QPushButton#record_btn[recording="true"] { background-color: #f38ba8; }
QPushButton#save_btn { background-color: #89b4fa; color: #1e1e2e; border: none; }
QPushButton#done_btn { background-color: #a6e3a1; color: #1e1e2e; border: none; }
QProgressBar {
    background-color: #313244; border: none; border-radius: 6px;
    color: #cdd6f4; text-align: center; height: 12px;
}
QProgressBar::chunk { background-color: #a6e3a1; border-radius: 6px; }
"""


class TrainingDialog(QDialog):
    """Guide l'utilisateur dans quelques phrases d'apprentissage."""

    record_requested = pyqtSignal(str)
    save_requested = pyqtSignal(str, str)
    completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recognized_text = ""
        self._recording = False
        self.setWindowTitle("VoixClaire - Entrainement")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(760, 560)
        self.setStyleSheet(TRAINING_STYLE)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        title = QLabel("Entrainement de la voix")
        title.setObjectName("title")
        layout.addWidget(title)

        hint = QLabel(
            "Lis une phrase, arrete l'enregistrement, corrige si besoin, puis valide."
        )
        hint.setObjectName("hint")
        layout.addWidget(hint)

        self.progress = QProgressBar()
        self.progress.setRange(0, len(TRAINING_PHRASES))
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        main_row = QHBoxLayout()
        main_row.setSpacing(14)

        self.list_widget = QListWidget()
        for phrase in TRAINING_PHRASES:
            self.list_widget.addItem(QListWidgetItem(phrase))
        self.list_widget.currentRowChanged.connect(self._on_phrase_changed)
        main_row.addWidget(self.list_widget, 1)

        right = QVBoxLayout()
        right.setSpacing(10)

        self.phrase_label = QLabel("")
        self.phrase_label.setObjectName("phrase")
        self.phrase_label.setWordWrap(True)
        right.addWidget(self.phrase_label)

        self.status_label = QLabel("Clique sur Parler pour commencer.")
        self.status_label.setObjectName("hint")
        self.status_label.setWordWrap(True)
        right.addWidget(self.status_label)

        self.recognized_edit = QTextEdit()
        self.recognized_edit.setPlaceholderText("Ce que VoixClaire a compris apparaitra ici.")
        self.recognized_edit.setMaximumHeight(100)
        right.addWidget(QLabel("VoixClaire a compris :"))
        right.addWidget(self.recognized_edit)

        self.corrected_edit = QTextEdit()
        self.corrected_edit.setPlaceholderText("Phrase correcte a apprendre.")
        self.corrected_edit.setMaximumHeight(100)
        right.addWidget(QLabel("Phrase correcte :"))
        right.addWidget(self.corrected_edit)

        buttons = QHBoxLayout()
        self.record_btn = QPushButton("Parler")
        self.record_btn.setObjectName("record_btn")
        self.record_btn.setProperty("recording", "false")
        self.record_btn.clicked.connect(self._on_record_clicked)
        buttons.addWidget(self.record_btn)

        self.save_btn = QPushButton("Valider cette phrase")
        self.save_btn.setObjectName("save_btn")
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.save_btn.setEnabled(False)
        buttons.addWidget(self.save_btn)

        right.addLayout(buttons)
        main_row.addLayout(right, 2)
        layout.addLayout(main_row)

        bottom = QHBoxLayout()
        bottom.addStretch()
        skip_btn = QPushButton("Passer")
        skip_btn.clicked.connect(self._next_phrase)
        bottom.addWidget(skip_btn)

        done_btn = QPushButton("Terminer")
        done_btn.setObjectName("done_btn")
        done_btn.clicked.connect(self._on_done)
        bottom.addWidget(done_btn)
        layout.addLayout(bottom)

        self.list_widget.setCurrentRow(0)

    @property
    def current_phrase(self) -> str:
        item = self.list_widget.currentItem()
        return item.text() if item else ""

    def _on_phrase_changed(self, row: int):
        phrase = self.current_phrase
        self.phrase_label.setText(phrase)
        self.corrected_edit.setPlainText(phrase)
        self.recognized_edit.clear()
        self._recognized_text = ""
        self.save_btn.setEnabled(False)
        self.status_label.setText("Clique sur Parler, puis lis la phrase.")

    def _on_record_clicked(self):
        if self.current_phrase:
            self.record_requested.emit(self.current_phrase)

    def recording_started(self):
        self._recording = True
        self.record_btn.setText("Arreter")
        self.record_btn.setProperty("recording", "true")
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)
        self.status_label.setText("Je t'ecoute...")
        self.save_btn.setEnabled(False)

    def recording_stopped(self):
        self._recording = False
        self.record_btn.setText("Parler")
        self.record_btn.setProperty("recording", "false")
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)
        self.status_label.setText("Je reflechis...")

    def show_result(self, recognized: str):
        self._recognized_text = recognized.strip()
        self.recognized_edit.setPlainText(self._recognized_text)
        if not self.corrected_edit.toPlainText().strip():
            self.corrected_edit.setPlainText(self.current_phrase)
        self.status_label.setText("Corrige la phrase correcte si besoin, puis valide.")
        self.save_btn.setEnabled(bool(self._recognized_text))

    def show_error(self, message: str):
        self.status_label.setText(message)
        self.recording_stopped()

    def _on_save_clicked(self):
        original = self.recognized_edit.toPlainText().strip()
        corrected = self.corrected_edit.toPlainText().strip()
        if original and corrected:
            self.save_requested.emit(original, corrected)
            self._mark_done()
            self._next_phrase()

    def _mark_done(self):
        row = self.list_widget.currentRow()
        item = self.list_widget.item(row)
        if item and not item.text().startswith("[OK] "):
            item.setText("[OK] " + item.text())
            self.progress.setValue(self.progress.value() + 1)

    def _next_phrase(self):
        row = self.list_widget.currentRow()
        if row < self.list_widget.count() - 1:
            self.list_widget.setCurrentRow(row + 1)
        else:
            self.status_label.setText("Entrainement termine. Tu peux fermer.")

    def _on_done(self):
        self.completed.emit()
        self.accept()
