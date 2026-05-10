"""Transcription audio avec faster-whisper."""

import numpy as np
from faster_whisper import WhisperModel
from config import MODEL_CACHE_DIR


class Transcriber:
    """Wrapper autour de faster-whisper pour la transcription."""

    def __init__(self, model_size: str = "small", language: str = "fr",
                 compute_type: str = "int8", beam_size: int = 3):
        self.model_size = model_size
        self.language = language
        self.compute_type = compute_type
        self.beam_size = beam_size
        self.model = None
        self._loading = False
        self.context_terms = []

    def load_model(self, progress_callback=None):
        """Charge le modele Whisper. Peut prendre du temps au premier lancement."""
        self._loading = True
        try:
            if progress_callback:
                progress_callback("Chargement du modele Whisper...")
            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type=self.compute_type,
                download_root=str(MODEL_CACHE_DIR),
            )
            if progress_callback:
                progress_callback("Modele charge !")
        finally:
            self._loading = False

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    @property
    def is_loading(self) -> bool:
        return self._loading

    def set_context_terms(self, terms: list[str]):
        """Donne au modele quelques mots appris fiables comme contexte."""
        self.context_terms = [t.strip() for t in terms if t and t.strip()][:80]

    def _initial_prompt(self) -> str:
        prompt = (
            "Transcription en francais naturel. L'utilisateur peut avoir une "
            "prononciation atypique, mais il respecte la grammaire et les accords. "
            "Preferer des phrases francaises courantes, sans traduire."
        )
        if self.context_terms:
            prompt += " Mots et noms importants: " + ", ".join(self.context_terms) + "."
        return prompt

    def transcribe(self, audio: np.ndarray) -> dict:
        """
        Transcrit un segment audio.

        Retourne:
            {
                "text": "texte complet",
                "words": [
                    {"word": "mot", "start": 0.0, "end": 0.5, "probability": 0.95},
                    ...
                ],
                "segments": [...]
            }
        """
        if self.model is None:
            raise RuntimeError("Le modele n'est pas charge. Appelez load_model() d'abord.")

        segments_gen, info = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=self.beam_size,
            best_of=max(self.beam_size, 3),
            temperature=[0.0, 0.2, 0.4],
            condition_on_previous_text=False,
            initial_prompt=self._initial_prompt(),
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=300,
            ),
            no_speech_threshold=0.5,
            log_prob_threshold=-1.0,
            compression_ratio_threshold=2.4,
        )

        full_text = ""
        all_words = []
        all_segments = []

        for segment in segments_gen:
            full_text += segment.text
            all_segments.append({
                "text": segment.text,
                "start": segment.start,
                "end": segment.end,
            })
            if segment.words:
                for w in segment.words:
                    all_words.append({
                        "word": w.word.strip(),
                        "start": w.start,
                        "end": w.end,
                        "probability": w.probability,
                    })

        return {
            "text": full_text.strip(),
            "words": all_words,
            "segments": all_segments,
        }

    def extract_word_audio(self, audio: np.ndarray, word_info: dict,
                           sample_rate: int = 16000, padding_ms: int = 50) -> np.ndarray:
        """Extrait le segment audio correspondant a un mot."""
        padding_samples = int(padding_ms * sample_rate / 1000)
        start_sample = max(0, int(word_info["start"] * sample_rate) - padding_samples)
        end_sample = min(len(audio), int(word_info["end"] * sample_rate) + padding_samples)
        return audio[start_sample:end_sample]
