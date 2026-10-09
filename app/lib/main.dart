import 'dart:async';

import 'package:flutter/material.dart';
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
  final office = TextEditingController(),
      cnpj = TextEditingController(),
      initial = TextEditingController(),
      finalPeriod = TextEditingController(),
      output = TextEditingController();
  List<Map<String, dynamic>> rows = [];
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
      cnpj.text = config['officeCnpj'] ?? '';
      initial.text = config['initial'] ?? '';
      finalPeriod.text = config['final'] ?? '';
      output.text = config['output'] ?? '';
      rows = (workspace['rows'] as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
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
    if (path != null)
      await act(template ? 'template' : 'export', {'path': path, 'rows': rows});
  }

  Future<void> start() async {
    try {
      await persist();
      await engine.call('start', {'settings': settings, 'rows': rows});
      setState(() {
        running = true;
        paused = false;
        attention = null;
      });
    } catch (e) {
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
    if (picked != null)
      await act('recover', {
        'row': matches.first,
        'settings': settings,
        'path': picked.files.single.path,
        'guide': number.text,
        'due': due.text,
      });
    number.dispose();
    due.dispose();
  }

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
        for (final entry in {
          'fgts': 'FGTS',
          'consignado': 'Consignado',
          'total': 'Total',
        }.entries)
          DataRow(
            cells: [
              DataCell(Text(entry.value)),
              DataCell(Text(currency(expected[entry.key]))),
              DataCell(Text(currency(found[entry.key]))),
              DataCell(Text(currency(diff[entry.key]))),
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
                    child: SingleChildScrollView(
                      child: SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
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
                                        setState(() => row['selected'] = value);
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
                                          initialValue:
                                              row[key]?.toString() ?? '',
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
                                      icon: const Icon(Icons.close, size: 18),
                                      onPressed: running
                                          ? null
                                          : () {
                                              setState(() => rows.remove(row));
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
                    field(
                      'Inicial · MM/AAAA',
                      initial,
                      width: 160,
                      enabled: !running,
                    ),
                    field(
                      'Final · MM/AAAA',
                      finalPeriod,
                      width: 160,
                      enabled: !running,
                    ),
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
                      final panel = Container(
                        width: size.maxWidth > 1050 ? 340 : null,
                        padding: const EdgeInsets.all(20),
                        color: paused
                            ? const Color(0xffffedcf)
                            : const Color(0xffe8eee7),
                        child: SingleChildScrollView(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
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
                                  padding: const EdgeInsets.only(top: 12),
                                  child: Text('CNPJ: ${attention!['company']}'),
                                ),
                              if (attention?['expected'] != null)
                                SingleChildScrollView(
                                  scrollDirection: Axis.horizontal,
                                  child: discrepancy(),
                                ),
                              if (paused && running) ...[
                                const SizedBox(height: 20),
                                const Text(
                                  'Corrija os dados ou resolva a etapa no Chrome. Retomar confere os valores novamente.',
                                ),
                                const SizedBox(height: 12),
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 8,
                                  children: [
                                    FilledButton(
                                      onPressed: () => act('resume'),
                                      child: const Text('Retomar'),
                                    ),
                                    OutlinedButton(
                                      onPressed: () => act('skip'),
                                      child: const Text('Ignorar empresa'),
                                    ),
                                    OutlinedButton(
                                      onPressed: recovery,
                                      child: const Text('Recuperar PDF'),
                                    ),
                                  ],
                                ),
                              ],
                              const Divider(height: 32),
                              const Text(
                                'Certificado e CAPTCHA',
                                style: TextStyle(fontWeight: FontWeight.w600),
                              ),
                              const SizedBox(height: 8),
                              const Text(
                                'Selecione o certificado, informe o PIN e resolva CAPTCHA diretamente no Chrome. A localização não é autorizada.',
                              ),
                              TextButton(
                                onPressed: ready && (!running || paused)
                                    ? () => act('close_browser')
                                    : null,
                                child: const Text(
                                  'Fechar Chrome para trocar certificado',
                                ),
                              ),
                              const Divider(height: 24),
                              ExpansionTile(
                                tilePadding: EdgeInsets.zero,
                                title: const Text('Histórico desta sessão'),
                                children: [
                                  for (final entry in log.reversed.take(20))
                                    Padding(
                                      padding: const EdgeInsets.symmetric(
                                        vertical: 6,
                                      ),
                                      child: SelectableText(entry),
                                    ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      );
                      if (size.maxWidth > 1050)
                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Expanded(child: table()),
                            const SizedBox(width: 24),
                            panel,
                          ],
                        );
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
    saver?.cancel();
    subscription?.cancel();
    engine.close();
    for (final c in [office, cnpj, initial, finalPeriod, output]) {
      c.dispose();
    }
    super.dispose();
  }
}
