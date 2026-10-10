"""Per-user Linux installation, atomic replacement and desktop registration."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from .version import VERSION

APP_ID = 'org.fgtsguias.desktop'

def desktop_quote(value):
    if '\n' in value or '\r' in value or '=' in value:
        raise ValueError('Escolha um caminho sem quebras de linha ou sinal de igual para registrar o atalho.')
    # Desktop Entry string escaping is applied before Exec argument quoting.
    quoted = ''.join('\\' + char if char in '\\"`$' else '%%' if char == '%' else char for char in value)
    return '"' + quoted.replace('\\', '\\\\').replace('\t', '\\t') + '"'

def payload():
    if sys.platform != 'linux' or not getattr(sys, 'frozen', False):
        raise ValueError('Abra o instalador Linux baixado na página de releases.')
    source = Path(sys.executable).resolve().parent.parent
    if not (source / 'fgts_guias').is_file() or not (source / 'fgts-install.json').is_file():
        raise ValueError('O instalador está incompleto. Baixe novamente.')
    return source

def info():
    payload()
    return {'version':VERSION, 'destination':str(Path.home() / '.local/opt/fgts-guias')}

def running_app():
    # Exclude this installer window, but detect portable and installed instances.
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            if (process / 'exe').resolve().name == 'fgts_guias':
                arguments = (process / 'cmdline').read_bytes().split(b'\0')
                if b'--install' not in arguments:
                    return True
        except (OSError, PermissionError):
            continue
    return False

def install(source, destination, data_root, desktop=False, home=None, applications=None):
    import fcntl
    target = Path(destination).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with (target.parent / ('.' + target.name + '.install.lock')).open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('Outra instalação está em andamento. Aguarde sua conclusão.') from exc
        return _install(source, destination, data_root, desktop, home, applications)

def _install(source, destination, data_root, desktop=False, home=None, applications=None):
    if running_app():
        raise ValueError('Feche o FGTS Guias antes de instalar ou atualizar.')
    source, target, data_root = Path(source).resolve(), Path(destination).expanduser().resolve(), Path(data_root).resolve()
    if source == target or source in target.parents or target in source.parents or target == data_root or target in data_root.parents or data_root in target.parents:
        raise ValueError('Escolha uma pasta exclusiva para instalar o aplicativo.')
    manifest = source / 'fgts-install.json'
    if json.loads(manifest.read_text()).get('appId') != APP_ID or not (source / 'fgts_guias').is_file():
        raise ValueError('O pacote de instalação não é válido.')
    if target.exists():
        marker = target / 'fgts-install.json'
        if not marker.is_file() or json.loads(marker.read_text()).get('appId') != APP_ID:
            raise ValueError('A pasta escolhida contém outros arquivos. Escolha uma pasta nova.')
    home = Path(home or Path.home())
    applications = Path(applications or Path(os.environ.get('XDG_DATA_HOME', home / '.local/share')) / 'applications')
    launcher = applications / 'fgts-guias.desktop'
    icon = str(target / 'fgts-guias.svg').replace('\\', '\\\\').replace('\t', '\\t')
    entry = ('[Desktop Entry]\nType=Application\nName=FGTS Guias\nComment=Emissão assistida de guias FGTS\n'
             f'Exec={desktop_quote(str(target / "fgts_guias"))}\n'
             f'Icon={icon}\nTerminal=false\nCategories=Office;Finance;\nStartupNotify=true\n')
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.fgts-stage-', dir=target.parent))
    backup = target.with_name(target.name + '.previous-' + uuid.uuid4().hex[:8])
    old_entry = launcher.read_bytes() if launcher.exists() else None
    moved = placed = False
    try:
        shutil.copytree(source, stage, dirs_exist_ok=True)
        (stage / 'fgts_guias').chmod(0o755)
        (stage / 'engine/fgts-guias-engine').chmod(0o755)
        if target.exists():
            target.rename(backup)
            moved = True
        stage.rename(target)
        placed = True
        applications.mkdir(parents=True, exist_ok=True)
        temporary_entry = applications / ('.fgts-' + uuid.uuid4().hex + '.desktop')
        temporary_entry.write_text(entry)
        temporary_entry.replace(launcher)
        if desktop:
            # xdg-user-dir handles localized desktop paths; no shell expansion.
            utility = shutil.which('xdg-user-dir')
            directory = Path(subprocess.check_output([utility, 'DESKTOP'], text=True).strip()) if utility else home / 'Desktop'
            if not directory.is_dir() or directory.resolve() == home.resolve():
                raise ValueError('A pasta da área de trabalho não foi encontrada. Desmarque o atalho e tente novamente.')
            shortcut = directory / 'fgts-guias.desktop'
            shortcut.write_text(entry)
            shortcut.chmod(0o755)
    except BaseException:
        if placed:
            shutil.rmtree(target)
        if moved:
            backup.rename(target)
        if old_entry is not None:
            launcher.write_bytes(old_entry)
        elif launcher.exists():
            launcher.unlink()
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {'path':str(target / 'fgts_guias'), 'backup':str(backup) if moved else None}
