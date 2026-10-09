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
  String status = 'Conectando ao motor local…', chrome = '';
  StreamSubscription<Map<String, dynamic>>? subscription;
  Timer? saver;
  Map<String, dynamic> get settings => {
        'officeName': office.text,
        'officeCnpj': cnpj.text,
        'initial': initial.text,
        'final': finalPeriod.text,
        'output': output.text,
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
          log.add(event['message'].toString());
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
          status = 'PDF conferido e salvo: ${event['path']}';
        }
        if (event['event'] == 'finished') {
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
      rows = (workspace['rows'] as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
      maskRows();
      setState(() {
        ready = true;
        chrome = data['chrome']?.toString() ?? '';
        status = chrome.isEmpty
            ? 'Instale o Google Chrome para emitir.'
            : 'Pronto para preparar o lote.';
      });
    } catch (e) {
      setState(() => status = 'Não foi possível iniciar: $e');
    }
  }

  Future<void> persist() async {
    await engine.call('save', {'settings': settings, 'rows': rows});
  }

  void changed() {
    saver?.cancel();
    saver = Timer(const Duration(milliseconds: 500), () {
      persist().catchError((e) {
        showError(e);
      });
    });
  }

  void showError(Object e) {
    if (mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.toString())));
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
      dialogTitle: template ? 'Salvar template' : 'Exportar empresas',
      fileName: template ? 'template-fgts.xlsx' : 'empresas.xlsx',
      type: FileType.custom,
      allowedExtensions: ['xlsx', 'csv'],
    );
    if (path != null) {
      await act(template ? 'template' : 'export', {'path': path, 'rows': rows});
    }
  }

  Future<void> start() async {
    try {
      await persist();
      setState(() {
        running = true;
        paused = false;
        attention = null;
      });
      await engine.call('start', {'settings': settings, 'rows': rows});
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
      showError('Selecione a empresa pausada antes de recuperar.');
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
                'Baixe a guia existente pelo Chrome. Informe os dados para conferir o PDF antes de salvá-lo na pasta escolhida.',
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
        'row': matches.first,
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
        DataColumn(label: Text('Esperado')),
        DataColumn(label: Text('Portal')),
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
                          child: const Text('Baixar template'),
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
                                              decoration: const InputDecoration(
                                                border: InputBorder.none,
                                              ),
                                              onChanged: (value) {
                                                row[key] = value;
                                                changed();
                                              },
                                            ),
                                          ),
                                        ),
                                      DataCell(
                                        Text(
                                          {
                                                'saved': 'Salvo',
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
                    const SizedBox(width: 20),
                    const Text(
                      'Emissão assistida',
                      style: TextStyle(color: Colors.black54),
                    ),
                    const Spacer(),
                    Chip(
                      label: Text(
                        chrome.isEmpty
                            ? 'Chrome necessário'
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
                      'Escritório / titular',
                      office,
                      width: 230,
                      enabled: !running,
                    ),
                    field(
                      'CNPJ do escritório',
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
                          labelText: 'Pasta dos PDFs',
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
                                  'fgts': '0,00',
                                  'consignado': '0,00',
                                  'total': '0,00',
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
                      child: const Text('Template'),
                    ),
                    TextButton(
                      onPressed: ready ? () => export(false) : null,
                      child: const Text('Exportar'),
                    ),
                    FilledButton.icon(
                      onPressed:
                          ready && !running && chrome.isNotEmpty ? start : null,
                      icon: const Icon(Icons.play_arrow),
                      label: const Text('Emitir selecionadas'),
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
                                      if (attention?['decision_id'] != null)
                                        const Padding(
                                          padding: EdgeInsets.only(top: 12),
                                          child: Text(
                                              'Aceitar libera somente esta conferência, uma vez. Outras divergências continuam bloqueando; a planilha não é alterada.'),
                                        ),
                                      if (attention?['expected'] != null)
                                        SingleChildScrollView(
                                          scrollDirection: Axis.horizontal,
                                          child: discrepancy(),
                                        ),
                                      if (paused && running) ...[
                                        const SizedBox(height: 20),
                                        Text(
                                          attention?['decision_id'] != null
                                              ? 'Aceite esta divergência ou negue para revisar antes de continuar.'
                                              : 'Corrija os dados ou resolva a etapa no Chrome. Retomar confere os valores novamente.',
                                        ),
                                        const SizedBox(height: 12),
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
                                      const Text(
                                        'Certificado e CAPTCHA',
                                        style: TextStyle(
                                            fontWeight: FontWeight.w600),
                                      ),
                                      const SizedBox(height: 8),
                                      const Text(
                                        'O Chrome fica minimizado durante o lote e aparece quando precisa de você. Conclua certificado, PIN ou CAPTCHA no Chrome; a autenticação concluída retoma automaticamente. Para outras pendências, use Retomar. Abrir Chrome permite acompanhar a página.',
                                      ),
                                      TextButton(
                                        onPressed: ready && (!running || paused)
                                            ? () => act('close_browser')
                                            : null,
                                        child: const Text(
                                            'Fechar Chrome para trocar certificado'),
                                      ),
                                      const Divider(height: 24),
                                      ExpansionTile(
                                        tilePadding: EdgeInsets.zero,
                                        title: const Text(
                                            'Histórico desta sessão'),
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
                const SizedBox(height: 12),
                const Text(
                  'Dados locais · Nenhum pagamento é realizado · Salvo significa PDF conferido na pasta escolhida',
                  style: TextStyle(fontSize: 12, color: Colors.black54),
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
