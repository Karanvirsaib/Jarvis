from contextlib import closing
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from core.memory.honcho_client import LocalMemoryStore
from apps.jarvis import server

class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'memory.db'
        self.store = LocalMemoryStore(self.path)
    def tearDown(self):
        self.tmp.cleanup()
    def test_legacy_migration_preserves_history_and_facts(self):
        legacy = Path(self.tmp.name) / 'legacy.db'
        with closing(sqlite3.connect(legacy)) as conn, conn:
            conn.execute('CREATE TABLE stable_facts (id INTEGER PRIMARY KEY, category TEXT, fact TEXT, timestamp REAL)')
            conn.execute("INSERT INTO stable_facts VALUES (1, 'Project', 'Uses Python', 100)")
        first = LocalMemoryStore(legacy)
        first.add_message('user', 'sample')
        second = LocalMemoryStore(legacy)
        self.assertEqual(second.list_facts()[0]['source'], 'legacy')
        self.assertEqual(second.list_facts()[0]['content'], 'Uses Python')
        self.assertEqual(second.get_recent_context(), [('user', 'sample')])
    def test_crud_survives_restart(self):
        fact_id = self.store.add_fact('Project', 'Uses Python')
        self.assertTrue(self.store.update_fact(fact_id, 'Project', 'Uses SQLite'))
        reopened = LocalMemoryStore(self.path)
        self.assertEqual(reopened.list_facts()[0]['content'], 'Uses SQLite')
        self.assertTrue(reopened.delete_fact(fact_id))
        self.assertFalse(reopened.delete_fact(fact_id))
        self.assertEqual(reopened.relevant_facts('SQLite'), [])
    def test_chat_session_persists_and_rotates_without_deleting_history(self):
        self.store.add_message('user', 'Keep this history')
        first = self.store.chat_session()
        self.assertTrue(first.startswith('jarvis-chat-'))
        self.assertEqual(LocalMemoryStore(self.path).chat_session(), first)
        second = self.store.chat_session(new=True)
        self.assertNotEqual(first, second)
        self.assertEqual(LocalMemoryStore(self.path).chat_session(), second)
        self.assertEqual(self.store.get_recent_context(), [('user', 'Keep this history')])

    def test_chat_history_and_assistant_results_are_session_scoped(self):
        first = self.store.chat_session()
        self.store.add_message('user', 'First conversation detail', session_id=first)
        self.store.set_run_session('run_first', first)
        self.store.add_run_result('run_first', 'First conversation answer')
        second = self.store.chat_session(new=True)
        self.store.add_message('user', 'Second conversation detail', session_id=second)
        self.assertEqual(self.store.get_recent_context(session_id=first), [
            ('user', 'First conversation detail'), ('assistant', 'First conversation answer')])
        self.assertEqual(self.store.get_recent_context(session_id=second), [
            ('user', 'Second conversation detail')])

    def test_terminal_run_history_is_idempotent_across_restart(self):
        self.store.add_run_result('run_example', 'Completed')
        reopened = LocalMemoryStore(self.path)
        reopened.add_run_result('run_example', 'Completed')
        self.assertEqual(reopened.get_recent_context(), [('assistant', 'Completed')])

    def test_validation_and_retrieval_budget(self):
        for category, content in [('', 'x'), ('x', ''), ('x', 'x'*2001), (None, 'x')]:
            with self.assertRaises(ValueError): self.store.add_fact(category, content)
        self.store.add_fact('Project', 'Jarvis uses SQLite')
        self.store.add_fact('Travel', 'Visit Japan')
        self.store.add_fact('Preferences', 'Prefer concise replies')
        results = self.store.relevant_facts('Jarvis SQLite')
        self.assertEqual(results[0]['category'], 'Project')
        self.assertEqual(len(results), 2)
        self.assertEqual(self.store.relevant_facts('SQLite', max_chars=1), [])

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = LocalMemoryStore(Path(self.tmp.name) / 'test.db')
        self.memory_patch = patch.object(server, 'memory', self.store)
        self.memory_patch.start()
        self.workflow_patch = patch.object(server, 'workflows', server.WorkflowStore(Path(self.tmp.name) / 'workflows.db'))
        self.workflow_patch.start()
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), server.JarvisHandler)
        self.base = f'http://127.0.0.1:{self.http.server_port}'
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
    def tearDown(self):
        self.http.shutdown(); self.http.server_close(); self.thread.join()
        self.memory_patch.stop(); self.workflow_patch.stop(); self.tmp.cleanup()
    def request(self, path, data=None, origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin: headers['Origin'] = origin
        req = Request(self.base+path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try:
            with urlopen(req) as response: return response.status, json.load(response)
        except HTTPError as error: return error.code, json.load(error)
    def test_crud_and_origin(self):
        self.assertEqual(self.request('/api/memory', {'category':'Profile','content':'Test'}, 'http://evil.example')[0],403)
        self.assertEqual(self.request('/api/memory', {'category':'Profile','content':'Test'}, 'http://127.0.0.1:1')[0],403)
        status, result = self.request('/api/memory', {'category':'Profile','content':'Test'}, self.base)
        self.assertEqual(status,201)
        fact_id = result['id']
        self.assertEqual(self.request('/api/memory')[1]['facts'][0]['source'],'user')
        self.assertEqual(self.request(f'/api/memory/{fact_id}/update', {'category':'Profile','content':'Changed'})[0],200)
        self.assertEqual(self.request(f'/api/memory/{fact_id}/delete', {})[0],200)
        self.assertEqual(self.request(f'/api/memory/{fact_id}/update', {'category':'Profile','content':'Changed'})[0],404)
        self.assertEqual(self.request('/api/memory', [1])[0],400)
        self.assertEqual(self.request('/api/memory', {'category':'Profile','content':''})[0],400)
    def test_new_conversation_routes_to_fresh_persistent_session(self):
        response = unittest.mock.Mock(status_code=202)
        response.json.return_value = {'id':'test-chat','status':'queued'}
        with patch.object(server, '_hermes_request', return_value=response) as hermes:
            self.assertEqual(self.request('/api/runs', {'message':'Hello'})[0],202)
            first = hermes.call_args.kwargs['json']['session_id']
            self.assertNotEqual(first, 'jarvis-local-workspace')
            self.request('/api/runs', {'message':'Again'})
            second = hermes.call_args.kwargs['json']['session_id']
            self.assertNotEqual(second, first)
            status, result = self.request('/api/chat/new', {})
            self.assertEqual(status,200)
            self.request('/api/runs', {'message':'Fresh'})
            third = hermes.call_args.kwargs['json']['session_id']
            self.assertNotEqual(third, result['session_id'])
            self.assertNotEqual(second, third)

    def test_run_memory_is_explicit_and_bounded(self):
        self.store.add_fact('Preferences','Prefer concise replies')
        response = unittest.mock.Mock(status_code=202)
        response.json.return_value = {'id':'test-run','status':'queued'}
        with patch.object(server, '_hermes_request', return_value=response) as hermes:
            status, result = self.request('/api/runs', {'message':'Hello'})
            self.assertEqual(status,202)
            self.assertEqual(hermes.call_args.kwargs['json']['input'],'Hello')
            self.assertEqual(result['memory_used'],[])
            status, result = self.request('/api/runs', {'message':'Hello', 'include_memory':True})
            self.assertIn('Prefer concise replies',hermes.call_args.kwargs['json']['input'])
            self.assertEqual(len(result['memory_used']),1)
            self.assertEqual(self.request('/api/runs', {'message':'Hello','include_memory':'yes'})[0],400)
            self.assertEqual(hermes.call_count,2)

    def test_same_chat_context_is_included_but_new_chat_context_is_isolated(self):
        response=unittest.mock.Mock(status_code=202)
        response.json.return_value={'id':'context-run','status':'queued'}
        with patch.object(server, '_hermes_request', return_value=response) as hermes:
            self.assertEqual(self.request('/api/runs', {'message':'Find data analyst roles in Toronto'})[0],202)
            self.request('/api/runs', {'message':'Check this as well'})
            same_chat_input=hermes.call_args.kwargs['json']['input']
            self.assertIn('Find data analyst roles in Toronto', same_chat_input)
            fresh=self.request('/api/chat/new', {})[1]['session_id']
            self.request('/api/runs', {'message':'Check this as well'})
            new_chat_input=hermes.call_args.kwargs['json']['input']
            self.assertNotEqual(hermes.call_args.kwargs['json']['session_id'], fresh)
            self.assertNotIn('Find data analyst roles in Toronto', new_chat_input)

if __name__ == '__main__': unittest.main()
