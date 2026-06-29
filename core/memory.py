import sqlite3
from pathlib import Path
import re


class MemoryManager:

    def __init__(self):
        Path("data").mkdir(exist_ok=True)

        self.conn = sqlite3.connect("data/jarvis.db")
        self.cursor = self.conn.cursor()

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        self.conn.commit()

    # -------------------------
    # BASIC MEMORY FUNCTIONS
    # -------------------------

    def remember(self, key, value):
        self.cursor.execute(
            "INSERT OR REPLACE INTO memory VALUES (?, ?)",
            (key, value)
        )
        self.conn.commit()

    def recall(self, key):
        self.cursor.execute(
            "SELECT value FROM memory WHERE key=?",
            (key,)
        )

        result = self.cursor.fetchone()
        return result[0] if result else None

    # -------------------------
    # AUTO MEMORY EXTRACTION
    # -------------------------

    def extract_and_store(self, text: str):

    text_lower = text.lower().strip()

    patterns = [
        (r"^my name is (.+)$", "name"),
        (r"^i am (.+)$", "identity"),
        (r"^my favorite language is (.+)$", "favorite_language"),
        (r"^i like (.+)$", "preference")
    ]

    for pattern, key in patterns:
        match = re.match(pattern, text_lower)

        if match:
            value = match.group(1).strip()

            # safety filter: ignore junk like "i?"
            if len(value) < 2 or "?" in value:
                return None

            self.remember(key, value)
            return f"Stored {key} = {value}"

    return None
