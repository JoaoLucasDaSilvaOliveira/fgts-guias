import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fgts_guias/inputs.dart';

void main() {
  test('zero fields remain empty while payload supplies zero and total', () {
    final row = <String, dynamic>{
      'fgts': '0,00',
      'consignado': '',
      'total': '0,00'
    };
    final controllers = CompanyControllers(row);
    expect(controllers.fields['fgts']!.text, isEmpty);
    expect(controllers.fields['consignado']!.text, isEmpty);
    expect(controllers.fields['total']!.text, isEmpty);
    expect(companyPayload(row)['fgts'], '0,00');
    expect(companyPayload(row)['total'], '0,00');
    controllers.dispose();
  });

  test('sum is exact and imported total is derived from the components', () {
    expect(rowTotal({'fgts': '0,10', 'consignado': '0,20'}), '0,30');
    expect(
        companyPayload({
          'fgts': '1.234,56',
          'consignado': '43,86',
          'total': '999,99'
        })['total'],
        '1278,42');
    expect(rowTotal({'fgts': '', 'consignado': '10,'}), '10,00');
    expect(() => moneyCents('invalid'), throwsFormatException);
  });

  test('pasting a currency value into an empty field preserves cents', () {
    final pasted = MoneyFormatter().formatEditUpdate(
      TextEditingValue.empty,
      const TextEditingValue(
          text: 'R\$ 1.234,56', selection: TextSelection.collapsed(offset: 11)),
    );
    expect(pasted.text, '1234,56');
    expect(moneyCents(pasted.text), 123456);
  });
}
