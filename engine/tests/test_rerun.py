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
