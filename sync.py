"""Synchronisation des corrections par profil utilisateur via GitHub.

Fonctionne en mode "offline-first":
- Les corrections sont TOUJOURS stockees localement (cle USB ou PC)
- Quand internet est dispo, on synchronise avec GitHub
- Si pas internet, tout continue de marcher normalement
"""

import json
import subprocess
import shutil
import re
from pathlib import Path
from datetime import datetime
from config import DATA_DIR, IS_PORTABLE
from database import CorrectionDB, get_connection


CORRECTIONS_FILE = "corrections.json"
PHRASES_FILE = "phrase_corrections.json"


def _sanitize_name(name: str) -> str:
    """Convertit un prenom en nom de dossier safe."""
    name = name.strip().lower()
    name = re.sub(r'[^a-z0-9_-]', '_', name)
    return re.sub(r'_+', '_', name).strip('_') or "default"


def _get_sync_dir() -> Path:
    """Repertoire du clone git pour la sync."""
    if IS_PORTABLE:
        # Sur la cle USB, a cote de data/
        return DATA_DIR.parent / "sync_repo"
    else:
        return DATA_DIR / "sync_repo"


class GitHubSync:
    """
    Synchronise les corrections vers GitHub, un dossier par profil.

    Structure du depot GitHub:
        corrections/
            liam/
                corrections.json
                phrase_corrections.json
            jean_pascal/
                corrections.json
                phrase_corrections.json

    Fonctionnement offline-first:
    1. Les corrections sont toujours en local (BDD SQLite sur la cle)
    2. sync() essaie de pull/push GitHub
    3. Si pas internet → echec silencieux, tout marche quand meme
    4. Au prochain sync reussi, tout est rattrape
    """

    def __init__(self, repo_url: str, db: CorrectionDB, user_name: str):
        self.repo_url = repo_url
        self.db = db
        self.user_name = user_name
        self.profile_dir_name = _sanitize_name(user_name)
        self.sync_dir = _get_sync_dir()
        self._git = shutil.which("git")

    @property
    def is_configured(self) -> bool:
        return bool(self.repo_url) and self._git is not None

    @property
    def is_cloned(self) -> bool:
        return (self.sync_dir / ".git").exists()

    def _run_git(self, *args, check=True) -> subprocess.CompletedProcess:
        cmd = [self._git] + list(args)
        return subprocess.run(
            cmd,
            cwd=str(self.sync_dir),
            capture_output=True,
            text=True,
            check=check,
            timeout=15,  # timeout court pour ne pas bloquer si pas internet
        )

    def _has_internet(self) -> bool:
        """Verifie rapidement si GitHub est accessible."""
        try:
            import urllib.request
            urllib.request.urlopen("https://github.com", timeout=3)
            return True
        except Exception:
            return False

    def list_profiles(self) -> list[str]:
        """Liste les profils sur le depot GitHub."""
        if not self.is_cloned:
            return []
        corrections_dir = self.sync_dir / "corrections"
        if not corrections_dir.exists():
            return []
        return [d.name for d in corrections_dir.iterdir() if d.is_dir()]

    def setup(self) -> str:
        """Clone ou met a jour le depot."""
        if not self._git:
            return "Erreur: git absent"

        if self.is_cloned:
            try:
                self._run_git("pull", "--rebase", "origin", "main", check=False)
                return "OK"
            except Exception:
                return "Erreur pull"
        else:
            self.sync_dir.mkdir(parents=True, exist_ok=True)
            try:
                subprocess.run(
                    [self._git, "clone", self.repo_url, str(self.sync_dir)],
                    capture_output=True, text=True, check=True, timeout=30,
                )
                return "OK"
            except subprocess.CalledProcessError:
                # Depot vide: initialiser
                try:
                    self._run_git("init")
                    self._run_git("remote", "add", "origin", self.repo_url, check=False)
                    self._run_git("branch", "-M", "main")
                    # Configurer git dans le repo de sync
                    self._run_git("config", "user.name", "VoixClaire")
                    self._run_git("config", "user.email", "voixclaire@sync")
                    # Premier commit
                    profile_dir = self.sync_dir / "corrections" / self.profile_dir_name
                    profile_dir.mkdir(parents=True, exist_ok=True)
                    self._export_to_files()
                    self._run_git("add", ".")
                    self._run_git("commit", "-m", f"Init profil {self.user_name}")
                    self._run_git("push", "-u", "origin", "main", check=False)
                    return "OK"
                except Exception as e:
                    return f"Erreur init: {e}"

    def sync(self) -> str:
        """
        Synchronise avec GitHub (offline-first).

        Retourne un message de statut.
        Ne leve jamais d'exception - en cas d'echec, les corrections
        locales continuent de fonctionner.
        """
        if not self.is_configured:
            return "offline"

        if not self._has_internet():
            return "offline"

        try:
            # Pull
            result = self.setup()
            if "Erreur" in result and "pull" not in result:
                return result

            # S'assurer que git est configure dans le repo
            self._run_git("config", "user.name", "VoixClaire", check=False)
            self._run_git("config", "user.email", "voixclaire@sync", check=False)

            # Creer le dossier profil
            profile_dir = self.sync_dir / "corrections" / self.profile_dir_name
            profile_dir.mkdir(parents=True, exist_ok=True)

            # Importer les corrections du depot vers la BDD locale
            imported = self._import_from_files()

            # Exporter la BDD locale vers les fichiers
            self._export_to_files()

            # Commit + push
            self._run_git("add", ".", check=False)
            status = self._run_git("status", "--porcelain", check=False)
            if status.stdout.strip():
                hostname = self._get_hostname()
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                self._run_git(
                    "commit", "-m",
                    f"Sync {self.user_name} depuis {hostname} - {ts}",
                    check=False,
                )
                self._run_git("push", "origin", "main", check=False)

            return f"OK ({imported} importees)"

        except Exception as e:
            # En cas d'erreur, on continue en mode offline
            return f"offline ({e})"

    def _export_to_files(self):
        """Exporte les corrections locales vers les fichiers du profil."""
        profile_dir = self.sync_dir / "corrections" / self.profile_dir_name
        profile_dir.mkdir(parents=True, exist_ok=True)

        corrections = self.db.get_all_corrections()
        corr_data = [
            {
                "wrong_text": c["wrong_text"],
                "correct_text": c["correct_text"],
                "count": c["count"],
                "confidence": c["confidence"],
            }
            for c in corrections
        ]
        with open(profile_dir / CORRECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(corr_data, f, indent=2, ensure_ascii=False)

        conn = get_connection()
        phrases = conn.execute(
            "SELECT wrong_phrase, correct_phrase, count FROM phrase_corrections"
        ).fetchall()
        phrase_data = [dict(p) for p in phrases]
        conn.close()
        with open(profile_dir / PHRASES_FILE, "w", encoding="utf-8") as f:
            json.dump(phrase_data, f, indent=2, ensure_ascii=False)

    def _import_from_files(self) -> int:
        """Importe les corrections du depot vers la BDD locale."""
        imported = 0
        profile_dir = self.sync_dir / "corrections" / self.profile_dir_name

        corr_file = profile_dir / CORRECTIONS_FILE
        if corr_file.exists():
            with open(corr_file, "r", encoding="utf-8") as f:
                corrections = json.load(f)
            conn = get_connection()
            for c in corrections:
                conn.execute("""
                    INSERT INTO corrections (wrong_text, correct_text, count, confidence)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(wrong_text, correct_text) DO UPDATE SET
                        count = MAX(count, excluded.count),
                        confidence = MAX(confidence, excluded.confidence),
                        updated_at = datetime('now','localtime')
                """, (c["wrong_text"], c["correct_text"],
                      c.get("count", 1), c.get("confidence", 1.0)))
                imported += 1
            conn.commit()
            conn.close()

        phrase_file = profile_dir / PHRASES_FILE
        if phrase_file.exists():
            with open(phrase_file, "r", encoding="utf-8") as f:
                phrases = json.load(f)
            conn = get_connection()
            for p in phrases:
                conn.execute("""
                    INSERT INTO phrase_corrections (wrong_phrase, correct_phrase, count)
                    VALUES (?, ?, ?)
                    ON CONFLICT(wrong_phrase) DO UPDATE SET
                        correct_phrase = excluded.correct_phrase,
                        count = MAX(count, excluded.count),
                        updated_at = datetime('now','localtime')
                """, (p["wrong_phrase"], p["correct_phrase"], p.get("count", 1)))
                imported += 1
            conn.commit()
            conn.close()

        self.db._load_cache()
        return imported

    @staticmethod
    def _get_hostname() -> str:
        import socket
        return socket.gethostname()
