# FGTS Guias

Emissão assistida de guias do FGTS Digital em uma janela desktop. Importe suas empresas, informe a competência e acompanhe as conferências antes de cada emissão. A interface é Flutter; a navegação no Google Chrome é feita por um motor Python local.

**Emissão e recuperação de guias validadas em lotes reais no Linux e no Windows.** Há instaladores e pacotes portáteis para Linux e Windows. A compatibilidade com cada modelo de certificado e o macOS ainda precisam de validação. O app emite guias; o pagamento é feito fora dele.

## Baixar o aplicativo

Abra [Releases](https://github.com/JoaoLucasDaSilvaOliveira/fgts-guias/releases/latest) e baixe o pacote do seu sistema:

- **Linux x64 (CachyOS/Arch, Ubuntu/Debian):** baixe o `.run`. Nas propriedades do arquivo, permita executá-lo como programa e abra o instalador. Escolha a pasta e instale; o app aparecerá no menu de aplicativos. O destino padrão é `~/.local/opt/fgts-guias`. Se preferir o terminal: `chmod +x fgts-guias-v0.3.0-linux-x64.run` e `./fgts-guias-v0.3.0-linux-x64.run`. Em Ubuntu/Debian, instale `libgtk-3-0` se necessário; no Arch/CachyOS, o pacote é `gtk3`.
- **Windows x64:** execute o `-setup.exe` e siga o assistente. Instala para seu usuário, oferece atalhos e inclui desinstalador. Se faltar runtime C++, instale o Microsoft Visual C++ Redistributable x64.

Também há `.tar.gz` (Linux) e `.zip` (Windows) para uso portátil. Extraia e mantenha `data`, `engine` e bibliotecas junto do executável. Google Chrome é obrigatório em todos os casos.

## Atualizar

No cabeçalho, abra **Atualizações**. O app verifica releases estáveis uma vez por dia ao abrir; essa opção pode ser desativada. Havendo uma nova versão, use **Baixar atualização**, escolha uma pasta e aguarde a verificação de integridade. Depois, feche o app e execute o instalador baixado.

Encerre o lote antes de atualizar. Empresas, configurações, histórico, perfil Chrome e PDFs são preservados. No Linux, a instalação anterior fica numa pasta `fgts-guias.previous-*` para recuperação. Veja [detalhes de instalação e recuperação](docs/instalacao.md).

Os pacotes incluem o motor Python. Não é necessário instalar Python ou Flutter para usá-los. Instale o Google Chrome e o software do certificado, quando exigido pelo fabricante. Os executáveis ainda não possuem assinatura digital.

## Requisitos

- **Google Chrome instalado**, em caminho padrão. Chromium, Vivaldi e outros navegadores não substituem esse requisito.
- Certificado digital do titular e, para empresas representadas, procuração válida no portal. Instale o middleware exigido pelo fabricante de seu token, quando aplicável.
- Para executar a partir do código: Python 3.11+ e Flutter/Dart compatível com o projeto, com ferramentas desktop do seu sistema.

## Executar a partir do repositório

Clone o repositório e entre na pasta:

```bash
git clone https://github.com/JoaoLucasDaSilvaOliveira/fgts-guias.git
cd fgts-guias
```

Prepare o motor:

Linux/macOS:
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ./engine
.venv/bin/python scripts/run.py
```
O script escolhe Linux ou macOS e informa caminhos absolutos ao Flutter.

Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .\engine
.\.venv\Scripts\python.exe scripts/run.py
```
O script escolhe Windows automaticamente. Não é necessário instalar Chromium do Playwright: o app exige o Chrome já instalado. [Documentação do Chrome no Playwright](https://playwright.dev/python/docs/browsers).

## Preparar as empresas

1. Informe nome e CNPJ do titular do certificado na interface. O app escolhe **Meu Perfil** se esse CNPJ for o da empresa; nas demais usa **Procurador**.
2. No menu **Planilha**, clique em **Baixar modelo** para salvar um XLSX ou CSV vazio. Também há [template CSV](templates/empresas.csv) no repositório.
3. Preencha e importe, ou use **Adicionar empresa** e edite na tabela. CNPJs recebem máscara automaticamente. FGTS mensal e consignado aceitam valores em reais com duas casas decimais. Campos vazios valem zero. O total é calculado automaticamente e não pode ser editado.

| Coluna | Conteúdo |
|---|---|
| COD | Código de identificação da empresa |
| EMPRESA | Nome usado no arquivo PDF |
| CNPJ | CNPJ numérico ou formatado, obrigatório; mantenha como texto no Excel |
| FGTS MENSAL | Valor em reais, por exemplo `100,00` |
| CONSIGNADO | Total de Parcela paga, ou `0,00` |
| TOTAL | Calculado pelo app como FGTS MENSAL + CONSIGNADO |
| OBSERVAÇÕES | Notas do operador |

**Planilha → Remover todas** limpa a tabela após sua confirmação, com o lote parado. As guias salvas, o registro das emissões e as configurações são preservados.

CSV usa UTF-8 e `;`. XLSX usa a primeira aba e primeira linha de cabeçalhos. O app não depende de Google Sheets nem extrai automaticamente os relatórios PDF. A transcrição dos valores deve ser conferida antes do lote.

Arraste a divisória no cabeçalho para ajustar a largura das colunas. As larguras ficam salvas. Clique duas vezes na divisória para restaurar a largura padrão da coluna.

## Otimização do download

Ao lado de **Baixar selecionadas**, escolha:

- **Baixar mesma guia:** confere e reutiliza o PDF salvo, se disponível. Caso contrário, busca a guia no portal.
- **Baixar nova guia:** sempre faz novo download da guia existente, mesmo com PDF salvo.

As opções não solicitam uma segunda emissão para um débito com guia registrada. Quando não há guia, o app segue o fluxo normal de emissão e conferência. Resultados incertos são recuperados antes de prosseguir.

## Emitir e acompanhar

1. Selecione competência Inicial/Final no calendário (o app usa o mês/ano da data escolhida) e escolha a pasta dos PDFs. Selecione as empresas.
2. Clique **Abrir Chrome**. Entre com GOV.BR, selecione certificado/PIN e resolva CAPTCHA pessoalmente. Aguarde o FGTS Digital abrir e use **Baixar selecionadas**. Durante o lote, o Chrome fica minimizado e aparece automaticamente quando houver uma pendência. Login concluído retoma automaticamente com o titular configurado; para divergências, escolha **Aceitar divergência** ou **Negar divergência**. Ao negar, revise a causa e use **Retomar**. O botão **Abrir Chrome** também permite inspecionar a mesma janela durante o lote. Esse modo preserva cookies, certificado e histórico do perfil do app, sem alternar para headless real. Veja [funcionamento da sessão](docs/chrome.md).
3. O app compara FGTS, consignados e total. Desmarca **Sem guia emitida** nas pesquisas para incluir débitos antes escondidos.
4. Divergências pausam o lote inteiro. **Aceitar divergência** autoriza somente os dados exibidos naquela etapa, uma vez. **Negar divergência** mantém o lote pausado para revisar relatórios e tabela; depois use **Retomar** para conferir novamente. Outras pendências mostram **Retomar**, **Ignorar empresa** e **Recuperar PDF**.
5. O vencimento sugerido é preservado; quando hoje é sugerido para atrasados, tenta amanhã e confere os totais. Valores adicionais provocam pausa.
6. PDF é salvo como `EMPRESA.pdf` na pasta escolhida depois de conferir CNPJ, competência, número, vencimento e total. Caracteres inválidos no nome são substituídos. Documento diferente com mesmo nome não é sobrescrito.

**Aguardando pagamento ou download incerto:** quando o download da emissão ultrapassa 5 segundos, o app abre **Consulta de Guias**, pesquisa com os filtros padrão e procura uma única guia pelo vencimento e valor, conferindo também o número quando registrado. Reimprime, valida CNPJ, competência, FGTS, consignado, total, número e vencimento, e salva na pasta escolhida. O indicador azul dos débitos também permite reimpressão de guia única. Não solicita nova emissão para substituir uma emissão incerta. Múltiplas candidatas, divergências ou formato desconhecido pausam o lote. **Recuperar PDF** continua disponível para intervenção manual.

**Não há débitos de interesse:** se o portal exibir essa mensagem para a empresa confirmada, o app registra o motivo e segue para a próxima. Pode ser MEI ou ausência de eventos enviados; o app não altera os valores importados. Ausência de itens na pesquisa e divergências financeiras continuam exigindo atenção.

**Aceitar divergência:** aparece junto a **Retomar** quando o app conseguiu identificar uma diferença específica de valor ou vencimento. A tela mostra esperado, encontrado, etapa e número da guia quando disponível. A aceitação libera somente aquela conferência uma vez, não altera a planilha e fica registrada localmente. Outra etapa ou dados diferentes exigem nova decisão. **Retomar** descarta a decisão pendente e confere novamente. Falhas de autenticação, empresa/competência incorreta, PDF inválido, várias guias candidatas ou leitura desconhecida não oferecem bypass.

**Fechar Chrome durante o lote:** encerra imediatamente o lote, inclusive quando pausado. O app não reabre a janela nem prossegue para outra empresa. Emissões solicitadas permanecem registradas para recuperação.

**Trocar certificado:** encerre o lote e feche todas as janelas do Chrome aberto pelo app. Depois, use **Abrir Chrome** e entre novamente com o titular configurado. Apenas fechar uma aba não troca o certificado.

## Dados e limites

Configuração, tabela e diário de emissão ficam no diretório local de dados do usuário. O perfil Chrome também persiste localmente; mantenha a conta do computador protegida. Arquivos privados não devem ser adicionados ao Git. Não há telemetria ou servidor do app. Veja [privacidade](docs/privacidade.md).

O portal pode mudar. Leitura ambígua, CAPTCHA, autenticação, PDF com formato diferente ou resultado incerto interrompem o processo. A validação estrita pode exigir intervenção mesmo em um PDF legítimo. Veja os resultados e limites da [validação manual](docs/validacao-manual.md).

## Empacotar

Execute `python scripts/package.py` no sistema alvo, dentro de um ambiente com as dependências do motor e PyInstaller (`python -m pip install pyinstaller`). O script compila Flutter, empacota o motor, verifica o protocolo UTF-8 e gera pacotes portáteis, instaladores e checksums. No Windows, instale também Inno Setup 6. Compile cada sistema nele próprio. Os workflows do GitHub fazem builds Linux/Windows; assinatura digital e notarização não estão incluídas. [Flutter desktop](https://docs.flutter.dev/platform-integration/desktop).

Documentação: [fluxo aprendido](docs/fluxo-fgts.md), [arquitetura](docs/arquitetura.md), [instruções para colaboradores](AGENTS.md). Licença MIT; contribuições devem usar exemplos fictícios.
