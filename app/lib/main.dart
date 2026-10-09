import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/rendering.dart' show ScrollCacheExtent;
import 'package:flutter_localizations/flutter_localizations.dart';
import 'inputs.dart';
import 'package:file_picker/file_picker.dart';

import 'engine.dart';

void main() => runApp(const GuideApp());
const ink = Color(0xff193b35);
const paper = Color(0xfff5f4ef);

class GuideApp extends StatelessWidget {
  final EngineClient? engine;
  const GuideApp({super.key, this.engine});
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
        home: Workspace(engine: engine),
      );
}

class Workspace extends StatefulWidget {
  final EngineClient? engine;
  const Workspace({super.key, this.engine});
  @override
  State<Workspace> createState() => _WorkspaceState();
}

class _WorkspaceState extends State<Workspace> {
  late final EngineClient engine;
  final scaffoldKey = GlobalKey<ScaffoldState>();
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
  String? activeCompany;
  String? get activeCompanyLabel {
    if (activeCompany == null) return null;
    for (final row in rows) {
      if (row['cnpj'].toString().replaceAll(RegExp(r'\D'), '') ==
          activeCompany) {
        final code = row['cod']?.toString().trim() ?? '';
        final name = row['empresa']?.toString().trim() ?? '';
        return name.isEmpty
            ? maskCnpj(activeCompany!)
            : code.isEmpty
                ? name
                : '$code — $name';
      }
    }
    return maskCnpj(activeCompany!);
  }

