"""Build and archive the application on the target OS."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

root = Path(__file__).resolve().parents[1]
platform = {'linux':'linux', 'win32':'windows', 'darwin':'macos'}.get(sys.platform)
if not platform:
    raise SystemExit('Sistema não suportado')
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--name','fgts-guias-engine',
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
    bundle=bundles[0]
    target=bundle/'Contents/Resources/engine'
elif platform=='windows':
    bundle=root/'app/build/windows/x64/runner/Release'
    target=bundle/'engine'
else:
    bundle=root/'app/build/linux/x64/release/bundle'
    target=bundle/'engine'
if target.exists(): shutil.rmtree(target)
shutil.copytree(root/'dist/engine/fgts-guias-engine',target)

# Verify the frozen engine using an empty, isolated user directory.
executable=target/('fgts-guias-engine.exe' if platform=='windows' else 'fgts-guias-engine')
with tempfile.TemporaryDirectory() as sandbox:
    env={**os.environ,'XDG_DATA_HOME':sandbox,'APPDATA':sandbox,'LOCALAPPDATA':sandbox}
    result=subprocess.run([str(executable)], input=json.dumps({'id':1,'command':'bootstrap'})+'\n',
                          capture_output=True,text=True,env=env,timeout=60,check=True)
    replies=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    reply=next(item for item in replies if item.get('id')==1)
    if not reply.get('ok') or reply['data']['workspace']:
        raise SystemExit('Motor empacotado não iniciou com workspace vazio')
    subprocess.run([str(executable), '--check-chrome'], env=env, timeout=60, check=True)

version=next(line.split(':',1)[1].strip().split('+')[0] for line in (root/'app/pubspec.yaml').read_text().splitlines() if line.startswith('version:'))
name=f'fgts-guias-v{version}-{platform}-x64'
release_dir=root/'dist/releases'
release_dir.mkdir(parents=True,exist_ok=True)
stage=root/'build/packages'/name
if stage.exists():shutil.rmtree(stage)
shutil.copytree(bundle,stage)
shutil.copyfile(root/'README.md',stage/'README.md')
shutil.copytree(root/'templates',stage/'templates')
if platform=='windows':
    archive=release_dir/(name+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as package:
        for path in sorted(stage.rglob('*')):
            if path.is_file():package.write(path,path.relative_to(stage.parent))
else:
    archive=release_dir/(name+'.tar.gz')
    with tarfile.open(archive,'w:gz') as package:package.add(stage,arcname=name)
digest=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
archive.with_name(archive.name+'.sha256').write_text(f'{digest}  {archive.name}\n')
print('Pacote preparado:',archive)
