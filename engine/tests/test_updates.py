import asyncio
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fgts_guias.updates import Updates, API, REPO, asset_name, semver

class Store:
    def __init__(self): self.value = {}; self.root = Path('/example/data')
    def get(self, key, default=None): return self.value.copy()
    def put(self, key, value): self.value = value

class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.payload = b'example installer'
        self.name = 'fgts-guias-v0.4.0-linux-x64.run'
        self.url = f'https://github.com/{REPO}/releases/download/v0.4.0/{self.name}'
        self.release = {'tag_name':'v0.4.0', 'draft':False, 'prerelease':False, 'assets':[
            {'name':self.name, 'size':len(self.payload), 'state':'uploaded',
             'browser_download_url':self.url, 'digest':'sha256:' + hashlib.sha256(self.payload).hexdigest()}]}
        self.store = Store()
        self.updates = Updates(self.store, lambda *args, **kwargs: None)
        self.platform = patch('fgts_guias.updates.platform.system', return_value='Linux')
        self.platform.start()
        self.machine = patch('fgts_guias.updates.platform.machine', return_value='x86_64')
        self.machine.start()
        self.addCleanup(self.platform.stop)
        self.addCleanup(self.machine.stop)
    def response(self, url):
        return io.BytesIO(json.dumps(self.release).encode() if url == API else self.payload)
    def test_numeric_versions_architecture_and_daily_cache(self):
        self.assertGreater(semver('v0.10.0'), semver('v0.9.9'))
        with self.assertRaises(ValueError): asset_name('v0.4.0', 'Linux', 'aarch64')
        with patch('fgts_guias.updates.open_url', side_effect=self.response) as request:
            self.assertTrue(asyncio.run(self.updates.check())['available'])
            self.assertTrue(asyncio.run(self.updates.check(True))['available'])
            self.assertEqual(request.call_count, 1)
    def test_validated_download_and_corruption_does_not_replace_file(self):
        with tempfile.TemporaryDirectory() as folder, patch('fgts_guias.updates.open_url', side_effect=self.response):
            result = self.updates.download('v0.4.0', folder)
            path = Path(result['path'])
            self.assertEqual(path.read_bytes(), self.payload)
            path.write_bytes(b'operator file')
            with self.assertRaises(ValueError): self.updates.download('v0.4.0', folder)
            self.assertEqual(path.read_bytes(), b'operator file')
    def test_bad_digest_leaves_no_installer_or_temporary_file(self):
        self.release['assets'][0]['digest'] = 'sha256:' + '0' * 64
        with tempfile.TemporaryDirectory() as folder, patch('fgts_guias.updates.open_url', side_effect=self.response):
            with self.assertRaises(ValueError): self.updates.download('v0.4.0', folder)
            self.assertEqual(list(Path(folder).iterdir()), [])
    def test_existing_temporary_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder, patch('fgts_guias.updates.open_url', side_effect=self.response):
            temporary = Path(folder) / (self.name + '.part')
            temporary.write_bytes(b'other download')
            with self.assertRaises(FileExistsError): self.updates.download('v0.4.0', folder)
            self.assertEqual(temporary.read_bytes(), b'other download')
    def test_unofficial_url_and_prerelease_are_rejected(self):
        self.release['assets'][0]['browser_download_url'] = 'https://example.com/installer'
        with tempfile.TemporaryDirectory() as folder, patch('fgts_guias.updates.open_url', side_effect=self.response):
            with self.assertRaises(ValueError): self.updates.download('v0.4.0', folder)
        self.release['prerelease'] = True
        with patch('fgts_guias.updates.open_url', side_effect=self.response):
            self.assertFalse(asyncio.run(self.updates.check())['available'])

    def test_active_batch_blocks_update_commands(self):
        from fgts_guias.__main__ import Engine
        async def run():
            with patch('fgts_guias.__main__.Storage', return_value=self.store):
                engine = Engine()
                engine.task = asyncio.create_task(asyncio.sleep(1))
                try:
                    for command in ('download_update', 'check_updates', 'install'):
                        with self.assertRaises(ValueError): await engine.command(command, {})
                finally:
                    engine.task.cancel()
        asyncio.run(run())
