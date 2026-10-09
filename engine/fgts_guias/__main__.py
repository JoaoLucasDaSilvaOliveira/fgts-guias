import asyncio
import json
import sys
from .storage import Storage
from .domain import normalize_row, period, valid_cnpj, digits
from .files import read_table, write_table
from .browser import Portal, chrome_path

class Engine:
    def __init__(self):
        self.store = Storage()
        self.gate = asyncio.Event()
        self.gate.set()
        self.task = None
        self.skip = False
        self.current = None
        self.browser_finished = False
        self.portal = Portal(self.store, self.event, self.checkpoint, self.browser_closed)
    def browser_closed(self):
        if self.task and not self.task.done() and not self.browser_finished:
            self.browser_finished = True
            self.task.cancel()
            self.event('finished', company=digits(self.current['cnpj']) if self.current else None, message='Chrome foi fechado. Lote encerrado imediatamente; emissões solicitadas ficam registradas para recuperação.')
    def event(self, kind, **values):
        print(json.dumps({'event':kind, **values}, ensure_ascii=False), flush=True)
    async def checkpoint(self):
        await self.gate.wait()
        if self.skip:
            raise ValueError('Empresa ignorada pelo operador')
    async def batch(self, rows, settings):
        try:
            for source in rows:
                self.current, self.skip = source, False
                while True:
                    try:
                        await self.checkpoint()
                        workspace = self.store.get('workspace', {})
                        source = next((r for r in workspace.get('rows', []) if digits(r.get('cnpj')) == digits(self.current['cnpj'])), self.current)
                        await self.portal.run(normalize_row(source), settings)
                        break
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        if self.skip:
                            self.event('skipped', company=digits(self.current['cnpj']))
                            break
                        self.gate.clear()
                        self.event('attention', company=digits(self.current['cnpj']), message=str(exc), **getattr(exc, 'details', {}))
                        await self.gate.wait()
                        if self.skip:
                            self.event('skipped', company=digits(self.current['cnpj']))
                            break
            self.event('finished', message='Lote encerrado. Confira as empresas salvas e ignoradas.')
        except asyncio.CancelledError:
            if not self.browser_finished:
                self.event('finished', message='Lote interrompido. Emissões solicitadas permanecem registradas.')
        finally:
            self.current = None
    async def command(self, name, data):
        if name == 'bootstrap':
            return {'workspace':self.store.get('workspace', {}), 'chrome':chrome_path(), 'dataDir':str(self.store.root)}
        if name == 'save':
            self.store.put('workspace', data)
        elif name == 'import':
            return {'rows':read_table(data['path'])}
        elif name in ['export','template']:
            write_table(data['path'], [] if name == 'template' else data['rows'])
        elif name == 'open_browser':
            if self.task and not self.task.done():
                raise ValueError('Encerre o lote antes de abrir outra sessão')
            await self.portal.launch(data['settings'])
            self.event('progress', message='Chrome conectado. Entre no GOV.BR antes de iniciar o lote.')
        elif name == 'start':
            if self.task and not self.task.done():
                raise ValueError('Já existe um lote em andamento')
            settings = data['settings']
            if not valid_cnpj(settings['officeCnpj']):
                raise ValueError('Informe um CNPJ válido para o escritório')
            if period(settings['initial']) > period(settings['final']):
                raise ValueError('Competência inicial deve preceder a final')
            if not settings.get('output') or not chrome_path():
                raise ValueError('Escolha a pasta de destino e instale o Google Chrome')
            rows = [r for r in data['rows'] if r.get('selected', True)]
            if not rows:
                raise ValueError('Selecione pelo menos uma empresa')
            normalized = [normalize_row(r) for r in rows]
            if len({r['cnpj'] for r in normalized}) != len(rows):
                raise ValueError('Há CNPJs repetidos no lote')
            self.browser_finished = False
            self.gate.set()
            self.task = asyncio.create_task(self.batch(rows, dict(settings)))
        elif name == 'pause':
            self.gate.clear()
            self.event('attention', message='Pausado. A ação atual será concluída antes da pausa.')
        elif name == 'resume':
            self.gate.set()
            self.event('progress', message='Retomando conferência…')
        elif name == 'skip':
            self.skip = True
            self.gate.set()
        elif name == 'stop':
            if self.task and not self.task.done():
                self.task.cancel()
                await self.task
        elif name == 'recover':
            if not self.current or self.gate.is_set():
                raise ValueError('Pause uma empresa antes de recuperar a guia')
            await self.portal.recover(normalize_row(data['row']), data['settings'], data['path'], data['guide'], data['due'])
        elif name == 'close_browser':
            if self.task and not self.task.done() and self.gate.is_set():
                raise ValueError('Pause antes de trocar o certificado')
            self.browser_closed()
            await self.portal.close()
        else:
            raise ValueError('Comando desconhecido')
        return {}

async def serve():
    engine = Engine()
    try:
        while line := await asyncio.to_thread(sys.stdin.readline):
            request = {}
            try:
                request = json.loads(line)
                result = await engine.command(request['command'], request.get('data', {}))
                reply = {'id':request['id'], 'ok':True, 'data':result}
            except Exception as exc:
                reply = {'id':request.get('id'), 'ok':False, 'error':str(exc)}
            print(json.dumps(reply, ensure_ascii=False), flush=True)
    finally:
        if engine.task and not engine.task.done():
            engine.task.cancel()
            await engine.task
        await engine.portal.close()
def main():
    asyncio.run(serve())
if __name__ == '__main__':
    main()
