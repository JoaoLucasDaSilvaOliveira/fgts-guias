import asyncio
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from fgts_guias.decisions import Decisions
from fgts_guias.browser import Portal

class DecisionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.records = []
        self.decisions = Decisions(SimpleNamespace(record_decision=self.records.append))
        self.company = {'cnpj':'00000000000191', 'fgts':100, 'total':100}

    async def test_acceptance_is_consumed_once_and_audited(self):
        descriptor, future = self.decisions.create(self.company, {'scope':'FGTS'}, {'fgts':100}, {'fgts':200})
        self.decisions.accept(descriptor['id'], self.company)
        self.assertTrue(await future)
        with self.assertRaises(ValueError):
            self.decisions.accept(descriptor['id'], self.company)
        self.assertEqual(len(self.records), 1)
        self.assertEqual(self.records[0]['found'], {'fgts':200})

    async def test_changed_input_or_wrong_token_does_not_release(self):
        descriptor, future = self.decisions.create(self.company, {'scope':'FGTS'}, {'fgts':100}, {'fgts':200})
        for token, company in [('expired', self.company), (descriptor['id'], {**self.company, 'fgts':300})]:
            with self.assertRaises(ValueError):
                self.decisions.accept(token, company)
        self.assertFalse(future.done())
        self.assertFalse(self.records)
        self.decisions.clear()

    async def test_new_decision_cannot_use_previous_authorization(self):
        descriptor, _ = self.decisions.create(self.company, {'scope':'FGTS'}, {'fgts':100}, {'fgts':200})
        self.decisions.accept(descriptor['id'], self.company)
        self.decisions.clear()
        new, future = self.decisions.create(self.company, {'scope':'Emissão'}, {'fgts':100}, {'fgts':200})
        self.assertNotEqual(descriptor['id'], new['id'])
        with self.assertRaises(ValueError):
            self.decisions.accept(descriptor['id'], self.company)
        self.assertFalse(future.done())
        self.decisions.clear()

    async def test_resume_and_cancellation_invalidate_pending_decision(self):
        descriptor, future = self.decisions.create(self.company, {}, {}, {})
        self.decisions.retry()
        self.assertFalse(await future)
        with self.assertRaises(ValueError):
            self.decisions.accept(descriptor['id'], self.company)
        self.decisions.clear()
        _, future = self.decisions.create(self.company, {}, {}, {})
        self.decisions.clear()
        self.assertTrue(future.cancelled())

    async def test_changed_portal_value_requires_a_new_decision(self):
        portal = Portal.__new__(Portal)
        requests = []
        async def decide(company, scope, expected, found, **context):
            requests.append(found.copy())
        async def no_op(*args):
            pass
        async def readback():
            return {'fgts':300}
        portal.decision = decide
        portal.guard = no_op
        portal.employer = no_op
        result = await portal.difference(self.company, 'FGTS', {'fgts':100}, {'fgts':200}, readback)
        self.assertEqual(requests, [{'fgts':200}, {'fgts':300}])
        self.assertEqual(result, {'fgts':300})
        await portal.difference(self.company, 'Emissão', {'fgts':100}, {'fgts':300}, readback)
        self.assertEqual(len(requests), 3)

class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_command_releases_only_current_suspended_validation(self):
        from fgts_guias.__main__ import Engine
        from fgts_guias.domain import normalize_row
        source = dict(cod='1', empresa='Empresa de exemplo', cnpj='00000000000191',
                      fgts='1,00', consignado='0,00', total='1,00', observacoes='')
        company = normalize_row(source)
        records = []
        engine = Engine.__new__(Engine)
        engine.store = SimpleNamespace(record_decision=records.append,
            get=lambda *_: {'rows':[source]})
        engine.decisions = Decisions(engine.store)
        engine.current = source
        engine.gate = asyncio.Event()
        engine.gate.set()
        engine.batch_settings = {'initial':'09/2026', 'final':'09/2026'}
        engine.event = lambda *args, **kwargs: None
        async def no_op(*args, **kwargs):
            pass
        engine.portal = SimpleNamespace(guard=no_op, visibility=no_op)
        task = asyncio.create_task(engine.decision(company, 'Vencimento',
            {'due':'20/10/2026'}, {'due':'19/10/2026'}))
        await asyncio.sleep(0)
        token = engine.decisions.pending[0]['id']
        await engine.command('accept_difference', {'decision_id':token})
        await task
        self.assertTrue(engine.gate.is_set())
        self.assertIsNone(engine.decisions.pending)
        self.assertEqual(len(records), 1)
        with self.assertRaises(ValueError):
            await engine.command('accept_difference', {'decision_id':token})

    async def test_pdf_identity_failure_never_offers_acceptance(self):
        portal = Portal.__new__(Portal)
        async def forbidden(*args, **kwargs):
            self.fail('Identidade inválida não pode abrir decisão de aceitação')
        portal.decision = forbidden
        company = dict(cnpj='00000000000191', fgts=100, consignado=0, total=100)
        values = dict(fgts=200, consignado=0, total=200, due='20/10/2026')
        with patch('fgts_guias.files.pdf_values', return_value=values), patch(
                'fgts_guias.browser.validate_pdf', side_effect=ValueError('CNPJ diferente')):
            with self.assertRaisesRegex(ValueError, 'CNPJ diferente'):
                await portal.verify_download('example.pdf', company,
                    {'initial':'09/2026','final':'09/2026'}, '20/10/2026', '0000000000000-0')

if __name__ == '__main__':
    unittest.main()
