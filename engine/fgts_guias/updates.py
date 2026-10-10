"""Release discovery and verified downloads. Never replace a running app."""
import hashlib
import asyncio
import json
import os
import platform
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from .version import VERSION

REPO = 'JoaoLucasDaSilvaOliveira/fgts-guias'
API = f'https://api.github.com/repos/{REPO}/releases/latest'
MAX_SIZE = 2 * 1024 ** 3

def semver(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', value)
    if not match:
        raise ValueError('A versão publicada não foi reconhecida.')
    return tuple(map(int, match.groups()))

def asset_name(tag, system=None, machine=None):
    semver(tag)
    system, machine = system or platform.system(), machine or platform.machine()
    if machine.lower() not in ('x86_64', 'amd64') or system not in ('Linux', 'Windows'):
        raise ValueError('Não há instalador para este sistema ou arquitetura.')
    suffix = 'linux-x64.run' if system == 'Linux' else 'windows-x64-setup.exe'
    return f'fgts-guias-v{tag.removeprefix("v")}-{suffix}'

def official_asset(url, tag, name):
    expected = f'https://github.com/{REPO}/releases/download/v{tag.removeprefix("v")}/{name}'
    if url != expected:
        raise ValueError('O endereço do pacote não corresponde ao repositório oficial.')
    return url

def open_url(url):
    request = Request(url, headers={'User-Agent':f'FGTSGuias/{VERSION}', 'Accept':'application/vnd.github+json'})
    response = urlopen(request, timeout=20)
    parsed = urlparse(response.url)
    if parsed.scheme != 'https' or parsed.hostname not in (
            'api.github.com', 'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'):
        response.close()
        raise ValueError('O download foi redirecionado para um endereço não reconhecido.')
    return response

class Updates:
    def __init__(self, store, notify):
        self.store, self.notify = store, notify

    async def check(self, automatic=False):
        preferences = self.store.get('updates', {})
        cached = preferences.get('release')
        if automatic and (not preferences.get('automatic', True) or time.time() - preferences.get('checked', 0) < 86400):
            result = {**(cached or {}), 'version':VERSION, 'automatic':preferences.get('automatic', True)}
            if result.get('tag') and semver(result['tag']) <= semver(VERSION):
                result['available'] = False
            return result
        try:
            def fetch():
                with open_url(API) as response:
                    return json.loads(response.read(2 * 1024 ** 2))
            release = await asyncio.to_thread(fetch)
            tag = release['tag_name']
            result = {'available':False, 'tag':tag, 'version':VERSION}
            if not release.get('draft') and not release.get('prerelease') and semver(tag) > semver(VERSION):
                name = asset_name(tag)
                assets = [a for a in release['assets'] if a['name'] == name and a.get('state') == 'uploaded']
                if len(assets) == 1:
                    asset = assets[0]
                    official_asset(asset['browser_download_url'], tag, name)
                    result.update(available=True, name=name, size=asset['size'])
                else:
                    result['message'] = 'A nova versão ainda não tem instalador para este sistema.'
            preferences.update(checked=time.time(), release=result)
            self.store.put('updates', preferences)
            return {**result, 'automatic':preferences.get('automatic', True)}
        except (URLError, HTTPError, TimeoutError, OSError, KeyError, ValueError) as exc:
            preferences['checked'] = time.time()
            if not cached:
                preferences['release'] = {'message':'Não foi possível consultar as atualizações. Tente novamente.'}
            self.store.put('updates', preferences)
            raise ValueError('Não foi possível consultar as atualizações. Confira a conexão e tente novamente.') from exc

    def download(self, tag, folder):
        try:
            return self._download(tag, folder)
        except (URLError, TimeoutError) as exc:
            raise ValueError('Não foi possível baixar a atualização. Confira a conexão e tente novamente.') from exc

    def _download(self, tag, folder):
        # Fetch fresh official metadata; URLs/digests from the UI are never accepted.
        with open_url(API) as response:
            release = json.loads(response.read(2 * 1024 ** 2))
        if release['tag_name'] != tag or release.get('draft') or release.get('prerelease') or semver(tag) <= semver(VERSION):
            raise ValueError('A versão disponível mudou. Verifique as atualizações novamente.')
        name = asset_name(tag)
        assets = [a for a in release['assets'] if a['name'] == name]
        if len(assets) != 1:
            raise ValueError('O instalador não está disponível para este sistema.')
        asset = assets[0]
        url = official_asset(asset['browser_download_url'], tag, name)
        digest = asset.get('digest', '') or ''
        expected = digest.removeprefix('sha256:') if digest.startswith('sha256:') else ''
        if not re.fullmatch(r'[0-9a-f]{64}', expected):
            checksum = next((a for a in release['assets'] if a['name'] == name + '.sha256'), None)
            if not checksum:
                raise ValueError('A release não fornece uma verificação de integridade do instalador.')
            with open_url(official_asset(checksum['browser_download_url'], tag, name + '.sha256')) as response:
                content = response.read(1024).decode('utf-8').strip()
            match = re.fullmatch(r'([0-9a-f]{64})\s+\*?' + re.escape(name), content)
            if not match:
                raise ValueError('A verificação de integridade publicada não é válida.')
            expected = match.group(1)
        size = asset['size']
        if not isinstance(size, int) or not 0 < size <= MAX_SIZE:
            raise ValueError('O tamanho do instalador não é válido.')
        destination = Path(folder).expanduser()
        if not destination.is_dir():
            raise ValueError('Escolha uma pasta existente para baixar a atualização.')
        target = destination / name
        if target.exists():
            with target.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() == expected:
                    return {'path':str(target)}
            raise ValueError('Já existe outro arquivo com esse nome. Escolha outra pasta.')
        temp = destination / (name + '.part')
        owned = False
        try:
            # Exclusive create also prevents two downloads from sharing a temporary file.
            with temp.open('xb') as stream:
                owned = True
                with open_url(url) as response:
                    return self._capture(response, stream, temp, target, size, expected)
        finally:
            if owned and temp.exists():
                temp.unlink()

    def _capture(self, response, stream, temp, target, size, expected):
        sha, count, last = hashlib.sha256(), 0, 0
        deadline = time.monotonic() + 1800
        while chunk := response.read(1024 * 1024):
            count += len(chunk)
            if count > size or time.monotonic() > deadline:
                raise ValueError('O download não foi concluído como esperado. Tente novamente.')
            stream.write(chunk)
            sha.update(chunk)
            if time.monotonic() - last > .25:
                self.notify('update_progress', downloaded=count, total=size)
                last = time.monotonic()
        stream.flush()
        os.fsync(stream.fileno())
        if count != size or sha.hexdigest() != expected:
            raise ValueError('A integridade do download não foi confirmada. Baixe novamente.')
        temp.chmod(0o700)
        # No overwrite if another download or operator created the target meanwhile.
        os.link(temp, target)
        return {'path':str(target)}
