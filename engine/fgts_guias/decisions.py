"""A pending operator decision releases only its suspended validation call."""
import asyncio
import copy
import uuid
from datetime import datetime, timezone

class RetryCompany(Exception):
    pass

class Decisions:
    def __init__(self, store):
        self.store = store
        self.pending = None

    def create(self, company, context, expected, found):
        if self.pending:
            raise ValueError('Já existe uma decisão pendente')
        descriptor = copy.deepcopy(dict(id=uuid.uuid4().hex, company=company,
            context=context, expected=expected, found=found))
        self.pending = (descriptor, asyncio.get_running_loop().create_future())
        return self.pending

    def accept(self, token, company):
        if not self.pending:
            raise ValueError('Não há decisão pendente')
        descriptor, future = self.pending
        if future.done() or descriptor['id'] != token or descriptor['company'] != company:
            raise ValueError('A decisão expirou ou os dados mudaram. Use Retomar para conferir novamente.')
        self.store.record_decision({**descriptor, 'action':'accepted', 'accepted_at':datetime.now(timezone.utc).isoformat()})
        future.set_result(True)

    def reject(self, token):
        if not self.pending:
            raise ValueError('Não há decisão pendente')
        descriptor, future = self.pending
        if future.done() or descriptor['id'] != token:
            raise ValueError('A decisão expirou. Confira a pendência atual.')
        self.store.record_decision({**descriptor, 'action':'rejected',
            'rejected_at':datetime.now(timezone.utc).isoformat()})
        future.set_result(False)

    def retry(self):
        if self.pending and not self.pending[1].done():
            self.pending[1].set_result(False)

    def clear(self):
        if self.pending and not self.pending[1].done():
            self.pending[1].cancel()
        self.pending = None
