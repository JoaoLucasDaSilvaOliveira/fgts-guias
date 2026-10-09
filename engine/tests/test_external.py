import os
import unittest
from unittest.mock import patch, Mock
from fgts_guias.external import external_environment, launch_external, system_library_search


class ExternalLaunchTests(unittest.TestCase):
    def frozen(self):
        return patch.multiple('fgts_guias.external.sys', frozen=True, _MEIPASS='/bundle', create=True)

    def test_linux_restores_original_library_path_only_for_child(self):
        with self.frozen(), patch('fgts_guias.external.sys.platform', 'linux'), patch.dict(os.environ, {
            'LD_LIBRARY_PATH':'/bundle:/system', 'LD_LIBRARY_PATH_ORIG':'/system'}, clear=True):
            with patch('fgts_guias.external.subprocess.Popen') as spawn:
                launch_external(['chrome'])
                self.assertEqual(spawn.call_args.kwargs['env']['LD_LIBRARY_PATH'], '/system')
            self.assertEqual(os.environ['LD_LIBRARY_PATH'], '/bundle:/system')

    def test_linux_without_original_removes_bundle_library_path(self):
        with self.frozen(), patch('fgts_guias.external.sys.platform', 'linux'), patch.dict(os.environ, {
            'LD_LIBRARY_PATH':'/bundle', 'PATH':'/bundle/bin:/bundle-other/bin:/usr/bin'}, clear=True):
            child = external_environment()
            self.assertNotIn('LD_LIBRARY_PATH', child)
            self.assertEqual(child['PATH'], '/bundle-other/bin:/usr/bin')

    def test_development_preserves_environment(self):
        with patch('fgts_guias.external.sys.frozen', False, create=True), patch.dict(os.environ, {'LD_LIBRARY_PATH':'/user/libs'}):
            self.assertEqual(external_environment(), dict(os.environ))

    def test_windows_restores_bundle_search_after_launch_failure(self):
        kernel = Mock()
        with self.frozen(), patch('fgts_guias.external.sys.platform', 'win32'), patch('ctypes.WinDLL', return_value=kernel, create=True):
            with self.assertRaises(RuntimeError):
                with system_library_search():
                    raise RuntimeError('spawn failed')
        self.assertEqual([call.args for call in kernel.SetDllDirectoryW.call_args_list], [(None,), ('/bundle',)])

    def test_frozen_validation_keeps_actionable_error(self):
        from fgts_guias.errors import user_message
        namespace = {}
        exec(compile("def fail():\n raise ValueError('Chrome encerrou antes de conectar.')", 'fgts_guias/chrome.py', 'exec'), namespace)
        try:
            namespace['fail']()
        except ValueError as error:
            self.assertEqual(user_message(error), 'Chrome encerrou antes de conectar.')
