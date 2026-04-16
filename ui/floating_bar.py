"""Barre flottante minimaliste - l'interface principale de VoixClaire."""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QSystemTrayIcon,
    QMenu, QApplication, QMessageBox, QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QColor, QPixmap, QPainter, QAction, QFont, QCursor

BAR_STYLE = """
QWidget#floating_bar {
    background-color: rgba(30, 30, 46, 230);
    border-bottom: 2px solid #89b4fa;
    border-bottom-left-radius: 12px;
    border-bottom-right-radius: 12px;
}

QLabel {
    color: #cdd6f4;
    font-family: 'Segoe UI', sans-serif;
}

QLabel#app_name {
    font-size: 13px;
    font-weight: bold;
    color: #89b4fa;
}

QLabel#status_label {
    font-size: 13px;
    color: #a6adc8;
}

QPushButton#mic_btn {
    background-color: #a6e3a1;
    border: none;
    border-radius: 20px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
    font-size: 18px;
}

QPushButton#mic_btn:hover {
    background-color: #94e2d5;
}

QPushButton#mic_btn[recording="true"] {
    background-color: #f38ba8;
}

QPushButton#small_btn {
    background-color: transparent;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 10px;
    color: #a6adc8;
    font-size: 11px;
}

QPushButton#small_btn:hover {
    background-color: #313244;
    border-color: #89b4fa;
    color: #cdd6f4;
}

QComboBox#profile_combo {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 10px;
    color: #94e2d5;
    font-size: 12px;
    font-weight: 500;
    min-width: 80px;
}

QComboBox#profile_combo:hover {
    border-color: #89b4fa;
}

QComboBox#profile_combo QAbstractItemView {
    background-color: #313244;
    border: 1px solid #45475a;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}

QComboBox#mic_combo {
    background-color: transparent;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 2px 6px;
    color: #a6adc8;
    font-size: 10px;
    max-width: 120px;
}

QComboBox#mic_combo QAbstractItemView {
    background-color: #313244;
    border: 1px solid #45475a;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
}
"""


def create_mic_icon(recording: bool = False) -> QIcon:
    """Cree une icone de microphone."""
    size = 40
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("transparent"))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    bg_color = QColor("#f38ba8") if recording else QColor("#a6e3a1")
    p.setBrush(bg_color)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(0, 0, size, size)

    p.setBrush(QColor("#1e1e2e"))
    p.drawRoundedRect(14, 6, 12, 18, 6, 6)
    p.drawRect(18, 24, 4, 4)
    p.drawRect(12, 28, 16, 3)

    p.end()
    return QIcon(pixmap)


