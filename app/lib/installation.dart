import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'engine.dart';

class InstallationPage extends StatefulWidget {
  final EngineClient? engine;
  const InstallationPage({super.key, this.engine});
  @override
  State<InstallationPage> createState() => _InstallationPageState();
}

class _InstallationPageState extends State<InstallationPage> {
  late final EngineClient engine;
  final destination = TextEditingController();
  bool ready = false, busy = false, desktop = false;
  String? installed, message;
  String version = '';
  @override
  void initState() {
    super.initState();
    engine = widget.engine ?? EngineClient();
    prepare();
  }

  Future<void> prepare() async {
    try {
      await engine.connect();
      final data = await engine.call('installation_info');
      if (!mounted) return;
      setState(() {
        destination.text = data['destination'] as String;
        version = data['version'] as String;
        ready = true;
      });
    } catch (error) {
      if (mounted) setState(() => message = error.toString());
    }
  }

  Future<void> install() async {
    setState(() {
      busy = true;
      message = null;
    });
    try {
      final result = await engine.call('install', {
        'destination': destination.text,
        'desktop': desktop,
      });
      if (mounted) setState(() => installed = result['path'] as String);
    } catch (error) {
      if (mounted) setState(() => message = error.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  void dispose() {
    destination.dispose();
    engine.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(
            child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 620),
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(32),
                  child: Card(
                      child: Padding(
                          padding: const EdgeInsets.all(28),
                          child: Column(
                              mainAxisSize: MainAxisSize.min,
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                    installed == null
                                        ? 'Instalar FGTS Guias'
                                        : 'Instalação concluída',
                                    style: Theme.of(context)
                                        .textTheme
                                        .headlineMedium),
                                const SizedBox(height: 12),
                                Text(installed == null
                                    ? 'Versão $version · Linux'
                                    : 'Abra o aplicativo pelo menu de aplicativos.'),
                                const SizedBox(height: 24),
                                if (installed == null) ...[
                                  TextField(
                                      controller: destination,
                                      enabled: ready && !busy,
                                      decoration: InputDecoration(
                                          labelText: 'Pasta de instalação',
                                          suffixIcon: IconButton(
                                              tooltip: 'Escolher pasta',
                                              icon:
                                                  const Icon(Icons.folder_open),
                                              onPressed: !ready || busy
                                                  ? null
                                                  : () async {
                                                      final folder =
                                                          await FilePicker
                                                              .platform
                                                              .getDirectoryPath();
                                                      if (folder != null) {
                                                        destination.text =
                                                            '$folder${Platform.pathSeparator}fgts-guias';
                                                      }
                                                    }))),
                                  const SizedBox(height: 12),
                                  CheckboxListTile(
                                      contentPadding: EdgeInsets.zero,
                                      title: const Text(
                                          'Criar atalho na área de trabalho'),
                                      value: desktop,
                                      onChanged: busy
                                          ? null
                                          : (value) => setState(
                                              () => desktop = value ?? false)),
                                  const SizedBox(height: 8),
                                  const Text(
                                      'O aplicativo será instalado para seu usuário. Atualizações preservam suas empresas, configurações e guias.'),
                                ],
                                if (message != null)
                                  Padding(
                                      padding: const EdgeInsets.only(top: 16),
                                      child: Text(message!,
                                          style: TextStyle(
                                              color: Theme.of(context)
                                                  .colorScheme
                                                  .error))),
                                if (busy)
                                  const Padding(
                                      padding: EdgeInsets.only(top: 20),
                                      child: LinearProgressIndicator()),
                                const SizedBox(height: 24),
                                Wrap(spacing: 12, runSpacing: 8, children: [
                                  FilledButton(
                                      onPressed: busy ||
                                              (!ready && installed == null)
                                          ? null
                                          : installed == null
                                              ? install
                                              : () async {
                                                  await engine.call(
                                                      'launch_installed',
                                                      {'path': installed});
                                                  await SystemNavigator.pop();
                                                },
                                      child: Text(busy
                                          ? 'Instalando…'
                                          : installed == null
                                              ? 'Instalar'
                                              : 'Abrir FGTS Guias')),
                                  TextButton(
                                      onPressed: busy
                                          ? null
                                          : () => SystemNavigator.pop(),
                                      child: Text(installed == null
                                          ? 'Cancelar'
                                          : 'Fechar')),
                                ]),
                              ]))),
                ))),
      );
}
