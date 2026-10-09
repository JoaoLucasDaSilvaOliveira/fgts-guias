from decimal import Decimal, InvalidOperation
import re
import unicodedata

HEADERS = ['COD', 'EMPRESA', 'CNPJ', 'FGTS MENSAL', 'CONSIGNADO', 'TOTAL', 'OBSERVAÇÕES']

def digits(value):
    return re.sub(r'\D', '', str(value or ''))

def money(value):
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
    else:
        text = str(value if value is not None else '').replace('R$', '').strip().replace(' ', '')
        if not re.fullmatch(r'(?:\d+(?:[.,]\d{1,2})?|\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?)', text):
            raise ValueError('Valor monetário inválido; informe zero explicitamente quando não houver valor')
        if ',' in text:
            text = text.replace('.', '').replace(',', '.')
        elif re.fullmatch(r'\d{1,3}(?:\.\d{3})+', text):
            text = text.replace('.', '')
        try:
            number = Decimal(text or '0')
        except InvalidOperation as exc:
            raise ValueError('Valor monetário inválido') from exc
    if not number.is_finite() or number < 0 or number != number.quantize(Decimal('.01')):
        raise ValueError('Informe valores positivos ou zero, com até duas casas decimais')
    return int(number * 100)

def reais(cents):
    return f'{cents // 100:,}'.replace(',', '.') + f',{cents % 100:02d}'

def valid_cnpj(value):
    text = digits(value)
    if len(text) != 14 or len(set(text)) == 1:
        return False
    for size, weights in [(12, [5,4,3,2,9,8,7,6,5,4,3,2]), (13, [6,5,4,3,2,9,8,7,6,5,4,3,2])]:
        rem = sum(int(n)*w for n,w in zip(text[:size], weights)) % 11
        if int(text[size]) != (0 if rem < 2 else 11-rem):
            return False
    return True

def normalize_row(row):
    item = dict(row)
    item['cnpj'] = digits(item.get('cnpj'))
    if not valid_cnpj(item['cnpj']):
        raise ValueError(f"CNPJ inválido: {item.get('empresa', '')}")
    if not str(item.get('empresa', '')).strip() or not str(item.get('cod', '')).strip():
        raise ValueError('COD e EMPRESA são obrigatórios')
    for key in ['fgts', 'consignado', 'total']:
        item[key] = money(item.get(key))
    if item['fgts'] + item['consignado'] != item['total']:
        raise ValueError(f"{item['empresa']}: TOTAL deve ser FGTS MENSAL + CONSIGNADO")
    item['observacoes'] = str(item.get('observacoes', ''))
    return item

def period(value):
    if not re.fullmatch(r'(0[1-9]|1[0-2])/20\d{2}', str(value)):
        raise ValueError('Competência deve estar no formato MM/AAAA')
    month, year = map(int, value.split('/'))
    return year*12 + month

def safe_filename(name):
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip().rstrip('.')
    if not text:
        raise ValueError('Nome de arquivo vazio')
    if text.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
        text = '_' + text
    return text[:160] + '.pdf'

def header_key(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value)) if not unicodedata.combining(c)).strip().upper()