def create_tray_icon(recording: bool = False) -> QIcon:
    """Cree l'icone pour la barre des taches."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor("transparent"))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor("#f38ba8") if recording else QColor("#89b4fa")
    p.setBrush(color)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(2, 2, 28, 28)
    p.setBrush(QColor("#1e1e2e"))
    p.drawRoundedRect(11, 5, 10, 14, 5, 5)
    p.drawRect(14, 19, 4, 3)
    p.drawRect(9, 22, 14, 2)
    p.end()
    return QIcon(pixmap)


class FloatingBar(QWidget):
    """
    Barre flottante en haut de l'ecran.

    Contient:
    - Selecteur de profil (Liam / Papa / ...)
    - Gros bouton micro
    - Selecteur de micro
    - Boutons: mots appris, sync, parametres
    """

    # Signaux
    record_clicked = pyqtSignal()
    dictionary_clicked = pyqtSignal()
    history_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    quit_clicked = pyqtSignal()
    sync_clicked = pyqtSignal()
    profile_changed = pyqtSignal(str)     # nom du profil
    mic_changed = pyqtSignal(object)      # device index (int ou None)

    # Signal pour annuler l'enregistrement
    cancel_recording = pyqtSignal()

    def __init__(self, user_name: str = "", profiles: list[str] = None,
                 mic_devices: list[dict] = None, parent=None):
        super().__init__(parent)
        self.user_name = user_name
        self.profiles = profiles or []
        self.mic_devices = mic_devices or []
        self._recording = False
        self._mic_locked = False  # Anti-double-clic
        self._setup_ui()
        self._setup_tray()

    def _setup_ui(self):
        self.setObjectName("floating_bar")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(BAR_STYLE)

        screen = QApplication.primaryScreen().geometry()
        bar_width = min(800, screen.width() - 100)
        bar_height = 56
        x = (screen.width() - bar_width) // 2
        self.setGeometry(x, 0, bar_width, bar_height)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(10)

        # Nom de l'app
        app_label = QLabel("VoixClaire")
        app_label.setObjectName("app_name")
        layout.addWidget(app_label)

        # Bouton Annuler (visible seulement pendant l'enregistrement)
        self.btn_cancel_rec = QPushButton("Annuler")
        self.btn_cancel_rec.setObjectName("small_btn")
        self.btn_cancel_rec.setToolTip("Annuler l'enregistrement en cours")
        self.btn_cancel_rec.setStyleSheet(
            "QPushButton { background-color: #f38ba8; border: none; "
            "border-radius: 6px; padding: 4px 10px; color: #1e1e2e; "
            "font-size: 11px; font-weight: bold; }"
            "QPushButton:hover { background-color: #eba0ac; }"
        )
        self.btn_cancel_rec.setVisible(False)
        self.btn_cancel_rec.clicked.connect(self._on_cancel_recording)
        layout.addWidget(self.btn_cancel_rec)

        # Selecteur de profil
        self.profile_combo = QComboBox()
        self.profile_combo.setObjectName("profile_combo")
        self._populate_profiles()
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        layout.addWidget(self.profile_combo)

        layout.addStretch()

        # Status
        self.status_label = QLabel("Pret")
        self.status_label.setObjectName("status_label")
        layout.addWidget(self.status_label)

        # GROS bouton micro
        self.mic_btn = QPushButton()
        self.mic_btn.setObjectName("mic_btn")
        self.mic_btn.setIcon(create_mic_icon(False))
        self.mic_btn.setToolTip("Cliquer pour parler")
        self.mic_btn.setProperty("recording", "false")
        self.mic_btn.clicked.connect(self._on_mic_clicked)
        layout.addWidget(self.mic_btn)

        layout.addStretch()

        # Selecteur de micro (petit)
        self.mic_combo = QComboBox()
        self.mic_combo.setObjectName("mic_combo")
        self.mic_combo.setToolTip("Choisir le microphone")
        self._populate_mics()
        self.mic_combo.currentIndexChanged.connect(self._on_mic_changed)
        layout.addWidget(self.mic_combo)

        # Boutons discrets
        btn_history = QPushButton("Historique")
        btn_history.setObjectName("small_btn")
        btn_history.setToolTip("Derniers textes dictes")
        btn_history.clicked.connect(self.history_clicked.emit)
        layout.addWidget(btn_history)

        btn_dict = QPushButton("Mots appris")
        btn_dict.setObjectName("small_btn")
        btn_dict.clicked.connect(self.dictionary_clicked.emit)
        layout.addWidget(btn_dict)

        btn_sync = QPushButton("Sync")
        btn_sync.setObjectName("small_btn")
        btn_sync.clicked.connect(self.sync_clicked.emit)
        layout.addWidget(btn_sync)

        btn_settings = QPushButton("...")
        btn_settings.setObjectName("small_btn")
        btn_settings.setToolTip("Parametres")
        btn_settings.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(btn_settings)

        # Bouton reduire (masque la barre, reste dans le tray)
        btn_minimize = QPushButton("\u2014")
        btn_minimize.setObjectName("small_btn")
        btn_minimize.setToolTip("Reduire dans la barre des taches")
        btn_minimize.setFixedWidth(28)
        btn_minimize.clicked.connect(self._minimize_to_tray)
        layout.addWidget(btn_minimize)

        # Bouton fermer
        btn_close = QPushButton("X")
        btn_close.setObjectName("small_btn")
        btn_close.setToolTip("Quitter VoixClaire")
        btn_close.setFixedWidth(28)
        btn_close.setStyleSheet(
            "QPushButton { background-color: transparent; border: 1px solid #45475a; "
            "border-radius: 6px; color: #a6adc8; font-size: 11px; }"
            "QPushButton:hover { background-color: #f38ba8; border-color: #f38ba8; color: #1e1e2e; }"
        )
        btn_close.clicked.connect(self.quit_clicked.emit)
        layout.addWidget(btn_close)

    def _populate_profiles(self):
        """Remplit le selecteur de profils."""
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for p in self.profiles:
            # Afficher le nom avec majuscule
            display = p.replace('_', ' ').title()
            self.profile_combo.addItem(display, p)
        # Selectionner le profil actuel
        for i in range(self.profile_combo.count()):
            if self.profile_combo.itemData(i) == self.user_name.lower().replace(' ', '_'):
                self.profile_combo.setCurrentIndex(i)
                break
        self.profile_combo.blockSignals(False)

    def _populate_mics(self):
        """Remplit le selecteur de microphones."""
        self.mic_combo.blockSignals(True)
        self.mic_combo.clear()
        self.mic_combo.addItem("Micro par defaut", None)
        for dev in self.mic_devices:
            # Raccourcir le nom si trop long
            name = dev["name"]
            if len(name) > 25:
                name = name[:22] + "..."
            self.mic_combo.addItem(name, dev["index"])
        self.mic_combo.blockSignals(False)

    def update_profiles(self, profiles: list[str], current: str = ""):
        """Met a jour la liste des profils."""
        self.profiles = profiles
        if current:
            self.user_name = current
        self._populate_profiles()

    def _on_profile_changed(self, text):
        profile_id = self.profile_combo.currentData()
        if profile_id:
            self.profile_changed.emit(profile_id)

    def _on_mic_changed(self, index):
        device_index = self.mic_combo.currentData()
        self.mic_changed.emit(device_index)

    def _setup_tray(self):
        """Icone dans la barre des taches Windows."""
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(create_tray_icon(False))
        self.tray.setToolTip("VoixClaire - Pret")

        menu = QMenu()
        action_show = QAction("Afficher la barre", self)
        action_show.triggered.connect(self.show)
        menu.addAction(action_show)

        action_record = QAction("Parler / Arreter", self)
        action_record.triggered.connect(self._on_mic_clicked)
        menu.addAction(action_record)

        menu.addSeparator()

        action_dict = QAction("Mots appris", self)
        action_dict.triggered.connect(self.dictionary_clicked.emit)
        menu.addAction(action_dict)

        action_settings = QAction("Parametres", self)
        action_settings.triggered.connect(self.settings_clicked.emit)
        menu.addAction(action_settings)

        menu.addSeparator()

        action_quit = QAction("Quitter VoixClaire", self)
        action_quit.triggered.connect(self.quit_clicked.emit)
        menu.addAction(action_quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _minimize_to_tray(self):
        """Masque la barre, reste accessible via l'icone dans la barre des taches."""
        self.hide()
        self.tray.showMessage(
            "VoixClaire",
            "VoixClaire est reduit. Double-cliquez l'icone pour le rouvrir.",
            QSystemTrayIcon.MessageIcon.Information, 2000
        )

    def _on_mic_clicked(self):
        # Anti-double-clic: bloquer pendant 1.5 seconde apres un clic
        if self._mic_locked:
            return
        self._mic_locked = True
        QTimer.singleShot(1500, self._unlock_mic)
        self.record_clicked.emit()

    def _unlock_mic(self):
        self._mic_locked = False

    def _on_cancel_recording(self):
        """Annule l'enregistrement en cours."""
        self.cancel_recording.emit()

    def set_recording(self, recording: bool):
        """Met a jour l'etat visuel d'enregistrement."""
        self._recording = recording
        self.mic_btn.setProperty("recording", "true" if recording else "false")
        self.mic_btn.setIcon(create_mic_icon(recording))
        self.mic_btn.style().unpolish(self.mic_btn)
        self.mic_btn.style().polish(self.mic_btn)
        self.tray.setIcon(create_tray_icon(recording))
        self.btn_cancel_rec.setVisible(recording)

        if recording:
            self.status_label.setText("Je t'ecoute...")
            self.status_label.setStyleSheet("color: #f38ba8; font-weight: bold; font-size: 13px;")
            self.mic_btn.setToolTip("Cliquer pour arreter")
            self.tray.setToolTip("VoixClaire - Enregistrement...")
        else:
            self.status_label.setText("Pret")
            self.status_label.setStyleSheet("color: #a6adc8; font-size: 13px;")
            self.mic_btn.setToolTip("Cliquer pour parler")
            self.tray.setToolTip("VoixClaire - Pret")

    def set_status(self, text: str, color: str = "#a6adc8"):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 13px;")

    def show_tray_message(self, title: str, message: str, duration_ms: int = 3000):
        self.tray.showMessage(
            title, message,
            QSystemTrayIcon.MessageIcon.Information, duration_ms
        )

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
