"""SQLite-backed long-term memory for Jarvis."""

from pathlib import Path
from difflib import SequenceMatcher
import re
import sqlite3
import threading
from typing import Optional


class MemoryManager:
    def __init__(self, database_path: str | Path = "data/jarvis.db") -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._lock = threading.RLock()
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS memory "
            "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS interactions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, user_input TEXT NOT NULL, "
            "response TEXT NOT NULL, rating INTEGER DEFAULT 0, "
            "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS learned_commands ("
            "phrase TEXT PRIMARY KEY, command TEXT NOT NULL, "
            "uses INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS action_audit ("
            "id TEXT PRIMARY KEY, action_name TEXT NOT NULL, preview TEXT NOT NULL, "
            "risk TEXT NOT NULL, status TEXT NOT NULL, detail TEXT DEFAULT '', "
            "created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        self.connection.commit()

    def remember(self, key: str, value: str) -> None:
        clean_key = key.strip().lower()
        clean_value = value.strip()
        if not clean_key or not clean_value:
            raise ValueError("Memory key and value cannot be empty.")
        with self._lock:
            self.connection.execute(
                "INSERT OR REPLACE INTO memory (key, value) VALUES (?, ?)",
                (clean_key, clean_value),
            )
            self.connection.commit()

    def recall(self, key: str) -> Optional[str]:
        with self._lock:
            row = self.connection.execute(
                "SELECT value FROM memory WHERE key = ?", (key.strip().lower(),)
            ).fetchone()
        return row[0] if row else None

    def all(self) -> dict[str, str]:
        with self._lock:
            rows = self.connection.execute(
                "SELECT key, value FROM memory ORDER BY key"
            ).fetchall()
        return dict(rows)

    def forget(self, key: str) -> bool:
        with self._lock:
            cursor = self.connection.execute(
                "DELETE FROM memory WHERE key = ?", (key.strip().lower(),)
            )
            self.connection.commit()
        return cursor.rowcount > 0

    def extract_and_store(self, text: str) -> Optional[str]:
        patterns = (
            (r"^my name is (.+)$", "name"),
            (r"^my favorite language is (.+)$", "favorite_language"),
            (r"^i like (.+)$", "preference"),
        )
        for pattern, key in patterns:
            match = re.match(pattern, text.strip(), flags=re.IGNORECASE)
            if match:
                value = match.group(1).strip().rstrip(".")
                if len(value) >= 2 and "?" not in value:
                    self.remember(key, value)
                    return f"I'll remember that your {key.replace('_', ' ')} is {value}."
        return None

    def context(self) -> str:
        memories = self.all()
        if not memories:
            return "No saved user facts."
        return "\n".join(f"- {key}: {value}" for key, value in memories.items())

    def record_interaction(self, user_input: str, response: str) -> int:
        with self._lock:
            cursor = self.connection.execute(
                "INSERT INTO interactions (user_input, response) VALUES (?, ?)",
                (user_input.strip(), response.strip()),
            )
            self.connection.commit()
            return int(cursor.lastrowid)

    def rate_interaction(self, interaction_id: int, rating: int) -> bool:
        normalized = 1 if rating > 0 else -1 if rating < 0 else 0
        with self._lock:
            cursor = self.connection.execute(
                "UPDATE interactions SET rating = ? WHERE id = ?",
                (normalized, interaction_id),
            )
            self.connection.commit()
            return cursor.rowcount > 0

    def learn_command(self, phrase: str, command: str) -> None:
        normalized = self._normalize_phrase(phrase)
        if not normalized or not command.strip():
            raise ValueError("Learned phrase and command cannot be empty.")
        with self._lock:
            self.connection.execute(
                "INSERT OR REPLACE INTO learned_commands (phrase, command, uses) "
                "VALUES (?, ?, COALESCE((SELECT uses FROM learned_commands WHERE phrase = ?), 0))",
                (normalized, command.strip(), normalized),
            )
            self.connection.commit()

    def recall_learned_command(self, phrase: str, threshold: float = 0.84) -> Optional[str]:
        normalized = self._normalize_phrase(phrase)
        with self._lock:
            rows = self.connection.execute(
                "SELECT phrase, command FROM learned_commands"
            ).fetchall()
            if not rows:
                return None
            best_phrase, best_command = max(
                rows,
                key=lambda row: SequenceMatcher(None, normalized, row[0]).ratio(),
            )
            score = SequenceMatcher(None, normalized, best_phrase).ratio()
            if score < threshold:
                return None
            self.connection.execute(
                "UPDATE learned_commands SET uses = uses + 1 WHERE phrase = ?",
                (best_phrase,),
            )
            self.connection.commit()
            return str(best_command)

    def relevant_successes(self, text: str, limit: int = 3) -> list[tuple[str, str]]:
        query_tokens = set(self._normalize_phrase(text).split())
        if not query_tokens:
            return []
        with self._lock:
            rows = self.connection.execute(
                "SELECT user_input, response FROM interactions WHERE rating = 1 "
                "ORDER BY id DESC LIMIT 200"
            ).fetchall()
        scored = []
        for user_input, response in rows:
            tokens = set(self._normalize_phrase(user_input).split())
            score = len(query_tokens & tokens) / max(1, len(query_tokens | tokens))
            if score > 0:
                scored.append((score, user_input, response))
        scored.sort(reverse=True, key=lambda item: item[0])
        return [(user, response) for _, user, response in scored[:limit]]

    def learning_stats(self) -> dict[str, int]:
        with self._lock:
            interactions = self.connection.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
            positive = self.connection.execute(
                "SELECT COUNT(*) FROM interactions WHERE rating = 1"
            ).fetchone()[0]
            corrections = self.connection.execute(
                "SELECT COUNT(*) FROM learned_commands"
            ).fetchone()[0]
        return {"interactions": interactions, "positive": positive, "learned_commands": corrections}

    def clear_learning(self) -> None:
        with self._lock:
            self.connection.execute("DELETE FROM interactions")
            self.connection.execute("DELETE FROM learned_commands")
            self.connection.commit()

    def record_action(
        self, action_id: str, action_name: str, preview: str, status: str, risk: str
    ) -> None:
        with self._lock:
            self.connection.execute(
                "INSERT INTO action_audit (id, action_name, preview, risk, status) "
                "VALUES (?, ?, ?, ?, ?)",
                (action_id, action_name, preview, risk, status),
            )
            self.connection.commit()

    def update_action(self, action_id: str, status: str, detail: str = "") -> None:
        with self._lock:
            self.connection.execute(
                "UPDATE action_audit SET status = ?, detail = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, detail, action_id),
            )
            self.connection.commit()

    def recent_actions(self, limit: int = 10) -> list[dict[str, str]]:
        safe_limit = max(1, min(int(limit), 50))
        with self._lock:
            rows = self.connection.execute(
                "SELECT id, action_name, risk, status, detail, created_at "
                "FROM action_audit ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [
            {
                "id": row[0], "action": row[1], "risk": row[2],
                "status": row[3], "detail": row[4], "created_at": row[5],
            }
            for row in rows
        ]

    @staticmethod
    def _normalize_phrase(text: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def __enter__(self) -> "MemoryManager":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
