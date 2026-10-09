import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'inputs.dart';
import 'package:file_picker/file_picker.dart';

import 'engine.dart';

void main() => runApp(const GuideApp());
const ink = Color(0xff193b35);
const paper = Color(0xfff5f4ef);

class GuideApp extends StatelessWidget {
  const GuideApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        debugShowCheckedModeBanner: false,
        title: 'FGTS Guias',
        locale: const Locale('pt', 'BR'),
        supportedLocales: const [Locale('pt', 'BR')],
        localizationsDelegates: GlobalMaterialLocalizations.delegates,
        theme: ThemeData(
          useMaterial3: true,
          scaffoldBackgroundColor: paper,
          colorScheme: ColorScheme.fromSeed(seedColor: ink),
          inputDecorationTheme: const InputDecorationTheme(
            border: OutlineInputBorder(),
            isDense: true,
          ),
          filledButtonTheme: FilledButtonThemeData(
            style: FilledButton.styleFrom(backgroundColor: ink),
          ),
          textTheme: const TextTheme(
            headlineMedium: TextStyle(fontWeight: FontWeight.w700, color: ink),
          ),
        ),
        home: const Workspace(),
      );
}

class Workspace extends StatefulWidget {
  const Workspace({super.key});
  @override
  State<Workspace> createState() => _WorkspaceState();
}

class _WorkspaceState extends State<Workspace> {
  final engine = EngineClient();
  final tableScroll = ScrollController();
  final tableHorizontalScroll = ScrollController();
  final office = TextEditingController(),
      cnpj = TextEditingController(),
      initial = TextEditingController(),
      finalPeriod = TextEditingController(),
      output = TextEditingController();
  List<Map<String, dynamic>> rows = [];
  final controllers = <Map<String, dynamic>, CompanyControllers>{};
  final states = <String, String>{};
  final log = <String>[];
  Map<String, dynamic>? attention;
  bool ready = false, running = false, paused = false;
  bool downloadSaved = false;
  String status = 'Iniciando o aplicativo…', chrome = '';
  StreamSubscription<Map<String, dynamic>>? subscription;
  Timer? saver;
  Map<String, dynamic> get settings => {
        'officeName': office.text,
        'officeCnpj': cnpj.text,
        'initial': initial.text,
        'final': finalPeriod.text,
        'output': output.text,
        'downloadSaved': downloadSaved,
      };
  @override
  void initState() {
    super.initState();
    connect();
  }

