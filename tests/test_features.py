import base64
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from core.screen_context import validate_image, analyze_screen
from core.workflows import WorkflowStore
import test_memory as memory_tests

def sample_image():
    import zlib
    def chunk(kind, data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    data = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',32,32,8,2,0,0,0))
    data += chunk(b'IDAT',zlib.compress((b'\x00'+b'\xff\x00\x00'*32)*32))+chunk(b'IEND',b'')
    return 'data:image/png;base64,'+base64.b64encode(data).decode()

class ScreenTests(unittest.TestCase):
    def test_validation_and_local_route(self):
        image=sample_image()
        for invalid in [None,'https://example.com/a.png','data:image/png;base64,!!!']:
            with self.assertRaises(ValueError): validate_image(invalid)
        result=Mock(); result.json.return_value={'message':{'content':'Red square'}}
        with patch('core.screen_context.requests.post',return_value=result) as call:
            self.assertEqual(analyze_screen(image,'What color?'),'Red square')
            self.assertEqual(call.call_args.args[0],'http://127.0.0.1:11435/api/chat')
            self.assertNotIn('tools',call.call_args.kwargs['json'])
            self.assertEqual(len(call.call_args.kwargs['json']['messages'][1]['images']),1)
        huge=bytearray(base64.b64decode(image.split(',')[1])); huge[16:24]=struct.pack('>II',9000,9000)
        with self.assertRaises(ValueError):validate_image('data:image/png;base64,'+base64.b64encode(huge).decode())

class WorkflowTests(unittest.TestCase):
    def test_saved_definitions_and_run_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'flows.db'; store=WorkflowStore(path)
            flow=store.create('Report','Summarize findings',['Read','Summarize'])
            store.add_run('run_test','Report',flow)
            store.update_run('run_test','completed','Finished')
            reopened=WorkflowStore(path)
            self.assertEqual(reopened.get(flow)['steps'],['Read','Summarize'])
            self.assertEqual(reopened.runs()[0]['output'],'Finished')
            with self.assertRaises(ValueError):store.create('Bad','Task',[])
            with self.assertRaises(ValueError):store.create('Bad','Task',['x']*13)

class FeatureApiTests(memory_tests.ApiTests):
    def test_run_approval_only_allows_single_action_or_deny(self):
        response = Mock(status_code=200)
        response.json.return_value = {"resolved": 1}
        with patch.object(memory_tests.server, '_hermes_request', return_value=response) as hermes:
            self.assertEqual(self.request('/api/runs/r-1/approval', {'choice':'always','request_id':'x'})[0], 400)
            self.assertEqual(self.request('/api/runs/r-1/approval', {'choice':'once','request_id':''})[0], 400)
            self.assertEqual(hermes.call_count, 0)
            status, result = self.request('/api/runs/r-1/approval', {'choice':'once','request_id':'req-1'})
            self.assertEqual(status, 200)
            self.assertEqual(result['resolved'], 1)
            self.assertEqual(hermes.call_args.args, ('POST', '/v1/runs/r-1/approval'))
            self.assertEqual(hermes.call_args.kwargs['json'], {'choice':'once','request_id':'req-1'})

    def test_knowledge_index_lists_only_supported_files_from_approved_roots(self):
        server = memory_tests.server
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / 'approved'
            root.mkdir()
            (root / 'resume.pdf').write_bytes(b'%PDF')
            (root / 'ignore.exe').write_bytes(b'no')
            (root / 'node_modules').mkdir()
            (root / 'node_modules' / 'package.json').write_text('{}')
            with patch.object(server, '_KNOWLEDGE_CONFIG', base / 'approved.json'):
                server._save_knowledge_roots([str(root)])
                self.assertEqual(server._knowledge_roots(), [str(root.resolve())])
                files = server._knowledge_files()
                self.assertEqual([item['name'] for item in files], ['resume.pdf'])
                self.assertIn('path', files[0])

    def test_profile_document_is_only_shared_after_explicit_memory_consent(self):
        response=Mock(status_code=202)
        response.json.side_effect=[{'id':'profile-off','status':'queued'}, {'id':'profile-on','status':'queued'}]
        with patch.object(memory_tests.server, '_hermes_request', return_value=response) as hermes, \
             patch.object(memory_tests.server, '_load_profile_reference', return_value='Acceptance profile marker'):
            status, result=self.request('/api/runs', {'message':'Summarize my background'})
            self.assertEqual(status,202)
            self.assertNotIn('Acceptance profile marker', hermes.call_args.kwargs['json']['input'])
            self.assertFalse(result['profile_reference_used'])
            status, result=self.request('/api/runs', {'message':'Summarize my background', 'include_memory':True})
            self.assertEqual(status,202)
            self.assertIn('Acceptance profile marker', hermes.call_args.kwargs['json']['input'])
            self.assertTrue(result['profile_reference_used'])

    def test_tool_event_evidence_filters_failed_calls(self):
        response=Mock(ok=True)
        response.headers={'Content-Type':'text/event-stream'}
        response.text=(
            'data: {"event":"tool.completed","tool":"web_search","error":false}\n\n'
            'data: {"event":"tool.completed","tool":"terminal","error":true}\n\n'
            'data: {"event":"subagent.complete"}\n\n'
        )
        with patch.object(memory_tests.server, '_tool_execution_verified_at', None), \
             patch.object(memory_tests.server, '_tool_execution_verified_tools', set()), \
             patch.object(memory_tests.server, '_hermes_request', return_value=response):
            self.assertEqual(memory_tests.server._hermes_tool_evidence('acceptance-run'), ['delegate_task','web_search'])
            status = memory_tests.server._tool_execution_status()
            self.assertTrue(status['verified'])
            self.assertEqual(status['tools'], ['delegate_task','web_search'])

    def test_explicit_tool_requests_are_not_missed_by_action_check(self):
        self.assertTrue(memory_tests.server._request_requires_tool_evidence(
            'Use the terminal tool now to run printf JARVIS_TOOL_PROBE'))
        self.assertTrue(memory_tests.server._request_requires_tool_evidence(
            'Open the browser and check this page'))
        self.assertFalse(memory_tests.server._request_requires_tool_evidence(
            'What can the terminal tool do?'))

    def test_resume_matching_request_starts_fresh_and_requires_real_tools(self):
        server = memory_tests.server
        request = "Here's my CV. Learn my resume and find matching jobs, then make an Excel file with scores and apply links."
        self.assertTrue(server._JOB_SEARCH_REQUEST.search(request))
        self.assertTrue(server._request_requires_tool_evidence(request))
        with patch.object(server.memory, 'get_recent_context') as history:
            self.assertEqual(server._relevant_continuation_context(request, 'session-x'), [])
            history.assert_not_called()
        self.assertTrue(server._job_export_has_live_evidence(['web_search', 'web_extract']))
        self.assertFalse(server._job_export_has_live_evidence(['terminal']))
        self.assertFalse(server._job_export_has_live_evidence(['web_search']))
        self.assertTrue(server._job_export_has_live_evidence(['web_search', 'browser_navigate']))
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(server, 'EXPORT_ROOT', Path(tmp)):
                output, export = server._extract_job_export(
                    'unverified-export-run',
                    '<jarvis_job_results>{"criteria":{},"jobs":[]}</jarvis_job_results>',
                    allow_export=False,
                )
                self.assertIsNone(export)
                self.assertEqual(output, '')
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_resume_matching_routes_skill_and_makes_real_tool_call_mandatory(self):
        response = Mock(status_code=202)
        response.json.return_value = {'id':'resume-match-run','status':'queued'}
        message = "Here's my CV. Learn my resume and find matching jobs, then make an Excel file with scores and apply links."
        with patch.object(memory_tests.server, '_hermes_request', return_value=response) as hermes, \
             patch.object(memory_tests.server, '_relevant_continuation_context', return_value=[]) as history:
            self.assertEqual(self.request('/api/runs', {'message':message})[0], 202)
        request = hermes.call_args.kwargs['json']
        self.assertTrue(request['model_options']['jarvis_require_tool_call'])
        self.assertIn('This is a job-search task', request['instructions'])
        self.assertIn('do not ask which positions', request['instructions'])
        self.assertNotIn('Recent messages', request['input'])
        history.assert_called_once()

    def test_selected_document_always_requires_a_real_tool_call(self):
        response = Mock(status_code=202)
        response.json.return_value = {'id':'selected-file-run','status':'queued'}
        with tempfile.NamedTemporaryFile(suffix='.txt') as selected_file, \
             patch.object(memory_tests.server, '_local_model_ready', return_value=True), \
             patch.object(memory_tests.server, '_hermes_request', return_value=response) as hermes:
            status, _ = self.request('/api/runs', {
                'message':'What does this say?',
                'attachments':[{'path':selected_file.name}],
            })
        self.assertEqual(status, 202)
        request = hermes.call_args.kwargs['json']
        self.assertTrue(request['model_options']['jarvis_require_tool_call'])
        self.assertIn('User-selected local files', request['input'])

    def test_action_claim_is_marked_unverified_without_completed_tool_events(self):
        self.workflow_patch.stop()
        self.workflow_patch=patch.object(memory_tests.server, 'workflows', WorkflowStore(Path(self.tmp.name)/'guard.db'))
        self.workflow_patch.start()
        memory_tests.server.workflows.add_run('guard-run','Search jobs',request_text='Search for data analyst jobs')
        status_response=Mock(status_code=200)
        status_response.json.return_value={'status':'completed','output':'I searched and found three current roles.'}
        events_response=Mock(ok=True)
        events_response.headers={'Content-Type':'text/event-stream'}
        events_response.text='data: {"event":"run.completed"}\n\n'
        with patch.object(memory_tests.server, '_hermes_request', side_effect=[status_response,events_response]):
            status,data=self.request('/api/runs/guard-run')
        self.assertEqual(status,200)
        self.assertEqual(data['action_verification'],'unverified')
        self.assertEqual(data['tool_evidence'],[])
        self.assertTrue(data['output'].startswith('Action not completed:'))
        self.assertNotIn('three current roles', data['output'])

    def test_screen_and_workflow_routes(self):
        with patch('apps.jarvis.server.analyze_screen',return_value='Red square'):
            status,data=self.request('/api/screen/analyze',{'image':sample_image(),'question':'Color?'})
            self.assertEqual(status,200);self.assertTrue(data['local_only'])
        status,data=self.request('/api/workflows',{'title':'Report','objective':'Read only report','steps':['Read','Summarize']})
        self.assertEqual(status,201)
        flow=data['id']
        response=Mock(status_code=202);response.json.return_value={'id':'run_flow','status':'queued'}
        with patch('apps.jarvis.server._hermes_request',return_value=response) as hermes:
            status,data=self.request('/api/runs',{'workflow_id':flow})
            self.assertEqual(status,202)
            self.assertIn('1. Read',hermes.call_args.kwargs['json']['input'])
            self.assertTrue(hermes.call_args.kwargs['json']['session_id'].startswith('jarvis-run-'))
        status,data=self.request('/api/workflows')
        self.assertEqual(data['runs'][0]['workflow_id'],flow)
        self.assertEqual(self.request('/api/runs',{'workflow_id':9999})[0],400)
        response=Mock(status_code=200);response.json.return_value={'status':'completed','output':'Done'}
        events=Mock(ok=True);events.headers={'Content-Type':'text/event-stream'}
        events.text='data: {"event":"tool.completed","tool":"terminal","error":false}\n\n'
        with patch('apps.jarvis.server._hermes_request',side_effect=[response,events]):
            self.assertEqual(self.request('/api/runs/run_flow')[0],200)
        self.assertEqual(self.request('/api/workflows')[1]['runs'][0]['output'],'Done')
