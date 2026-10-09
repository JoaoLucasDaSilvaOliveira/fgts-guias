import io
import json
import unittest
from unittest.mock import patch
from fgts_guias.__main__ import configure_stdio


class ProtocolEncodingTests(unittest.TestCase):
    def test_utf8_requests_and_events_with_windows_default_code_page(self):
        request = {'command':'save', 'data':{'empresa':'Empresa São José', 'observacoes':'Conferência'}}
        incoming = io.BytesIO((json.dumps(request, ensure_ascii=False) + '\n').encode('utf-8'))
        outgoing = io.BytesIO()
        diagnostic = io.BytesIO()
        stdin = io.TextIOWrapper(incoming, encoding='cp1252')
        stdout = io.TextIOWrapper(outgoing, encoding='cp1252')
        stderr = io.TextIOWrapper(diagnostic, encoding='cp1252')
        with patch('sys.stdin', stdin), patch('sys.stdout', stdout), patch('sys.stderr', stderr):
            configure_stdio()
            self.assertEqual(json.loads(stdin.readline()), request)
            print(json.dumps({'event':'progress','message':'Abrindo empresa… São José'}, ensure_ascii=False), flush=True)
            stderr.write('Autenticação necessária\n')
            stderr.flush()
        event = json.loads(outgoing.getvalue().decode('utf-8'))
        self.assertEqual(event['message'], 'Abrindo empresa… São José')
        self.assertEqual(diagnostic.getvalue().decode('utf-8'), 'Autenticação necessária\n')
