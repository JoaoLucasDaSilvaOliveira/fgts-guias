"""Launch installed programs without PyInstaller's private library search paths."""
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path


def external_environment():
    env = dict(os.environ)
    if not getattr(sys, 'frozen', False):
        return env
    if sys.platform.startswith('linux'):
        original = env.get('LD_LIBRARY_PATH_ORIG')
        if original is not None:
            env['LD_LIBRARY_PATH'] = original
        else:
            env.pop('LD_LIBRARY_PATH', None)
    bundle = Path(sys._MEIPASS).resolve()
    for variable in ('PATH', 'DYLD_LIBRARY_PATH'):
        if variable in env:
            env[variable] = os.pathsep.join(
                value for value in env[variable].split(os.pathsep)
                if not value or not Path(value).resolve().is_relative_to(bundle))
    return env


@contextmanager
def system_library_search():
    # Windows inherits SetDllDirectory independently of the environment. Reset
    # only around process creation, then restore it for the bundled driver.
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        yield
        return
    import ctypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
    kernel.SetDllDirectoryW.restype = ctypes.c_int
    if not kernel.SetDllDirectoryW(None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        if not kernel.SetDllDirectoryW(sys._MEIPASS):
            raise ctypes.WinError(ctypes.get_last_error())


def launch_external(args, **options):
    with system_library_search():
        return subprocess.Popen(args, env=external_environment(), **options)
