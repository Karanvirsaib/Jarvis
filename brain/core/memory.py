import sqlite3
from pathlib import Path


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
