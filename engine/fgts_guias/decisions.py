"""Operator decisions, with exact-value reuse during one company iteration."""
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
        self.accepted = {}
        self.identity = None

    @staticmethod
    def pairs(expected, found):
        return {key: (value, found.get(key)) for key, value in expected.items()}

    def observe(self, company, context, expected, found):
        identity = (company['cnpj'], context.get('initial'), context.get('final'))
        if identity != self.identity:
            self.accepted.clear()
            self.identity = identity
        pairs = self.pairs(expected, found)
        for key, pair in pairs.items():
            if self.accepted.get(key) != pair:
                self.accepted.pop(key, None)
        return pairs

    def covered(self, company, context, expected, found):
        pairs = self.observe(company, context, expected, found)
        derived_total = all(all(key in data for key in ('fgts', 'consignado', 'total')) and
            data['total'] == data['fgts'] + data['consignado'] for data in (expected, found))
        covered = all(before == after or self.accepted.get(key) == (before, after)
            for key, (before, after) in pairs.items() if key != 'total' or not derived_total)
        if covered and derived_total and expected['total'] != found['total']:
            self.accepted['total'] = copy.deepcopy(pairs['total'])
        return covered

    def reset_company(self):
        self.clear()
        self.accepted.clear()
        self.identity = None

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
            raise ValueError('Os dados mudaram desde a conferência. Negue a divergência e clique em Retomar para conferir os valores atualizados.')
        self.store.record_decision({**descriptor, 'action':'accepted', 'accepted_at':datetime.now(timezone.utc).isoformat()})
        pairs = self.observe(company, descriptor['context'], descriptor['expected'], descriptor['found'])
        self.accepted.update(copy.deepcopy({key: pair for key, pair in pairs.items() if pair[0] != pair[1]}))
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
