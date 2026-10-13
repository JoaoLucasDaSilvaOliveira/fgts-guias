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

    def accept_values(self, expected, found):
        context = {'initial':'09/2026', 'final':'09/2026', 'scope':'Consignado'}
        descriptor, _ = self.decisions.create(self.company, context, expected, found)
        self.decisions.accept(descriptor['id'], self.company)
        self.decisions.clear()
        return context

    async def test_same_components_across_steps_and_derived_total_are_reused(self):
        expected = {'fgts':100,'consignado':50,'total':150}
        found = {'fgts':100,'consignado':70,'total':170}
        context = self.accept_values(expected, found)
        for scope in ('Consignado', 'Vencimento', 'Emissão', 'Conferência do PDF'):
            self.assertTrue(self.decisions.covered(self.company, {**context,'scope':scope}, expected, found))
        self.assertTrue(self.decisions.covered(self.company, context, {'total':150}, {'total':170}))
        self.assertEqual(len(self.records), 1)

    async def test_changed_pair_or_new_field_requires_acceptance(self):
        expected = {'fgts':100,'consignado':50,'total':150}
        found = {'fgts':100,'consignado':70,'total':170}
        context = self.accept_values(expected, found)
        self.assertFalse(self.decisions.covered(self.company, context, expected, {**found,'fgts':110,'total':180}))
        self.assertFalse(self.decisions.covered(self.company, context, expected, {**found,'consignado':80,'total':180}))
        self.assertFalse(self.decisions.covered(self.company, context, expected, found))

    async def test_return_to_expected_invalidates_old_value(self):
        context = self.accept_values({'consignado':50},{'consignado':70})
        self.decisions.observe(self.company, context, {'consignado':50},{'consignado':50})
        self.assertFalse(self.decisions.covered(self.company, context, {'consignado':50},{'consignado':70}))

    async def test_company_iteration_period_and_expected_value_are_boundaries(self):
        context = self.accept_values({'consignado':50},{'consignado':70})
        self.assertFalse(self.decisions.covered(self.company, context, {'consignado':60},{'consignado':70}))
        context = self.accept_values({'consignado':50},{'consignado':70})
        self.assertFalse(self.decisions.covered(self.company, {**context,'initial':'10/2026'}, {'consignado':50},{'consignado':70}))
        context = self.accept_values({'consignado':50},{'consignado':70})
        self.assertFalse(self.decisions.covered({**self.company,'cnpj':'11111111000111'}, context, {'consignado':50},{'consignado':70}))
        context = self.accept_values({'consignado':50},{'consignado':70})
        self.decisions.reset_company()
        self.assertFalse(self.decisions.covered(self.company, context, {'consignado':50},{'consignado':70}))

    async def test_unexplained_total_and_new_date_are_not_covered(self):
        expected = {'fgts':100,'consignado':50,'total':150}
        found = {'fgts':100,'consignado':70,'total':170}
        context = self.accept_values(expected, found)
        self.assertFalse(self.decisions.covered(self.company, context, expected, {**found,'total':180}))
        self.assertFalse(self.decisions.covered(self.company, context,
            {**expected,'due':'20/10/2026'},{**found,'due':'19/10/2026'}))

    async def test_acceptance_is_consumed_once_and_audited(self):
        descriptor, future = self.decisions.create(self.company, {'scope':'FGTS'}, {'fgts':100}, {'fgts':200})
        self.decisions.accept(descriptor['id'], self.company)
        self.assertTrue(await future)
        with self.assertRaises(ValueError):
            self.decisions.accept(descriptor['id'], self.company)
        self.assertEqual(len(self.records), 1)
        self.assertEqual(self.records[0]['found'], {'fgts':200})

    async def test_rejection_consumes_only_current_decision_and_audits(self):
        descriptor, future = self.decisions.create(self.company, {}, {}, {})
        with self.assertRaises(ValueError):
            self.decisions.reject('expired')
        self.assertFalse(future.done())
        self.decisions.reject(descriptor['id'])
        self.assertFalse(await future)
        self.assertEqual(self.records[0]['action'], 'rejected')
        with self.assertRaises(ValueError):
            self.decisions.accept(descriptor['id'], self.company)
        with self.assertRaises(ValueError):
            self.decisions.reject(descriptor['id'])
        self.assertEqual(len(self.records), 1)

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
    async def test_cross_step_reuse_still_rereads_and_checks_identity(self):
        from fgts_guias.__main__ import Engine
        engine = Engine.__new__(Engine)
        engine.decisions = Decisions(SimpleNamespace(record_decision=lambda *_: None))
        engine.batch_settings = {'initial':'09/2026','final':'09/2026'}
        engine.gate = asyncio.Event()
        engine.gate.set()
        company = {'cnpj':'00000000000191'}
        expected, found = {'consignado':50}, {'consignado':70}
        confirmations, checks = [], []
        def event(kind, **data):
            if kind == 'attention':
                confirmations.append(data)
                engine.decisions.accept(data['decision_id'], company)
                engine.gate.set()
        engine.event = event
        portal = Portal.__new__(Portal)
        portal.decision = engine.decision
        portal.observe = engine.observe_difference
        async def guard(*args): checks.append('guard')
        async def employer(*args): checks.append('employer')
        async def visibility(*args): pass
        async def readback():
            checks.append('readback')
            return found.copy()
        portal.guard, portal.employer, portal.visibility = guard, employer, visibility
        engine.portal = portal
        for scope in ('Consignado', 'Emissão', 'Conferência do PDF'):
            self.assertEqual(await portal.difference(company, scope, expected, found, readback), found)
        self.assertEqual(len(confirmations), 1)
        self.assertEqual(checks.count('employer'), 3)
        self.assertEqual(checks.count('readback'), 3)
        found = {'consignado':80}
        await portal.difference(company, 'Emissão', expected, found, readback)
        self.assertEqual(len(confirmations), 2)
        engine.decisions.reset_company()
        await portal.difference(company, 'Consignado', expected, found, readback)
        self.assertEqual(len(confirmations), 3)

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

    async def test_reject_command_keeps_batch_paused_for_review(self):
        from fgts_guias.__main__ import Engine
        from fgts_guias.decisions import RetryCompany
        engine = Engine.__new__(Engine)
        records, events = [], []
        engine.store = SimpleNamespace(record_decision=records.append)
        engine.decisions = Decisions(engine.store)
        engine.current = {'cnpj':'00000000000191'}
        engine.gate = asyncio.Event()
        engine.gate.set()
        engine.batch_settings = {'initial':'09/2026', 'final':'09/2026'}
        engine.event = lambda kind, **data: events.append((kind, data))
        async def no_op(*args, **kwargs):
            pass
        engine.portal = SimpleNamespace(visibility=no_op)
        task = asyncio.create_task(engine.decision(engine.current, 'FGTS',
            {'fgts':100}, {'fgts':200}))
        await asyncio.sleep(0)
        token = engine.decisions.pending[0]['id']
        await engine.command('reject_difference', {'decision_id':token})
        with self.assertRaises(RetryCompany):
            await task
        self.assertFalse(engine.gate.is_set())
        self.assertIsNone(engine.decisions.pending)
        self.assertEqual(events[-1][0], 'attention')
        self.assertNotIn('decision_id', events[-1][1])
        self.assertEqual(records[0]['action'], 'rejected')

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
