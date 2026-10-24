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
            self.assertTrue(hermes.call_args.kwargs['json']['session_id'].startswith('jarvis-workflow-'))
        status,data=self.request('/api/workflows')
        self.assertEqual(data['runs'][0]['workflow_id'],flow)
        self.assertEqual(self.request('/api/runs',{'workflow_id':9999})[0],400)
        response=Mock(status_code=200);response.json.return_value={'status':'completed','output':'Done'}
        with patch('apps.jarvis.server._hermes_request',return_value=response):
            self.assertEqual(self.request('/api/runs/run_flow')[0],200)
        self.assertEqual(self.request('/api/workflows')[1]['runs'][0]['output'],'Done')