  StreamSubscription<Map<String, dynamic>>? subscription;
  Timer? saver;
  Map<String, dynamic> get settings => {
        'officeName': office.text,
        'officeCnpj': cnpj.text,
        'initial': initial.text,
        'final': finalPeriod.text,
        'output': output.text,
        'downloadSaved': downloadSaved,
        'columnWidths': gridWidths,
      };
  @override
  void initState() {
    super.initState();
    engine = widget.engine ?? EngineClient();
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
          activeCompany = event['company'].toString();
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
            final results = [
              if (saved > 0)
                '$saved ${saved == 1 ? 'guia salva' : 'guias salvas'}',
              if (reused > 0)
                '$reused ${reused == 1 ? 'guia reutilizada' : 'guias reutilizadas'}',
              if (skipped > 0)
                '$skipped ${skipped == 1 ? 'empresa ignorada' : 'empresas ignoradas'}',
            ];
            final summary = results.length < 2
                ? results.join()
                : '${results.take(results.length - 1).join(', ')} e ${results.last}';
            status = summary.isEmpty
                ? 'Lote concluído.'
                : 'Lote concluído. $summary.';
          }
          running = false;
          paused = false;
          attention = null;
          activeCompany = null;
        }
        final companyLabel = activeCompanyLabel;
        log.add(companyLabel == null ? status : '$companyLabel · $status');
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
      final savedWidths = config['columnWidths'];
      if (savedWidths is List && savedWidths.length == gridWidths.length) {
        for (var index = 0; index < gridWidths.length; index++) {
          final width = savedWidths[index];
          if (width is num && width.isFinite) {
            gridWidths[index] =
                width.toDouble().clamp(minGridWidths[index], 1200);
          }
        }
      }
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

  Future<void> start() => startBatch();

  Future<void> startBatch() async {
    try {
      await persist();
      setState(() {
        states.clear();
        log.clear();
        status = 'Iniciando o lote…';
        activeCompany = null;
        running = true;
        paused = false;
        attention = null;
      });
      await engine.call('start', {
        'settings': settings,
        'rows': rows.map(companyPayload).toList(),
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

  void addCompany() {
    setState(() => rows.add({
          'cod': '',
          'empresa': '',
          'cnpj': '',
          'fgts': '',
          'consignado': '',
          'total': '',
          'observacoes': '',
          'selected': true,
        }));
    changed();
  }

  void openConfiguration() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) scaffoldKey.currentState?.openEndDrawer();
    });
    WidgetsBinding.instance.ensureVisualUpdate();
  }

  void closeConfiguration() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) scaffoldKey.currentState?.closeEndDrawer();
    });
    WidgetsBinding.instance.ensureVisualUpdate();
  }

  Widget settingsCard() => Material(
        color: Colors.white,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
            side: const BorderSide(color: Color(0xffdce3dc))),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: openConfiguration,
          child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Row(children: [
                const Icon(Icons.tune, size: 20),
                const SizedBox(width: 12),
                const Text('Configuração do lote',
                    style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(width: 20),
                Expanded(
                    child: Text(
                        initial.text.isEmpty
                            ? ''
                            : '${office.text} · ${initial.text} a ${finalPeriod.text}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.right,
                        style: const TextStyle(color: Colors.black54))),
                const SizedBox(width: 12),
                const Icon(Icons.chevron_right),
              ])),
        ),
      );

  Widget settingsDrawer() => Drawer(
        width: 440,
        child: SafeArea(
            child: SingleChildScrollView(
                child: Padding(
          padding: const EdgeInsets.all(24),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Expanded(
                  child: Text('Configuração do lote',
                      style: TextStyle(
                          fontSize: 20, fontWeight: FontWeight.w600))),
              IconButton(
                  tooltip: 'Fechar configuração',
                  onPressed: closeConfiguration,
                  icon: const Icon(Icons.close))
            ]),
            const SizedBox(height: 24),
            field('Titular do certificado', office,
                width: double.infinity, enabled: !running),
            const SizedBox(height: 16),
            field('CNPJ do titular', cnpj,
                width: double.infinity, enabled: !running),
            const SizedBox(height: 16),
            Row(children: [
              Expanded(child: competence('Período inicial', initial)),
              const SizedBox(width: 12),
              Expanded(child: competence('Período final', finalPeriod))
            ]),
            const SizedBox(height: 16),
            TextField(
              controller: output,
              readOnly: true,
              decoration: InputDecoration(
                  labelText: 'Pasta das guias',
                  suffixIcon: IconButton(
                    tooltip: 'Escolher pasta',
                    icon: const Icon(Icons.folder_open),
                    onPressed: running
                        ? null
                        : () async {
                            final path =
                                await FilePicker.platform.getDirectoryPath();
                            if (path != null) {
                              setState(() => output.text = path);
                              changed();
                            }
                          },
                  )),
            ),
          ]),
        ))),
      );

  Widget emissionActions() => Wrap(
        spacing: 8,
        runSpacing: 8,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          if (!running) ...[
            FilledButton.icon(
              onPressed: ready &&
                      chrome.isNotEmpty &&
                      rows.any((r) => r['selected'] != false)
                  ? start
                  : null,
              icon: const Icon(Icons.download_outlined),
              label: const Text('Baixar selecionadas'),
            ),
            PopupMenuButton<String>(
              enabled: ready,
              tooltip: 'Otimização do download',
              constraints: const BoxConstraints(minWidth: 320, maxWidth: 360),
              onSelected: (value) {
                setState(() => downloadSaved = value == 'new');
                changed();
              },
              itemBuilder: (_) => [
                for (final option in ['same', 'new'])
                  PopupMenuItem(
                      value: option,
                      height: 76,
                      key: ValueKey('download-$option-option'),
                      child: Row(children: [
                        Icon(
                            downloadSaved == (option == 'new')
                                ? Icons.radio_button_checked
                                : Icons.radio_button_unchecked,
                            size: 20),
                        const SizedBox(width: 12),
                        Expanded(
                            child: Column(
                                mainAxisSize: MainAxisSize.min,
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                              Text(
                                  option == 'same'
                                      ? 'Baixar mesma guia'
                                      : 'Baixar nova guia',
                                  style: const TextStyle(
                                      fontWeight: FontWeight.w600)),
                              const SizedBox(height: 4),
                              Text(
                                  option == 'same'
                                      ? 'Reutiliza o PDF salvo, se disponível.'
                                      : 'Faz novo download, mesmo com PDF salvo.',
                                  style: const TextStyle(
                                      fontSize: 12, color: Colors.black54)),
                            ])),
                      ])),
              ],
              child: Container(
                height: 44,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                decoration: BoxDecoration(
                    border: Border.all(color: const Color(0xffb9c8bd)),
                    borderRadius: BorderRadius.circular(10)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text(
                      downloadSaved ? 'Baixar nova guia' : 'Baixar mesma guia'),
                  const SizedBox(width: 8),
                  const Icon(Icons.expand_more, size: 18),
                ]),
              ),
            ),
          ] else ...[
            if (!paused)
              OutlinedButton.icon(
                  onPressed: () => act('pause'),
                  icon: const Icon(Icons.pause),
                  label: const Text('Pausar')),
            TextButton(
                onPressed: () => act('stop'),
                child: const Text('Encerrar lote')),
          ],
        ],
      );

  Widget companyToolbar() => Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
        child: LayoutBuilder(builder: (context, size) {
          final companies = Wrap(
              spacing: 4,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                TextButton.icon(
                    onPressed: ready && !running ? importRows : null,
                    icon: const Icon(Icons.upload_file_outlined, size: 18),
                    label: const Text('Importar')),
                TextButton.icon(
                    onPressed: ready && !running ? addCompany : null,
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('Adicionar')),
                PopupMenuButton<String>(
                  tooltip: 'Opções da planilha',
                  enabled: ready,
                  onSelected: (value) {
                    if (value == 'template') export(true);
                    if (value == 'export') export(false);
                    if (value == 'remove') removeAllCompanies();
                  },
                  itemBuilder: (_) => [
                    const PopupMenuItem(
                        value: 'template', child: Text('Baixar modelo')),
                    const PopupMenuItem(
                        value: 'export', child: Text('Exportar planilha')),
                    const PopupMenuDivider(),
                    PopupMenuItem(
                        value: 'remove',
                        enabled: !running && rows.isNotEmpty,
                        child: const Text('Remover todas',
                            style: TextStyle(color: Color(0xff9a3427)))),
                  ],
                  child: const Padding(
                      padding:
                          EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                      child: Row(mainAxisSize: MainAxisSize.min, children: [
                        Text('Planilha'),
                        SizedBox(width: 4),
                        Icon(Icons.expand_more, size: 18)
                      ])),
                ),
              ]);
          if (size.maxWidth >= 940) {
            return Row(children: [
              Expanded(child: companies),
              const SizedBox(width: 12),
              emissionActions()
            ]);
          }
          return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                companies,
                const SizedBox(height: 8),
                emissionActions()
              ]);
        }),
      );

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
          const SizedBox(height: 8),
          companyToolbar(),
          const Divider(height: 1),
          Expanded(
            child: rows.isEmpty
                ? Center(
                    child: SingleChildScrollView(
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
                  ))
                : companyGrid(),
          ),
        ],
      );

  static const gridKeys = [
    'cod',
    'empresa',
    'cnpj',
    'fgts',
    'consignado',
    'total',
    'observacoes',
    'status',
    'remove'
  ];
  static const gridLabels = [
    'COD',
    'EMPRESA',
    'CNPJ',
    'FGTS MENSAL',
    'CONSIGNADO',
    'TOTAL',
    'OBSERVAÇÕES',
    'SITUAÇÃO',
    ''
  ];
  final gridWidths = List<double>.from(defaultGridWidths);
  static const minGridWidths = [
    64.0,
    120.0,
    145.0,
    104.0,
    104.0,
    90.0,
    140.0,
    100.0,
    44.0
  ];
  static const defaultGridWidths = [
    90.0,
    220.0,
    165.0,
    120.0,
    120.0,
    120.0,
    230.0,
    140.0,
    44.0
  ];

  Widget companyInput(Map<String, dynamic> row, String key) => TextFormField(
        key: ValueKey('${identityHashCode(row)}-$key'),
        controller: controllers
            .putIfAbsent(row, () => CompanyControllers(row))
            .fields[key],
        inputFormatters: key == 'cnpj'
            ? [CnpjFormatter()]
            : ['fgts', 'consignado'].contains(key)
                ? [MoneyFormatter()]
                : null,
        keyboardType: ['fgts', 'consignado', 'total'].contains(key)
            ? const TextInputType.numberWithOptions(decimal: true)
            : key == 'cnpj'
                ? TextInputType.number
                : TextInputType.text,
        textAlign: ['fgts', 'consignado', 'total'].contains(key)
            ? TextAlign.right
            : TextAlign.left,
        enabled: !running ||
            (paused &&
                ['fgts', 'consignado', 'total', 'observacoes'].contains(key)),
        readOnly: key == 'total',
        decoration: InputDecoration(
            border: InputBorder.none,
            hintText:
                ['fgts', 'consignado', 'total'].contains(key) ? '0,00' : null),
        onChanged: (value) {
          row[key] = value;
          if (key == 'fgts' || key == 'consignado') {
            row['total'] = rowTotal(row);
            controllers[row]?.fields['total']?.text =
                companyFieldText(row, 'total');
          }
          changed();
        },
      );

  void resizeColumn(int index, double delta, {bool save = false}) {
    setState(() => gridWidths[index] =
        (gridWidths[index] + delta).clamp(minGridWidths[index], 1200));
    if (save) changed();
  }

  Widget columnHeader(int index) => Stack(children: [
        Positioned.fill(
            child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(gridLabels[index],
                        style: const TextStyle(
                            fontWeight: FontWeight.w600, fontSize: 12))))),
        if (gridKeys[index] != 'remove')
          Positioned(
            right: 0,
            top: 0,
            bottom: 0,
            width: 12,
            child: Semantics(
              label: 'Ajustar largura: ${gridLabels[index]}',
              value: '${gridWidths[index].round()} pixels',
              increasedValue:
                  '${(gridWidths[index] + 20).clamp(minGridWidths[index], 1200).round()} pixels',
              decreasedValue:
                  '${(gridWidths[index] - 20).clamp(minGridWidths[index], 1200).round()} pixels',
              onIncrease: () => resizeColumn(index, 20, save: true),
              onDecrease: () => resizeColumn(index, -20, save: true),
              child: Focus(
                  onKeyEvent: (_, event) {
                    if (event is KeyDownEvent &&
                        (event.logicalKey == LogicalKeyboardKey.arrowLeft ||
                            event.logicalKey ==
                                LogicalKeyboardKey.arrowRight)) {
                      resizeColumn(
                          index,
                          event.logicalKey == LogicalKeyboardKey.arrowRight
                              ? 10
                              : -10,
                          save: true);
                      return KeyEventResult.handled;
                    }
                    return KeyEventResult.ignored;
                  },
                  child: Tooltip(
                    message: 'Arraste para ajustar a largura',
                    child: MouseRegion(
                      cursor: SystemMouseCursors.resizeLeftRight,
                      child: GestureDetector(
                        key: ValueKey('resize-column-${gridKeys[index]}'),
                        behavior: HitTestBehavior.opaque,
                        onHorizontalDragUpdate: (details) =>
                            resizeColumn(index, details.delta.dx),
                        onHorizontalDragEnd: (_) => changed(),
                        onHorizontalDragCancel: changed,
                        onDoubleTap: () {
                          setState(() =>
                              gridWidths[index] = defaultGridWidths[index]);
                          changed();
                        },
                        child: Center(
                            child: Container(
                                width: 2,
                                height: 22,
                                color: const Color(0xffb1beb3))),
                      ),
                    ),
                  )),
            ),
          ),
      ]);

  Widget gridRow(Map<String, dynamic>? row) {
    final header = row == null;
    return Container(
      height: 56,
      decoration: BoxDecoration(
          color: header
              ? const Color(0xffe6ebe5)
              : row['selected'] != false
                  ? const Color(0xfff0f4ef)
                  : Colors.white,
          border: const Border(bottom: BorderSide(color: Color(0xffe0e6df)))),
      child: Row(children: [
        SizedBox(
            width: 48,
            child: Checkbox(
              value: header
                  ? rows.every((r) => r['selected'] != false)
                  : row['selected'] != false,
              onChanged: running
                  ? null
                  : (value) {
                      setState(() {
                        if (header) {
                          for (final r in rows) {
                            r['selected'] = value;
                          }
                        } else {
                          row['selected'] = value;
                        }
                      });
                      changed();
                    },
            )),
        for (var index = 0; index < gridKeys.length; index++)
          Container(
            width: gridWidths[index],
            height: 56,
            padding: EdgeInsets.symmetric(
                horizontal: header || gridKeys[index] == 'remove' ? 0 : 12),
            alignment: Alignment.centerLeft,
            color: gridKeys[index] == 'total' ? const Color(0xffdce3dc) : null,
            child: header
                ? columnHeader(index)
                : gridKeys[index] == 'status'
                    ? Text({
                          'saved': 'Salvo',
                          'reused': 'Já salva',
                          'attention': 'Atenção',
                          'progress': 'Em andamento',
                          'skipped': 'Ignorada',
                          'finished': 'Interrompida'
                        }[states[row['cnpj']
                            .toString()
                            .replaceAll(RegExp(r'\D'), '')]] ??
                        'Preparada')
                    : gridKeys[index] == 'remove'
                        ? IconButton(
                            tooltip: 'Remover empresa',
                            icon: const Icon(Icons.close, size: 18),
                            onPressed: running
                                ? null
                                : () {
                                    setState(() => rows.remove(row));
                                    maskRows();
                                    changed();
                                  })
                        : companyInput(row, gridKeys[index]),
          ),
      ]),
    );
  }

  Widget companyGrid() => LayoutBuilder(builder: (context, constraints) {
        final width =
            48 + gridWidths.fold<double>(0, (sum, value) => sum + value);
        return Scrollbar(
          controller: tableHorizontalScroll,
          thumbVisibility: true,
          notificationPredicate: (notification) =>
              notification.metrics.axis == Axis.horizontal,
          child: Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: SingleChildScrollView(
                controller: tableHorizontalScroll,
                scrollDirection: Axis.horizontal,
                child: SizedBox(
                    width: width,
                    height: constraints.maxHeight - 12,
                    child: Column(children: [
                      gridRow(null),
                      Expanded(
                          child: Scrollbar(
                        controller: tableScroll,
                        notificationPredicate: (notification) =>
                            notification.metrics.axis == Axis.vertical,
                        child: ListView.builder(
                            controller: tableScroll,
                            itemExtent: 56,
                            scrollCacheExtent:
                                const ScrollCacheExtent.pixels(112),
                            itemCount: rows.length,
                            itemBuilder: (context, index) =>
                                gridRow(rows[index])),
                      )),
                    ])),
              )),
        );
      });
  @override
  Widget build(BuildContext context) => Scaffold(
        key: scaffoldKey,
        endDrawer: settingsDrawer(),
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(20),
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
                    OutlinedButton.icon(
                      onPressed: ready
                          ? () => act('open_browser', {'settings': settings})
                          : null,
                      icon: const Icon(Icons.open_in_browser, size: 18),
                      label: const Text('Abrir Chrome'),
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                settingsCard(),
                const SizedBox(height: 20),
                Expanded(
                  child: LayoutBuilder(
                    builder: (context, size) {
                      final workspace = Material(
                        color: Colors.white,
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                            side: const BorderSide(color: Color(0xffdce3dc))),
                        clipBehavior: Clip.antiAlias,
                        child: Padding(
                            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                            child: table()),
                      );
                      if (!running && !paused && log.isEmpty) return workspace;
                      final panel = Material(
                          borderRadius: BorderRadius.circular(14),
                          clipBehavior: Clip.antiAlias,
                          color: paused
                              ? const Color(0xffffedcf)
                              : const Color(0xffe8eee7),
                          child: SizedBox(
                              width: size.maxWidth > 1150 ? 310 : null,
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
                                      if (activeCompanyLabel != null) ...[
                                        SelectableText(
                                          activeCompanyLabel!,
                                          key: const ValueKey('active-company'),
                                          style: const TextStyle(
                                            fontWeight: FontWeight.w600,
                                            fontSize: 16,
                                          ),
                                        ),
                                        const SizedBox(height: 8),
                                      ],
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
                                        maintainState: true,
                                        expansionAnimationStyle:
                                            const AnimationStyle(
                                                duration:
                                                    Duration(milliseconds: 160),
                                                curve: Curves.easeOutCubic),
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
                      if (size.maxWidth > 1150) {
                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Expanded(child: workspace),
                            const SizedBox(width: 16),
                            panel,
                          ],
                        );
                      }
                      return Column(
                        children: [
                          Expanded(child: workspace),
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
