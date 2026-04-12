"""Capture audio depuis le microphone."""

import threading
import numpy as np
import sounddevice as sd
from scipy.io import wavfile
import io


class AudioEngine:
    """Gere l'enregistrement audio depuis le microphone."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1,
                 device_index: int | None = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_index = device_index
        self._recording = False
        self._audio_buffer = []
        self._stream = None
        self._lock = threading.Lock()
        self._level_callback = None  # callback(float) pour le niveau audio

    def set_level_callback(self, callback):
        """Definit un callback appele avec le niveau audio (0.0-1.0)."""
        self._level_callback = callback

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback appele par sounddevice pour chaque bloc audio."""
        if self._recording:
            with self._lock:
                self._audio_buffer.append(indata.copy())
            if self._level_callback:
                level = np.abs(indata).mean()
                # Normaliser approximativement entre 0 et 1
                normalized = min(1.0, level * 10)
                self._level_callback(normalized)

    def start_recording(self):
        """Demarre l'enregistrement."""
        with self._lock:
            self._audio_buffer = []
        self._recording = True
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32',
                device=self.device_index,
                callback=self._audio_callback,
                blocksize=1024,
            )
            self._stream.start()
        except sd.PortAudioError as e:
            self._recording = False
            raise RuntimeError(f"Erreur microphone: {e}")

    def stop_recording(self) -> np.ndarray | None:
        """Arrete l'enregistrement et retourne l'audio capture."""
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            if not self._audio_buffer:
                return None
            audio = np.concatenate(self._audio_buffer, axis=0)
            self._audio_buffer = []

        # Convertir en mono si necessaire
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        return audio

    @property
    def is_recording(self) -> bool:
        return self._recording

    def get_audio_as_wav_bytes(self, audio: np.ndarray) -> bytes:
        """Convertit un array numpy en bytes WAV."""
        buf = io.BytesIO()
        # Convertir float32 en int16
        audio_int16 = (audio * 32767).astype(np.int16)
        wavfile.write(buf, self.sample_rate, audio_int16)
        return buf.getvalue()

    @staticmethod
    def list_devices() -> list[dict]:
        """Liste les peripheriques audio disponibles."""
        devices = sd.query_devices()
        result = []
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                result.append({
                    "index": i,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "sample_rate": dev["default_samplerate"],
                })
        return result
