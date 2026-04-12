"""Dialogue pour gerer le dictionnaire de corrections."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView,
)
from PyQt6.QtCore import Qt
from database import CorrectionDB


class DictionaryDialog(QDialog):
    """Fenetre pour visualiser et gerer les corrections apprises."""

    def __init__(self, db: CorrectionDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("VoixClaire - Dictionnaire personnel")
        self.setMinimumSize(700, 500)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Titre
        title = QLabel("Dictionnaire de corrections")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(title)

        # Barre de recherche
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Rechercher :"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrer les corrections...")
        self.search_input.textChanged.connect(self._filter_table)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Ajout manuel
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Ajouter :"))
        self.wrong_input = QLineEdit()
        self.wrong_input.setPlaceholderText("Mot reconnu (ex: fuit)")
        add_layout.addWidget(self.wrong_input)
        add_layout.addWidget(QLabel("->"))
        self.correct_input = QLineEdit()
        self.correct_input.setPlaceholderText("Mot correct (ex: oui)")
        add_layout.addWidget(self.correct_input)
        btn_add = QPushButton("Ajouter")
        btn_add.setObjectName("validate_btn")
        btn_add.clicked.connect(self._add_manual)
        add_layout.addWidget(btn_add)
        layout.addLayout(add_layout)

        # Tableau
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Reconnu", "Correction", "Utilisations", "Confiance", ""
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # Stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(self.stats_label)

        # Bouton fermer
        btn_close = QPushButton("Fermer")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

    def _load_data(self):
        corrections = self.db.get_all_corrections()
        self.table.setRowCount(len(corrections))

        for i, corr in enumerate(corrections):
            self.table.setItem(i, 0, QTableWidgetItem(corr["wrong_text"]))
            self.table.setItem(i, 1, QTableWidgetItem(corr["correct_text"]))
            self.table.setItem(i, 2, QTableWidgetItem(str(corr["count"])))
            confidence_pct = f"{corr['confidence'] * 100:.0f}%"
            self.table.setItem(i, 3, QTableWidgetItem(confidence_pct))

            btn_del = QPushButton("Supprimer")
            btn_del.setObjectName("delete_btn")
            correction_id = corr["id"]
            btn_del.clicked.connect(lambda checked, cid=correction_id: self._delete(cid))
            self.table.setCellWidget(i, 4, btn_del)

        stats = self.db.get_stats()
        self.stats_label.setText(
            f"{stats['total_corrections']} corrections apprises  |  "
            f"{stats['total_uses']} utilisations totales  |  "
            f"{stats['total_sessions']} sessions de dictee"
        )

    def _filter_table(self, text):
        text_lower = text.lower()
        for i in range(self.table.rowCount()):
            wrong = self.table.item(i, 0).text().lower()
            correct = self.table.item(i, 1).text().lower()
            visible = text_lower in wrong or text_lower in correct
            self.table.setRowHidden(i, not visible)

    def _add_manual(self):
        wrong = self.wrong_input.text().strip()
        correct = self.correct_input.text().strip()
        if not wrong or not correct:
            return
        if wrong.lower() == correct.lower():
            QMessageBox.warning(self, "Erreur", "Les deux mots sont identiques.")
            return
        self.db.add_correction(wrong, correct)
        self.wrong_input.clear()
        self.correct_input.clear()
        self._load_data()

    def _delete(self, correction_id: int):
        reply = QMessageBox.question(
            self, "Confirmer",
            "Supprimer cette correction ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_correction(correction_id)
            self._load_data()
