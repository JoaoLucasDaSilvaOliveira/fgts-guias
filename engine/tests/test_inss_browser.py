"""Real locator tests against local fixtures; all network requests are fulfilled."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from playwright.async_api import async_playwright
from fgts_guias.browser import chrome_path, Attention
from fgts_guias.inss import InssPortal, BASE, DCTF

LIST = '''<table id="ctl00_cphConteudo_tabelaListagemDctf_GridViewDctfs">
<tr><th>Período de Apuração</th><th>Categoria</th><th>Situação</th><th>Saldo a Pagar</th><th>Serviços</th></tr>
<tr><td>09/2026</td><td>Geral</td><td>Ativa</td><td><table><tr><td><input type="checkbox"></td><td>123,45</td></tr></table></td>
<td><a href="ResumoVinculacoes/VinculacoesCompleta.aspx">Visualizar</a></td></tr></table>'''
DETAIL = '''<div>Empresa de exemplo - CNPJ 12.345.678/0001-95</div>
<div>Período de Apuração: 09/2026</div>
<table id="cphConteudo_TabelaVinculacoesDARF_GridViewVinculacoes">
<tr><td>Total Apurado Empresa 12.345.678/0001-95</td><td>200,00</td>
<td><input type="checkbox" checked>123,45</td></tr></table>'''
PROFILE = '''<user-menu>
<button id="avatar-dropdown-trigger" aria-expanded="false" onclick="this.setAttribute('aria-expanded','true')">Escritório</button>
<representacao-atual></representacao-atual>
<form onsubmit="event.preventDefault(); document.querySelector('representacao-atual').textContent='Procurador de: Empresa de exemplo 12.345.678/0001-95';">
<input id="input-representar-cpfcnpj">
<div role="combobox" tabindex="0" onkeydown="document.getElementById('options').hidden=false">Digite um perfil</div>
<div id="options" hidden><div role="option" onclick="document.getElementById('options').hidden=true">Procurador</div></div>
<button type="submit">Representar</button></form>
<button aria-label="Fechar Menu" onclick="document.getElementById('avatar-dropdown-trigger').setAttribute('aria-expanded','false')">X</button>
</user-menu>'''

@unittest.skipUnless(chrome_path(), 'Requires installed Google Chrome')
class LocatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime=await async_playwright().start()
        self.browser=await self.runtime.chromium.launch(executable_path=chrome_path(),headless=True)
        self.context=await self.browser.new_context()
        self.page=await self.context.new_page()
        self.page.set_default_timeout(2000)
        store=SimpleNamespace(root=Path(tempfile.gettempdir()))
        async def checkpoint(): pass
        self.portal=InssPortal(store,lambda *args,**kw:None,checkpoint,lambda:None)
        self.portal.context=self.context
        self.portal.page=self.page
        self.portal.competence='09/2026'
        self.company={'cnpj':'12345678000195','inss':12345}
        async def route(request):
            url=request.request.url
            body=PROFILE if url.startswith(BASE) else LIST if url.endswith('ListaDctfs.aspx') else DETAIL
            await request.fulfill(body=body,content_type='text/html; charset=utf-8')
        await self.context.route('**/*',route)
    async def asyncTearDown(self):
        await self.browser.close()
        await self.runtime.stop()
    async def test_nested_balance_and_detail_selected_total(self):
        await self.page.goto(DCTF+'ListaDctfs.aspx')
        await self.portal.detail(self.company)
        self.assertEqual(await self.portal.summary(self.company),{'inss':12345})
    async def test_list_difference_stops_before_opening_declared_row(self):
        await self.page.goto(DCTF+'ListaDctfs.aspx')
        with self.assertRaises(Attention): await self.portal.detail({**self.company,'inss':99999})
        self.assertTrue(self.page.url.endswith('ListaDctfs.aspx'))
    async def test_representation_form_does_not_match_recent_history(self):
        await self.page.goto(BASE)
        self.portal.rfb_page=self.page
        await self.portal.profile(self.company,{'officeCnpj':'00000000000191'})
        self.assertEqual(await self.page.locator('#input-representar-cpfcnpj').input_value(),self.company['cnpj'])
        self.assertEqual(await self.page.locator('#avatar-dropdown-trigger').get_attribute('aria-expanded'),'false')
    async def test_auth_reset_does_not_remove_unrelated_cookies(self):
        await self.context.add_cookies([
            {'name':'test','value':'example','domain':domain,'path':'/'}
            for domain in ['sso.acesso.gov.br','servicos.receitafederal.gov.br','example.org']])
        chrome=self.portal.chrome
        chrome.context=self.context
        chrome.cdp=SimpleNamespace(send=AsyncMock())
        await chrome.reset_authentication()
        cookies=await self.context.cookies()
        self.assertEqual([cookie['domain'] for cookie in cookies],['example.org'])
        self.assertEqual(chrome.cdp.send.await_count,5)
