"""Injection de texte dans la fenetre active via le presse-papier."""

import time
import pyperclip
from pynput.keyboard import Controller, Key


class TextInjector:
    """
    Injecte du texte dans la fenetre Windows actuellement active.

    Utilise le presse-papier + Ctrl+V pour une compatibilite maximale
    avec tous les types d'applications (navigateur, Word, Notepad, etc.).
    """

    def __init__(self):
        self._keyboard = Controller()

    def inject_text(self, text: str):
        """
        Injecte le texte dans la fenetre active.

        Sauvegarde le contenu precedent du presse-papier et le restaure apres.
        """
        if not text:
            return

        # Sauvegarder le presse-papier actuel
        try:
            previous_clipboard = pyperclip.paste()
        except Exception:
            previous_clipboard = ""

        try:
            # Copier le texte dans le presse-papier
            pyperclip.copy(text)
            time.sleep(0.05)

            # Simuler Ctrl+V
            self._keyboard.press(Key.ctrl)
            self._keyboard.press('v')
            self._keyboard.release('v')
            self._keyboard.release(Key.ctrl)

            time.sleep(0.1)
        finally:
            # Restaurer le presse-papier apres un delai
            time.sleep(0.2)
            try:
                pyperclip.copy(previous_clipboard)
            except Exception:
                pass

    def inject_key(self, key: Key):
        """Simule une touche (ex: Enter, Tab)."""
        self._keyboard.press(key)
        self._keyboard.release(key)
