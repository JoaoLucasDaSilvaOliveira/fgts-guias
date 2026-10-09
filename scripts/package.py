"""Run manually on the target OS after operator validation; not a CI job."""
from pathlib import Path
import subprocess
import sys
import shutil

root = Path(__file__).resolve().parents[1]
platform = {'linux':'linux', 'win32':'windows', 'darwin':'macos'}.get(sys.platform)
if not platform:
    raise SystemExit('Sistema não suportado')
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--onedir','--name','fgts-guias-engine',
                '--paths',str(root/'engine'),'--collect-all','playwright',
                '--distpath',str(root/'dist/engine'),'--workpath',str(root/'build/pyinstaller'),
                '--specpath',str(root/'build'),str(root/'engine/run_engine.py')],check=True,cwd=root)
flutter = shutil.which('flutter')
if not flutter:
    raise SystemExit('Flutter não encontrado')
subprocess.run([flutter,'pub','get'],check=True,cwd=root/'app')
subprocess.run([flutter,'build',platform,'--release'],check=True,cwd=root/'app')
if platform=='macos':
    bundles = list((root/'app/build/macos/Build/Products/Release').glob('*.app'))
    if len(bundles)!=1: raise SystemExit('Pacote macOS ambíguo')
    target=bundles[0]/'Contents/Resources/engine'
elif platform=='windows':
    target=root/'app/build/windows/x64/runner/Release/engine'
else:
    target=root/'app/build/linux/x64/release/bundle/engine'
shutil.copytree(root/'dist/engine/fgts-guias-engine',target,dirs_exist_ok=True)
print('Pacote preparado em',target.parent)
