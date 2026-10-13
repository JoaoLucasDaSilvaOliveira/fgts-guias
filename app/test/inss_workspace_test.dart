import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fgts_guias/main.dart';
import 'workspace_layout_test.dart' show FakeEngine;

void main() {
  testWidgets(
      'switching service keeps FGTS data, INSS is monetary and batch locks service',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(800, 650));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final engine = FakeEngine();
    await tester.pumpWidget(GuideApp(engine: engine));
    await tester.pumpAndSettle();
    final selector = find.byKey(const ValueKey('service-selector'));
    await tester
        .tap(find.descendant(of: selector, matching: find.text('INSS')));
    await tester.pumpAndSettle();
    expect(find.text('FGTS MENSAL'), findsNothing);
    final field = find.byWidgetPredicate((widget) =>
        widget is TextFormField && widget.key.toString().contains('-inss'));
    expect(field, findsOneWidget);
    await tester.enterText(field, 'R\$ 123,45 letras');
    await tester.pump(const Duration(milliseconds: 600));
    expect(engine.saves.last['rows'][0]['inss'], '123,45');
    expect(engine.saves.last['rows'][0]['fgts'], '100,00');
    expect(engine.saves.last['settings']['service'], 'inss');
    expect(engine.saves.last['settings']['initial'],
        engine.saves.last['settings']['final']);
    await tester.tap(find.text('Configuração do lote'));
    await tester.pumpAndSettle();
    expect(find.text('Competência'), findsOneWidget);
    expect(find.text('Período final'), findsNothing);
    await tester.tap(find.byTooltip('Fechar configuração'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Baixar selecionadas'));
    await tester.pumpAndSettle();
    expect(tester.widget<SegmentedButton<String>>(selector).onSelectionChanged,
        isNull);
    expect(tester.takeException(), isNull);
  });
}
