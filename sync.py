"""Synchronisation des corrections par profil utilisateur via GitHub."""

import json
import subprocess
import shutil
import re
from pathlib import Path
from datetime import datetime
from config import DATA_DIR
from database import CorrectionDB, get_connection


SYNC_DIR = DATA_DIR / "sync_repo"
CORRECTIONS_FILE = "corrections.json"
PHRASES_FILE = "phrase_corrections.json"


def _sanitize_name(name: str) -> str:
    """Convertit un prenom en nom de dossier safe."""
    # Minuscules, remplacer espaces et accents
    name = name.strip().lower()
    name = re.sub(r'[^a-z0-9_-]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name or "default"


class GitHubSync:
    """
    Synchronise les corrections vers un depot GitHub avec un dossier par profil.

    Structure du depot:
        corrections/
            liam/
                corrections.json
                phrase_corrections.json
            jean_pascal/
                corrections.json
                phrase_corrections.json

    Chaque poste pull les corrections de son profil, les fusionne
    avec sa base locale, et push le resultat.
    """

    def __init__(self, repo_url: str, db: CorrectionDB, user_name: str):
        self.repo_url = repo_url
        self.db = db
        self.user_name = user_name
        self.profile_dir_name = _sanitize_name(user_name)
        self._git = shutil.which("git")

    @property
    def is_configured(self) -> bool:
        return bool(self.repo_url) and self._git is not None

    @property
    def is_cloned(self) -> bool:
        return (SYNC_DIR / ".git").exists()

    def _run_git(self, *args, cwd=None, check=True) -> subprocess.CompletedProcess:
        cmd = [self._git] + list(args)
        return subprocess.run(
            cmd,
            cwd=str(cwd or SYNC_DIR),
            capture_output=True,
            text=True,
            check=check,
            timeout=30,
        )

    def list_profiles(self) -> list[str]:
        """Liste les profils existants sur le depot."""
        if not self.is_cloned:
            return []
        corrections_dir = SYNC_DIR / "corrections"
        if not corrections_dir.exists():
            return []
        return [d.name for d in corrections_dir.iterdir() if d.is_dir()]

    def setup(self) -> str:
        """Clone ou met a jour le depot."""
        if not self._git:
            return "Erreur: git n'est pas installe."

        if self.is_cloned:
            try:
                self._run_git("pull", "--rebase", "origin", "main", check=False)
                return "OK"
            except Exception:
                return "Erreur pull"
        else:
            SYNC_DIR.mkdir(parents=True, exist_ok=True)
            try:
                subprocess.run(
                    [self._git, "clone", self.repo_url, str(SYNC_DIR)],
                    capture_output=True, text=True, check=True, timeout=60,
                )
                return "OK"
            except subprocess.CalledProcessError:
                # Depot vide: initialiser
                try:
                    self._run_git("init")
                    self._run_git("remote", "add", "origin", self.repo_url, check=False)
                    self._run_git("branch", "-M", "main")
                    # Premier commit
                    profile_dir = SYNC_DIR / "corrections" / self.profile_dir_name
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
        Synchronise les corrections:
        1. Pull depuis GitHub
        2. Importe les corrections du profil
        3. Exporte les corrections locales
        4. Push vers GitHub
        """
        if not self.is_configured:
            return "Non configure"

        # Setup / pull
        result = self.setup()
        if "Erreur" in result:
            return result

        # Creer le dossier du profil
        profile_dir = SYNC_DIR / "corrections" / self.profile_dir_name
        profile_dir.mkdir(parents=True, exist_ok=True)

        # Importer
        self._import_from_files()

        # Exporter
        self._export_to_files()

        # Commit + push
        try:
            self._run_git("add", ".")
            status = self._run_git("status", "--porcelain")
            if status.stdout.strip():
                hostname = self._get_hostname()
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                self._run_git(
                    "commit", "-m",
                    f"Sync {self.user_name} depuis {hostname} - {ts}"
                )
                self._run_git("push", "origin", "main", check=False)
        except subprocess.CalledProcessError:
            pass

        return "OK"

    def _export_to_files(self):
        """Exporte les corrections locales vers les fichiers du profil."""
        profile_dir = SYNC_DIR / "corrections" / self.profile_dir_name
        profile_dir.mkdir(parents=True, exist_ok=True)

        # Corrections mot-a-mot
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

        # Corrections de phrases
        conn = get_connection()
        phrases = conn.execute(
            "SELECT wrong_phrase, correct_phrase, count FROM phrase_corrections"
        ).fetchall()
        phrase_data = [dict(p) for p in phrases]
        conn.close()
        with open(profile_dir / PHRASES_FILE, "w", encoding="utf-8") as f:
            json.dump(phrase_data, f, indent=2, ensure_ascii=False)

    def _import_from_files(self):
        """Importe les corrections du profil depuis les fichiers GitHub."""
        profile_dir = SYNC_DIR / "corrections" / self.profile_dir_name

        # Corrections mot-a-mot
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
            conn.commit()
            conn.close()

        # Corrections de phrases
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
            conn.commit()
            conn.close()

        self.db._load_cache()

    @staticmethod
    def _get_hostname() -> str:
        import socket
        return socket.gethostname()
