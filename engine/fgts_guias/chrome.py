"""Conventional Chrome launch with a dedicated persistent profile."""
import asyncio
import json
import socket
import subprocess
import time
from urllib.request import build_opener, ProxyHandler
from playwright.async_api import async_playwright

class ChromeSession:
    def __init__(self, root):
        self.root = root
        self.playwright = self.browser = self.context = self.process = self.cdp = None
        self.port = None
        self.closing = False

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
            self.process = subprocess.Popen([
                executable, '--user-data-dir=' + str(profile),
                '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=' + str(self.port),
                '--no-first-run', 'https://fgtsdigital.sistema.gov.br/'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
            self.context.set_default_timeout(15000)
            self.cdp = await self.browser.new_browser_cdp_session()
            await self.cdp.send('Browser.setDownloadBehavior', {
                'behavior':'allowAndName', 'downloadPath':str(downloads), 'eventsEnabled':True})
            for origin in ['https://fgtsdigital.sistema.gov.br', 'https://sso.acesso.gov.br']:
                await self.cdp.send('Browser.setPermission', {
                    'permission':{'name':'geolocation'}, 'setting':'denied', 'origin':origin})
            return self.context
        except BaseException:
            await self.close()
            raise

    @staticmethod
    def version(endpoint):
        with build_opener(ProxyHandler({})).open(endpoint + '/json/version', timeout=1) as response:
            return json.load(response)

    async def close(self):
        self.closing = True
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
                    self.process.terminate()
            self.playwright = self.browser = self.context = self.process = self.cdp = None
            self.port = None
