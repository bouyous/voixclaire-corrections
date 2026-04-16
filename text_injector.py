"""Injection de texte dans la fenetre active via le presse-papier."""

import time
import threading
import ctypes
import ctypes.wintypes
import os

# API Windows
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Messages Windows
WM_PASTE = 0x0302
WM_SETFOCUS = 0x0007

# Constantes pour SendInput
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_V = 0x56


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("_input", _INPUT),
    ]


def _send_key(vk, up=False):
    """Envoie une touche via keybd_event (plus compatible que SendInput)."""
    flags = 0x0002 if up else 0  # KEYEVENTF_KEYUP
    user32.keybd_event(vk, 0, flags, 0)
    return 1


def _set_clipboard(text: str) -> bool:
    """Met du texte dans le presse-papier via l'API Windows directe."""
    CF_UNICODETEXT = 13
    try:
        if not user32.OpenClipboard(0):
            time.sleep(0.05)
            if not user32.OpenClipboard(0):
                return False
        user32.EmptyClipboard()
        data = text.encode('utf-16-le') + b'\x00\x00'
        h = kernel32.GlobalAlloc(0x0042, len(data))
        if not h:
            user32.CloseClipboard()
            return False
        ptr = kernel32.GlobalLock(h)
        ctypes.memmove(ptr, data, len(data))
        kernel32.GlobalUnlock(h)
        user32.SetClipboardData(CF_UNICODETEXT, h)
        user32.CloseClipboard()
        return True
    except Exception:
        try:
            user32.CloseClipboard()
        except Exception:
            pass
        return False


def _get_window_title(hwnd) -> str:
    """Recupere le titre d'une fenetre."""
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def _is_voixclaire_window(hwnd) -> bool:
    """Verifie si un hwnd appartient a VoixClaire (meme PID)."""
    try:
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == os.getpid():
            return True
    except Exception:
        pass
    return False


class TextInjector:
    """
    Injecte du texte dans la fenetre Windows cible.

    Surveille en permanence la fenetre active et memorise
    la derniere qui n'appartient pas a VoixClaire.
    """

    def __init__(self):
        self._target_hwnd = None
        self._lock = threading.Lock()
        self._running = True
        self._watcher = threading.Thread(target=self._watch_foreground, daemon=True)
        self._watcher.start()

    def _watch_foreground(self):
        """Thread qui surveille la fenetre active toutes les 300ms."""
        while self._running:
            try:
                hwnd = user32.GetForegroundWindow()
                if hwnd and not _is_voixclaire_window(hwnd):
                    with self._lock:
                        self._target_hwnd = hwnd
            except Exception:
                pass
            time.sleep(0.3)

    def save_active_window(self):
        """Appel explicite de sauvegarde."""
        try:
            hwnd = user32.GetForegroundWindow()
            if hwnd and not _is_voixclaire_window(hwnd):
                with self._lock:
                    self._target_hwnd = hwnd
        except Exception:
            pass

    def get_target_info(self) -> str:
        """Pour debug: retourne le titre de la fenetre cible."""
        with self._lock:
            if self._target_hwnd:
                return _get_window_title(self._target_hwnd)
        return "(aucune)"

    def inject_text(self, text: str):
        """Injecte le texte dans la fenetre cible memorisee."""
        if not text:
            return

        # 1. Mettre le texte dans le presse-papier via pyperclip (fiable)
        try:
            import pyperclip
            pyperclip.copy(text)
            print(f"[INJECT] Clipboard set via pyperclip: OK", flush=True)
        except Exception as e:
            # Fallback API Windows
            ok = _set_clipboard(text)
            print(f"[INJECT] Clipboard set via API: {ok}", flush=True)
            if not ok:
                return

        time.sleep(0.1)

        with self._lock:
            target = self._target_hwnd

        if not target:
            print("[INJECT] Pas de fenetre cible !", flush=True)
            return

        title = _get_window_title(target)
        print(f"[INJECT] Fenetre cible hwnd={target} titre='{title}'", flush=True)

        # 2. Redonner le focus a la fenetre cible
        self._force_foreground(target)
        time.sleep(0.3)

        # 3. Verifier le focus
        current_fg = user32.GetForegroundWindow()
        fg_title = _get_window_title(current_fg)
        print(f"[INJECT] Focus actuel: hwnd={current_fg} titre='{fg_title}'", flush=True)

        # 4. Envoyer Ctrl+V via SendInput
        r1 = _send_key(VK_CONTROL)
        time.sleep(0.02)
        r2 = _send_key(VK_V)
        time.sleep(0.05)
        r3 = _send_key(VK_V, up=True)
        time.sleep(0.02)
        r4 = _send_key(VK_CONTROL, up=True)
        print(f"[INJECT] SendInput results: {r1},{r2},{r3},{r4}", flush=True)

        # 5. Backup: WM_PASTE au cas ou SendInput ne marche pas
        time.sleep(0.2)
        focused_child = self._get_focused_child(target)
        paste_target = focused_child if focused_child else target
        user32.PostMessageW(paste_target, WM_PASTE, 0, 0)
        print(f"[INJECT] WM_PASTE envoye a {paste_target}", flush=True)

    def stop(self):
        """Arrete le thread de surveillance."""
        self._running = False

    @staticmethod
    def _get_focused_child(parent_hwnd):
        """Trouve la fenetre enfant qui a le focus dans la fenetre parent."""
        try:
            # Obtenir le thread de la fenetre
            thread_id = user32.GetWindowThreadProcessId(parent_hwnd, None)
            # Obtenir le focus dans ce thread
            gui_info = GUITHREADINFO()
            gui_info.cbSize = ctypes.sizeof(GUITHREADINFO)
            if user32.GetGUIThreadInfo(thread_id, ctypes.byref(gui_info)):
                if gui_info.hwndFocus:
                    return gui_info.hwndFocus
        except Exception:
            pass
        return None

    @staticmethod
    def _force_foreground(hwnd):
        """Force une fenetre au premier plan."""
        try:
            target_thread = user32.GetWindowThreadProcessId(hwnd, None)
            current_thread = kernel32.GetCurrentThreadId()

            # Attacher les threads
            if target_thread != current_thread:
                user32.AttachThreadInput(current_thread, target_thread, True)

            # Alt press/release pour deverrouiller
            _send_key(VK_MENU)
            _send_key(VK_MENU, up=True)

            # Restaurer si minimise
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE

            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)

            # Detacher
            if target_thread != current_thread:
                user32.AttachThreadInput(current_thread, target_thread, False)
        except Exception as e:
            print(f"[INJECT] _force_foreground erreur: {e}", flush=True)


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("hwndActive", ctypes.wintypes.HWND),
        ("hwndFocus", ctypes.wintypes.HWND),
        ("hwndCapture", ctypes.wintypes.HWND),
        ("hwndMenuOwner", ctypes.wintypes.HWND),
        ("hwndMoveSize", ctypes.wintypes.HWND),
        ("hwndCaret", ctypes.wintypes.HWND),
        ("rcCaret", ctypes.wintypes.RECT),
    ]
