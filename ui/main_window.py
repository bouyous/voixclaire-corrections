"""Controleur principal - lie la barre flottante, l'overlay et le moteur."""

import threading
import numpy as np
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from config import (
    load_config, save_config, set_user_profile,
    list_local_profiles, APP_NAME, GITHUB_REPO,
)
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

    Coordonne la barre flottante, l'overlay, le moteur audio,
    la transcription, l'apprentissage et la synchronisation.
    """

    _transcription_ready = pyqtSignal(str, list, object)
    _model_status = pyqtSignal(str)
    _audio_level = pyqtSignal(float)
    _error_signal = pyqtSignal(str)

    def __init__(self, user_name: str):
        super().__init__()
        self.user_name = user_name
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

        # Lister les profils et les micros
        profiles = self._get_all_profiles()
        mic_devices = []
        try:
            mic_devices = AudioEngine.list_devices()
        except Exception:
            pass

        # UI
        self.bar = FloatingBar(
            user_name=user_name,
            profiles=profiles,
            mic_devices=mic_devices,
        )
        self.overlay = TranscriptionOverlay()

        # Connecter signaux
        self._connect_signals()

        # Audio level callback
        self.audio.set_level_callback(lambda lvl: self._audio_level.emit(lvl))

        # Sync au demarrage
        threading.Thread(target=self._sync_on_start, daemon=True).start()

        # Charger le modele
        self._load_model_async()

    def _get_all_profiles(self) -> list[str]:
        """Combine les profils locaux et distants."""
        profiles = list_local_profiles()
        try:
            remote = self.sync.list_profiles()
            for p in remote:
                if p not in profiles:
                    profiles.append(p)
        except Exception:
            pass
        # S'assurer que le profil actuel est dans la liste
        current_id = self.user_name.lower().replace(' ', '_')
        import re
        current_id = re.sub(r'[^a-z0-9_\-]', '_', current_id)
        if current_id not in profiles:
            profiles.insert(0, current_id)
        return sorted(profiles)

    def _connect_signals(self):
        # Barre flottante
        self.bar.record_clicked.connect(self._toggle_recording)
        self.bar.dictionary_clicked.connect(self._show_dictionary)
        self.bar.settings_clicked.connect(self._show_settings)
        self.bar.quit_clicked.connect(self._quit)
        self.bar.sync_clicked.connect(self._manual_sync)
        self.bar.profile_changed.connect(self._on_profile_changed)
        self.bar.mic_changed.connect(self._on_mic_changed)

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

    # --- Changement de profil ---

    def _on_profile_changed(self, profile_id: str):
        """L'utilisateur a change de profil dans le menu deroulant."""
        if self._is_recording:
            return  # Pas de changement pendant l'enregistrement

        self.user_name = profile_id

        # Recharger les chemins vers le nouveau profil
        set_user_profile(profile_id)
        self.config = load_config()
        self.config["user_name"] = profile_id
        save_config(self.config)

        # Recreer la base et le learner pour le nouveau profil
        self.db = CorrectionDB()
        self.learner = AdaptiveLearner(self.db)
        self.sync = GitHubSync(GITHUB_REPO, self.db, profile_id)

        display_name = profile_id.replace('_', ' ').title()
        self.bar.set_status(f"Profil : {display_name}", "#94e2d5")
        self.bar.show_tray_message(APP_NAME, f"Profil change : {display_name}")

    # --- Changement de micro ---

    def _on_mic_changed(self, device_index):
        """L'utilisateur a change de micro."""
        if self._is_recording:
            return
        self.audio = AudioEngine(
            sample_rate=self.config["sample_rate"],
            device_index=device_index,
        )
        self.audio.set_level_callback(lambda lvl: self._audio_level.emit(lvl))
        self.config["device_index"] = device_index
        save_config(self.config)

        mic_name = "par defaut" if device_index is None else f"#{device_index}"
        self.bar.set_status(f"Micro : {mic_name}", "#a6adc8")

    # --- Modele ---

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
        elif status.startswith("Sync"):
            self.bar.set_status(status, "#a6e3a1")
        else:
            self.bar.set_status(status, "#fab387")

    # --- Enregistrement ---

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

    # --- Transcription ---

    def _on_transcription(self, text: str, words: list, audio_data):
        self._current_audio = audio_data
        self._current_words = words
        self._original_text = text

        corrected, modifications = self.learner.apply_corrections(text)

        self.overlay.show_transcription(corrected, self.bar.geometry())

        if modifications:
            mods = ", ".join(f'"{m["original"]}"->"{m["corrected"]}"' for m in modifications)
            self.bar.set_status(f"Corrige auto: {mods}", "#a6e3a1")
        else:
            self.bar.set_status("Verifie le texte", "#89b4fa")

    def _on_correction(self, original: str, corrected: str):
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
        self.injector.inject_text(text)
        self.db.save_session(self._original_text, text, injected=True)
        self.bar.set_status("Texte ecrit !", "#a6e3a1")
        QTimer.singleShot(3000, lambda: self.bar.set_status("Pret"))

    def _on_audio_level(self, level: float):
        pass

    def _on_error(self, message: str):
        self.bar.set_status(f"Erreur: {message}", "#f38ba8")

    # --- Dialogues ---

    def _show_dictionary(self):
        dialog = DictionaryDialog(self.db)
        dialog.exec()

    def _show_settings(self):
        dialog = SettingsDialog()
        if dialog.exec():
            self.bar.show_tray_message(
                APP_NAME, "Redemarrez pour appliquer certains changements."
            )

    # --- Sync ---

    def _manual_sync(self):
        self.bar.set_status("Synchronisation...", "#89b4fa")
        def _do_sync():
            try:
                result = self.sync.sync()
                # Mettre a jour la liste des profils
                profiles = self._get_all_profiles()
                QTimer.singleShot(0, lambda: self.bar.update_profiles(profiles, self.user_name))
                self._model_status.emit(f"Sync OK !")
            except Exception as e:
                self._error_signal.emit(f"Sync: {e}")
        threading.Thread(target=_do_sync, daemon=True).start()

    def _sync_on_start(self):
        try:
            self.sync.sync()
            profiles = self._get_all_profiles()
            QTimer.singleShot(0, lambda: self.bar.update_profiles(profiles, self.user_name))
        except Exception:
            pass

    def _quit(self):
        try:
            self.sync.sync()
        except Exception:
            pass
        self.bar.tray.hide()
        QApplication.quit()
