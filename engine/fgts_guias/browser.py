"""Portal adapter. All selectors refer to visible controls, never financial APIs."""
import asyncio
import os
import re
import shutil
import uuid
from .errors import user_message
from playwright.async_api import expect
from pathlib import Path
from datetime import date, timedelta
from .chrome import ChromeSession
from .domain import digits, money, reais, safe_filename
from .files import validate_pdf, guide_due, guide_number
from .decisions import RetryCompany

BASE = 'https://fgtsdigital.sistema.gov.br/'
HOME = BASE + 'portal/servicos'
GUIDE = BASE + 'cobranca/#/gestao-guias/emissao-guia-parametrizada'
CONSULT = BASE + 'cobranca/#/gestao-guias/consulta-guias'

class Attention(Exception):
    def __init__(self, message, **details):
        super().__init__(message)
        self.details = details

def chrome_path():
    candidates = [shutil.which('google-chrome'), shutil.which('google-chrome-stable'),
                  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    for root in ['PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA']:
        if os.environ.get(root):
            candidates.append(str(Path(os.environ[root]) / 'Google/Chrome/Application/chrome.exe'))
    return next((str(p) for p in candidates if p and Path(p).is_file()), None)

class Portal:
    def __init__(self, storage, notify, checkpoint, on_closed, decision=None):
        self.store, self.notify, self.checkpoint = storage, notify, checkpoint
        self.context = self.page = None
        self.chrome = ChromeSession(storage.root)
        self.on_closed = on_closed
        self.decision = decision
        self.validation_stage = 'FGTS'
        self.observed_browser = None
        self.page_session = None

    async def launch(self, settings=None):
        settings = settings or self.store.get('workspace', {}).get('settings', {})
        executable = chrome_path()
        if not executable:
            raise Attention('Instale o Google Chrome antes de iniciar.')
        self.context = await self.chrome.open(executable, settings)
        if self.observed_browser != self.chrome.browser:
            self.observed_browser = self.chrome.browser
            browser = self.chrome.browser
            browser.on('disconnected', lambda *_: self.window_closed(browser))
        if self.page and not self.page.is_closed() and self.page.context == self.context:
            return
        candidates = [page for page in self.context.pages
                      if 'fgtsdigital.sistema.gov.br/' in page.url or 'sso.acesso.gov.br/' in page.url]
        if len(candidates) > 1:
            raise Attention('Há mais de uma aba FGTS/GOV.BR. Deixe aberta somente a aba que deseja usar.')
        self.page = candidates[0] if candidates else await self.context.new_page()
        page = self.page
        self.page_session = await self.context.new_cdp_session(page)
        await self.page_session.send('Emulation.setFocusEmulationEnabled', {'enabled':True})
        page.on('close', lambda *_: self.window_closed(page))
        if not candidates:
            await self.page.goto(BASE)
        await self.visibility(False)

    async def visibility(self, visible):
        await self.chrome.visibility(self.page, visible)
        self.notify('browser_visibility', visible=visible)

    async def authentication_ready(self, settings):
        if not self.page or self.page.is_closed():
            return False
        if not self.page.url.startswith(BASE) or '/login' in self.page.url:
            return False
        try:
            await self.guard(checkpoint=False)
        except Attention:
            return False
        identity = self.page.get_by_role('button', name=re.compile(r'^Abrir Menu de usuário '))
        if await identity.count() != 1:
            return False
        label = await identity.get_attribute('aria-label') or ''
        holder = re.search(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b', label)
        return bool(holder and digits(holder.group()) == digits(settings['officeCnpj']))

    def window_closed(self, source):
        if source not in (self.page, self.chrome.browser):
            return
        if not self.chrome.closing:
            self.on_closed()

    async def close(self):
        await self.chrome.close()
        self.context = self.page = self.page_session = None

    async def text(self):
        return await self.page.locator('body').inner_text()

    async def guard(self, checkpoint=True):
        if checkpoint:
            await self.checkpoint()
        text = await self.text()
        challenge = bool(re.search(r'captcha inválido|resolva o captcha', text, re.I))
        for frame in self.page.frames:
            if frame == self.page.main_frame or 'captcha' not in frame.url.lower():
                continue
            owner = await frame.frame_element()
            if not await owner.is_visible():
                continue
            checkbox = frame.get_by_role('checkbox')
            if await checkbox.count():
                challenge = challenge or await checkbox.first.get_attribute('aria-checked') != 'true'
            elif 'bframe' in frame.url or 'challenge' in frame.url:
                content = frame.locator('body')
                challenge = challenge or (await content.is_visible() and bool((await content.inner_text()).strip()))
        if challenge:
            raise Attention('Responda ao CAPTCHA no Chrome. O lote continuará quando o FGTS Digital abrir.', reason='captcha')
        if 'acesso.gov.br' in self.page.url or '/login' in self.page.url:
            raise Attention('Conclua o login com seu certificado no Chrome. O lote continuará quando o FGTS Digital abrir.', reason='authentication')

    async def click(self, name):
        await self.guard()
        await self.page.get_by_role('button', name=name, exact=True).click()
        await self.page.get_by_role('progressbar', name='Carregando', exact=True).wait_for(state='hidden', timeout=60000)

    async def step(self, number):
        await self.page.locator(f'[role="tab"][step="{number}"][active]').wait_for(state='visible', timeout=60000)
        await self.page.get_by_role('progressbar', name='Carregando', exact=True).wait_for(state='hidden', timeout=60000)

    async def employer(self, company):
        match = re.search(r'Empregador:\s*([\d./-]+)', await self.text())
        if not match or digits(match.group(1)) != company['cnpj']:
            raise Attention('O empregador no portal difere do CNPJ selecionado. Confira o perfil.')

    async def profile(self, company, settings):
        await self.page.goto(HOME)
        await self.guard()
        cookies = self.page.get_by_role('button', name='Aceitar', exact=True)
        if await cookies.count() and await cookies.first.is_visible():
            await cookies.first.click()
        body = await self.text()
        office = digits(settings['officeCnpj'])
        # The portal exposes the holder in the avatar button's accessible name.
        identity = self.page.get_by_role('button', name=re.compile(r'^Abrir Menu de usuário '))
        label = await identity.get_attribute('aria-label') if await identity.count() == 1 else ''
        holder = re.search(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b', label or '')
        if not holder:
            raise Attention('Não foi possível confirmar o titular do certificado no portal. Confira no Chrome se o login foi concluído com o certificado correspondente ao CNPJ informado no app.')
        if digits(holder.group()) != office:
            raise Attention('O certificado usado no login pertence a outro CNPJ. Confira o titular informado no app ou feche todas as janelas do Chrome do app para entrar com outro certificado.')
        if company['cnpj'] in digits(body.split('Empregador:', 1)[-1].split('\n', 1)[0]) and '/servicos' in self.page.url:
            return
        if '/escolhaPerfil' in self.page.url:
            heading = self.page.get_by_role('heading', name='Definir Perfil', exact=True)
            await heading.wait_for(state='visible')
        else:
            await self.page.get_by_role('button', name='Trocar Perfil', exact=True).click()
            heading = self.page.get_by_role('heading', name='Trocar Perfil', exact=True)
            await heading.wait_for(state='visible')
        dialog = self.page.get_by_role('dialog').filter(has=heading).last
        combo = dialog.get_by_role('combobox', name='Perfil', exact=True)
        await combo.click()
        await dialog.get_by_role('option', name='Meu Perfil' if company['cnpj'] == office else 'Procurador', exact=True).click()
        if company['cnpj'] != office:
            await dialog.get_by_role('textbox', name='Empregador a ser representado', exact=True).fill(company['cnpj'])
        buttons = dialog.get_by_role('button', name=re.compile('^(Definir|Selecionar)$'))
        await buttons.last.click()
        await dialog.wait_for(state='hidden')
        await self.page.wait_for_url('**/portal/servicos', timeout=30000)
        await self.page.get_by_role('progressbar', name='Carregando', exact=True).wait_for(state='hidden', timeout=60000)
        cnpj = company['cnpj']
        formatted = f'{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}'
        await self.page.get_by_text(re.compile(r'Empregador:\s*' + re.escape(formatted))).first.wait_for(state='visible', timeout=30000)
        body = await self.text()
        match = re.search(r'Empregador:\s*([\d./-]+)', body)
        if not match or digits(match.group(1)) != company['cnpj']:
            raise Attention('O empregador no portal difere do CNPJ selecionado. Confira o perfil.')

    async def periods(self, initial, final):
        for label, value in [('Inicial', initial), ('Final', final)]:
            combo = self.page.get_by_role('combobox', name=re.compile(label))
            await combo.first.wait_for(state='visible')
            if await combo.count() != 1:
                raise Attention('Não foi possível preencher o período. Abra o Chrome, confira as competências inicial e final e clique em Retomar.')
            await combo.click()
            await combo.fill(value)
            await self.page.get_by_role('option', name=value, exact=True).click()

    async def summary(self):
        result = {}
        for key, label in [('fgts', 'Total FGTS'), ('consignado', re.compile(r'^Total (?:dos )?Consignados?$')), ('total', 'Total da Guia')]:
            nodes = self.page.get_by_text(label, exact=True)
            await nodes.first.wait_for(state='visible')
            found = []
            for index in range(await nodes.count()):
                node = nodes.nth(index)
                if not await node.is_visible():
                    continue
                value = node.locator('xpath=following-sibling::*[not(self::br)][1]')
                await expect(value).to_have_text(re.compile(r'^\s*(?:R\$\s*)?\d[\d.]*,\d{2}\s*$'), timeout=15000)
                content = await value.inner_text()
                values = re.findall(r'(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})', content)
                if len(values) == 1:
                    found.append(money(values[0]))
            if not found or len(set(found)) != 1:
                raise Attention(f'Não foi possível ler um valor único de {label}. Confira no Chrome.')
            result[key] = found[0]
        return result

    async def final_summary(self):
        result = {'fgts': 0, 'consignado': 0, 'total': 0}
        seen = set()
        tables = self.page.get_by_role('table')
        await tables.first.wait_for(state='visible')
        for table in await tables.all():
            headers = [' '.join(t.split()) for t in await table.get_by_role('columnheader').all_inner_texts()]
            columns = [i for i, name in enumerate(headers) if re.fullmatch(r'Total(?:\s*[^\w]*)?', name)]
            kind = 'fgts' if any('FGTS Mensal' in h for h in headers) else 'consignado' if any('Consignado' in h for h in headers) else None
            values = [t.strip() for t in await table.get_by_role('row').last.get_by_role('cell').all_inner_texts()]
            if kind is None or kind in seen or len(columns) != 1 or len(values) != len(headers) or 'Total' not in values:
                raise Attention('Resumo final da guia não reconhecido. Confira os totais no Chrome.')
            result[kind] = money(values[columns[0]])
            seen.add(kind)
        if 'fgts' not in seen:
            raise Attention('Total FGTS ausente na conferência final.')
        result['total'] = result['fgts'] + result['consignado']
        return result

    async def difference(self, company, scope, expected, found, readback, **context):
        while expected != found:
            if not self.decision:
                raise Attention('Valores divergentes. Revise a planilha e os relatórios antes de retomar.', expected=expected, found=found)
            await self.decision(company, scope, expected, found, **context)
            await self.guard()
            await self.employer(company)
            current = await readback()
            if current == found:
                return current
            found = current
        return found

    async def compare(self, company, actual, loans=True):
        expected = {k: company[k] for k in ['fgts', 'consignado', 'total']}
        if not loans:
            expected = {'fgts': company['fgts'], 'consignado': 0, 'total': company['fgts']}
        reader = self.final_summary if self.validation_stage == 'Emissão' else self.summary
        await self.difference(company, self.validation_stage, expected, actual, reader)

    async def check(self, selector, checked):
        control = self.page.locator(selector)
        if await control.is_checked() != checked:
            control_id = await control.get_attribute('id')
            label = self.page.locator(f'label[for="{control_id}"]') if control_id else None
            if label is not None and await label.count() == 1:
                await label.click()
            else:
                await control.set_checked(checked)
        if await control.is_checked() != checked:
            raise Attention('O portal não confirmou o filtro solicitado. Confira no Chrome.')

    async def search(self, company, settings):
        checkbox = self.page.locator('#sem-guia-emitida')
        if await checkbox.count():
            await self.check('#sem-guia-emitida', False)
        await self.click('Pesquisar')
        body = await self.text()
        if 'Nenhum item encontrado' in body:
            raise Attention('Nenhum débito encontrado, mesmo incluindo guias emitidas. Confira no sistema de folha.')
        if settings.get('restartEmission', False):
            return False
        pending = self.page.locator('[tooltip*="guias aguardando pagamento"], [title*="guias aguardando pagamento"], [data-original-title*="guias aguardando pagamento"], [ngbtooltip*="guias aguardando pagamento"]')
        if await pending.count() or 'Existem guias aguardando pagamento' in body:
            await self.reprint(company, settings)
            return True
        icons = self.page.get_by_role('table').locator('[class*="info-circle"], [class*="circle-info"], [class*="info-sign"], svg[data-icon*="info"]')
        for index in range(await icons.count()):
            icon = icons.nth(index)
            if await icon.is_visible():
                await icon.hover()
                tooltip = self.page.get_by_role('tooltip')
                if await tooltip.count():
                    content = ' '.join(await tooltip.all_inner_texts())
                    if 'guias aguardando pagamento' in content.lower():
                        await self.reprint(company, settings)
                        return True
                else:
                    raise Attention('Não foi possível confirmar se há uma guia aguardando pagamento. Abra o Chrome e confira as guias existentes antes de retomar.', recovery=True)

    async def recover_from_portal(self, company, settings):
        """Read-only lookup after uncertain issuance; never repeat Emitir Guia."""
        key = self.store.job_key(company, settings['initial'], settings['final'])
        previous = self.store.job(key) or {}
        await self.profile(company, settings)
        await self.page.goto(CONSULT)
        await self.guard()
        await self.employer(company)
        candidates = []
        alternatives = []
        for attempt in range(3):
            await self.click('Pesquisar')
            table = self.page.get_by_role('table').filter(
                has=self.page.get_by_text('Número da Guia', exact=True))
            await table.wait_for(state='visible')
            candidates = []
            alternatives = []
            for page_index in range(20):
                headers = await table.get_by_role('columnheader').all_inner_texts()
                if not headers:
                    headers = await table.get_by_role('row').first.get_by_role('cell').all_inner_texts()
                def column(label):
                    matches = [i for i, value in enumerate(headers) if label in value]
                    if len(matches) != 1:
                        raise Attention('Não foi possível ler a lista de guias. Abra a Consulta de Guias no Chrome e confira a guia que deseja recuperar.', recovery=True)
                    return matches[0]
                number_index, due_index, total_index = [column(label) for label in
                    ['Número da Guia', 'Vencimento da Guia', 'Valor Total']]
                for row in await table.get_by_role('row').all():
                    cells = await row.get_by_role('cell').all_inner_texts()
                    if len(cells) <= max(number_index, due_index, total_index):
                        continue
                    number = cells[number_index].strip()
                    due = cells[due_index].strip()
                    if not re.fullmatch(r'\d{10,30}-\d', number):
                        continue
                    if previous.get('guide') and number != previous['guide']:
                        continue
                    amount = money(cells[total_index].strip())
                    if 'Aguardando Pagamento' not in ' '.join(cells) or 'MENSAL' not in ' '.join(cells):
                        continue
                    if previous.get('guide') or due == previous.get('due') or amount == company['total']:
                        alternatives.append((number, due, amount))
                    if previous.get('due') and due != previous['due']:
                        continue
                    if amount != company['total']:
                        continue
                    candidates.append((number, due, amount))
                next_page = self.page.get_by_role('button', name='Página seguinte', exact=True)
                if not await next_page.count() or await next_page.is_disabled():
                    break
                await next_page.click()
                await self.page.get_by_role('progressbar', name='Carregando').wait_for(state='hidden', timeout=60000)
            else:
                raise Attention('A consulta retornou muitas guias. Localize a guia no Chrome e use Recuperar PDF para salvar o arquivo.', recovery=True)
            candidates = list(dict.fromkeys(candidates))
            if candidates:
                break
            if attempt < 2:
                await asyncio.sleep(2)
        if not candidates and len(set(alternatives)) == 1:
            candidates = alternatives
        if len(candidates) != 1:
            raise Attention('Não foi possível identificar uma única guia com o valor e vencimento informados. Confira a Consulta de Guias no Chrome e use Recuperar PDF se já tiver o arquivo.', recovery=True)
        number, due, amount = candidates[0]
        # Search again to return to the first page, then locate the recorded number.
        await self.click('Pesquisar')
        for _ in range(20):
            row = table.get_by_role('row').filter(has=self.page.get_by_role('cell', name=number, exact=True))
            if await row.count() == 1:
                break
            next_page = self.page.get_by_role('button', name='Página seguinte', exact=True)
            if not await next_page.count() or await next_page.is_disabled():
                raise Attention('A guia mudou na consulta. Confira no Chrome.', recovery=True)
            await next_page.click()
            await self.page.get_by_role('progressbar', name='Carregando').wait_for(state='hidden', timeout=60000)
        else:
            raise Attention('Não foi possível localizar novamente a guia.', recovery=True)
        async def read_candidate():
            cells = await row.get_by_role('cell').all_inner_texts()
            if cells[number_index].strip() != number:
                raise Attention('A guia mudou na consulta.', recovery=True)
            return {'due':cells[due_index].strip(), 'total':money(cells[total_index].strip())}
        observed = await read_candidate()
        expected = {'due':previous.get('due') or due, 'total':company['total']}
        result = await self.difference(company, 'Recuperação da guia', expected, observed, read_candidate, guide=number)
        due = result['due']
        self.store.save_job(key, {'state':'recovering', 'guide':number, 'due':due,
            'company':company, 'initial':settings['initial'], 'final':settings['final']})
        await row.get_by_role('button', name='Abrir menu de opções de impressão', exact=True).click()
        print_guide = self.page.get_by_text('Imprimir guia', exact=True)
        await print_guide.wait_for(state='visible')
        self.notify('progress', company=company['cnpj'], message='Consulta de Guias · Baixando a guia emitida…')
        try:
            download, path = await self.chrome.download(self.page, print_guide.click)
            await self.save_download(download, company, settings, due, number)
        except RetryCompany:
            raise
        except Exception as exc:
            raise Attention('A guia consultada não foi salva: ' + user_message(exc), recovery=True) from exc

    async def run(self, company, settings):
        await self.launch(settings)
        await self.guard()
        initial, final = settings['initial'], settings['final']
        key = self.store.job_key(company, initial, final)
        previous = self.store.job(key)
        if previous and previous['state'] == 'saved' and not settings.get('restartEmission', False):
            if any(previous['company'].get(k) != company[k] for k in ['fgts','consignado','total']):
                raise Attention('Os valores importados mudaram após a emissão. Confira a guia existente.', recovery=True)
            if settings.get('downloadSaved', False):
                self.notify('progress', company=company['cnpj'],
                    message='Buscando a guia já emitida para baixar novamente…')
                await self.recover_from_portal(company, settings)
                return
            path = Path(previous['path'])
            try:
                validate_pdf(path, previous.get('verified_company', company), initial, final, previous['due'], previous['guide'])
            except Exception as exc:
                if path.exists():
                    raise Attention('O PDF salvo precisa de revisão: ' + user_message(exc), recovery=True)
                await self.recover_from_portal(company, settings)
                return
            destination = Path(settings['output']) / safe_filename(company['empresa'])
            if destination.resolve() != path.resolve():
                await self.recover(company, settings, str(path), previous['guide'], previous['due'])
                return
            self.notify('saved', company=company['cnpj'], path=str(path), reused=True)
            return
        if previous and previous['state'] in ['issuing', 'download_pending', 'recovering']:
            await self.recover_from_portal(company, settings)
            return
        await self.profile(company, settings)
        await self.page.goto(GUIDE)
        await self.guard()
        await self.employer(company)
        self.validation_stage = 'FGTS'
        self.notify('progress', company=company['cnpj'], message='1 de 4 · Conferindo FGTS')
        body = await self.text()
        if 'Não há débitos de interesse' in body:
            reason = 'O portal não apresenta débitos para esta empresa. Confira o enquadramento ou o envio dos eventos na folha de pagamento.'
            self.store.save_job(key, {'state':'no_debts', 'reason':reason, 'company':company,
                                     'initial':initial, 'final':final})
            self.notify('skipped', company=company['cnpj'], message=company['empresa'] + ': ' + reason)
            return
        if 'Há um ou mais débitos já adicionados' in body:
            for value in {initial, final}:
                if value not in body:
                    raise Attention('Há débitos de uma emissão anterior selecionados no portal. Abra o Chrome e confira se pertencem ao período informado antes de retomar.')
            actual = await self.summary()
            await self.compare(company, actual, loans=actual['consignado'] != 0)
        else:
            await self.periods(initial, final)
            for selector, checked in [('#debitos-mensal', True), ('#debitos-rescisorios', False), ('#processo-trabalhista', False)]:
                await self.check(selector, checked)
            if await self.search(company, settings):
                return
            if not await self.page.get_by_text('Resumo dos débitos adicionados à guia', exact=True).count():
                await self.check('#selecionar-todos', True)
                await self.click('Adicionar à guia')
                await self.compare(company, await self.summary(), loans=False)
            else:
                actual = await self.summary()
                await self.compare(company, actual, loans=actual['consignado'] != 0)
        await self.click('Avançar')
        await self.step(2)
        self.validation_stage = 'Consignados'
        self.notify('progress', company=company['cnpj'], message='2 de 4 · Conferindo consignados')
        actual = await self.summary()
        if actual != {k: company[k] for k in ['fgts','consignado','total']}:
            # Repeat the search with emitted guides visible before reporting a mismatch.
            if await self.search(company, settings):
                return
            actual = await self.summary()
        await self.compare(company, actual)
        await self.click('Avançar')
        await self.step(3)
        self.validation_stage = 'Vencimento'
        self.notify('progress', company=company['cnpj'], message='3 de 4 · Conferindo vencimento')
        field = self.page.get_by_role('textbox', name=re.compile('Vencimento da Guia'))
        await expect(field).to_have_value(re.compile(r'^\d{2}/\d{2}/\d{4}$'), timeout=15000)
        due = await field.input_value()
        today = date.today().strftime('%d/%m/%Y')
        if due == today:
            due = (date.today() + timedelta(days=1)).strftime('%d/%m/%Y')
            await field.fill(due)
            await field.press('Tab')
        async def read_due():
            value = await field.input_value()
            from datetime import datetime
            datetime.strptime(value, '%d/%m/%Y')
            return {'due':value}
        result = await self.difference(company, 'Vencimento', {'due':due}, await read_due(), read_due)
        due = result['due']
        await self.compare(company, await self.summary())
        await self.click('Avançar')
        await self.step(4)
        self.validation_stage = 'Emissão'
        self.notify('progress', company=company['cnpj'], message='4 de 4 · Conferindo a guia antes de emitir')
        await self.compare(company, await self.final_summary())
        await self.guard()
        await self.employer(company)
        self.store.save_job(key, {'state':'issuing', 'due':due, 'company':company, 'initial':initial, 'final':final})
        try:
            download, downloaded_path = await self.chrome.download(self.page, lambda: self.click('Emitir Guia'), timeout=5)
        except Exception:
            self.notify('progress', company=company['cnpj'], message='O download está demorando. Buscando a guia na Consulta de Guias…')
            await self.recover_from_portal(company, settings)
            return
        try:
            number = guide_number(downloaded_path)
        except Exception as exc:
            raise Attention('Guia emitida; número não identificado no PDF. Recupere a guia existente.', recovery=True) from exc
        await self.save_download(download, company, settings, due, number)

    async def reprint(self, company, settings):
        await self.guard()
        await self.employer(company)
        icon = self.page.locator('[tooltip*="guias aguardando pagamento"]').first
        if not await icon.count():
            raise Attention('A guia pendente não disponibilizou o controle de reimpressão.', recovery=True)
        await icon.click()
        dialog = self.page.get_by_role('dialog').filter(has=self.page.get_by_role('heading', name='Guias Aguardando Pagamento', exact=True))
        await dialog.wait_for(state='visible')
        links = dialog.locator('[tooltip="Reimprimir guia"]')
        numbers = [text.strip() for text in await links.all_inner_texts()]
        if len(numbers) != 1 or not re.fullmatch(r'\d{10,30}-\d', numbers[0]):
            raise Attention('Há mais de uma guia pendente ou o número não foi identificado. Confira a guia correta.', recovery=True)
        number = numbers[0]
        key = self.store.job_key(company, settings['initial'], settings['final'])
        previous = self.store.job(key)
        if previous and previous.get('guide') and previous['guide'] != number:
            raise Attention('A guia pendente difere do número registrado. Confira antes de recuperar.', recovery=True)
        self.store.save_job(key, {'state':'recovering', 'guide':number, 'company':company,
                                 'initial':settings['initial'], 'final':settings['final']})
        self.notify('progress', company=company['cnpj'], message='Baixando e conferindo a guia existente…')
        try:
            download, path = await self.chrome.download(self.page, links.first.click)
            due = guide_due(path)
            await self.save_download(download, company, settings, due, number)
        except RetryCompany:
            raise
        except Exception as exc:
            raise Attention('A guia existente não foi salva: ' + user_message(exc), recovery=True) from exc
        await dialog.get_by_role('button', name='Fechar', exact=True).click()

    async def verify_download(self, path, company, settings, due, number):
        from .files import pdf_values
        actual = pdf_values(path)
        verified = {**company, **{k:actual[k] for k in ['fgts','consignado','total']}}
        # Identity, guide number, period and valid PDF remain mandatory before any acceptance.
        validate_pdf(path, verified, settings['initial'], settings['final'], actual['due'], number)
        expected = {**{k:company[k] for k in ['fgts','consignado','total']}, 'due':due}
        async def read_pdf():
            values = pdf_values(path)
            validate_pdf(path, {**company, **{k:values[k] for k in ['fgts','consignado','total']}},
                         settings['initial'], settings['final'], values['due'], number)
            return values
        accepted = await self.difference(company, 'Conferência do PDF', expected, actual, read_pdf, guide=number)
        return {**company, **{k:accepted[k] for k in ['fgts','consignado','total']}}, accepted['due']

    async def save_download(self, download, company, settings, due, number):
        key = self.store.job_key(company, settings['initial'], settings['final'])
        job = {'state':'download_pending','due':due,'guide':number,'company':company,
               'initial':settings['initial'],'final':settings['final']}
        self.store.save_job(key, job)
        folder = Path(settings['output'])
        folder.mkdir(parents=True, exist_ok=True)
        filename = company['empresa']
        if settings.get('restartEmission', False):
            filename += ' - ' + number
        target = folder / safe_filename(filename)
        temp = folder / ('.' + target.name + '.' + uuid.uuid4().hex + '.part')
        job['temporary'] = str(temp)
        self.store.save_job(key, job)
        await download.save_as(str(temp))
        try:
            verified, due = await self.verify_download(temp, company, settings, due, number)
            job.update(verified_company=verified, due=due)
            if target.exists():
                validate_pdf(target, verified, settings['initial'], settings['final'], due, number)
                temp.unlink()
            else:
                temp.rename(target)
        except RetryCompany:
            raise
        except Exception as exc:
            raise Attention('A guia foi baixada, mas não passou pela conferência: ' + user_message(exc), recovery=True, temporary=str(temp)) from exc
        job.update(state='saved', path=str(target))
        self.store.save_job(key, job)
        self.notify('saved', company=company['cnpj'], path=str(target))

    async def recover(self, company, settings, path, number, due):
        # The operator selects a downloaded existing guide. No new issue is attempted.
        validate_pdf(Path(path), company, settings['initial'], settings['final'], due, number)
        class Existing:
            async def save_as(self, destination):
                shutil.copyfile(path, destination)
        await self.save_download(Existing(), company, settings, due, number)
