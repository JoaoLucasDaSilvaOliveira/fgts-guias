import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;

class EngineClient {
  Process? process;
  int serial = 0;
  final pending = <int, Completer<Map<String, dynamic>>>{};
  final events = StreamController<Map<String, dynamic>>.broadcast();
  Future<void> connect() async {
    final exe = File(Platform.resolvedExecutable).parent.path;
    final name =
        Platform.isWindows ? 'fgts-guias-engine.exe' : 'fgts-guias-engine';
    final candidates = [
      p.join(exe, 'engine', name),
      p.normalize(p.join(exe, '..', 'Resources', 'engine', name)),
    ];
    String? binary;
    for (final candidate in candidates) {
      if (File(candidate).existsSync()) {
        binary = candidate;
        break;
      }
    }
    if (binary != null) {
      process = await Process.start(binary, []);
    } else {
      const defined = String.fromEnvironment('ENGINE_SOURCE');
      final source = defined.isNotEmpty
          ? defined
          : p.normalize(p.join(Directory.current.path, '..', 'engine'));
      const configured = String.fromEnvironment('PYTHON');
      final python = configured.isNotEmpty
          ? configured
          : (Platform.isWindows ? 'python' : 'python3');
      process = await Process.start(
          python,
          [
            '-u',
            '-m',
            'fgts_guias',
          ],
          workingDirectory: source);
    }
    process!.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) {
      try {
        final data = jsonDecode(line) as Map<String, dynamic>;
        if (data.containsKey('event')) {
          events.add(data);
        } else {
          final request = pending.remove(data['id']);
          if (data['ok'] == true) {
            request?.complete(Map<String, dynamic>.from(data['data']));
          } else {
            request?.completeError(data['error'] ??
                'Não foi possível concluir a ação. Tente novamente.');
          }
        }
      } catch (_) {
        events.add({
          'event': 'attention',
          'message':
              'O aplicativo perdeu a comunicação com a emissão. Encerre o lote e reinicie o aplicativo.',
        });
      }
    });
    process!.stderr
        .transform(utf8.decoder)
        .listen((text) => events.add({'event': 'diagnostic', 'message': text}));
    process!.exitCode.then((code) {
      for (final waiter in pending.values) {
        waiter.completeError(
            'A emissão foi interrompida. Feche e abra o aplicativo para continuar.');
      }
      pending.clear();
      events.add({
        'event': 'finished',
        'message':
            'A emissão foi interrompida. Feche e abra o aplicativo para continuar. Guias já solicitadas serão recuperadas ao retomar o lote.',
      });
    });
  }

  Future<Map<String, dynamic>> call(
    String command, [
    Map<String, dynamic> data = const {},
  ]) {
    if (process == null) {
      return Future.error(
          'A emissão está indisponível. Feche e abra o aplicativo para continuar.');
    }
    final id = ++serial;
    final result = Completer<Map<String, dynamic>>();
    pending[id] = result;
    process!.stdin.writeln(
      jsonEncode({'id': id, 'command': command, 'data': data}),
    );
    return result.future;
  }

  Future<void> close() async {
    await process?.stdin.close();
  }
}
