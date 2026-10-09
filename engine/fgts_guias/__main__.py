import asyncio
import json
import sys
from .storage import Storage
from .errors import user_message
from .domain import normalize_row, period, valid_cnpj, digits
from .files import read_table, write_table
from .browser import Portal, chrome_path
from .decisions import Decisions, RetryCompany

class Engine:
    def __init__(self):
        self.store = Storage()
        self.decisions = Decisions(self.store)
        self.batch_settings = None
        self.gate = asyncio.Event()
        self.gate.set()
        self.task = None
        self.skip = False
        self.current = None
        self.browser_finished = False
        self.auth_watcher = None
        self.portal = Portal(self.store, self.event, self.checkpoint, self.browser_closed, self.decision)
    def browser_closed(self):
        if self.task and not self.task.done() and not self.browser_finished:
            self.browser_finished = True
            self.task.cancel()
            self.event('finished', company=digits(self.current['cnpj']) if self.current else None, message='O Chrome foi fechado e o lote foi interrompido. Ao iniciar novamente, o app recupera as guias já solicitadas.')
    def event(self, kind, **values):
        print(json.dumps({'event':kind, **values}, ensure_ascii=False), flush=True)
    async def checkpoint(self):
        await self.gate.wait()
        if self.skip:
            raise ValueError('Empresa ignorada pelo operador')
    def cancel_auth_watcher(self):
        if self.auth_watcher and not self.auth_watcher.done():
            self.auth_watcher.cancel()
        self.auth_watcher = None

    async def watch_authentication(self, settings):
        try:
            while not self.gate.is_set():
                await asyncio.sleep(1)
                if await self.portal.authentication_ready(settings):
                    await self.portal.visibility(False)
                    self.gate.set()
                    self.event('progress', message='Autenticação concluída. Retomando em segundo plano…')
                    return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.event('diagnostic', message='Retomada automática indisponível; use Retomar: ' + str(exc))

    async def decision(self, company, scope, expected, found, **context):
        settings = self.batch_settings
        descriptor, future = self.decisions.create(company, {
            'scope':scope, 'initial':settings['initial'], 'final':settings['final'], **context}, expected, found)
        self.gate.clear()
        self.event('attention', company=company['cnpj'], message='Os dados encontrados diferem dos informados. Confira os valores abaixo antes de continuar.',
            decision_id=descriptor['id'], expected=expected, found=found,
            difference={k:found[k]-v for k,v in expected.items() if isinstance(v, int) and isinstance(found.get(k), int)},
            scope=scope, guide=context.get('guide'))
        try:
            await self.portal.visibility(True)
            if not await future:
                raise RetryCompany()
        finally:
            self.decisions.clear()

    async def batch(self, rows, settings):
        self.batch_settings = settings
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
                    except RetryCompany:
                        if self.skip:
                            self.event('skipped', company=digits(self.current['cnpj']))
                            break
                        continue
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        if self.skip:
                            self.event('skipped', company=digits(self.current['cnpj']))
                            break
                        self.gate.clear()
                        self.event('diagnostic', message=repr(exc))
                        details = getattr(exc, 'details', {})
                        self.event('attention', company=digits(self.current['cnpj']), message=user_message(exc), **details)
                        try:
                            await self.portal.visibility(True)
                        except Exception as window_error:
                            self.event('diagnostic', message='Não foi possível mostrar Chrome: ' + str(window_error))
                        self.cancel_auth_watcher()
                        if details.get('reason') in ['authentication', 'captcha']:
                            self.auth_watcher = asyncio.create_task(self.watch_authentication(settings))
                        await self.gate.wait()
                        self.cancel_auth_watcher()
                        if self.skip:
                            self.event('skipped', company=digits(self.current['cnpj']))
                            break
            try:
                await self.portal.visibility(False)
            except Exception as exc:
                self.event('diagnostic', message='Não foi possível minimizar Chrome ao concluir: ' + str(exc))
            self.event('finished', completed=True, message='Lote concluído. Confira as guias salvas e as empresas ignoradas.')
        except asyncio.CancelledError:
            if not self.browser_finished:
                self.event('finished', message='Lote interrompido. Ao iniciar novamente, o app recupera as guias já solicitadas.')
        finally:
            self.cancel_auth_watcher()
            self.decisions.clear()
            self.batch_settings = None
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
                if not self.portal.page or self.portal.page.is_closed():
                    raise ValueError('Encerre o lote antes de abrir outra sessão')
            else:
                await self.portal.launch(data['settings'])
            await self.portal.visibility(True)
        elif name == 'start':
            if self.task and not self.task.done():
                raise ValueError('Já existe um lote em andamento')
            settings = data['settings']
            if not valid_cnpj(settings['officeCnpj']):
                raise ValueError('Informe um CNPJ válido para o titular do certificado.')
            if period(settings['initial']) > period(settings['final']):
                raise ValueError('O período inicial não pode ser posterior ao final.')
            if not settings.get('output') or not chrome_path():
                raise ValueError('Escolha a pasta onde salvar as guias e confira se o Google Chrome está instalado.')
            rows = [r for r in data['rows'] if r.get('selected', True)]
            if not rows:
                raise ValueError('Selecione pelo menos uma empresa')
            normalized = [normalize_row(r) for r in rows]
            if len({r['cnpj'] for r in normalized}) != len(rows):
                raise ValueError('Há CNPJs repetidos no lote')
            settings = dict(settings)
            self.browser_finished = False
            self.gate.set()
            self.task = asyncio.create_task(self.batch(rows, dict(settings)))
        elif name == 'pause':
            self.decisions.retry()
            self.cancel_auth_watcher()
            self.gate.clear()
            await self.portal.visibility(True)
            self.event('attention', message='Pausa solicitada. O app conclui a ação em andamento e aguarda você retomar.')
        elif name == 'accept_difference':
            if not self.current or self.gate.is_set() or not self.decisions.pending:
                raise ValueError('Não há divergência específica aguardando aceitação')
            workspace = self.store.get('workspace', {})
            source = next((r for r in workspace.get('rows', []) if digits(r.get('cnpj')) == digits(self.current['cnpj'])), self.current)
            await self.portal.guard(checkpoint=False)
            await self.portal.visibility(False)
            try:
                self.decisions.accept(data.get('decision_id'), normalize_row(source))
            except Exception:
                await self.portal.visibility(True)
                raise
            self.gate.set()
            self.event('progress', message='Divergência aceita nesta etapa. Continuando a conferência…')
        elif name == 'reject_difference':
            if not self.current or self.gate.is_set() or not self.decisions.pending:
                raise ValueError('Não há divergência específica aguardando decisão')
            self.decisions.reject(data.get('decision_id'))
            self.event('attention', company=self.current['cnpj'],
                message='Divergência negada. Revise os dados ou a guia no Chrome. Retomar fará uma nova conferência.')
        elif name == 'resume':
            await self.portal.guard(checkpoint=False)
            await self.portal.visibility(False)
            self.cancel_auth_watcher()
            self.decisions.retry()
            self.gate.set()
            self.event('progress', message='Retomando conferência…')
        elif name == 'skip':
            self.cancel_auth_watcher()
            await self.portal.visibility(False)
            self.skip = True
            self.decisions.retry()
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
                engine.event('diagnostic', message=repr(exc))
                reply = {'id':request.get('id'), 'ok':False, 'error':user_message(exc)}
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
