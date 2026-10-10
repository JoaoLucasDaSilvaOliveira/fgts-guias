import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fgts_guias/engine.dart';
import 'package:fgts_guias/main.dart';
import 'package:fgts_guias/updates.dart';

class InstallationEngine extends EngineClient {
  int attempts = 0;
  @override
  Future<void> connect() async {}
  @override
  Future<Map<String, dynamic>> call(String command,
      [Map<String, dynamic> data = const {}]) async {
    if (command == 'installation_info') {
      return {
        'version': '0.3.0',
        'destination': '/home/example/.local/opt/fgts-guias'
      };
    }
    if (command == 'install') {
      attempts++;
      if (attempts == 1) {
        throw 'Feche o FGTS Guias antes de instalar ou atualizar.';
      }
      return {'path': '/home/example/.local/opt/fgts-guias/fgts_guias'};
    }
    return {};
  }

  @override
  Future<void> close() async {
    await events.close();
  }
}

class WaitingUpdateEngine extends EngineClient {
  final release = Completer<Map<String, dynamic>>();
  @override
  Future<Map<String, dynamic>> call(String command,
          [Map<String, dynamic> data = const {}]) =>
      release.future;
}

void main() {
  testWidgets('installer keeps destination after failure and succeeds on retry',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(800, 650));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final engine = InstallationEngine();
    await tester.pumpWidget(GuideApp(engine: engine, installing: true));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Instalar'));
    await tester.pumpAndSettle();
    expect(find.text('Feche o FGTS Guias antes de instalar ou atualizar.'),
        findsOneWidget);
    expect(
        find.widgetWithText(TextField, '/home/example/.local/opt/fgts-guias'),
        findsOneWidget);
    await tester.tap(find.text('Instalar'));
    await tester.pumpAndSettle();
    expect(find.text('Instalação concluída'), findsOneWidget);
    expect(find.text('Abrir FGTS Guias'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets('update check locks starting work and unlocks on completion',
      (tester) async {
    final engine = WaitingUpdateEngine();
    final busy = <bool>[];
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            body:
                UpdateMenu(engine: engine, running: false, onBusy: busy.add))));
    await tester.pump();
    expect(busy, [true]);
    engine.release
        .complete({'version': '0.3.0', 'available': true, 'tag': 'v0.4.0'});
    await tester.pumpAndSettle();
    expect(busy, [true, false]);
    expect(find.byType(Badge), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    await engine.events.close();
  });
  testWidgets('active batch disables update menu and never checks releases',
      (tester) async {
    final engine = WaitingUpdateEngine();
    final busy = <bool>[];
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            body:
                UpdateMenu(engine: engine, running: true, onBusy: busy.add))));
    await tester.pumpAndSettle();
    expect(busy, isEmpty);
    expect(
        tester.widget<IconButton>(find.byType(IconButton)).onPressed, isNull);
    await tester.pumpWidget(const SizedBox());
    await engine.events.close();
  });
}
