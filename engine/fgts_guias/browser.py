"""Portal adapter. All selectors refer to visible controls, never financial APIs."""
import os
import re
import shutil
import uuid
from pathlib import Path
from datetime import date, timedelta
from playwright.async_api import async_playwright
from .domain import digits, money, reais, safe_filename
from .files import validate_pdf

BASE = 'https://fgtsdigital.sistema.gov.br/'
HOME = BASE + 'portal/servicos'
GUIDE = BASE + 'cobranca/#/gestao-guias/emissao-guia-parametrizada'

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
    def __init__(self, storage, notify, checkpoint):
        self.store, self.notify, self.checkpoint = storage, notify, checkpoint
        self.context = self.page = self.playwright = None

    async def launch(self):
        if self.context:
            return
        executable = chrome_path()
        if not executable:
            raise Attention('Instale o Google Chrome antes de iniciar.')
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            str(self.store.root / 'chrome-profile'), executable_path=executable,
            headless=False, accept_downloads=True, permissions=[], no_viewport=True)
        self.context.set_default_timeout(15000)
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        await self.page.goto(BASE)

    async def close(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        self.context = self.page = self.playwright = None

    async def text(self):
        return await self.page.locator('body').inner_text()

    async def guard(self):
        await self.checkpoint()
        text = await self.text()
        if re.search(r'captcha|sou humano|não sou um robô', text, re.I) or any('captcha' in f.url for f in self.page.frames):
            raise Attention('Resolva o CAPTCHA no Chrome e clique em Retomar.')
        if 'acesso.gov.br' in self.page.url or '/login' in self.page.url:
            raise Attention('Entre com GOV.BR e selecione o certificado digital no Chrome. Depois clique em Retomar.')

    async def click(self, name):
        await self.guard()
        await self.page.get_by_role('button', name=name, exact=True).click()
        loading = self.page.get_by_text('Carregando', exact=False)
        if await loading.count() and await loading.first.is_visible():
            await loading.first.wait_for(state='hidden', timeout=60000)

    async def profile(self, company, settings):
        await self.page.goto(HOME)
        await self.guard()
        cookies = self.page.get_by_role('button', name='Aceitar', exact=True)
        if await cookies.count() and await cookies.first.is_visible():
            await cookies.first.click()
        body = await self.text()
        office = digits(settings['officeCnpj'])
        # The certificate holder must be present in the header/profile before switching.
        header = await self.page.locator('header, .header-info, .header-menu').all_inner_texts()
        if office not in digits(' '.join(header)):
            raise Attention('Confirme no Chrome o titular do certificado. O CNPJ do escritório não foi identificado no cabeçalho.')
        if company['cnpj'] in digits(body.split('Empregador:', 1)[-1].split('\n', 1)[0]) and '/servicos' in self.page.url:
            return
        switch = self.page.get_by_text('Trocar Perfil', exact=True)
        if await switch.count() and await switch.first.is_visible():
            await switch.first.click()
        combo = self.page.get_by_role('combobox', name=re.compile('Perfil'))
        await combo.click()
        await self.page.get_by_text('Meu Perfil' if company['cnpj'] == office else 'Procurador', exact=True).last.click()
        if company['cnpj'] != office:
            await self.page.get_by_role('textbox', name=re.compile('Empregador a ser representado')).fill(company['cnpj'])
        buttons = self.page.get_by_role('button', name=re.compile('^(Definir|Selecionar)$'))
        await buttons.last.click()
        await self.page.wait_for_url('**/portal/servicos', timeout=30000)
        body = await self.text()
        match = re.search(r'Empregador:\s*([\d./-]+)', body)
        if not match or digits(match.group(1)) != company['cnpj']:
            raise Attention('O empregador no portal difere do CNPJ selecionado. Confira o perfil.')

    async def periods(self, initial, final):
        for label, value in [('Inicial', initial), ('Final', final)]:
            combo = self.page.get_by_role('combobox', name=re.compile(label))
            if await combo.count() != 1:
                raise Attention('Configure a competência Inicial e Final no Chrome; o portal alterou os controles.')
            await combo.click()
            await combo.fill(value)
            await self.page.get_by_text(value, exact=True).last.click()

    async def summary(self):
        result = {}
        for key, label in [('fgts', 'Total FGTS'), ('consignado', 'Total dos Consignados'), ('total', 'Total da Guia')]:
            nodes = self.page.get_by_text(label, exact=True)
            found = []
            for index in range(await nodes.count()):
                node = nodes.nth(index)
                if not await node.is_visible():
                    continue
                # Keep the extraction inside the label's rendered summary block.
                content = await node.evaluate('(e) => e.parentElement.innerText')
                values = re.findall(r'(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})', content)
                if len(values) == 1:
                    found.append(money(values[0]))
            if not found or len(set(found)) != 1:
                raise Attention(f'Não foi possível ler um valor único de {label}. Confira no Chrome.')
            result[key] = found[0]
        return result

    def compare(self, company, actual, loans=True):
        expected = {k: company[k] for k in ['fgts', 'consignado', 'total']}
        if not loans:
            expected = {'fgts': company['fgts'], 'consignado': 0, 'total': company['fgts']}
        if actual != expected:
            raise Attention('Valores divergentes. Revise a planilha e os relatórios antes de retomar.',
                            expected=expected, found=actual,
                            difference={k: actual[k]-expected[k] for k in expected})

    async def search(self):
        checkbox = self.page.locator('#sem-guia-emitida')
        if await checkbox.count():
            await checkbox.set_checked(False)
        await self.click('Pesquisar')
        body = await self.text()
        if 'Nenhum item encontrado' in body:
            raise Attention('Nenhum débito encontrado, mesmo incluindo guias emitidas. Confira no sistema de folha.')
        pending = self.page.locator('[title*="guias aguardando pagamento"], [data-original-title*="guias aguardando pagamento"], [ngbtooltip*="guias aguardando pagamento"]')
        if await pending.count() or 'Existem guias aguardando pagamento' in body:
            raise Attention('Há guia aguardando pagamento. Recupere a guia existente no Chrome; a emissão automática foi interrompida.', recovery=True)
        icons = self.page.get_by_role('table').locator('[class*="info-circle"], [class*="circle-info"], [class*="info-sign"]')
        for index in range(await icons.count()):
            icon = icons.nth(index)
            if await icon.is_visible():
                await icon.hover()
                tooltip = self.page.get_by_role('tooltip')
                if await tooltip.count():
                    content = ' '.join(await tooltip.all_inner_texts())
                    if 'guias aguardando pagamento' in content.lower():
                        raise Attention('Há guia aguardando pagamento. Recupere a guia existente.', recovery=True)
                else:
                    raise Attention('Símbolo de informação na tabela não reconhecido. Confira se existe guia aguardando pagamento.', recovery=True)

    async def run(self, company, settings):
        await self.launch()
        await self.guard()
        initial, final = settings['initial'], settings['final']
        key = self.store.job_key(company, initial, final)
        previous = self.store.job(key)
        if previous and previous['state'] == 'saved':
            if any(previous['company'].get(k) != company[k] for k in ['fgts','consignado','total']):
                raise Attention('Os valores importados mudaram após a emissão. Confira a guia existente.', recovery=True)
            path = Path(previous['path'])
            try:
                validate_pdf(path, company, initial, final, previous['due'], previous['guide'])
            except Exception as exc:
                raise Attention('O PDF salvo precisa de revisão: ' + str(exc), recovery=True)
            destination = Path(settings['output']) / safe_filename(company['empresa'])
            if destination.resolve() != path.resolve():
                await self.recover(company, settings, str(path), previous['guide'], previous['due'])
                return
            self.notify('saved', company=company['cnpj'], path=str(path), reused=True)
            return
        if previous and previous['state'] in ['issuing', 'download_pending']:
            raise Attention('Emissão anterior registrada. Recupere o PDF existente, sem emitir novamente.', recovery=True)
        await self.profile(company, settings)
        await self.page.goto(GUIDE)
        await self.guard()
        self.notify('progress', company=company['cnpj'], message='1 de 4 · Conferindo FGTS')
        body = await self.text()
        if 'Há um ou mais débitos já adicionados' in body:
            for value in {initial, final}:
                if value not in body:
                    raise Attention('Confirme a competência do progresso salvo no Chrome antes de continuar.')
            actual = await self.summary()
            self.compare(company, actual, loans=actual['consignado'] != 0)
        else:
            await self.periods(initial, final)
            for selector, checked in [('#debitos-mensal', True), ('#debitos-rescisorios', False), ('#processo-trabalhista', False)]:
                await self.page.locator(selector).set_checked(checked)
            await self.search()
            await self.page.locator('#selecionar-todos').set_checked(True)
            await self.click('Adicionar à guia')
            self.compare(company, await self.summary(), loans=False)
        await self.click('Avançar')
        self.notify('progress', company=company['cnpj'], message='2 de 4 · Conferindo consignados')
        actual = await self.summary()
        if actual != {k: company[k] for k in ['fgts','consignado','total']}:
            # Repeat the search with emitted guides visible before reporting a mismatch.
            await self.search()
            actual = await self.summary()
        self.compare(company, actual)
        await self.click('Avançar')
        self.notify('progress', company=company['cnpj'], message='3 de 4 · Conferindo vencimento')
        field = self.page.get_by_role('textbox', name=re.compile('Vencimento da Guia'))
        due = await field.input_value()
        today = date.today().strftime('%d/%m/%Y')
        if due == today:
            due = (date.today() + timedelta(days=1)).strftime('%d/%m/%Y')
            await field.fill(due)
            await field.press('Tab')
        if await field.input_value() != due:
            raise Attention('O portal não confirmou o vencimento solicitado. Confira a data no Chrome.')
        self.compare(company, await self.summary())
        await self.click('Avançar')
        self.notify('progress', company=company['cnpj'], message='4 de 4 · Conferindo e emitindo')
        self.compare(company, await self.summary())
        await self.guard()
        self.store.save_job(key, {'state':'issuing', 'due':due, 'company':company, 'initial':initial, 'final':final})
        try:
            async with self.page.expect_download(timeout=60000) as info:
                await self.click('Emitir Guia')
            download = await info.value
        except Exception as exc:
            raise Attention('A emissão foi solicitada, mas o download não foi confirmado. Recupere a guia existente.', recovery=True) from exc
        body = await self.text()
        numbers = set(re.findall(r'\b\d{10,30}-\d\b', body))
        if len(numbers) != 1:
            raise Attention('Guia emitida; número não identificado. Recupere e confira o PDF.', recovery=True)
        number = numbers.pop()
        await self.save_download(download, company, settings, due, number)

    async def save_download(self, download, company, settings, due, number):
        key = self.store.job_key(company, settings['initial'], settings['final'])
        job = {'state':'download_pending','due':due,'guide':number,'company':company,
               'initial':settings['initial'],'final':settings['final']}
        self.store.save_job(key, job)
        folder = Path(settings['output'])
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / safe_filename(company['empresa'])
        temp = folder / ('.' + target.name + '.' + uuid.uuid4().hex + '.part')
        job['temporary'] = str(temp)
        self.store.save_job(key, job)
        await download.save_as(str(temp))
        try:
            validate_pdf(temp, company, settings['initial'], settings['final'], due, number)
            if target.exists():
                validate_pdf(target, company, settings['initial'], settings['final'], due, number)
                temp.unlink()
            else:
                temp.rename(target)
        except Exception as exc:
            raise Attention('PDF baixado, mas não salvo como concluído: ' + str(exc), recovery=True, temporary=str(temp)) from exc
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
