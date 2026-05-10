import tempfile
import unittest
from pathlib import Path

import config
from adaptive_learner import AdaptiveLearner
from database import CorrectionDB


class LearningSafetyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        config.DB_PATH = root / "voixclaire.db"
        config.AUDIO_SAMPLES_DIR = root / "audio_samples"
        config.AUDIO_SAMPLES_DIR.mkdir(exist_ok=True)
        self.db = CorrectionDB()
        self.learner = AdaptiveLearner(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_short_ambiguous_word_does_not_autocorrect_after_one_edit(self):
        self.learner.learn_from_edit("jeu veux manger", "je veux manger")

        corrected, modifications = self.learner.apply_corrections("jeu joue")

        self.assertEqual(corrected, "jeu joue")
        self.assertEqual(modifications, [])

    def test_short_ambiguous_word_autocorrects_after_repeated_evidence(self):
        for _ in range(3):
            self.learner.learn_from_edit("jeu veux manger", "je veux manger")

        corrected, modifications = self.learner.apply_corrections("jeu veux manger")

        self.assertEqual(corrected, "je veux manger")
        self.assertEqual(modifications[0]["original"], "jeu")

    def test_punctuation_and_capitalization_are_preserved(self):
        self.learner.learn_from_edit("briancon", "Briancon")
        self.db.add_correction("brillant", "briancon")
        self.db.add_correction("brillant", "briancon")

        corrected, _ = self.learner.apply_corrections("Brillant!")

        self.assertEqual(corrected, "Briancon!")

    def test_large_phrase_edit_is_not_saved_as_global_phrase(self):
        original = "je veux aller au parc puis faire un dessin"
        corrected = "je veux aller au parc et ensuite faire un dessin"

        learned = self.learner.learn_from_edit(original, corrected)
        phrase = self.db.get_phrase_correction(original)

        self.assertIsNone(phrase)
        self.assertLessEqual(len(learned), 1)


if __name__ == "__main__":
    unittest.main()
