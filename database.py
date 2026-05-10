"""Base de donnees SQLite pour les corrections et l'historique."""

import sqlite3
import json
import numpy as np
import re
from pathlib import Path
from datetime import datetime
import config

SHORT_AMBIGUOUS_WORDS = {
    "a", "as", "au", "aux", "ce", "ces", "c", "d", "de", "des", "du",
    "en", "et", "est", "es", "il", "ils", "j", "je", "l", "la", "le",
    "les", "m", "ma", "me", "mes", "mon", "ne", "on", "ou", "où",
    "s", "sa", "se", "ses", "son", "ta", "te", "tes", "ton", "tu",
    "un", "une", "y",
}


def normalize_text(text: str) -> str:
    """Normalise un texte pour les recherches sans perdre l'original sauvegarde."""
    text = text.strip().lower()
    text = re.sub(r"^[^\wÀ-ÿ']+|[^\wÀ-ÿ']+$", "", text, flags=re.UNICODE)
    return text


def is_ambiguous_word(text: str) -> bool:
    """Repere les mots courts qui provoquent facilement des corrections parasites."""
    normalized = normalize_text(text)
    return len(normalized) <= 3 or normalized in SHORT_AMBIGUOUS_WORDS


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialise le schema de la base de donnees."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wrong_text TEXT NOT NULL,
            correct_text TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            confidence REAL DEFAULT 1.0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(wrong_text, correct_text)
        );

        CREATE INDEX IF NOT EXISTS idx_corrections_wrong
            ON corrections(wrong_text);

        CREATE INDEX IF NOT EXISTS idx_corrections_score
            ON corrections(wrong_text, count, confidence);

        CREATE TABLE IF NOT EXISTS audio_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correction_id INTEGER,
            mfcc_features BLOB,
            duration_ms INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (correction_id) REFERENCES corrections(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_text TEXT,
            corrected_text TEXT,
            injected INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS phrase_corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wrong_phrase TEXT NOT NULL,
            correct_phrase TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(wrong_phrase)
        );
    """)
    conn.commit()
    conn.close()


class CorrectionDB:
    """Interface pour gerer les corrections apprises."""

    def __init__(self):
        init_db()
        self._cache = {}
        self._load_cache()

    def _load_cache(self):
        """Charge toutes les corrections en memoire pour acces rapide."""
        conn = get_connection()
        rows = conn.execute(
            "SELECT wrong_text, correct_text, count, confidence FROM corrections "
            "ORDER BY count DESC"
        ).fetchall()
        self._cache = {}
        for row in rows:
            wrong = normalize_text(row["wrong_text"])
            if wrong not in self._cache:
                self._cache[wrong] = []
            self._cache[wrong].append({
                "correct": row["correct_text"],
                "count": row["count"],
                "confidence": row["confidence"],
            })
        conn.close()

    def get_correction(self, wrong_text: str) -> str | None:
        """Retourne la meilleure correction auto-applicable pour un mot."""
        candidate = self.get_correction_candidate(wrong_text)
        return candidate["correct"] if candidate else None

    def get_correction_candidate(self, wrong_text: str) -> dict | None:
        """
        Retourne la meilleure correction si elle est assez fiable.

        Les mots courts/frequents ("je", "tu", "jeu"...) demandent plus de
        preuves avant d'etre appliques automatiquement, sinon une correction
        utile finit par casser toute la dictee.
        """
        wrong_lower = normalize_text(wrong_text)
        candidates = self._cache.get(wrong_lower, [])
        if not candidates:
            return None

        ranked = sorted(
            candidates,
            key=lambda c: (c["count"] * c["confidence"], c["count"]),
            reverse=True,
        )
        best = ranked[0]
        score = best["count"] * best["confidence"]
        competing_score = ranked[1]["count"] * ranked[1]["confidence"] if len(ranked) > 1 else 0
        ambiguous = is_ambiguous_word(wrong_lower) or is_ambiguous_word(best["correct"])

        if ambiguous:
            if best["count"] < 3 or best["confidence"] < 0.85:
                return None
            if competing_score and score < competing_score * 2:
                return None
        elif best["count"] < 2 and best["confidence"] < 0.8:
            return None

        return {
            "wrong": wrong_lower,
            "correct": best["correct"],
            "count": best["count"],
            "confidence": best["confidence"],
            "ambiguous": ambiguous,
        }

    def get_all_corrections(self) -> list[dict]:
        """Retourne toutes les corrections."""
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, wrong_text, correct_text, count, confidence, "
            "created_at, updated_at FROM corrections ORDER BY count DESC"
        ).fetchall()
        result = [dict(row) for row in rows]
        conn.close()
        return result

    def add_correction(self, wrong_text: str, correct_text: str,
                       mfcc_features: np.ndarray | None = None):
        """Ajoute ou met a jour une correction."""
        wrong_lower = normalize_text(wrong_text)
        correct_clean = correct_text.strip()
        if wrong_lower == correct_clean.lower():
            return

        conn = get_connection()
        try:
            # Supprimer la correction inverse si elle existe (evite les boucles)
            conn.execute(
                "DELETE FROM corrections WHERE wrong_text=? AND correct_text=?",
                (correct_clean.lower(), wrong_lower)
            )

            # Upsert: incrementer le compteur si la correction existe deja
            conn.execute("""
                INSERT INTO corrections (wrong_text, correct_text, count)
                VALUES (?, ?, 1)
                ON CONFLICT(wrong_text, correct_text)
                DO UPDATE SET
                    count = count + 1,
                    confidence = MIN(1.0, confidence + 0.1),
                    updated_at = datetime('now','localtime')
            """, (wrong_lower, correct_clean))

            # Sauvegarder les features audio si fournies
            if mfcc_features is not None:
                correction_id = conn.execute(
                    "SELECT id FROM corrections WHERE wrong_text=? AND correct_text=?",
                    (wrong_lower, correct_clean)
                ).fetchone()["id"]
                mfcc_blob = mfcc_features.tobytes()
                conn.execute(
                    "INSERT INTO audio_samples (correction_id, mfcc_features) VALUES (?, ?)",
                    (correction_id, mfcc_blob)
                )

            conn.commit()
        finally:
            conn.close()

        self._load_cache()

    def delete_correction(self, correction_id: int):
        """Supprime une correction mot."""
        conn = get_connection()
        conn.execute("DELETE FROM corrections WHERE id=?", (correction_id,))
        conn.commit()
        conn.close()
        self._load_cache()

    def get_all_phrase_corrections(self) -> list[dict]:
        """Retourne toutes les corrections de phrases."""
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, wrong_phrase, correct_phrase, count, created_at "
            "FROM phrase_corrections ORDER BY count DESC"
        ).fetchall()
        result = [dict(row) for row in rows]
        conn.close()
        return result

    def delete_phrase_correction(self, phrase_id: int):
        """Supprime une correction de phrase."""
        conn = get_connection()
        conn.execute("DELETE FROM phrase_corrections WHERE id=?", (phrase_id,))
        conn.commit()
        conn.close()

    def delete_all_corrections(self):
        """Supprime TOUTES les corrections (mots + phrases). Utile en cas de bug."""
        conn = get_connection()
        conn.execute("DELETE FROM corrections")
        conn.execute("DELETE FROM phrase_corrections")
        conn.commit()
        conn.close()
        self._load_cache()

    def add_phrase_correction(self, wrong_phrase: str, correct_phrase: str):
        """Ajoute une correction au niveau phrase."""
        wrong_phrase = wrong_phrase.lower().strip()
        correct_phrase = correct_phrase.strip()
        if not wrong_phrase or not correct_phrase or wrong_phrase == correct_phrase.lower():
            return
        conn = get_connection()
        conn.execute("""
            INSERT INTO phrase_corrections (wrong_phrase, correct_phrase)
            VALUES (?, ?)
            ON CONFLICT(wrong_phrase)
            DO UPDATE SET
                correct_phrase = ?,
                count = count + 1,
                updated_at = datetime('now','localtime')
        """, (wrong_phrase, correct_phrase, correct_phrase))
        conn.commit()
        conn.close()

    def get_phrase_correction(self, phrase: str) -> str | None:
        """Cherche une correction au niveau phrase."""
        conn = get_connection()
        row = conn.execute(
            "SELECT correct_phrase FROM phrase_corrections WHERE wrong_phrase=? "
            "ORDER BY count DESC LIMIT 1",
            (phrase.lower().strip(),)
        ).fetchone()
        conn.close()
        return row["correct_phrase"] if row else None

    def get_prompt_terms(self, limit: int = 80) -> list[str]:
        """Mots fiables a donner en contexte au moteur de transcription."""
        conn = get_connection()
        rows = conn.execute(
            "SELECT correct_text, count, confidence FROM corrections "
            "WHERE count >= 2 AND confidence >= 0.8 "
            "ORDER BY count DESC, confidence DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()

        terms = []
        seen = set()
        for row in rows:
            term = row["correct_text"].strip()
            key = normalize_text(term)
            if key and key not in seen:
                terms.append(term)
                seen.add(key)
        return terms

    def save_session(self, original: str, corrected: str, injected: bool = False):
        """Sauvegarde une session de dictee."""
        conn = get_connection()
        conn.execute(
            "INSERT INTO sessions (original_text, corrected_text, injected) VALUES (?,?,?)",
            (original, corrected, int(injected))
        )
        conn.commit()
        conn.close()

    def get_stats(self) -> dict:
        """Statistiques d'utilisation."""
        conn = get_connection()
        stats = {
            "total_corrections": conn.execute(
                "SELECT COUNT(*) FROM corrections").fetchone()[0],
            "total_sessions": conn.execute(
                "SELECT COUNT(*) FROM sessions").fetchone()[0],
            "total_uses": conn.execute(
                "SELECT COALESCE(SUM(count), 0) FROM corrections").fetchone()[0],
        }
        conn.close()
        return stats
