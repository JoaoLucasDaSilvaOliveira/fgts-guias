import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from fgts_guias.browser import Portal, Attention

class RerunTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.company = dict(cnpj='00000000000191', empresa='Empresa de exemplo',
                            fgts=100, consignado=0, total=100)
        self.settings = dict(initial='09/2026', final='09/2026', output='/tmp')
        self.previous = dict(state='saved', company=self.company.copy(),
                             path='/tmp/Empresa de exemplo.pdf', due='20/10/2026', guide='0123456789012-3')
        self.portal = Portal.__new__(Portal)
        self.portal.store = SimpleNamespace(job_key=lambda *_:'example', job=lambda *_:self.previous)
        self.portal.launch = AsyncMock()
        self.portal.guard = AsyncMock()
        self.portal.notify = Mock()
        self.portal.recover_from_portal = AsyncMock()
        self.portal.profile = AsyncMock(side_effect=AssertionError('Emissão não deve iniciar'))

    async def test_default_reuses_saved_pdf_on_every_run(self):
        with patch('fgts_guias.browser.validate_pdf') as validate:
            await self.portal.run(self.company, self.settings)
            await self.portal.run(self.company, self.settings)
        self.assertEqual(validate.call_count, 2)
        self.portal.recover_from_portal.assert_not_awaited()
        self.assertEqual(self.portal.notify.call_args.kwargs['reused'], True)
        self.portal.profile.assert_not_awaited()

    async def test_redownload_recovers_existing_guide_without_using_cache(self):
        with patch('fgts_guias.browser.validate_pdf') as validate:
            await self.portal.run(self.company, {**self.settings, 'downloadSaved':True})
        validate.assert_not_called()
        self.portal.recover_from_portal.assert_awaited_once()
        self.assertEqual(self.previous['guide'], '0123456789012-3')
        self.portal.profile.assert_not_awaited()

    async def test_changed_amount_still_blocks_redownload(self):
        with self.assertRaises(Attention):
            await self.portal.run({**self.company, 'fgts':200, 'total':200},
                                  {**self.settings, 'downloadSaved':True})
        self.portal.recover_from_portal.assert_not_awaited()

    async def test_uncertain_issuance_always_recovers_even_without_option(self):
        self.previous['state'] = 'download_pending'
        await self.portal.run(self.company, self.settings)
        self.portal.recover_from_portal.assert_awaited_once()
        self.portal.profile.assert_not_awaited()


class ExplicitRestartTests(RerunTests):
    async def test_confirmed_restart_reaches_fresh_selection_instead_of_cache(self):
        self.portal.profile.side_effect = RuntimeError('fresh selection reached')
        with patch('fgts_guias.browser.validate_pdf') as validate:
            with self.assertRaisesRegex(RuntimeError, 'fresh selection reached'):
                await self.portal.run(self.company, {**self.settings, 'restartEmission':True})
        validate.assert_not_called()
        self.portal.profile.assert_awaited_once()
        self.portal.recover_from_portal.assert_not_awaited()

    async def test_restart_still_recovers_uncertain_emission(self):
        self.previous['state'] = 'issuing'
        await self.portal.run(self.company, {**self.settings, 'restartEmission':True})
        self.portal.recover_from_portal.assert_awaited_once()
        self.portal.profile.assert_not_awaited()

    async def test_pending_guide_indicator_does_not_override_explicit_restart(self):
        self.portal.page = SimpleNamespace(locator=lambda *_:SimpleNamespace(count=AsyncMock(return_value=0)))
        self.portal.click = AsyncMock()
        self.portal.text = AsyncMock(return_value='Existem guias aguardando pagamento')
        self.portal.reprint = AsyncMock()
        result = await self.portal.search(self.company, {**self.settings, 'restartEmission':True})
        self.assertFalse(result)
        self.portal.reprint.assert_not_awaited()
        result = await self.portal.search(self.company, self.settings)
        self.assertTrue(result)
        self.portal.reprint.assert_awaited_once()

class RestartHistoryTests(unittest.TestCase):
    def test_restart_archives_history_without_erasing_active_intention(self):
        import sqlite3
        import json
        from fgts_guias.storage import Storage
        store = Storage.__new__(Storage)
        store.db = sqlite3.connect(':memory:')
        self.addCleanup(store.db.close)
        store.db.execute('CREATE TABLE jobs (key TEXT PRIMARY KEY,value TEXT)')
        store.db.execute('CREATE TABLE emission_history (id TEXT PRIMARY KEY,job_key TEXT,value TEXT)')
        company = {'cnpj':'00000000000191'}
        key = store.job_key(company, '09/2026', '09/2026')
        previous = {'state':'issuing','guide':'0123456789012-3'}
        store.save_job(key, previous)
        store.archive_restart([company], '09/2026', '09/2026')
        self.assertEqual(store.job(key), previous)
        archived = store.db.execute('SELECT job_key,value FROM emission_history').fetchone()
        self.assertEqual(archived[0], key)
        self.assertEqual(json.loads(archived[1])['previous'], previous)
        self.assertIsNone(store.job(store.job_key(company, '10/2026', '10/2026')))
