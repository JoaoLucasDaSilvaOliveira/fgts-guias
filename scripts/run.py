"""Developer launcher. Run with the virtual environment's Python."""
import subprocess
import sys
import shutil
from pathlib import Path
root = Path(__file__).resolve().parents[1]
platform = {'linux':'linux','darwin':'macos','win32':'windows'}.get(sys.platform)
flutter = shutil.which('flutter')
if not platform or not flutter:
    raise SystemExit('Instale Flutter desktop para seu sistema e adicione-o ao PATH.')
subprocess.run([flutter,'pub','get'],cwd=root/'app',check=True)
subprocess.run([flutter,'run','-d',platform,
                '--dart-define=PYTHON='+sys.executable,
                '--dart-define=ENGINE_SOURCE='+str(root/'engine')],cwd=root/'app',check=True)
