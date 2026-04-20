"""Dialogue pour gerer le dictionnaire de corrections."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView, QTabWidget, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from database import CorrectionDB


DICT_STYLE = """
QDialog { background-color: #1e1e2e; color: #cdd6f4; }
QLabel { color: #cdd6f4; font-family: 'Segoe UI', sans-serif; }
QLineEdit {
    background-color: #313244; border: 1px solid #45475a;
    border-radius: 6px; padding: 6px 10px; color: #cdd6f4;
}
QTableWidget {
    background-color: #181825; border: none;
    gridline-color: #313244; color: #cdd6f4;
    font-size: 13px;
}
QTableWidget::item:selected { background-color: #313244; }
QHeaderView::section {
    background-color: #313244; color: #89b4fa;
    padding: 6px; border: none; font-weight: bold;
}
QTabWidget::pane { border: 1px solid #45475a; background-color: #1e1e2e; }
QTabBar::tab {
    background-color: #313244; color: #a6adc8;
    padding: 8px 16px; border-radius: 4px 4px 0 0;
}
QTabBar::tab:selected { background-color: #89b4fa; color: #1e1e2e; font-weight: bold; }
QPushButton {
    background-color: #313244; border: 1px solid #45475a;
    border-radius: 6px; padding: 6px 14px; color: #cdd6f4; font-size: 12px;
}
QPushButton:hover { background-color: #45475a; }
QPushButton#del_btn {
    background-color: transparent; border: 1px solid #f38ba8;
    color: #f38ba8; padding: 3px 10px; font-size: 11px;
}
QPushButton#del_btn:hover { background-color: #f38ba8; color: #1e1e2e; }
QPushButton#add_btn {
    background-color: #a6e3a1; border: none; color: #1e1e2e; font-weight: bold;
}
QPushButton#add_btn:hover { background-color: #94e2d5; }
QPushButton#danger_btn {
    background-color: transparent; border: 1px solid #f38ba8;
    color: #f38ba8;
}
QPushButton#danger_btn:hover { background-color: #f38ba8; color: #1e1e2e; }
"""


class DictionaryDialog(QDialog):
    """Fenetre pour visualiser et gerer les corrections apprises."""

    def __init__(self, db: CorrectionDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("VoixClaire - Mots appris")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(720, 520)
        self.setStyleSheet(DICT_STYLE)
        self._setup_ui()
        self._load_all()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Titre
        title = QLabel("Mots et phrases appris")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(title)

        # Onglets: mots / phrases
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- Onglet 1: mots ---
        tab_words = QWidget()
        vbox_words = QVBoxLayout(tab_words)
        vbox_words.setSpacing(10)

        # Ajout manuel
        add_row = QHBoxLayout()
        self.wrong_input = QLineEdit()
        self.wrong_input.setPlaceholderText("Whisper reconnait (ex: jeu)")
        self.correct_input = QLineEdit()
        self.correct_input.setPlaceholderText("Mot correct (ex: je)")
        btn_add = QPushButton("Ajouter")
        btn_add.setObjectName("add_btn")
        btn_add.clicked.connect(self._add_manual)
        add_row.addWidget(QLabel("Quand Whisper dit :"))
        add_row.addWidget(self.wrong_input)
        add_row.addWidget(QLabel("→ ecrire :"))
        add_row.addWidget(self.correct_input)
        add_row.addWidget(btn_add)
        vbox_words.addLayout(add_row)

        # Recherche
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrer...")
        self.search_input.textChanged.connect(self._filter_words)
        search_row.addWidget(QLabel("Rechercher :"))
        search_row.addWidget(self.search_input)
        vbox_words.addLayout(search_row)

        self.words_table = QTableWidget()
        self.words_table.setColumnCount(5)
        self.words_table.setHorizontalHeaderLabels(["Reconnu", "Correction", "Fois", "Confiance", ""])
        self.words_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.words_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.words_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.words_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.words_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.words_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.words_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.words_table.verticalHeader().setVisible(False)
        vbox_words.addWidget(self.words_table)

        self.tabs.addTab(tab_words, "Corrections de mots")

        # --- Onglet 2: phrases ---
        tab_phrases = QWidget()
        vbox_phrases = QVBoxLayout(tab_phrases)

        self.phrases_table = QTableWidget()
        self.phrases_table.setColumnCount(4)
        self.phrases_table.setHorizontalHeaderLabels(["Phrase reconnue", "Phrase correcte", "Fois", ""])
        self.phrases_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.phrases_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.phrases_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.phrases_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.phrases_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.phrases_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.phrases_table.verticalHeader().setVisible(False)
        vbox_phrases.addWidget(self.phrases_table)

        self.tabs.addTab(tab_phrases, "Corrections de phrases")

        # Barre du bas
        bottom = QHBoxLayout()
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        bottom.addWidget(self.stats_label)
        bottom.addStretch()

        btn_clear_all = QPushButton("Tout effacer")
        btn_clear_all.setObjectName("danger_btn")
        btn_clear_all.setToolTip("Supprimer TOUTES les corrections apprises")
        btn_clear_all.clicked.connect(self._delete_all)
        bottom.addWidget(btn_clear_all)

        btn_close = QPushButton("Fermer")
        btn_close.clicked.connect(self.close)
        bottom.addWidget(btn_close)

        layout.addLayout(bottom)

    def _load_all(self):
        self._load_words()
        self._load_phrases()
        self._update_stats()

    def _load_words(self):
        corrections = self.db.get_all_corrections()
        self.words_table.setRowCount(len(corrections))
        for i, corr in enumerate(corrections):
            self.words_table.setItem(i, 0, QTableWidgetItem(corr["wrong_text"]))
            self.words_table.setItem(i, 1, QTableWidgetItem(corr["correct_text"]))
            self.words_table.setItem(i, 2, QTableWidgetItem(str(corr["count"])))
            self.words_table.setItem(i, 3, QTableWidgetItem(f"{corr['confidence']*100:.0f}%"))
            btn = QPushButton("Supprimer")
            btn.setObjectName("del_btn")
            cid = corr["id"]
            btn.clicked.connect(lambda checked, c=cid: self._delete_word(c))
            self.words_table.setCellWidget(i, 4, btn)

    def _load_phrases(self):
        phrases = self.db.get_all_phrase_corrections()
        self.phrases_table.setRowCount(len(phrases))
        for i, ph in enumerate(phrases):
            self.phrases_table.setItem(i, 0, QTableWidgetItem(ph["wrong_phrase"]))
            self.phrases_table.setItem(i, 1, QTableWidgetItem(ph["correct_phrase"]))
            self.phrases_table.setItem(i, 2, QTableWidgetItem(str(ph["count"])))
            btn = QPushButton("Supprimer")
            btn.setObjectName("del_btn")
            pid = ph["id"]
            btn.clicked.connect(lambda checked, p=pid: self._delete_phrase(p))
            self.phrases_table.setCellWidget(i, 3, btn)
        # Mettre a jour le titre de l'onglet
        self.tabs.setTabText(1, f"Corrections de phrases ({len(phrases)})")

    def _update_stats(self):
        stats = self.db.get_stats()
        phrases = self.db.get_all_phrase_corrections()
        self.tabs.setTabText(0, f"Mots ({stats['total_corrections']})")
        self.tabs.setTabText(1, f"Phrases ({len(phrases)})")
        self.stats_label.setText(
            f"{stats['total_corrections']} mots  |  {len(phrases)} phrases  |  "
            f"{stats['total_sessions']} dictees"
        )

    def _filter_words(self, text):
        text_lower = text.lower()
        for i in range(self.words_table.rowCount()):
            item0 = self.words_table.item(i, 0)
            item1 = self.words_table.item(i, 1)
            wrong = item0.text().lower() if item0 else ""
            correct = item1.text().lower() if item1 else ""
            self.words_table.setRowHidden(i, text_lower not in wrong and text_lower not in correct)

    def _add_manual(self):
        wrong = self.wrong_input.text().strip()
        correct = self.correct_input.text().strip()
        if not wrong or not correct:
            QMessageBox.warning(self, "Erreur", "Remplis les deux champs.")
            return
        if wrong.lower() == correct.lower():
            QMessageBox.warning(self, "Erreur", "Les deux mots sont identiques.")
            return
        self.db.add_correction(wrong, correct)
        self.wrong_input.clear()
        self.correct_input.clear()
        self._load_all()

    def _delete_word(self, correction_id: int):
        reply = QMessageBox.question(
            self, "Confirmer la suppression",
            "Supprimer cette correction de mot ?\n\nElle ne sera plus appliquee automatiquement.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_correction(correction_id)
            self._load_all()

    def _delete_phrase(self, phrase_id: int):
        reply = QMessageBox.question(
            self, "Confirmer la suppression",
            "Supprimer cette correction de phrase ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_phrase_correction(phrase_id)
            self._load_all()

    def _delete_all(self):
        reply = QMessageBox.question(
            self, "Tout effacer",
            "Supprimer TOUTES les corrections apprises ?\n\n"
            "VoixClaire devra tout reapprendre depuis le debut.\n"
            "Cette action est irreversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_all_corrections()
            self._load_all()
            QMessageBox.information(self, "Fait", "Toutes les corrections ont ete supprimees.")
