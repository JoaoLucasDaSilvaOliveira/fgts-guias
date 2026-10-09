import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fgts_guias/engine.dart';
import 'package:fgts_guias/main.dart';

class FakeEngine extends EngineClient {
  final saves = <Map<String, dynamic>>[];
  @override
  Future<void> connect() async {}
  @override
  Future<Map<String, dynamic>> call(String command,
      [Map<String, dynamic> data = const {}]) async {
    if (command == 'save') saves.add(data);
    if (command != 'bootstrap') return {};
    return {
      'chrome': '/example/chrome',
      'workspace': {
        'settings': {
          'officeName': 'Escritório de exemplo',
          'officeCnpj': '00000000000191',
          'initial': '09/2026',
          'final': '09/2026',
          'output': '/example/guias'
        },
        'rows': [
          {
            'cod': '1',
            'empresa': 'Empresa de exemplo',
            'cnpj': '00000000000191',
            'fgts': '100,00',
            'consignado': '0,00',
            'total': '100,00'
          }
        ],
      }
    };
  }

  @override
  Future<void> close() => events.close();
}

void main() {
  testWidgets(
      'tracking identifies the company through a pause and clears it on completion',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final engine = FakeEngine();
    await tester.pumpWidget(GuideApp(engine: engine));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Baixar selecionadas'));
    await tester.pump();
    engine.events.add({
      'event': 'progress',
      'company': '00000000000191',
      'message': 'Abrindo empresa…'
    });
    await tester.pump();
    expect(find.byKey(const ValueKey('active-company')), findsOneWidget);
    expect(find.text('1 — Empresa de exemplo'), findsOneWidget);
    engine.events.add({
      'event': 'attention',
      'company': '00000000000191',
      'message': 'Confira os valores.'
    });
    await tester.pump();
    expect(find.text('1 — Empresa de exemplo'), findsOneWidget);
    engine.events.add({
      'event': 'saved',
      'company': '00000000000191',
      'path': '/example/guia.pdf'
    });
    await tester.pump();
    engine.events.add({'event': 'finished', 'completed': true});
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('active-company')), findsNothing);
    expect(find.text('Lote concluído. 1 guia salva.'), findsOneWidget);
    expect(find.textContaining('0 já salvas'), findsNothing);
    expect(tester.takeException(), isNull);
  });
  for (final size in [
    const Size(800, 650),
    const Size(1280, 800),
    const Size(1680, 1000)
  ]) {
    testWidgets(
        'grouped toolbar fits $size and keeps emission options contextual',
        (tester) async {
      await tester.binding.setSurfaceSize(size);
      addTearDown(() => tester.binding.setSurfaceSize(null));
      tester.view.physicalSize = size;
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(GuideApp(engine: FakeEngine()));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(find.text('Baixar selecionadas'), findsOneWidget);
      expect(
          find.text('Faz novo download, mesmo com PDF salvo.'), findsNothing);
      await tester.tap(find.byTooltip('Otimização do download'));
      await tester.pumpAndSettle();
      expect(
          find.text('Reutiliza o PDF salvo, se disponível.'), findsOneWidget);
      expect(
          find.text('Faz novo download, mesmo com PDF salvo.'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('download-new-option')));
      await tester.pumpAndSettle();
      expect(find.text('Baixar selecionadas'), findsOneWidget);
      expect(find.text('Baixar nova guia'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.tap(find.text('Configuração do lote'));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await tester.tap(find.byTooltip('Fechar configuração'));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
  }
  testWidgets(
      'column resizing keeps header and data aligned and persists widths',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final engine = FakeEngine();
    await tester.pumpWidget(GuideApp(engine: engine));
    await tester.pumpAndSettle();
    final handle = find.byKey(const ValueKey('resize-column-empresa'));
    final field = find.byWidgetPredicate((widget) =>
        widget is TextFormField && widget.key.toString().contains('-empresa'));
    final before = tester.getSize(field).width;
    await tester.drag(handle, const Offset(80, 0));
    await tester.pump(const Duration(milliseconds: 600));
    await tester.pumpAndSettle();
    final after = tester.getSize(field).width;
    expect(after, greaterThan(before + 40));
    expect(engine.saves.last['settings']['columnWidths'][1], greaterThan(260));
    expect(engine.saves.last['rows'][0]['empresa'], 'Empresa de exemplo');
    expect(tester.takeException(), isNull);
    await tester.tap(handle);
    await tester.pump(const Duration(milliseconds: 50));
    await tester.tap(handle);
    await tester.pump(const Duration(milliseconds: 600));
    await tester.pumpAndSettle();
    expect(tester.getSize(field).width, before);
    expect(engine.saves.last['settings']['columnWidths'][1], 220);
  });
}
