"""Controleur principal - lie la barre flottante, l'overlay et le moteur."""

import threading
import numpy as np
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from config import load_config, save_config, APP_NAME, GITHUB_REPO
from database import CorrectionDB
from audio_engine import AudioEngine
from transcriber import Transcriber
from adaptive_learner import AdaptiveLearner
from text_injector import TextInjector
from sync import GitHubSync
from ui.floating_bar import FloatingBar
from ui.overlay import TranscriptionOverlay
from ui.dictionary_dialog import DictionaryDialog
from ui.settings_dialog import SettingsDialog


class AppController(QObject):
    """
    Controleur principal de l'application.

    Coordonne:
    - FloatingBar: la barre flottante avec le bouton micro
    - TranscriptionOverlay: la popup de correction
    - AudioEngine: capture micro
    - Transcriber: reconnaissance vocale (Whisper)
    - AdaptiveLearner: apprentissage des corrections
    - TextInjector: frappe dans la fenetre active
    - GitHubSync: synchronisation des profils
    """

    # Signaux thread-safe
    _transcription_ready = pyqtSignal(str, list, object)
    _model_status = pyqtSignal(str)
    _audio_level = pyqtSignal(float)
    _error_signal = pyqtSignal(str)

    def __init__(self, user_name: str):
        super().__init__()
        self.config = load_config()
        self.config["user_name"] = user_name
        save_config(self.config)

        # Composants metier
        self.db = CorrectionDB()
        self.audio = AudioEngine(
            sample_rate=self.config["sample_rate"],
            device_index=self.config.get("device_index"),
        )
        self.transcriber = Transcriber(
            model_size=self.config["whisper_model"],
            language=self.config["language"],
            compute_type=self.config["compute_type"],
            beam_size=self.config["beam_size"],
        )
        self.learner = AdaptiveLearner(self.db)
        self.injector = TextInjector()
        self.sync = GitHubSync(GITHUB_REPO, self.db, user_name)

        # Etat
        self._is_recording = False
        self._current_audio = None
        self._current_words = []
        self._original_text = ""

        # UI
        self.bar = FloatingBar(user_name=user_name)
        self.overlay = TranscriptionOverlay()

        # Connecter signaux
        self._connect_signals()

        # Audio level callback
        self.audio.set_level_callback(lambda lvl: self._audio_level.emit(lvl))

        # Sync au demarrage
        threading.Thread(target=self._sync_on_start, daemon=True).start()

        # Charger le modele
        self._load_model_async()

    def _connect_signals(self):
        # Barre flottante
        self.bar.record_clicked.connect(self._toggle_recording)
        self.bar.dictionary_clicked.connect(self._show_dictionary)
        self.bar.settings_clicked.connect(self._show_settings)
        self.bar.quit_clicked.connect(self._quit)
        self.bar.sync_clicked.connect(self._manual_sync)

        # Overlay
        self.overlay.text_validated.connect(self._on_correction)
        self.overlay.text_injected.connect(self._on_inject)

        # Signaux thread-safe
        self._transcription_ready.connect(self._on_transcription)
        self._model_status.connect(self._on_model_status)
        self._audio_level.connect(self._on_audio_level)
        self._error_signal.connect(self._on_error)

    def start(self):
        """Affiche la barre et demarre."""
        self.bar.show()
        self.bar.set_status("Chargement du modele...", "#fab387")

    def _load_model_async(self):
        def _load():
            try:
                self.transcriber.load_model(
                    lambda msg: self._model_status.emit(msg)
                )
                self._model_status.emit("ready")
            except Exception as e:
                self._error_signal.emit(f"Erreur modele: {e}")
        threading.Thread(target=_load, daemon=True).start()

    def _on_model_status(self, status: str):
        if status == "ready":
            self.bar.set_status("Pret - clique sur le micro !", "#a6e3a1")
            self.bar.show_tray_message(
                APP_NAME, "Pret ! Clique sur le micro pour parler."
            )
        else:
            self.bar.set_status(status, "#fab387")

    def _toggle_recording(self):
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if not self.transcriber.is_loaded:
            self.bar.set_status("Le modele charge encore, patiente...", "#fab387")
            return
        try:
            self.audio.start_recording()
            self._is_recording = True
            self.bar.set_recording(True)
        except RuntimeError as e:
            self._error_signal.emit(str(e))

    def _stop_recording(self):
        audio_data = self.audio.stop_recording()
        self._is_recording = False
        self.bar.set_recording(False)

        if audio_data is None or len(audio_data) < self.config["sample_rate"] * 0.3:
            self.bar.set_status("Trop court, reessaie !", "#fab387")
            return

        self.bar.set_status("Je reflechis...", "#89b4fa")

        def _transcribe():
            try:
                result = self.transcriber.transcribe(audio_data)
                self._transcription_ready.emit(
                    result["text"], result["words"], audio_data
                )
            except Exception as e:
                self._error_signal.emit(f"Erreur: {e}")

        threading.Thread(target=_transcribe, daemon=True).start()

    def _on_transcription(self, text: str, words: list, audio_data):
        self._current_audio = audio_data
        self._current_words = words
        self._original_text = text

        # Appliquer corrections apprises
        corrected, modifications = self.learner.apply_corrections(text)

        # Montrer l'overlay
        timeout = self.config.get("overlay_timeout", 5) if not modifications else 0
        self.overlay.show_transcription(corrected, timeout)

        if modifications:
            mods = ", ".join(f'"{m["original"]}"->"{m["corrected"]}"' for m in modifications)
            self.bar.set_status(f"Corrige auto: {mods}", "#a6e3a1")
        else:
            self.bar.set_status("Verifie le texte", "#89b4fa")

    def _on_correction(self, original: str, corrected: str):
        """L'utilisateur a corrige la transcription."""
        learned = self.learner.learn_from_edit(
            original, corrected,
            self._current_words, self._current_audio,
            self.config["sample_rate"],
        )
        self.db.save_session(self._original_text, corrected, injected=False)
        if learned:
            names = ", ".join(f'"{l["corrected"]}"' for l in learned)
            self.bar.set_status(f"J'ai appris: {names}", "#a6e3a1")
            self.bar.show_tray_message(APP_NAME, f"J'ai appris {len(learned)} mot(s) !")

    def _on_inject(self, text: str):
        """Injecte le texte dans la fenetre active."""
        self.injector.inject_text(text)
        self.db.save_session(self._original_text, text, injected=True)
        self.bar.set_status("Texte ecrit !", "#a6e3a1")
        # Reset apres 3s
        QTimer.singleShot(3000, lambda: self.bar.set_status("Pret"))

    def _on_audio_level(self, level: float):
        # On pourrait animer le bouton micro, pour l'instant on ignore
        pass

    def _on_error(self, message: str):
        self.bar.set_status(f"Erreur: {message}", "#f38ba8")

    def _show_dictionary(self):
        dialog = DictionaryDialog(self.db)
        dialog.setStyleSheet("")
        dialog.exec()

    def _show_settings(self):
        dialog = SettingsDialog()
        dialog.setStyleSheet("")
        if dialog.exec():
            self.bar.show_tray_message(
                APP_NAME, "Redemarrez pour appliquer certains changements."
            )

    def _manual_sync(self):
        self.bar.set_status("Synchronisation...", "#89b4fa")
        def _do_sync():
            try:
                result = self.sync.sync()
                self._model_status.emit("Sync OK !")
            except Exception as e:
                self._error_signal.emit(f"Sync: {e}")
        threading.Thread(target=_do_sync, daemon=True).start()

    def _sync_on_start(self):
        """Synchronise au demarrage."""
        try:
            self.sync.sync()
        except Exception:
            pass

    def _quit(self):
        # Sync avant de quitter
        try:
            self.sync.sync()
        except Exception:
            pass
        self.bar.tray.hide()
        QApplication.quit()
