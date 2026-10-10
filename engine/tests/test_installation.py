import json
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch
from fgts_guias.installation import APP_ID, install

@unittest.skipUnless(sys.platform == 'linux', 'Installer uses Linux desktop integration')
class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'payload'
        (self.source / 'engine').mkdir(parents=True)
        (self.source / 'fgts_guias').write_text('version 1')
        (self.source / 'engine/fgts-guias-engine').write_text('engine')
        (self.source / 'fgts-install.json').write_text(json.dumps({'appId':APP_ID}))
        self.target = self.root / 'folder with spaces/app'
        self.data = self.root / 'private-data'
        self.data.mkdir()
        (self.data / 'local.sqlite3').write_bytes(b'preserve')
        self.applications = self.root / 'applications'
        self.processes = patch('fgts_guias.installation.running_app', return_value=False)
        self.processes.start()
        self.addCleanup(self.processes.stop)
    def install(self, desktop=False):
        return install(self.source, self.target, self.data, desktop, home=self.root, applications=self.applications)
    def test_install_upgrade_and_data_preservation(self):
        self.install()
        entry = (self.applications / 'fgts-guias.desktop').read_text()
        self.assertIn(f'Exec="{self.target}/fgts_guias"', entry)
        (self.source / 'fgts_guias').write_text('version 2')
        result = self.install()
        self.assertEqual((self.target / 'fgts_guias').read_text(), 'version 2')
        self.assertEqual((Path(result['backup']) / 'fgts_guias').read_text(), 'version 1')
        self.assertEqual((self.data / 'local.sqlite3').read_bytes(), b'preserve')
    def test_failed_shortcut_restores_previous_version(self):
        self.install()
        previous = (self.applications / 'fgts-guias.desktop').read_bytes()
        (self.source / 'fgts_guias').write_text('version 2')
        with patch('fgts_guias.installation.shutil.which', return_value=None):
            with self.assertRaises(ValueError): self.install(desktop=True)
        self.assertEqual((self.target / 'fgts_guias').read_text(), 'version 1')
        self.assertEqual((self.applications / 'fgts-guias.desktop').read_bytes(), previous)
    def test_running_app_unrelated_folder_and_private_data_are_protected(self):
        with patch('fgts_guias.installation.running_app', return_value=True):
            with self.assertRaises(ValueError): self.install()
        self.target.mkdir(parents=True)
        (self.target / 'operator-file').write_text('keep')
        with self.assertRaises(ValueError): self.install()
        self.assertEqual((self.target / 'operator-file').read_text(), 'keep')
        with self.assertRaises(ValueError): install(self.source, self.data, self.data)
