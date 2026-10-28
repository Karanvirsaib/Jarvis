"""Local content planning board and brand context store."""

import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path


STAGES = ("idea", "research", "draft", "review", "approved", "published")
CHANNELS = ("Instagram", "YouTube", "LinkedIn", "TikTok", "X", "Newsletter", "Website")
FORMATS = ("Short video", "Long video", "Carousel", "Post", "Newsletter", "Article")


class ContentStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS content_profile (
                id INTEGER PRIMARY KEY CHECK (id=1), brand TEXT NOT NULL DEFAULT '', audience TEXT NOT NULL DEFAULT '',
                voice TEXT NOT NULL DEFAULT '', pillars TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("INSERT OR IGNORE INTO content_profile(id) VALUES (1)")
            db.execute("""CREATE TABLE IF NOT EXISTS content_items (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, channel TEXT NOT NULL, format TEXT NOT NULL,
                topic TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', stage TEXT NOT NULL DEFAULT 'idea',
                run_id TEXT, research_requested INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(content_items)")}
            if "research_requested" not in columns:
                db.execute("ALTER TABLE content_items ADD COLUMN research_requested INTEGER NOT NULL DEFAULT 0")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def profile(self):
        with self._connect() as db:
            return dict(db.execute("SELECT brand,audience,voice,pillars,updated_at FROM content_profile WHERE id=1").fetchone())

    def save_profile(self, brand, audience, voice, pillars):
        values = [str(item or "").strip() for item in (brand, audience, voice, pillars)]
        limits = (160, 1200, 1600, 1200)
        if any(len(value) > limit for value, limit in zip(values, limits)):
            raise ValueError("Brand profile field exceeds its character limit.")
        with self._connect() as db:
            db.execute("""UPDATE content_profile SET brand=?,audience=?,voice=?,pillars=?,updated_at=CURRENT_TIMESTAMP WHERE id=1""", values)
        return self.profile()

    def create(self, title, channel, content_format, topic, notes=""):
        values = [str(item or "").strip() for item in (title, channel, content_format, topic, notes)]
        title, channel, content_format, topic, notes = values
        if not title or len(title) > 140 or channel not in CHANNELS or content_format not in FORMATS or not topic or len(topic) > 2500 or len(notes) > 2500:
            raise ValueError("Provide a title, supported channel and format, and a topic. Check field limits.")
        item_id = uuid.uuid4().hex
        with self._connect() as db:
            db.execute("INSERT INTO content_items(id,title,channel,format,topic,notes) VALUES (?,?,?,?,?,?)", (item_id, title, channel, content_format, topic, notes))
        return self.get(item_id)

    def list(self):
        with self._connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM content_items ORDER BY updated_at DESC,created_at DESC")]

    def get(self, item_id):
        with self._connect() as db:
            row = db.execute("SELECT * FROM content_items WHERE id=?", (item_id,)).fetchone()
        return dict(row) if row else None

    def update_stage(self, item_id, stage):
        if stage not in STAGES:
            raise ValueError("Unsupported content stage.")
        with self._connect() as db:
            cursor = db.execute("UPDATE content_items SET stage=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (stage, item_id))
        return self.get(item_id) if cursor.rowcount else None

    def attach_run(self, item_id, run_id, research_requested=False):
        if not isinstance(run_id, str) or not run_id or len(run_id) > 160:
            raise ValueError("Invalid run id.")
        if not isinstance(research_requested, bool):
            raise ValueError("Invalid research setting.")
        with self._connect() as db:
            cursor = db.execute("UPDATE content_items SET run_id=?,research_requested=?,stage='research',updated_at=CURRENT_TIMESTAMP WHERE id=?", (run_id, int(research_requested), item_id))
        return self.get(item_id) if cursor.rowcount else None
