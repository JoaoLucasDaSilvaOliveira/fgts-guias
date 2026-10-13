"""Receita/DCTFWeb adapter for the observed monthly assisted workflow."""
import asyncio
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse
from .browser import Portal, Attention, chrome_path
from .domain import digits, money, safe_filename
from .inss_pdf import darf_values, validate_darf

BASE = 'https://servicos.receitafederal.gov.br/'
DCTF = 'https://dctfweb.cav.receita.fazenda.gov.br/AplicacoesWeb/DCTFWeb/Paginas/'


class InssPortal(Portal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rfb_page = self.dctf_page = None
        self.closing_tab = False
        self.certificate_requested = self.representation_pending = None
        self.competence = None

    async def launch(self, settings=None):
        executable = chrome_path()
        if not executable:
            raise Attention('Instale o Google Chrome antes de iniciar.')
        self.context = await self.chrome.open(executable, {**(settings or {}), 'portalUrl':BASE})
        if self.observed_browser != self.chrome.browser:
            self.observed_browser = self.chrome.browser
            browser = self.chrome.browser
            browser.on('disconnected', lambda *_: self.window_closed(browser))
        if not self.rfb_page or self.rfb_page.is_closed() or self.rfb_page.context != self.context:
            candidates = [p for p in self.context.pages if p.url.startswith(BASE) or urlparse(p.url).hostname == 'sso.acesso.gov.br']
            if len(candidates) > 1:
                raise Attention('Deixe somente uma aba Receita/GOV.BR aberta no Chrome do app.')
            blank = [page for page in self.context.pages if page.url == 'about:blank']
            self.rfb_page = candidates[0] if candidates else blank[0] if len(blank) == 1 else await self.context.new_page()
            rfb = self.rfb_page
            rfb.on('close', lambda *_: self.window_closed(rfb))
            if not candidates:
                await rfb.goto(BASE)
            await self.focus_page(rfb)
        self.page = self.dctf_page if self.dctf_page and not self.dctf_page.is_closed() else self.rfb_page
        await self.visibility(False)

    async def focus_page(self, page):
        session = await self.context.new_cdp_session(page)
        await session.send('Emulation.setFocusEmulationEnabled', {'enabled':True})

    def window_closed(self, source):
        if source == self.dctf_page and self.closing_tab:
            return
        if source in (self.rfb_page, self.dctf_page, self.chrome.browser) and not self.chrome.closing:
            self.on_closed()

    async def close(self):
        await super().close()
        self.rfb_page = self.dctf_page = None
        self.certificate_requested = self.representation_pending = None

    async def captcha_pending(self, page):
        for frame in page.frames:
            if frame == page.main_frame or 'captcha' not in frame.url.lower():
                continue
            owner = await frame.frame_element()
            if not await owner.is_visible():
                continue
            if not await owner.evaluate("el => { for (let n=el; n; n=n.parentElement) { if (Number(getComputedStyle(n).opacity) === 0) return false; } return true; }"):
                continue
            if 'frame=challenge' in frame.url or 'bframe' in frame.url:
                return True
            checkboxes = frame.get_by_role('checkbox')
            if await checkboxes.count() and await checkboxes.first.get_attribute('aria-checked') != 'true':
                return True
        return False

    async def request_certificate(self):
        if urlparse(self.rfb_page.url).hostname != 'sso.acesso.gov.br':
            return
        button = self.rfb_page.locator('#login-certificate')
        if self.certificate_requested != self.rfb_page.url and await button.is_visible() and await button.is_enabled():
            self.certificate_requested = self.rfb_page.url
            await button.click()

    async def authentication_ready(self, settings):
        if not self.page or self.page.is_closed() or await self.captcha_pending(self.page):
            return False
        if self.page == self.rfb_page:
            await self.request_certificate()
            if self.representation_pending and self.rfb_page.url == BASE:
                current = self.rfb_page.locator('representacao-atual')
                if not await current.is_visible():
                    return False
                content = await current.inner_text()
                cnpj, kind = self.representation_pending
                return cnpj in digits(content) and kind in content
            return self.rfb_page.url == BASE and await self.rfb_page.locator('#avatar-dropdown-trigger').is_visible()
        if self.page.url.startswith(DCTF) and self.page.url.endswith('Captcha.aspx'):
            await self.page.locator('#ctl00_cphConteudo_btnProsseguir').click()
            await self.page.wait_for_url('**/ListaDctfs.aspx', timeout=10000)
        return self.page.url.startswith(DCTF) and not self.page.url.endswith('Captcha.aspx')

    async def guard(self, checkpoint=True):
        if checkpoint:
            await self.checkpoint()
        if not self.page or self.page.is_closed():
            raise Attention('O Chrome foi fechado. Inicie o lote novamente.')
        if await self.captcha_pending(self.page):
            raise Attention('Conclua a verificação de segurança no Chrome. O app aguarda você resolver o desafio.', reason='captcha')
        if urlparse(self.page.url).hostname == 'sso.acesso.gov.br':
            await self.request_certificate()
            raise Attention('Selecione o certificado e informe o PIN no Chrome. O app aguarda o retorno à Receita.', reason='authentication')
        if not (self.page.url.startswith(BASE) or self.page.url.startswith(DCTF)):
            raise Attention('A navegação saiu do serviço esperado. Confira a página no Chrome.')

    async def optional(self, control):
        if await control.is_visible():
            try:
                await control.click(timeout=2000)
            except Exception:
                if await control.is_visible():
                    raise Attention('Um aviso inicial continua bloqueando o portal. Feche-o no Chrome e retome.')

    async def profile(self, company, settings):
        self.page = self.rfb_page
        await self.checkpoint()
        await self.request_certificate()
        if urlparse(self.page.url).hostname == 'sso.acesso.gov.br':
            await self.guard()
        if self.page.url != BASE:
            await self.page.goto(BASE)
        await self.guard()
        await self.optional(self.page.locator('#card0').get_by_role('button', name='Aceitar', exact=True))
        await self.optional(self.page.get_by_role('link', name='Pular Tutorial', exact=True))
        avatar = self.page.locator('#avatar-dropdown-trigger')
        if not await avatar.is_visible():
            await self.page.get_by_role('button', name=re.compile(r'Entrar com.*gov.br')).click()
            try:
                await self.page.wait_for_url(lambda url: str(url) != BASE, timeout=10000)
            except Exception:
                raise Attention('O acesso não redirecionou. Confira o CAPTCHA ou a mensagem do portal no Chrome.', reason='authentication')
            await self.request_certificate()
            raise Attention('Conclua a seleção do certificado e eventuais desafios no Chrome.', reason='authentication')
        if await avatar.get_attribute('aria-expanded') != 'true':
            await avatar.click()
        current = self.page.locator('representacao-atual')
        kind = 'Representante no CNPJ' if company['cnpj'] == digits(settings['officeCnpj']) else 'Procurador'
        async def ready():
            content = await current.inner_text() if await current.is_visible() else ''
            return company['cnpj'] in digits(content) and kind in content
        if not await ready():
            identity = (company['cnpj'], kind)
            if self.representation_pending != identity:
                input_cnpj = self.page.locator('#input-representar-cpfcnpj')
                await input_cnpj.fill(company['cnpj'])
                if digits(await input_cnpj.input_value()) != company['cnpj']:
                    raise Attention('O portal não confirmou o CNPJ informado.')
                await self.page.get_by_role('combobox').press('ArrowDown')
                option = self.page.get_by_role('option', name=kind, exact=True)
                if await option.count() != 1:
                    option = self.page.get_by_role('list', name='Options list', exact=True).get_by_text(kind, exact=True)
                if await option.count() != 1:
                    option = self.page.get_by_text(kind, exact=True)
                await option.click()
                form = input_cnpj.locator('xpath=ancestor::form[1]')
                buttons = await form.get_by_role('button', name=re.compile(r'^\s*(?:\S\s*)?Representar\s*$')).all()
                enabled = [b for b in buttons if await b.is_visible() and await b.is_enabled()]
                if len(enabled) != 1:
                    raise Attention('Não foi possível identificar o botão de representação. Confira a sidebar no Chrome.')
                self.representation_pending = identity
                await enabled[0].click()
            deadline = time.monotonic() + 15
            while not await ready():
                await self.guard()
                if time.monotonic() > deadline:
                    raise Attention('A representação ainda não foi confirmada. Confira o CAPTCHA, a procuração ou a mensagem na sidebar.', reason='authentication')
                await asyncio.sleep(.3)
        self.representation_pending = None
        await self.page.get_by_role('button', name='Fechar Menu', exact=True).click()

    async def employer(self, company):
        if self.page == self.rfb_page:
            content = await self.page.locator('#avatar-dropdown-trigger').inner_text()
            if company['cnpj'] not in digits(content):
                raise Attention('A empresa representada difere da empresa do lote.')
            return
        text = await self.text()
        match = re.search(r'\bCNPJ\s*([\d./-]+)', text)
        if not match or digits(match.group(1)) != company['cnpj']:
            raise Attention('O CNPJ do detalhamento difere da empresa selecionada.')
        period = re.search(r'Período de Apuração:\s*(\d{2}/\d{4})', text)
        if not period or period.group(1) != self.competence:
            raise Attention('A competência do detalhamento difere da competência do lote.')

    async def open_service(self):
        if not self.dctf_page or self.dctf_page.is_closed():
            self.page = self.rfb_page
            await self.page.get_by_role('tab', name='Negócios', exact=True).click()
            async with self.context.expect_page(timeout=20000) as opened:
                await self.page.get_by_role('link', name=re.compile(r'DCTFWeb')).click(button='middle')
            self.dctf_page = await opened.value
            service_page = self.dctf_page
            service_page.on('close', lambda *_: self.window_closed(service_page))
            await self.focus_page(service_page)
        self.page = self.dctf_page
        await self.page.wait_for_url(DCTF + '**', timeout=30000)
        # TODO(INSS, operador): integrar aqui a etapa "Sou humano".
        # Manter desafios com o operador; nunca avançar sem verificação aceita.
        await self.guard()
        if self.page.url.endswith('Captcha.aspx'):
            if not await self.authentication_ready({}):
                raise Attention('Conclua a verificação Sou humano na DCTFWeb.', reason='captcha')

    async def detail(self, company):
        if not self.page.url.endswith('ListaDctfs.aspx'):
            await self.employer(company)
            return
        table = self.page.locator('#ctl00_cphConteudo_tabelaListagemDctf_GridViewDctfs')
        await table.wait_for(state='visible')
        rows = table.get_by_role('row')
        headers = [re.sub(r'\s+', ' ', t).strip() for t in await rows.first.locator(':scope > th, :scope > td').all_inner_texts()]
        def index(label):
            if headers.count(label) != 1:
                raise Attention('O formato da lista de declarações mudou. Confira no Chrome.')
            return headers.index(label)
        pa, category, state, balance = [index(label) for label in ['Período de Apuração','Categoria','Situação','Saldo a Pagar']]
        candidates = []
        for row in await rows.all():
            cells = [value.strip() for value in await row.locator(':scope > td').all_inner_texts()]
            if len(cells) == len(headers) and cells[pa] == self.competence and cells[category] == 'Geral' and cells[state] == 'Ativa':
                candidates.append((row, money(cells[balance])))
        if len(candidates) != 1:
            raise Attention('Não há uma única declaração Geral ativa para a competência. Confira os filtros e a declaração no Chrome.')
        row, balance_value = candidates[0]
        if balance_value != company['inss']:
            raise Attention('O Saldo a Pagar da listagem difere do INSS informado. Confira a tabela do app e a declaração antes de retomar.',
                expected={'inss':company['inss']}, found={'inss':balance_value})
        await row.get_by_role('link', name='Visualizar', exact=True).click()
        await self.page.wait_for_url('**/ResumoVinculacoes/VinculacoesCompleta.aspx', timeout=30000)
        await self.employer(company)

    async def summary(self, company):
        await self.employer(company)
        rows = self.page.locator('#cphConteudo_TabelaVinculacoesDARF_GridViewVinculacoes').get_by_role('row')
        selected = []
        for row in await rows.all():
            cells = await row.locator(':scope > td').all_inner_texts()
            if any('Total Apurado Empresa' in value for value in cells):
                if company['cnpj'] not in digits(' '.join(cells)):
                    raise Attention('O resumo inclui outra empresa. Confira o detalhamento antes de emitir.')
                checkbox = row.get_by_role('checkbox')
                if await checkbox.count() != 1 or not await checkbox.is_checked():
                    raise Attention('O saldo da empresa não está selecionado. Confira a seleção no Chrome.')
                selected.append(money(cells[-1].strip()))
        if len(selected) != 1:
            raise Attention('Não foi possível identificar um único saldo selecionado no detalhamento.')
        return {'inss':selected[0]}

    async def finish_company(self):
        if self.dctf_page and not self.dctf_page.is_closed():
            self.closing_tab = True
            try:
                await self.dctf_page.close()
            finally:
                self.closing_tab = False
        self.dctf_page = None
        self.page = self.rfb_page

    async def save_pdf(self, path, company, settings, previous=None):
        key = self.store.job_key(company, settings['initial'], settings['final'], 'inss')
        job = previous or self.store.job(key) or {}
        values = darf_values(path)
        verified = {**company, 'inss':values['inss']}
        validate_darf(path, verified, self.competence, job.get('guide'), job.get('due'))
        async def reread():
            observed = darf_values(path)
            validate_darf(path, {**company, 'inss':observed['inss']}, self.competence, values['guide'], values['due'])
            return {'inss':observed['inss']}
        await self.difference(company, 'INSS · Conferência do PDF', {'inss':company['inss']}, {'inss':values['inss']}, reread, guide=values['guide'])
        folder = Path(settings['output']) / 'INSS'
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / safe_filename(company['empresa'])
        temporary = folder / ('.' + target.name + '.' + uuid.uuid4().hex + '.part')
        job.update(state='download_pending', service='inss', company=company,
            guide=values['guide'], due=values['due'], initial=self.competence, final=self.competence, temporary=str(path))
        self.store.save_job(key, job)
        try:
            shutil.copyfile(path, temporary)
            validate_darf(temporary, verified, self.competence, values['guide'], values['due'])
            if target.exists():
                validate_darf(target, verified, self.competence, values['guide'], values['due'])
            else:
                os.link(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
        job.update(state='saved', verified_company=verified, path=str(target))
        self.store.save_job(key, job)
        self.notify('saved', company=company['cnpj'], path=str(target))
        await self.finish_company()

    async def run(self, company, settings):
        self.competence = settings['initial']
        await self.launch(settings)
        key = self.store.job_key(company, self.competence, self.competence, 'inss')
        previous = self.store.job(key)
        if previous:
            if settings.get('downloadSaved'):
                raise Attention('A reimpressão automática de INSS ainda não está disponível. Use Recuperar PDF com o documento existente.', recovery=True)
            if previous.get('company', {}).get('inss') != company['inss']:
                raise Attention('O INSS mudou após uma emissão registrada. Confira a guia existente.', recovery=True)
            if previous['state'] == 'saved' and not settings.get('downloadSaved'):
                try:
                    validate_darf(previous['path'], previous.get('verified_company', company), self.competence, previous['guide'], previous['due'])
                except Exception as exc:
                    raise Attention('O PDF INSS salvo precisa de revisão ou não está disponível. Use Recuperar PDF com a guia existente.', recovery=True) from exc
                target = Path(settings['output']) / 'INSS' / safe_filename(company['empresa'])
                if Path(previous['path']).resolve() != target.resolve():
                    await self.save_pdf(previous['path'], company, settings, previous)
                    return
                self.notify('saved', company=company['cnpj'], path=previous['path'], reused=True)
                await self.finish_company()
                return
            if previous.get('temporary') and Path(previous['temporary']).is_file():
                await self.save_pdf(previous['temporary'], company, settings, previous)
                return
            raise Attention('Há uma emissão INSS registrada. Use Recuperar PDF com o documento já baixado. O app não repetirá a emissão.', recovery=True)
        await self.profile(company, settings)
        await self.open_service()
        await self.detail(company)
        self.notify('progress', company=company['cnpj'], message='INSS · Conferindo o saldo antes de emitir…')
        async def reread():
            return await self.summary(company)
        await self.difference(company, 'INSS · Saldo a Pagar', {'inss':company['inss']}, await reread(), reread)
        await self.guard()
        await self.employer(company)
        self.store.save_job(key, {'state':'issuing','service':'inss','company':company,'initial':self.competence,'final':self.competence})
        self.notify('progress', company=company['cnpj'], message='INSS · Emitindo e aguardando o PDF…')
        try:
            _, path = await self.chrome.download(self.page, self.page.locator('#LinkEmitirDARFIntegral').click, timeout=60)
        except Exception as exc:
            raise Attention('A emissão foi solicitada, mas o download não foi confirmado. Use Recuperar PDF; o app não repetirá a emissão.', recovery=True) from exc
        job = self.store.job(key)
        job.update(state='download_pending', temporary=str(path))
        self.store.save_job(key, job)
        await self.save_pdf(path, company, settings, job)

    async def recover(self, company, settings, path, number, due):
        self.competence = settings['initial']
        await self.launch(settings)
        validate_darf(path, company, self.competence, number or None, due or None)
        await self.save_pdf(path, company, settings)