  Future<void> connect() async {
    subscription = engine.events.stream.listen((event) {
      if (!mounted) return;
      setState(() {
        if (event['event'] == 'browser_visibility') return;
        if (event['event'] == 'diagnostic') {
          return;
        }
        status = event['message']?.toString() ?? status;
        if (event['company'] != null) {
          states[event['company'].toString()] = event['event'].toString();
        }
        if (event['event'] == 'attention') {
          paused = true;
          attention = event;
        }
        if (event['event'] == 'progress') {
          paused = false;
          attention = null;
        }
        if (event['event'] == 'saved') {
          final reused = event['reused'] == true;
          states[event['company'].toString()] = reused ? 'reused' : 'saved';
          status = reused
              ? 'Guia já salva e conferida: ${event['path']}'
              : 'PDF conferido e salvo: ${event['path']}';
        }
        if (event['event'] == 'finished') {
          if (event['completed'] == true) {
            final saved =
                states.values.where((value) => value == 'saved').length;
            final reused =
                states.values.where((value) => value == 'reused').length;
            final skipped =
                states.values.where((value) => value == 'skipped').length;
            status =
                'Lote concluído: $saved baixadas, $reused já salvas e $skipped empresas ignoradas.';
          }
          running = false;
          paused = false;
          attention = null;
        }
        log.add(status);
        if (log.length > 80) log.removeAt(0);
      });
    });
    try {
      await engine.connect();
      final data = await engine.call('bootstrap');
      final workspace = Map<String, dynamic>.from(data['workspace'] ?? {});
      final config = Map<String, dynamic>.from(workspace['settings'] ?? {});
      office.text = config['officeName'] ?? '';
      cnpj.text = maskCnpj(config['officeCnpj'] ?? '');
      initial.text = config['initial'] ?? '';
      finalPeriod.text = config['final'] ?? '';
      output.text = config['output'] ?? '';
      downloadSaved = config['downloadSaved'] == true;
      rows = (workspace['rows'] as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
      maskRows();
      setState(() {
        ready = true;
        chrome = data['chrome']?.toString() ?? '';
        status = chrome.isEmpty
            ? 'Instale o Google Chrome e reabra o aplicativo para emitir guias.'
            : 'Pronto.';
      });
    } catch (e) {
      setState(() => status =
          'Não foi possível iniciar o aplicativo. Feche e abra novamente. Se o problema continuar, reinstale o FGTS Guias.');
    }
  }

  Future<void> persist() async {
    await engine.call('save',
        {'settings': settings, 'rows': rows.map(companyPayload).toList()});
  }

  void changed() {
    saver?.cancel();
    saver = Timer(const Duration(milliseconds: 500), () {
      persist().catchError((e) {
        showError(e);
      });
    });
  }

  String errorMessage(Object error) {
    if (error is String) return error;
    return 'Não foi possível concluir esta ação. Tente novamente. Se o problema continuar, feche e abra o aplicativo.';
  }

  void showError(Object e) {
    if (mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(errorMessage(e))));
    }
  }

  Future<void> act(String command, [Map<String, dynamic>? data]) async {
    try {
      await persist();
      await engine.call(command, data ?? {});
    } catch (e) {
      showError(e);
    }
  }

  Future<void> removeAllCompanies() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remover todas as empresas?'),
        content: Text(
            'As ${rows.length} empresas serão removidas da tabela. As guias salvas permanecerão na pasta escolhida.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancelar')),
          FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Remover todas')),
        ],
      ),
    );
    if (confirmed != true || !mounted || running) return;
    saver?.cancel();
    try {
      await engine.call(
          'save', {'settings': settings, 'rows': <Map<String, dynamic>>[]});
      if (!mounted) return;
      setState(() {
        for (final controller in controllers.values) {
          controller.dispose();
        }
        controllers.clear();
        rows.clear();
        states.clear();
        attention = null;
        status = 'Empresas removidas.';
      });
    } catch (error) {
      showError(error);
    }
  }

  Future<void> importRows() async {
    final picked = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['csv', 'xlsx'],
    );
    if (picked == null) return;
    try {
      final data = await engine.call('import', {
        'path': picked.files.single.path,
      });
      setState(
        () => rows = (data['rows'] as List)
            .map((e) => Map<String, dynamic>.from(e))
            .toList(),
      );
      maskRows();
      await persist();
    } catch (e) {
      showError(e);
    }
  }

  Future<void> export(bool template) async {
    final path = await FilePicker.platform.saveFile(
      dialogTitle: template ? 'Salvar modelo de planilha' : 'Exportar empresas',
      fileName: template ? 'template-fgts.xlsx' : 'empresas.xlsx',
      type: FileType.custom,
      allowedExtensions: ['xlsx', 'csv'],
    );
    if (path != null) {
      await act(template ? 'template' : 'export',
          {'path': path, 'rows': rows.map(companyPayload).toList()});
    }
  }

  Future<void> restartEmission() async {
    final selected = rows.where((row) => row['selected'] != false).length;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Reiniciar emissão?'),
        content: Text(
            'Refazer a emissão de $selected empresas, de ${initial.text} a ${finalPeriod.text}? Isso pode gerar outra guia para débitos que já têm guia emitida. Os PDFs anteriores serão mantidos. Emissões com resultado incerto serão recuperadas antes de qualquer nova tentativa.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancelar')),
          FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Reiniciar emissão')),
        ],
      ),
    );
    if (confirmed == true && mounted && !running) {
      await startBatch(restart: true);
    }
  }

  Future<void> start() => startBatch();

  Future<void> startBatch({bool restart = false}) async {
    try {
      await persist();
      setState(() {
        states.clear();
        log.clear();
        status = 'Iniciando o lote…';
        running = true;
        paused = false;
        attention = null;
      });
      await engine.call('start', {
        'settings': settings,
        'rows': rows.map(companyPayload).toList(),
        'restartEmission': restart
      });
    } catch (e) {
      if (mounted) {
        setState(() => running = false);
      }
      showError(e);
    }
  }

  Future<void> recovery() async {
    final company = attention?['company'];
    final matches = rows.where(
      (r) => r['cnpj'].toString().replaceAll(RegExp(r'\D'), '') == company,
    );
    if (matches.isEmpty) {
      showError(
          'Não foi possível identificar a empresa pausada. Confira o lote antes de recuperar a guia.');
      return;
    }
    final number = TextEditingController(), due = TextEditingController();
    final accepted = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Recuperar guia existente'),
        content: SizedBox(
          width: 420,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'No Chrome, baixe o PDF da guia pela Consulta de Guias. Informe o número e o vencimento, depois selecione o arquivo baixado. O app confere e salva na pasta escolhida.',
              ),
              const SizedBox(height: 20),
              TextField(
                controller: number,
                decoration: const InputDecoration(labelText: 'Número da guia'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: due,
                decoration: const InputDecoration(
                  labelText: 'Vencimento · DD/MM/AAAA',
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Escolher PDF'),
          ),
        ],
      ),
    );
    if (accepted != true) return;
    final picked = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
    );
    if (picked != null) {
      await act('recover', {
        'row': companyPayload(matches.first),
        'settings': settings,
        'path': picked.files.single.path,
        'guide': number.text,
        'due': due.text,
      });
    }
    number.dispose();
    due.dispose();
  }

  void maskRows() {
    for (final row in rows) {
      row['cnpj'] = maskCnpj(row['cnpj']?.toString() ?? '');
      row['total'] = rowTotal(row);
    }
    final removed =
        controllers.keys.where((row) => !rows.contains(row)).toList();
    for (final row in removed) {
      controllers.remove(row)?.dispose();
    }
  }

  Widget competence(String label, TextEditingController controller) => SizedBox(
        width: 180,
        child: TextField(
            controller: controller,
            readOnly: true,
            enabled: !running,
            onTap: running
                ? null
                : () async {
                    final selected =
                        await pickCompetence(context, controller.text);
                    if (selected != null && mounted) {
                      setState(() => controller.text = selected);
                      changed();
                    }
                  },
            decoration: InputDecoration(
                labelText: label,
                suffixIcon: const Icon(Icons.calendar_month))),
      );

  Widget field(
    String label,
    TextEditingController controller, {
    double width = 180,
    bool enabled = true,
  }) =>
      SizedBox(
        width: width,
        child: TextField(
          controller: controller,
          enabled: enabled,
          inputFormatters: controller == cnpj ? [CnpjFormatter()] : null,
          keyboardType: controller == cnpj ? TextInputType.number : null,
          onChanged: (_) => changed(),
          decoration: InputDecoration(labelText: label),
        ),
      );
  String currency(dynamic value) {
    final n = (value as num?) ?? 0;
    return 'R\$ ${(n / 100).toStringAsFixed(2).replaceAll('.', ',')}';
  }

  Widget discrepancy() {
    final expected = attention?['expected'],
        found = attention?['found'],
        diff = attention?['difference'];
    if (expected == null) return const SizedBox.shrink();
    return DataTable(
      columnSpacing: 18,
      columns: const [
        DataColumn(label: Text('Valor')),
        DataColumn(label: Text('Informado')),
        DataColumn(label: Text('Encontrado')),
        DataColumn(label: Text('Diferença')),
      ],
      rows: [
        for (final key in (expected as Map).keys)
          DataRow(
            cells: [
              DataCell(Text({
                    'fgts': 'FGTS',
                    'consignado': 'Consignado',
                    'total': 'Total',
                    'due': 'Vencimento',
                  }[key] ??
                  key.toString())),
              DataCell(Text(expected[key] is num
                  ? currency(expected[key])
                  : expected[key].toString())),
              DataCell(Text(found[key] is num
                  ? currency(found[key])
                  : found[key].toString())),
              DataCell(Text(diff?[key] is num ? currency(diff[key]) : '—')),
            ],
          ),
      ],
    );
  }

  Widget table() => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text(
                'Empresas do lote',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
              ),
              const Spacer(),
              Text(
                '${rows.where((r) => r['selected'] != false).length} selecionadas',
              ),
            ],
          ),
          const SizedBox(height: 14),
          Expanded(
            child: rows.isEmpty
                ? Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.table_chart_outlined,
                          size: 44,
                          color: ink,
                        ),
                        const SizedBox(height: 14),
                        const Text(
                            'Importe uma planilha ou adicione uma empresa.'),
                        const SizedBox(height: 8),
                        TextButton(
                          onPressed: ready ? () => export(true) : null,
                          child: const Text('Baixar modelo de planilha'),
                        ),
                      ],
                    ),
                  )
                : Scrollbar(
                    controller: tableScroll,
                    notificationPredicate: (notification) =>
                        notification.metrics.axis == Axis.vertical,
                    child: Scrollbar(
                      controller: tableHorizontalScroll,
                      thumbVisibility: true,
                      scrollbarOrientation: ScrollbarOrientation.bottom,
                      notificationPredicate: (notification) =>
                          notification.metrics.axis == Axis.horizontal,
                      child: Padding(
                        padding: const EdgeInsets.only(bottom: 14, right: 12),
                        child: SingleChildScrollView(
                          controller: tableHorizontalScroll,
                          scrollDirection: Axis.horizontal,
                          child: SingleChildScrollView(
                            controller: tableScroll,
                            child: DataTable(
                              showCheckboxColumn: true,
                              columnSpacing: 22,
                              headingRowColor: WidgetStateProperty.all(
                                const Color(0xffe6ebe5),
                              ),
                              columns: [
                                for (final label in [
                                  'COD',
                                  'EMPRESA',
                                  'CNPJ',
                                  'FGTS MENSAL',
                                  'CONSIGNADO',
                                  'TOTAL',
                                  'OBSERVAÇÕES',
                                  'SITUAÇÃO',
                                  '',
                                ])
                                  DataColumn(
                                    label: Text(
                                      label,
                                      style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ),
                              ],
                              rows: [
                                for (final row in rows)
                                  DataRow(
                                    selected: row['selected'] != false,
                                    onSelectChanged: running
                                        ? null
                                        : (value) {
                                            setState(
                                                () => row['selected'] = value);
                                            changed();
                                          },
                                    cells: [
                                      for (final key in [
                                        'cod',
                                        'empresa',
                                        'cnpj',
                                        'fgts',
                                        'consignado',
                                        'total',
                                        'observacoes',
                                      ])
                                        DataCell(
                                          SizedBox(
                                            width: key == 'empresa'
                                                ? 220
                                                : key == 'observacoes'
                                                    ? 230
                                                    : key == 'cnpj'
                                                        ? 165
                                                        : 100,
                                            child: TextFormField(
                                              key: ValueKey(
                                                '${identityHashCode(row)}-$key',
                                              ),
                                              controller: controllers
                                                  .putIfAbsent(
                                                      row,
                                                      () => CompanyControllers(
                                                          row))
                                                  .fields[key],
                                              inputFormatters: key == 'cnpj'
                                                  ? [CnpjFormatter()]
                                                  : [
                                                      'fgts',
                                                      'consignado',
                                                      'total'
                                                    ].contains(key)
                                                      ? [MoneyFormatter()]
                                                      : null,
                                              keyboardType: [
                                                'fgts',
                                                'consignado',
                                                'total'
                                              ].contains(key)
                                                  ? const TextInputType
                                                      .numberWithOptions(
                                                      decimal: true)
                                                  : key == 'cnpj'
                                                      ? TextInputType.number
                                                      : TextInputType.text,
                                              enabled: !running ||
                                                  (paused &&
                                                      [
                                                        'fgts',
                                                        'consignado',
                                                        'total',
                                                        'observacoes'
                                                      ].contains(key)),
                                              readOnly: key == 'total',
                                              decoration: InputDecoration(
                                                border: InputBorder.none,
                                                hintText: [
                                                  'fgts',
                                                  'consignado',
                                                  'total'
                                                ].contains(key)
                                                    ? '0,00'
                                                    : null,
                                                filled: key == 'total',
                                                fillColor:
                                                    const Color(0xffdce3dc),
                                              ),
                                              onChanged: (value) {
                                                row[key] = value;
                                                if (key == 'fgts' ||
                                                    key == 'consignado') {
                                                  row['total'] = rowTotal(row);
                                                  controllers[row]
                                                          ?.fields['total']
                                                          ?.text =
                                                      companyFieldText(
                                                          row, 'total');
                                                }
                                                changed();
                                              },
                                            ),
                                          ),
                                        ),
                                      DataCell(
                                        Text(
                                          {
                                                'saved': 'Salvo',
                                                'reused': 'Já salva',
                                                'attention': 'Atenção',
                                                'progress': 'Em andamento',
                                                'skipped': 'Ignorada',
                                                'finished': 'Interrompida',
                                              }[states[row['cnpj']
                                                  .toString()
                                                  .replaceAll(
                                                      RegExp(r'\D'), '')]] ??
                                              'Preparada',
                                        ),
                                      ),
                                      DataCell(
                                        IconButton(
                                          tooltip: 'Remover empresa',
                                          icon:
                                              const Icon(Icons.close, size: 18),
                                          onPressed: running
                                              ? null
                                              : () {
                                                  setState(
                                                      () => rows.remove(row));
                                                  maskRows();
                                                  changed();
                                                },
                                        ),
                                      ),
                                    ],
                                  ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
          ),
        ],
      );
  @override
  Widget build(BuildContext context) => Scaffold(
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.description_outlined,
                        color: ink, size: 34),
                    const SizedBox(width: 12),
                    const Text(
                      'FGTS Guias',
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w700,
                        color: ink,
                      ),
                    ),
                    const Spacer(),
                    Chip(
                      label: Text(
                        chrome.isEmpty
                            ? 'Instale o Google Chrome'
                            : 'Google Chrome instalado',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    field(
                      'Titular do certificado',
                      office,
                      width: 230,
                      enabled: !running,
                    ),
                    field(
                      'CNPJ do titular',
                      cnpj,
                      width: 200,
                      enabled: !running,
                    ),
                    competence('Inicial · MM/AAAA', initial),
                    competence('Final · MM/AAAA', finalPeriod),
                    SizedBox(
                      width: 340,
                      child: TextField(
                        controller: output,
                        readOnly: true,
                        decoration: InputDecoration(
                          labelText: 'Pasta para salvar as guias',
                          suffixIcon: IconButton(
                            tooltip: 'Escolher pasta',
                            icon: const Icon(Icons.folder_open),
                            onPressed: running
                                ? null
                                : () async {
                                    final path = await FilePicker.platform
                                        .getDirectoryPath();
                                    if (path != null) {
                                      setState(() => output.text = path);
                                      changed();
                                    }
                                  },
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Wrap(spacing: 12, runSpacing: 12, children: [
                  OutlinedButton.icon(
                      onPressed: ready
                          ? () => act('open_browser', {'settings': settings})
                          : null,
                      icon: const Icon(Icons.open_in_browser),
                      label: const Text('Abrir Chrome')),
                ]),
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  controlAffinity: ListTileControlAffinity.leading,
                  title: const Text('Baixar novamente guias já salvas'),
                  value: downloadSaved,
                  onChanged: ready && !running
                      ? (value) {
                          setState(() => downloadSaved = value ?? false);
                          changed();
                        }
                      : null,
                ),
                const SizedBox(height: 20),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    OutlinedButton.icon(
                      onPressed: ready && !running ? importRows : null,
                      icon: const Icon(Icons.upload_file),
                      label: const Text('Importar CSV / Excel'),
                    ),
                    OutlinedButton.icon(
                      onPressed: ready && !running
                          ? () {
                              setState(
                                () => rows.add({
                                  'cod': '',
                                  'empresa': '',
                                  'cnpj': '',
                                  'fgts': '',
                                  'consignado': '',
                                  'total': '',
                                  'observacoes': '',
                                  'selected': true,
                                }),
                              );
                              changed();
                            }
                          : null,
                      icon: const Icon(Icons.add),
                      label: const Text('Adicionar empresa'),
                    ),
                    TextButton(
                      onPressed: ready ? () => export(true) : null,
                      child: const Text('Baixar modelo'),
                    ),
                    TextButton(
                      onPressed: ready ? () => export(false) : null,
                      child: const Text('Exportar planilha'),
                    ),
                    OutlinedButton.icon(
                      onPressed: ready && !running && rows.isNotEmpty
                          ? removeAllCompanies
                          : null,
                      icon: const Icon(Icons.delete_sweep_outlined),
                      label: const Text('Remover todas'),
                    ),
                    FilledButton.icon(
                      onPressed:
                          ready && !running && chrome.isNotEmpty ? start : null,
                      icon: const Icon(Icons.play_arrow),
                      label: const Text('Emitir selecionadas'),
                    ),
                    OutlinedButton.icon(
                      onPressed: ready &&
                              !running &&
                              chrome.isNotEmpty &&
                              rows.any((row) => row['selected'] != false)
                          ? restartEmission
                          : null,
                      icon: const Icon(Icons.restart_alt),
                      label: const Text('Reiniciar emissão'),
                    ),
                    if (running)
                      OutlinedButton(
                        onPressed: () => act('pause'),
                        child: const Text('Pausar'),
                      ),
                    if (running)
                      TextButton(
                        onPressed: () => act('stop'),
                        child: const Text('Encerrar lote'),
                      ),
                  ],
                ),
                const SizedBox(height: 20),
                Expanded(
                  child: LayoutBuilder(
                    builder: (context, size) {
                      final panel = Material(
                          color: paused
                              ? const Color(0xffffedcf)
                              : const Color(0xffe8eee7),
                          child: SizedBox(
                              width: size.maxWidth > 1050 ? 340 : null,
                              child: Padding(
                                padding: const EdgeInsets.all(20),
                                child: SingleChildScrollView(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        paused
                                            ? 'Sua atenção é necessária'
                                            : 'Acompanhamento',
                                        style: const TextStyle(
                                          fontSize: 20,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      const SizedBox(height: 16),
                                      SelectableText(status),
                                      if (attention?['company'] != null)
                                        Padding(
                                          padding:
                                              const EdgeInsets.only(top: 12),
                                          child: Text(
                                              'CNPJ: ${maskCnpj(attention!['company'].toString())}'),
                                        ),
                                      if (attention?['guide'] != null)
                                        Text('Guia: ${attention!['guide']}'),
                                      if (attention?['expected'] != null)
                                        SingleChildScrollView(
                                          scrollDirection: Axis.horizontal,
                                          child: discrepancy(),
                                        ),
                                      if (paused && running) ...[
                                        const SizedBox(height: 20),
                                        Wrap(
                                          spacing: 8,
                                          runSpacing: 8,
                                          children: [
                                            if (attention?['decision_id'] ==
                                                null)
                                              FilledButton(
                                                onPressed: () => act('resume'),
                                                child: const Text('Retomar'),
                                              ),
                                            if (attention?['decision_id'] !=
                                                null)
                                              FilledButton.icon(
                                                style: FilledButton.styleFrom(
                                                  backgroundColor:
                                                      const Color(0xff8a4b08),
                                                  foregroundColor: Colors.white,
                                                ),
                                                icon: const Icon(
                                                    Icons.fact_check_outlined),
                                                onPressed: () =>
                                                    act('accept_difference', {
                                                  'decision_id':
                                                      attention!['decision_id'],
                                                }),
                                                label: const Text(
                                                    'Aceitar divergência'),
                                              ),
                                            if (attention?['decision_id'] !=
                                                null)
                                              OutlinedButton.icon(
                                                icon: const Icon(Icons.close),
                                                onPressed: () =>
                                                    act('reject_difference', {
                                                  'decision_id':
                                                      attention!['decision_id'],
                                                }),
                                                label: const Text(
                                                    'Negar divergência'),
                                              ),
                                            if (attention?['decision_id'] ==
                                                null)
                                              OutlinedButton(
                                                onPressed: () => act('skip'),
                                                child: const Text(
                                                    'Ignorar empresa'),
                                              ),
                                            if (attention?['decision_id'] ==
                                                null)
                                              OutlinedButton(
                                                onPressed: recovery,
                                                child:
                                                    const Text('Recuperar PDF'),
                                              ),
                                          ],
                                        ),
                                      ],
                                      const Divider(height: 32),
                                      ExpansionTile(
                                        tilePadding: EdgeInsets.zero,
                                        title: const Text('Atividades do lote'),
                                        children: [
                                          for (final entry
                                              in log.reversed.take(20))
                                            Padding(
                                              padding:
                                                  const EdgeInsets.symmetric(
                                                vertical: 6,
                                              ),
                                              child: SelectableText(entry),
                                            ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              )));
                      if (size.maxWidth > 1050) {
                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Expanded(child: table()),
                            const SizedBox(width: 24),
                            panel,
                          ],
                        );
                      }
                      return Column(
                        children: [
                          Expanded(child: table()),
                          const SizedBox(height: 14),
                          SizedBox(height: 210, child: panel),
                        ],
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ),
      );
  @override
  void dispose() {
    tableScroll.dispose();
    tableHorizontalScroll.dispose();
    saver?.cancel();
    subscription?.cancel();
    engine.close();
    for (final row in controllers.values) {
      row.dispose();
    }
    for (final c in [office, cnpj, initial, finalPeriod, output]) {
      c.dispose();
    }
    super.dispose();
  }
}
