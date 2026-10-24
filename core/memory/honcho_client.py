from contextlib import closing
import sqlite3
import json
from pathlib import Path
import time
import uuid
import logging
import re

logger = logging.getLogger(__name__)

class LocalMemoryStore:
    """
    A persistent local memory store acting as a stand-in for Honcho (Plastic Labs).
    Provides dialectic memory: stable facts, project states, and session history.
    """
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        # Stable facts
        cur.execute('''
            CREATE TABLE IF NOT EXISTS stable_facts (
                id INTEGER PRIMARY KEY,
                category TEXT,
                fact TEXT,
                timestamp REAL
            )
        ''')
        # Add provenance without replacing existing facts or conversations.
        columns = {row[1] for row in cur.execute("PRAGMA table_info(stable_facts)")}
        for name, definition in (("source", "TEXT NOT NULL DEFAULT 'legacy'"),
                                 ("updated_at", "REAL")):
            if name not in columns:
                cur.execute(f"ALTER TABLE stable_facts ADD COLUMN {name} {definition}")
        # Session memory
        cur.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY,
                role TEXT,
                content TEXT,
                timestamp REAL
            )
        ''')
        cur.execute("CREATE TABLE IF NOT EXISTS recorded_runs (run_id TEXT PRIMARY KEY)")
        cur.execute("CREATE TABLE IF NOT EXISTS application_state (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.commit()
        conn.close()

    def chat_session(self, new=False):
        # Persist the selected conversation across web restarts. Never reuse the
        # legacy hardcoded session, which may be paused after unknown execution.
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT value FROM application_state WHERE key='chat_session'").fetchone()
            if row and not new:
                return row[0]
            session_id = 'jarvis-chat-' + uuid.uuid4().hex
            conn.execute("INSERT OR REPLACE INTO application_state(key,value) VALUES('chat_session',?)", (session_id,))
            return session_id

    def add_run_result(self, run_id, content):
        # One transaction keeps repeated dashboard polling/restarts from duplicating history.
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            inserted = conn.execute("INSERT OR IGNORE INTO recorded_runs(run_id) VALUES(?)", (run_id,)).rowcount
            if inserted and content:
                conn.execute("INSERT INTO conversation_history(role,content,timestamp) VALUES('assistant',?,?)",
                             (content, time.time()))

    @staticmethod
    def _validate_fact(category, fact):
        if not isinstance(category, str) or not 1 <= len(category.strip()) <= 80:
            raise ValueError("Category must be 1 to 80 characters")
        if not isinstance(fact, str) or not 1 <= len(fact.strip()) <= 2000:
            raise ValueError("Memory must be 1 to 2,000 characters")
        return category.strip(), fact.strip()

    def add_fact(self, category: str, fact: str, source: str = "user"):
        category, fact = self._validate_fact(category, fact)
        if source not in {"user", "legacy"}:
            raise ValueError("Invalid memory source")
        now = time.time()
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            cur = conn.execute(
                "INSERT INTO stable_facts (category, fact, timestamp, source, updated_at) VALUES (?, ?, ?, ?, ?)",
                (category, fact, now, source, now))
            return cur.lastrowid

    def list_facts(self):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(
                "SELECT id, category, fact AS content, timestamp AS created_at, "
                "COALESCE(updated_at, timestamp) AS updated_at, source FROM stable_facts ORDER BY id DESC")]

    def update_fact(self, fact_id, category, fact):
        category, fact = self._validate_fact(category, fact)
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            return conn.execute(
                "UPDATE stable_facts SET category=?, fact=?, updated_at=?, source='user' WHERE id=?",
                (category, fact, time.time(), fact_id)).rowcount > 0

    def delete_fact(self, fact_id):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            return conn.execute("DELETE FROM stable_facts WHERE id=?", (fact_id,)).rowcount > 0

    def relevant_facts(self, query, limit=8, max_chars=4000):
        # Bounded lexical retrieval; preferences/profile apply across requests.
        words = set(re.findall(r"[^\W_]{3,}", query.casefold()))
        ranked = []
        for item in self.list_facts():
            tokens = set(re.findall(r"[^\W_]{3,}", (item['category'] + ' ' + item['content']).casefold()))
            score = len(words & tokens)
            if score or item['category'].casefold() in {'preferences', 'profile'}:
                ranked.append((score, item))
        ranked.sort(key=lambda pair: (-pair[0], -pair[1]['id']))
        selected, used = [], 0
        for _, item in ranked:
            size = len(json.dumps(item, ensure_ascii=False))
            if used + size <= max_chars:
                selected.append(item)
                used += size
            if len(selected) >= limit:
                break
        return selected

    def get_facts(self, category: str = None) -> list:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        if category:
            cur.execute("SELECT fact FROM stable_facts WHERE category = ?", (category,))
        else:
            cur.execute("SELECT category, fact FROM stable_facts")
        results = cur.fetchall()
        conn.close()
        return results

    def add_message(self, role: str, content: str):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO conversation_history (role, content, timestamp) VALUES (?, ?, ?)",
                    (role, content, time.time()))
        conn.commit()
        conn.close()

    def get_recent_context(self, limit: int = 10) -> list:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT role, content FROM conversation_history ORDER BY timestamp DESC LIMIT ?", (limit,))
        results = cur.fetchall()
        conn.close()
        return list(reversed(results))
