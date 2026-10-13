"""Conventional Chrome launch with a dedicated persistent profile."""
import asyncio
import json
import socket
import shutil
import subprocess
import time
import re
import psutil
from urllib.request import build_opener, ProxyHandler
from playwright.async_api import async_playwright
from .external import launch_external

class ChromeSession:
    def __init__(self, root):
        self.root = root
        self.playwright = self.browser = self.context = self.process = self.cdp = None
        self.port = None
        self.closing = False
        self.owned = {}
        self.fresh_authentication = False

    async def open(self, executable, settings):
        if self.browser and self.browser.is_connected():
            return self.context
        await self.close()
        self.closing = False
        try:
            profile = self.root / 'chrome-profile'
            profile.mkdir(parents=True, exist_ok=True)
            preferences = profile / 'Default/Preferences'
            prefs = json.loads(preferences.read_text()) if preferences.exists() else {}
            prefs.setdefault('profile', {}).setdefault('default_content_setting_values', {})['geolocation'] = 2
            preferences.parent.mkdir(parents=True, exist_ok=True)
            preferences.write_text(json.dumps(prefs))
            with socket.socket() as port_socket:
                port_socket.bind(('127.0.0.1', 0))
                self.port = port_socket.getsockname()[1]
            self.process = launch_external([
                executable, '--user-data-dir=' + str(profile),
                '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=' + str(self.port),
                '--no-first-run', 'about:blank' if self.fresh_authentication else settings.get('portalUrl', 'https://fgtsdigital.sistema.gov.br/')],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.remember_processes()
            endpoint = f'http://127.0.0.1:{self.port}'
            deadline = time.monotonic() + 20
            while True:
                try:
                    version = await asyncio.to_thread(self.version, endpoint)
                    if not version.get('Browser', '').startswith('Chrome/'):
                        raise ValueError('A porta informada não pertence ao Google Chrome')
                    break
                except (OSError, TimeoutError):
                    if time.monotonic() >= deadline:
                        raise ValueError('Não foi possível abrir o Chrome do app. Feche a janela desse perfil e tente novamente.')
                    if self.process and self.process.poll() is not None:
                        raise ValueError('Chrome encerrou antes de conectar. Feche a sessão do perfil do app e tente novamente.')
                    await asyncio.sleep(.25)
            self.playwright = await async_playwright().start()
            downloads = self.root / 'download-cache'
            downloads.mkdir(parents=True, exist_ok=True)
            self.browser = await self.playwright.chromium.connect_over_cdp(
                endpoint, no_defaults=True, is_local=True, artifacts_dir=str(downloads))
            if not self.browser.contexts:
                raise ValueError('Chrome não disponibilizou o contexto padrão')
            self.context = self.browser.contexts[0]
            self.remember_processes()
            self.context.set_default_timeout(15000)
            self.cdp = await self.browser.new_browser_cdp_session()
            if self.fresh_authentication:
                await self.reset_authentication()
                self.fresh_authentication = False
            await self.cdp.send('Browser.setDownloadBehavior', {
                'behavior':'allowAndName', 'downloadPath':str(downloads), 'eventsEnabled':True})
            for origin in ['https://fgtsdigital.sistema.gov.br', 'https://sso.acesso.gov.br',
                           'https://servicos.receitafederal.gov.br', 'https://dctfweb.cav.receita.fazenda.gov.br']:
                await self.cdp.send('Browser.setPermission', {
                    'permission':{'name':'geolocation'}, 'setting':'denied', 'origin':origin})
            return self.context
        except BaseException:
            await self.close()
            raise

    async def visibility(self, page, visible):
        """Restore/minimize the same window without interrupting its session."""
        if not self.cdp or not page or page.is_closed():
            return
        session = await self.context.new_cdp_session(page)
        try:
            target = (await session.send('Target.getTargetInfo'))['targetInfo']['targetId']
            window = await self.cdp.send('Browser.getWindowForTarget', {'targetId':target})
            state = 'normal' if visible else 'minimized'
            await self.cdp.send('Browser.setWindowBounds', {
                'windowId':window['windowId'], 'bounds':{'windowState':state}})
            confirmed = await self.cdp.send('Browser.getWindowBounds', {'windowId':window['windowId']})
            if confirmed['bounds']['windowState'] != state:
                raise ValueError('Chrome não confirmou a alteração da janela.')
            if visible:
                await page.bring_to_front()
        finally:
            await session.detach()

    async def reset_authentication(self):
        await self.context.clear_cookies(domain=re.compile(
            r'(^|\.)(acesso\.gov\.br|receitafederal\.gov\.br|receita\.fazenda\.gov\.br|fgtsdigital\.sistema\.gov\.br)$'))
        for origin in ['https://sso.acesso.gov.br', 'https://servicos.receitafederal.gov.br',
                       'https://dctfweb.cav.receita.fazenda.gov.br', 'https://cav.receita.fazenda.gov.br',
                       'https://fgtsdigital.sistema.gov.br']:
            await self.cdp.send('Storage.clearDataForOrigin', {'origin':origin, 'storageTypes':'cookies,local_storage'})

    async def download(self, page, action, timeout=60):
        """Capture Chrome's completed download for this page, including CDP sessions."""
        session = await self.context.new_cdp_session(page)
        tree = (await session.send('Page.getFrameTree'))['frameTree']
        def frames(node):
            return {node['frame']['id']}.union(*(frames(child) for child in node.get('childFrames', [])))
        frame_ids = frames(tree)
        await session.detach()
        future = asyncio.get_running_loop().create_future()
        current = None
        def begin(event):
            nonlocal current
            if event.get('frameId') in frame_ids and current is None:
                current = event['guid']
        def progress(event):
            if event.get('guid') != current or future.done():
                return
            if event['state'] == 'completed':
                future.set_result(self.root / 'download-cache' / current)
            elif event['state'] == 'canceled':
                future.set_exception(ValueError('Chrome cancelou o download da guia'))
        self.cdp.on('Browser.downloadWillBegin', begin)
        self.cdp.on('Browser.downloadProgress', progress)
        try:
            async def capture():
                await action()
                return await future
            path = await asyncio.wait_for(capture(), timeout=timeout)
            if not path.is_file():
                raise ValueError('Chrome não disponibilizou o arquivo baixado')
            class Completed:
                async def save_as(self, destination):
                    await asyncio.to_thread(shutil.copyfile, path, destination)
            return Completed(), path
        finally:
            self.cdp.remove_listener('Browser.downloadWillBegin', begin)
            self.cdp.remove_listener('Browser.downloadProgress', progress)

    @staticmethod
    def version(endpoint):
        with build_opener(ProxyHandler({})).open(endpoint + '/json/version', timeout=1) as response:
            return json.load(response)

    def remember_processes(self):
        if not self.process:
            return
        try:
            root = psutil.Process(self.process.pid)
            if root.pid in self.owned and root.create_time() != self.owned[root.pid]:
                return
            for process in [root, *root.children(recursive=True)]:
                try:
                    self.owned[process.pid] = process.create_time()
                except psutil.NoSuchProcess:
                    pass
        except psutil.NoSuchProcess:
            pass

    def owned_alive(self):
        alive = []
        for pid, created in self.owned.items():
            try:
                process = psutil.Process(pid)
                if process.create_time() == created and process.status() != psutil.STATUS_ZOMBIE:
                    alive.append(process)
            except psutil.NoSuchProcess:
                pass
        return alive

    def finish_processes(self):
        alive = self.owned_alive()
        for process in alive:
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(alive, timeout=5)
        for process in alive:
            try:
                process.kill()
            except psutil.NoSuchProcess:
                pass
        psutil.wait_procs(alive, timeout=5)
        if self.owned_alive():
            raise ValueError('Não foi possível encerrar todos os processos do Chrome do app. Feche essa sessão antes de trocar de serviço.')

    async def close(self):
        self.closing = True
        self.remember_processes()
        try:
            if self.cdp:
                try:
                    await self.cdp.send('Browser.close')
                except Exception:
                    pass
        finally:
            if self.playwright:
                await self.playwright.stop()
            if self.process:
                try:
                    await asyncio.to_thread(self.process.wait, timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            await asyncio.to_thread(self.finish_processes)
            self.owned.clear()
            self.playwright = self.browser = self.context = self.process = self.cdp = None
            self.port = None
