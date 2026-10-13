import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from fgts_guias.domain import normalize_row
from fgts_guias.files import read_table, write_table
from fgts_guias.inss import InssPortal, Attention
from fgts_guias.inss_pdf import parse_darf
from fgts_guias.storage import Storage

TEXT = '''Documento de Arrecadação de Receitas Federais
12.345.678/0001-95 Empresa de exemplo
Número do Documento
07.16.26286.1234567-8 Pagar este documento até
20/10/2026 Observações
Valor Total do Documento
123,45
setembro/2026 20/10/2026
PA:09/2026 Vencimento:20/10/2026
Número: 07.16.26286.1234567-8
Pagar até: 20/10/2026
Valor: 123,45
'''

class InssDataTests(unittest.TestCase):
    def test_darf_fields_and_conflicting_identity_period_amount(self):
        values = parse_darf(TEXT)
        self.assertEqual(values, dict(cnpj='12345678000195', guide='07.16.26286.1234567-8',
            inss=12345, period='09/2026', due='20/10/2026'))
        for extra in ('\n98.765.432/0001-98', '\nPA:08/2026', '\nValor: 999,99', '\nPagar até: 21/10/2026'):
            with self.assertRaises(ValueError): parse_darf(TEXT + extra)
    def test_inss_does_not_depend_on_fgts_and_template_roundtrip(self):
        source = dict(cod='1',empresa='Empresa de exemplo',cnpj='12345678000195',inss='123,45')
        self.assertEqual(normalize_row(source, 'inss')['inss'],12345)
        with self.assertRaises(ValueError): normalize_row({**source,'inss':''}, 'inss')
        with tempfile.TemporaryDirectory() as folder:
            for suffix in ('csv','xlsx'):
                path = Path(folder)/('example.'+suffix)
                write_table(path,[source],'inss')
                row = read_table(path,'inss')[0]
                self.assertEqual(normalize_row(row,'inss')['inss'],12345)
                self.assertNotIn('fgts',row)
    def test_inss_and_fgts_history_do_not_collide(self):
        store=Storage.__new__(Storage)
        company={'cnpj':'12345678000195'}
        self.assertEqual(store.job_key(company,'09/2026','09/2026'),'12345678000195:09/2026:09/2026')
        self.assertNotEqual(store.job_key(company,'09/2026','09/2026'),store.job_key(company,'09/2026','09/2026','inss'))

class InssWorkflowTests(unittest.IsolatedAsyncioTestCase):
    def portal(self, job):
        store = SimpleNamespace(root=Path(tempfile.gettempdir()), job=lambda *_:job,
            job_key=lambda *_:'inss:example', save_job=lambda *_:None)
        events=[]
        portal=InssPortal(store,lambda event,**data:events.append((event,data)),AsyncMock(),lambda:None)
        portal.launch=AsyncMock()
        portal.profile=AsyncMock()
        return portal,events
    async def test_uncertain_issue_never_clicks_issue_again(self):
        company={'cnpj':'12345678000195','inss':12345}
        for state in ('issuing','download_pending'):
            portal,_=self.portal({'state':state,'company':company})
            with self.assertRaises(Attention) as error:
                await portal.run(company,{'initial':'09/2026','final':'09/2026'})
            self.assertTrue(error.exception.details['recovery'])
            portal.profile.assert_not_called()
    async def test_saved_pdf_reused_only_after_validation(self):
        company={'cnpj':'12345678000195','empresa':'Exemplo','inss':12345}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'INSS/Exemplo.pdf'
            job={'state':'saved','company':company,'path':str(path),'guide':'number','due':'20/10/2026'}
            portal,events=self.portal(job)
            with patch('fgts_guias.inss.validate_darf') as validate:
                await portal.run(company,{'initial':'09/2026','final':'09/2026','output':folder})
                validate.assert_called_once()
            self.assertTrue(events[-1][1]['reused'])
            portal.profile.assert_not_called()
    async def test_failure_to_close_prevents_service_change(self):
        from fgts_guias.__main__ import Engine
        engine=Engine.__new__(Engine)
        engine.service='fgts'; engine.task=None; engine.auth_watcher=None
        engine.portal=SimpleNamespace(close=AsyncMock(side_effect=ValueError('still open')))
        original=engine.portal
        with self.assertRaises(ValueError): await engine.select_service('inss')
        self.assertEqual(engine.service,'fgts')
        self.assertIs(engine.portal,original)
    async def test_active_batch_cannot_change_service(self):
        from fgts_guias.__main__ import Engine
        engine=Engine.__new__(Engine)
        engine.service='fgts'; engine.task=SimpleNamespace(done=lambda:False)
        with self.assertRaises(ValueError): await engine.select_service('inss')
