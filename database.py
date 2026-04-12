"""Base de donnees SQLite pour les corrections et l'historique."""

import sqlite3
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
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
            wrong = row["wrong_text"].lower()
            if wrong not in self._cache:
                self._cache[wrong] = []
            self._cache[wrong].append({
                "correct": row["correct_text"],
                "count": row["count"],
                "confidence": row["confidence"],
            })
        conn.close()

    def get_correction(self, wrong_text: str) -> str | None:
        """Retourne la meilleure correction pour un mot/phrase."""
        wrong_lower = wrong_text.lower().strip()
        candidates = self._cache.get(wrong_lower, [])
        if not candidates:
            return None
        # Prendre la correction la plus frequente
        best = max(candidates, key=lambda c: c["count"] * c["confidence"])
        return best["correct"]

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
        wrong_lower = wrong_text.lower().strip()
        correct_clean = correct_text.strip()
        if wrong_lower == correct_clean.lower():
            return

        conn = get_connection()
        try:
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
        """Supprime une correction."""
        conn = get_connection()
        conn.execute("DELETE FROM corrections WHERE id=?", (correction_id,))
        conn.commit()
        conn.close()
        self._load_cache()

    def add_phrase_correction(self, wrong_phrase: str, correct_phrase: str):
        """Ajoute une correction au niveau phrase."""
        conn = get_connection()
        conn.execute("""
            INSERT INTO phrase_corrections (wrong_phrase, correct_phrase)
            VALUES (?, ?)
            ON CONFLICT(wrong_phrase)
            DO UPDATE SET
                correct_phrase = ?,
                count = count + 1,
                updated_at = datetime('now','localtime')
        """, (wrong_phrase.lower().strip(), correct_phrase.strip(),
              correct_phrase.strip()))
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
