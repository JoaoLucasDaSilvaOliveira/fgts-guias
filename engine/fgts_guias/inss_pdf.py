"""Strict validation of the observed SENDA DARF format, without changing PDFs."""
import re
from datetime import datetime
from pathlib import Path
from pypdf import PdfReader
from .domain import digits, money

MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
          'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
NUMBER = r'\d{2}\.\d{2}\.\d{5}\.\d{7}-\d'

def parse_darf(text):
    if 'Documento de Arrecadação' not in text or 'Receitas Federais' not in text:
        raise ValueError('O PDF não foi reconhecido como DARF da DCTFWeb.')
    cnpjs = {digits(value) for value in re.findall(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b', text)}
    numbers = set(re.findall(NUMBER, text))
    totals = {money(value) for value in re.findall(r'(?:Valor Total do Documento|Valor:)\s*([\d.]+,\d{2})', text)}
    dues = set(re.findall(r'(?:Pagar este documento até|Pagar até:|Vencimento:)\s*(\d{2}/\d{2}/\d{4})', text))
    periods = set(re.findall(r'PA\s*:\s*((?:0[1-9]|1[0-2])/20\d{2})', text))
    for month, year in re.findall(r'\b(' + '|'.join(MONTHS) + r')/(20\d{2})\b', text.lower()):
        periods.add(f'{MONTHS.index(month)+1:02d}/{year}')
    fields = {'cnpj':cnpjs, 'guide':numbers, 'inss':totals, 'due':dues, 'period':periods}
    if any(len(values) != 1 for values in fields.values()):
        raise ValueError('CNPJ, competência, total, vencimento ou número do DARF não foi identificado de forma única. Confira o PDF.')
    result = {key:next(iter(values)) for key,values in fields.items()}
    datetime.strptime(result['due'], '%d/%m/%Y')
    return result

def darf_values(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size < 100:
        raise ValueError('O download não é um PDF válido.')
    with path.open('rb') as stream:
        if stream.read(5) != b'%PDF-':
            raise ValueError('O download não é um PDF válido.')
    reader = PdfReader(path)
    if reader.is_encrypted or not reader.pages:
        raise ValueError('O PDF está protegido ou não contém páginas legíveis.')
    return parse_darf('\n'.join(page.extract_text() or '' for page in reader.pages))

def validate_darf(path, company, competence, guide=None, due=None):
    values = darf_values(path)
    if values['cnpj'] != company['cnpj'] or values['period'] != competence:
        raise ValueError('O CNPJ ou a competência do DARF difere da empresa selecionada.')
    if values['inss'] != company['inss']:
        raise ValueError('O total do DARF difere do INSS informado.')
    if guide and values['guide'] != guide or due and values['due'] != due:
        raise ValueError('O número ou o vencimento do DARF difere da guia registrada.')
    return values
