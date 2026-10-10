import 'dart:async';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'engine.dart';

class UpdateMenu extends StatefulWidget {
  final EngineClient engine;
  final bool running;
  final ValueChanged<bool> onBusy;
  const UpdateMenu(
      {super.key,
      required this.engine,
      required this.running,
      required this.onBusy});
  @override
  State<UpdateMenu> createState() => _UpdateMenuState();
}

class _UpdateMenuState extends State<UpdateMenu> {
  Map<String, dynamic> release = {};
  bool checking = false;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => check(automatic: true));
  }

  Future<void> check({bool automatic = false}) async {
    if (widget.running || checking) return;
    setState(() => checking = true);
    widget.onBusy(true);
    try {
      final result =
          await widget.engine.call('check_updates', {'automatic': automatic});
      if (mounted) setState(() => release = result);
    } catch (error) {
      if (mounted && !automatic) {
        setState(() => release = {...release, 'message': error.toString()});
      }
    } finally {
      if (mounted) {
        setState(() => checking = false);
        widget.onBusy(false);
      }
    }
  }

  Future<void> showUpdates() async {
    if (widget.running || checking) return;
    await check();
    if (!mounted) return;
    await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (_) => UpdateDialog(
            engine: widget.engine, release: release, onBusy: widget.onBusy));
  }

  @override
  Widget build(BuildContext context) => IconButton(
        tooltip: widget.running
            ? 'Atualizações disponíveis após encerrar o lote'
            : 'Atualizações',
        onPressed: widget.running || checking ? null : showUpdates,
        icon: checking
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2))
            : Badge(
                isLabelVisible: release['available'] == true,
                child: const Icon(Icons.system_update_alt)),
      );
}

class UpdateDialog extends StatefulWidget {
  final EngineClient engine;
  final Map<String, dynamic> release;
  final ValueChanged<bool> onBusy;
  const UpdateDialog(
      {super.key,
      required this.engine,
      required this.release,
      required this.onBusy});
  @override
  State<UpdateDialog> createState() => _UpdateDialogState();
}

class _UpdateDialogState extends State<UpdateDialog> {
  bool busy = false, automatic = true;
  double? progress;
  String? message, downloaded;
  StreamSubscription<Map<String, dynamic>>? subscription;
  @override
  void initState() {
    super.initState();
    automatic = widget.release['automatic'] != false;
    subscription = widget.engine.events.stream.listen((event) {
      if (event['event'] == 'update_progress' && mounted) {
        setState(() =>
            progress = (event['downloaded'] as num) / (event['total'] as num));
      }
    });
  }

  @override
  void dispose() {
    subscription?.cancel();
    super.dispose();
  }

  Future<void> download() async {
    final folder = await FilePicker.platform
        .getDirectoryPath(dialogTitle: 'Salvar instalador');
    if (folder == null || !mounted) return;
    setState(() {
      busy = true;
      message = null;
    });
    widget.onBusy(true);
    try {
      final result = await widget.engine.call(
          'download_update', {'tag': widget.release['tag'], 'folder': folder});
      if (mounted) setState(() => downloaded = result['path'] as String);
    } catch (error) {
      if (mounted) setState(() => message = error.toString());
    } finally {
      if (mounted) setState(() => busy = false);
      widget.onBusy(false);
    }
  }

  @override
  Widget build(BuildContext context) => PopScope(
      canPop: !busy,
      child: AlertDialog(
        title: const Text('Atualizações'),
        content: SizedBox(
            width: 430,
            child: SingleChildScrollView(
                child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                  Text(
                      'Versão instalada: ${widget.release['version'] ?? '0.3.0'}'),
                  const SizedBox(height: 12),
                  Text(downloaded != null
                      ? 'Download concluído e integridade confirmada.'
                      : widget.release['available'] == true
                          ? '${widget.release['tag']} disponível.'
                          : widget.release['message']?.toString() ??
                              'Você está usando a versão mais recente.'),
                  if (downloaded != null) ...[
                    const SizedBox(height: 12),
                    SelectableText(downloaded!),
                    const SizedBox(height: 12),
                    const Text(
                        'Feche o FGTS Guias e execute esse instalador para atualizar.'),
                  ],
                  const SizedBox(height: 16),
                  CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Verificar ao abrir'),
                      subtitle: const Text('Uma consulta por dia.'),
                      value: automatic,
                      onChanged: busy
                          ? null
                          : (value) async {
                              try {
                                await widget.engine.call('update_preferences',
                                    {'automatic': value ?? true});
                                if (mounted) {
                                  setState(() => automatic = value ?? true);
                                }
                              } catch (error) {
                                if (mounted) {
                                  setState(() => message = error.toString());
                                }
                              }
                            }),
                  if (busy) ...[
                    const SizedBox(height: 12),
                    LinearProgressIndicator(value: progress),
                    const SizedBox(height: 8),
                    Text(progress == null
                        ? 'Baixando…'
                        : 'Baixando… ${(progress! * 100).round()}%')
                  ],
                  if (message != null)
                    Text(message!,
                        style: TextStyle(
                            color: Theme.of(context).colorScheme.error)),
                ]))),
        actions: [
          TextButton(
              onPressed: busy ? null : () => Navigator.pop(context),
              child: const Text('Fechar')),
          if (widget.release['available'] == true && downloaded == null)
            FilledButton(
                onPressed: busy ? null : download,
                child: const Text('Baixar atualização')),
        ],
      ));
}
