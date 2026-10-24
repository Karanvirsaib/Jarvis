"""Jarvis workflow definitions and run references; Hermes owns execution."""
from contextlib import closing
import json
import sqlite3
import time

TERMINAL = {'completed', 'failed', 'cancelled', 'expired'}

class WorkflowStore:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn, conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY, title TEXT NOT NULL, objective TEXT NOT NULL,
                    steps TEXT NOT NULL, created_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id TEXT PRIMARY KEY, workflow_id INTEGER, title TEXT NOT NULL,
                    status TEXT NOT NULL, output TEXT NOT NULL DEFAULT '', updated_at REAL NOT NULL);
            ''')
    def connect(self):
        return closing(sqlite3.connect(self.path))
    def create(self, title, objective, steps):
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 100:
            raise ValueError('Title must be 1 to 100 characters')
        if not isinstance(objective, str) or not 1 <= len(objective.strip()) <= 2000:
            raise ValueError('Objective must be 1 to 2,000 characters')
        if not isinstance(steps, list) or not 1 <= len(steps) <= 12:
            raise ValueError('Provide 1 to 12 steps')
        if any(not isinstance(step, str) or not 1 <= len(step.strip()) <= 400 for step in steps):
            raise ValueError('Each step must be 1 to 400 characters')
        with self.connect() as conn, conn:
            return conn.execute('INSERT INTO workflows(title,objective,steps,created_at) VALUES(?,?,?,?)',
                (title.strip(), objective.strip(), json.dumps([s.strip() for s in steps]), time.time())).lastrowid
    def list(self):
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            items = [dict(row) for row in conn.execute('SELECT * FROM workflows ORDER BY id DESC')]
        for item in items:
            item['steps'] = json.loads(item['steps'])
        return items
    def get(self, workflow_id):
        return next((item for item in self.list() if item['id'] == workflow_id), None)
    def add_run(self, run_id, title, workflow_id=None, status='queued'):
        with self.connect() as conn, conn:
            conn.execute('INSERT OR IGNORE INTO workflow_runs(run_id,workflow_id,title,status,updated_at) VALUES(?,?,?,?,?)',
                (run_id, workflow_id, title[:100], status, time.time()))
    def update_run(self, run_id, status, output=''):
        with self.connect() as conn, conn:
            conn.execute('UPDATE workflow_runs SET status=?,output=?,updated_at=? WHERE run_id=?',
                (status, output[:50000], time.time(), run_id))
    def runs(self):
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute('SELECT * FROM workflow_runs ORDER BY updated_at DESC LIMIT 100')]
