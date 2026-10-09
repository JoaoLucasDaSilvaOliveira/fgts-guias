import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

String maskCnpj(String value) {
  final digits = value.replaceAll(RegExp(r'\D'), '');
  final buffer = StringBuffer();
  for (var i = 0; i < digits.length && i < 14; i++) {
    if (i == 2 || i == 5) buffer.write('.');
    if (i == 8) buffer.write('/');
    if (i == 12) buffer.write('-');
    buffer.write(digits[i]);
  }
  return buffer.toString();
}

class CnpjFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
      TextEditingValue oldValue, TextEditingValue newValue) {
    if (!newValue.composing.isCollapsed) return oldValue;
    final text = maskCnpj(newValue.text);
    final end =
        newValue.selection.extentOffset.clamp(0, newValue.text.length).toInt();
    final count =
        newValue.text.substring(0, end).replaceAll(RegExp(r'\D'), '').length;
    var position = 0, seen = 0;
    while (position < text.length && seen < count) {
      if (RegExp(r'\d').hasMatch(text[position])) seen++;
      position++;
    }
    return TextEditingValue(
        text: text, selection: TextSelection.collapsed(offset: position));
  }
}

/// Preserve decimal semantics: typing 12,34 means twelve reais, not 1.234.
/// Letters are dropped; a malformed numeric edit is silently rejected.
class MoneyFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
      TextEditingValue oldValue, TextEditingValue newValue) {
    if (!newValue.composing.isCollapsed) return oldValue;
    var clean = newValue.text.replaceAll(RegExp(r'[^0-9,.]'), '');
    if (newValue.text.isNotEmpty && clean.isEmpty) return oldValue;
    final grouped =
        clean.contains(',') || RegExp(r'^\d{1,3}(?:\.\d{3})+$').hasMatch(clean);
    clean = grouped ? clean.replaceAll('.', '') : clean.replaceAll('.', ',');
    if (!RegExp(r'^\d*(?:,\d{0,2})?$').hasMatch(clean)) return oldValue;
    final end =
        newValue.selection.extentOffset.clamp(0, newValue.text.length).toInt();
    var prefix =
        newValue.text.substring(0, end).replaceAll(RegExp(r'[^0-9,.]'), '');
    prefix = grouped ? prefix.replaceAll('.', '') : prefix.replaceAll('.', ',');
    if (clean.startsWith(',')) {
      clean = '0$clean';
      prefix = '0$prefix';
    }
    return TextEditingValue(
        text: clean,
        selection: TextSelection.collapsed(
            offset: prefix.length.clamp(0, clean.length).toInt()));
  }
}

int moneyCents(String value) {
  var text = value.replaceAll('R\$', '').replaceAll(' ', '').trim();
  if (text.contains(',') || RegExp(r'^\d{1,3}(?:\.\d{3})+$').hasMatch(text)) {
    text = text.replaceAll('.', '');
  } else {
    text = text.replaceAll('.', ',');
  }
  if (!RegExp(r'^\d*(?:,\d{0,2})?$').hasMatch(text)) {
    throw const FormatException('Valor monetário inválido');
  }
  final parts = text.split(',');
  return (int.tryParse(parts.first) ?? 0) * 100 +
      (parts.length > 1 ? int.parse(parts[1].padRight(2, '0')) : 0);
}

String moneyText(int cents) =>
    '${cents ~/ 100},${(cents % 100).toString().padLeft(2, '0')}';

String rowTotal(Map<String, dynamic> row) =>
    moneyText(moneyCents(row['fgts']?.toString() ?? '') +
        moneyCents(row['consignado']?.toString() ?? ''));

Map<String, dynamic> companyPayload(Map<String, dynamic> row) => {
      ...row,
      'fgts': moneyText(moneyCents(row['fgts']?.toString() ?? '')),
      'consignado': moneyText(moneyCents(row['consignado']?.toString() ?? '')),
      'total': rowTotal(row),
    };

String companyFieldText(Map<String, dynamic> row, String key) {
  final value = row[key]?.toString() ?? '';
  if (key == 'cnpj') return maskCnpj(value);
  if (['fgts', 'consignado', 'total'].contains(key) && moneyCents(value) == 0) {
    return '';
  }
  return value;
}

class CompanyControllers {
  final Map<String, TextEditingController> fields;
  CompanyControllers(Map<String, dynamic> row)
      : fields = {
          for (final key in [
            'cod',
            'empresa',
            'cnpj',
            'fgts',
            'consignado',
            'total',
            'observacoes'
          ])
            key: TextEditingController(text: companyFieldText(row, key))
        };
  void dispose() {
    for (final controller in fields.values) {
      controller.dispose();
    }
  }
}

Future<String?> pickCompetence(BuildContext context, String current) async {
  final parts = current.split('/');
  final now = DateTime.now();
  final parsed = parts.length == 2
      ? DateTime((int.tryParse(parts[1]) ?? now.year).clamp(2000, 2099).toInt(),
          (int.tryParse(parts[0]) ?? now.month).clamp(1, 12).toInt())
      : now;
  final value = await showDatePicker(
      context: context,
      initialDate: parsed,
      firstDate: DateTime(2000),
      lastDate: DateTime(2099, 12, 31),
      helpText: 'Selecione uma data do mês de apuração',
      fieldLabelText: 'Data no mês de apuração',
      cancelText: 'Cancelar',
      confirmText: 'Selecionar');
  return value == null
      ? null
      : '${value.month.toString().padLeft(2, '0')}/${value.year}';
}
