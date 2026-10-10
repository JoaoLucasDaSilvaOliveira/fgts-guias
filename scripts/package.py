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
version=next(line.split(':',1)[1].strip().split('+')[0] for line in (root/'app/pubspec.yaml').read_text().splitlines() if line.startswith('version:'))
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
    requests = [
        {'id':1,'command':'bootstrap'},
        {'id':2,'command':'start','data':{'settings':{'officeCnpj':''}}},
    ]
    result=subprocess.run([str(executable)], input=''.join(json.dumps(request)+'\n' for request in requests),
                          capture_output=True,text=True,encoding='utf-8',env=env,timeout=60,check=True)
    replies=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    reply=next(item for item in replies if item.get('id')==1)
    if not reply.get('ok') or reply['data']['workspace'] or reply['data'].get('version') != version:
        raise SystemExit('Motor empacotado não iniciou com workspace vazio')
    validation = next(item for item in replies if item.get('id') == 2)
    if validation.get('ok') or 'válido' not in validation.get('error', ''):
        raise SystemExit('Motor empacotado não respondeu à validação em UTF-8')
    subprocess.run([str(executable), '--check-chrome'], env=env, timeout=60, check=True)

name=f'fgts-guias-v{version}-{platform}-x64'
release_dir=root/'dist/releases'
release_dir.mkdir(parents=True,exist_ok=True)
stage=root/'build/packages'/name
if stage.exists():shutil.rmtree(stage)
shutil.copytree(bundle,stage)
shutil.copyfile(root/'README.md',stage/'README.md')
shutil.copytree(root/'templates',stage/'templates')
shutil.copyfile(root/'packaging/assets/fgts-guias.svg',stage/'fgts-guias.svg')
(stage/'fgts-install.json').write_text(json.dumps({'appId':'org.fgtsguias.desktop','version':version}))
if platform=='linux':
    # Exercise the actual frozen installer, isolated from the user's data/menu.
    with tempfile.TemporaryDirectory(prefix='fgts-installer-check-') as sandbox:
        destination=Path(sandbox)/'program'
        env={**os.environ,'XDG_DATA_HOME':str(Path(sandbox)/'data')}
        requests=[{'id':1,'command':'installation_info'},
                  {'id':2,'command':'install','data':{'destination':str(destination)}}]
        result=subprocess.run([str(stage/'engine/fgts-guias-engine')],
            input=''.join(json.dumps(request)+'\n' for request in requests),
            capture_output=True,text=True,encoding='utf-8',env=env,timeout=90,check=True)
        replies=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
        if len(replies)!=2 or not all(reply.get('ok') for reply in replies) or not (destination/'fgts_guias').is_file():
            raise SystemExit('Instalador Linux congelado não passou pela instalação isolada: '+result.stdout)
if platform=='windows':
    archive=release_dir/(name+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as package:
        for path in sorted(stage.rglob('*')):
            if path.is_file():package.write(path,path.relative_to(stage.parent))
else:
    archive=release_dir/(name+'.tar.gz')
    with tarfile.open(archive,'w:gz') as package:package.add(stage,arcname=name)
def checksum(path):
    with path.open('rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    path.with_name(path.name+'.sha256').write_text(f'{digest}  {path.name}\n')
checksum(archive)
if platform=='linux':
    header=(root/'packaging/linux/launcher.sh').read_text().replace('@PACKAGE_NAME@',name)
    with archive.open('rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    header=header.replace('@PAYLOAD_SHA256@',digest)
    installer=release_dir/(name+'.run')
    with installer.open('wb') as output, archive.open('rb') as payload:
        output.write(header.encode())
        shutil.copyfileobj(payload,output)
    installer.chmod(0o755)
    checksum(installer)
elif platform=='windows':
    compiler=shutil.which('ISCC') or r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
    subprocess.run([compiler,f'/DAppVersion={version}',f'/DBundlePath={stage}',f'/DOutputPath={release_dir}',
                    str(root/'packaging/windows/installer.iss')],check=True,cwd=root)
    checksum(release_dir/(name+'-setup.exe'))
print('Pacote preparado:',archive)
