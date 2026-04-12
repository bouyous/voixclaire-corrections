"""Barre flottante minimaliste - l'interface principale de VoixClaire."""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QSystemTrayIcon,
    QMenu, QApplication, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
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

QLabel#user_label {
    font-size: 12px;
    color: #94e2d5;
    font-weight: 500;
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
"""


def create_mic_icon(recording: bool = False) -> QIcon:
    """Cree une icone de microphone."""
    size = 40
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("transparent"))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Fond
    bg_color = QColor("#f38ba8") if recording else QColor("#a6e3a1")
    p.setBrush(bg_color)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(0, 0, size, size)

    # Micro (symbole simplifie)
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
    - Nom de l'app + profil utilisateur
    - Gros bouton micro (cliquer pour parler)
    - Texte de statut
    - Boutons discrets: dictionnaire, parametres
    """

    # Signaux
    record_clicked = pyqtSignal()
    dictionary_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    quit_clicked = pyqtSignal()
    sync_clicked = pyqtSignal()

    def __init__(self, user_name: str = "", parent=None):
        super().__init__(parent)
        self.user_name = user_name
        self._recording = False
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

        # Taille et position
        screen = QApplication.primaryScreen().geometry()
        bar_width = min(700, screen.width() - 100)
        bar_height = 56
        x = (screen.width() - bar_width) // 2
        self.setGeometry(x, 0, bar_width, bar_height)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(12)

        # Nom de l'app
        app_label = QLabel("VoixClaire")
        app_label.setObjectName("app_name")
        layout.addWidget(app_label)

        # Profil
        if self.user_name:
            user_label = QLabel(f"  {self.user_name}")
            user_label.setObjectName("user_label")
            layout.addWidget(user_label)

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

        # Boutons discrets
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

    def _on_mic_clicked(self):
        self.record_clicked.emit()

    def set_recording(self, recording: bool):
        """Met a jour l'etat visuel d'enregistrement."""
        self._recording = recording
        self.mic_btn.setProperty("recording", "true" if recording else "false")
        self.mic_btn.setIcon(create_mic_icon(recording))
        self.mic_btn.style().unpolish(self.mic_btn)
        self.mic_btn.style().polish(self.mic_btn)
        self.tray.setIcon(create_tray_icon(recording))

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
        """Permet de deplacer la barre en la faisant glisser."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
