import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fgts_guias/engine.dart';
import 'package:fgts_guias/main.dart';

class FakeEngine extends EngineClient {
  @override
  Future<void> connect() async {}
  @override
  Future<Map<String, dynamic>> call(String command,
      [Map<String, dynamic> data = const {}]) async {
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
      expect(find.text('Emitir selecionadas'), findsOneWidget);
      expect(find.text('Baixar novamente guias já salvas'), findsNothing);
      await tester.tap(find.byTooltip('Opções de emissão'));
      await tester.pumpAndSettle();
      expect(find.text('Baixar novamente guias já salvas'), findsOneWidget);
      expect(find.text('Reiniciar emissão'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('download-saved-option')));
      await tester.pumpAndSettle();
      expect(find.text('Baixar selecionadas'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.tap(find.text('Configuração do lote'));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
  }
}
