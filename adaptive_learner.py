"""Systeme d'apprentissage adaptatif pour les corrections vocales."""

import difflib
import numpy as np
from database import CorrectionDB


class AdaptiveLearner:
    """
    Apprend les corrections de l'utilisateur et les applique automatiquement.

    Deux niveaux de correction:
    1. Correction mot-a-mot: "fuit" -> "oui" (basee sur le texte)
    2. Correction de phrase: "je ve fuit" -> "je veux oui" (basee sur des sequences)

    Le systeme apprend a chaque correction et augmente la confiance au fil du temps.
    """

    def __init__(self, db: CorrectionDB):
        self.db = db

    def apply_corrections(self, text: str) -> tuple[str, list[dict]]:
        """
        Applique les corrections apprises au texte transcrit.

        Retourne:
            (texte_corrige, liste_de_modifications)
            Chaque modification: {"original": str, "corrected": str, "position": int}
        """
        # D'abord, verifier les corrections de phrase complete
        phrase_correction = self.db.get_phrase_correction(text)
        if phrase_correction:
            return phrase_correction, [{"original": text, "corrected": phrase_correction,
                                        "position": 0, "type": "phrase"}]

        # Ensuite, corrections mot-a-mot
        words = text.split()
        corrected_words = []
        modifications = []

        for i, word in enumerate(words):
            correction = self.db.get_correction(word)
            if correction:
                corrected_words.append(correction)
                if correction.lower() != word.lower():
                    modifications.append({
                        "original": word,
                        "corrected": correction,
                        "position": i,
                        "type": "word",
                    })
            else:
                corrected_words.append(word)

        corrected_text = " ".join(corrected_words)
        return corrected_text, modifications

    def learn_from_edit(self, original_text: str, corrected_text: str,
                        word_infos: list[dict] | None = None,
                        audio: np.ndarray | None = None,
                        sample_rate: int = 16000):
        """
        Apprend les corrections en comparant le texte original et le texte corrige.

        Utilise un algorithme de diff pour identifier les mots changes,
        y compris les insertions et suppressions.
        """
        if original_text.strip() == corrected_text.strip():
            return []

        orig_words = original_text.strip().split()
        corr_words = corrected_text.strip().split()

        # Si le nombre de mots est le meme, comparaison directe
        if len(orig_words) == len(corr_words):
            return self._learn_aligned(orig_words, corr_words, word_infos, audio, sample_rate)

        # Sinon, utiliser SequenceMatcher pour aligner
        return self._learn_with_diff(orig_words, corr_words, word_infos, audio, sample_rate)

    def _learn_aligned(self, orig_words, corr_words, word_infos, audio, sample_rate):
        """Apprend quand les mots sont alignes 1-a-1."""
        learned = []
        for i, (orig, corr) in enumerate(zip(orig_words, corr_words)):
            if orig.lower() != corr.lower():
                # Extraire l'audio du mot si disponible
                mfcc = None
                if audio is not None and word_infos and i < len(word_infos):
                    mfcc = self._extract_mfcc(audio, word_infos[i], sample_rate)

                self.db.add_correction(orig, corr, mfcc)
                learned.append({"original": orig, "corrected": corr})
        return learned

    def _learn_with_diff(self, orig_words, corr_words, word_infos, audio, sample_rate):
        """Apprend en utilisant un diff pour gerer insertions/suppressions."""
        matcher = difflib.SequenceMatcher(None, orig_words, corr_words)
        learned = []

        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op == "replace":
                # Mots remplaces - apprendre les substitutions
                orig_chunk = " ".join(orig_words[i1:i2])
                corr_chunk = " ".join(corr_words[j1:j2])

                if i2 - i1 == 1 and j2 - j1 == 1:
                    # Remplacement mot-a-mot
                    mfcc = None
                    if audio is not None and word_infos and i1 < len(word_infos):
                        mfcc = self._extract_mfcc(audio, word_infos[i1], sample_rate)
                    self.db.add_correction(orig_words[i1], corr_words[j1], mfcc)
                    learned.append({"original": orig_words[i1], "corrected": corr_words[j1]})
                else:
                    # Remplacement multi-mots: sauver comme correction de phrase
                    self.db.add_phrase_correction(orig_chunk, corr_chunk)
                    learned.append({"original": orig_chunk, "corrected": corr_chunk})

        # Ne PAS sauver la phrase complete en plus — cela cree des corrections
        # parasites impossibles a supprimer depuis le dictionnaire

        return learned

    def _extract_mfcc(self, audio: np.ndarray, word_info: dict,
                      sample_rate: int) -> np.ndarray | None:
        """Extrait les coefficients MFCC d'un segment audio."""
        try:
            import librosa
            padding_ms = 50
            padding_samples = int(padding_ms * sample_rate / 1000)
            start = max(0, int(word_info["start"] * sample_rate) - padding_samples)
            end = min(len(audio), int(word_info["end"] * sample_rate) + padding_samples)
            segment = audio[start:end]

            if len(segment) < sample_rate * 0.05:  # Moins de 50ms
                return None

            mfcc = librosa.feature.mfcc(y=segment, sr=sample_rate, n_mfcc=13)
            # Moyenne sur le temps pour obtenir un vecteur fixe
            return mfcc.mean(axis=1).astype(np.float32)
        except Exception:
            return None

    def get_statistics(self) -> dict:
        """Retourne les statistiques d'apprentissage."""
        return self.db.get_stats()
