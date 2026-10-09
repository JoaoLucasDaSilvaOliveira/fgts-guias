# FGTS Guias

Emissão assistida de guias do FGTS Digital em uma janela desktop. Importe suas empresas, informe a competência e acompanhe as conferências antes de cada emissão. A interface é Flutter; a navegação no Google Chrome é feita por um motor Python local.

**Em validação manual da interface.** Ainda não há instaladores ou emissão real validada. O projeto tem estrutura para Linux, Windows e macOS; os três sistemas e certificados A1/A3 precisam ser validados. Nenhum pagamento é realizado pelo app.

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

1. Informe nome e CNPJ do escritório/titular na interface. O app escolhe **Meu Perfil** se esse CNPJ for o da empresa; nas demais usa **Procurador**.
2. Clique em **Template** para salvar um XLSX ou CSV vazio. Também há [template CSV](templates/empresas.csv) no repositório.
3. Preencha e importe, ou use **Adicionar empresa** e edite na tabela. CNPJs recebem máscara automaticamente. Os campos monetários ignoram letras; aceitam reais com duas casas decimais.

| Coluna | Conteúdo |
|---|---|
| COD | Código de identificação da empresa |
| EMPRESA | Nome usado no arquivo PDF |
| CNPJ | CNPJ numérico ou formatado, obrigatório; mantenha como texto no Excel |
| FGTS MENSAL | Valor em reais, por exemplo `100,00` |
| CONSIGNADO | Total de Parcela paga, ou `0,00` |
| TOTAL | FGTS MENSAL + CONSIGNADO, conferido pelo app |
| OBSERVAÇÕES | Notas do operador |

CSV usa UTF-8 e `;`. XLSX usa a primeira aba e primeira linha de cabeçalhos. O app não depende de Google Sheets nem extrai automaticamente os relatórios PDF. A transcrição dos valores deve ser conferida antes do lote.

## Emitir e acompanhar

1. Selecione competência Inicial/Final no calendário (o app usa o mês/ano da data escolhida) e escolha a pasta dos PDFs. Selecione as empresas.
2. Escolha a sessão do Chrome e clique **Abrir / conectar Chrome**. Entre com GOV.BR, selecione certificado/PIN e resolva CAPTCHA pessoalmente. Aguarde o FGTS Digital abrir e use **Emitir selecionadas**. O modo padrão mantém cookies e histórico do perfil do app. Para reutilizar Chrome já aberto, veja [configuração da sessão](docs/chrome.md).
3. O app compara FGTS, consignados e total. Desmarca **Sem guia emitida** nas pesquisas para incluir débitos antes escondidos.
4. Divergências pausam o lote inteiro. Revise relatórios e tabela, resolva o problema e retome. Caso o sistema de folha precise de correção, faça isso antes. **Ignorar empresa** é opção explícita.
5. O vencimento sugerido é preservado; quando hoje é sugerido para atrasados, tenta amanhã e confere os totais. Valores adicionais provocam pausa.
6. PDF é salvo como `EMPRESA.pdf` na pasta escolhida depois de conferir CNPJ, competência, número, vencimento e total. Caracteres inválidos no nome são substituídos. Documento diferente com mesmo nome não é sobrescrito.

**Aguardando pagamento ou download incerto:** não tente emitir outra guia. No Chrome, localize a guia existente pela reimpressão ou Consulta de Guias, baixe-a e use **Recuperar PDF**, informando número e vencimento. Depois retome: o registro salvo será conferido e reutilizado. A navegação automática da consulta ainda não foi implementada porque não foi demonstrada no treinamento.

**Trocar certificado:** pause e clique em **Fechar Chrome para trocar certificado**. O botão fecha todo o Chrome controlado pelo app; ao retomar, entre novamente com o titular configurado. No modo Chrome já aberto, o botão desconecta; feche todo esse Chrome manualmente para trocar o certificado. Apenas fechar uma aba não troca o certificado.

## Dados e limites

Configuração, tabela e diário de emissão ficam no diretório local de dados do usuário. O perfil Chrome também persiste localmente; mantenha a conta do computador protegida. Arquivos privados não devem ser adicionados ao Git. Não há telemetria ou servidor do app. Veja [privacidade](docs/privacidade.md).

O portal pode mudar. Leitura ambígua, CAPTCHA, autenticação, PDF com formato diferente ou resultado incerto interrompem o processo. A validação estrita pode exigir intervenção mesmo em um PDF legítimo. Não foram executados testes ou builds nesta etapa, conforme combinado; veja [validação manual](docs/validacao-manual.md).

## Empacotar

Após validar, execute `python scripts/package.py` no sistema alvo, dentro de um ambiente com as dependências do motor e PyInstaller (`python -m pip install pyinstaller`). O script prepara o motor e a aplicação Flutter e copia o motor para o pacote. Compile cada sistema nele próprio. Assinatura, notarização, instaladores e releases binárias são etapas posteriores. [Flutter desktop](https://docs.flutter.dev/platform-integration/desktop).

Documentação: [fluxo aprendido](docs/fluxo-fgts.md), [arquitetura](docs/arquitetura.md), [instruções para colaboradores](AGENTS.md). Licença MIT; contribuições devem usar exemplos fictícios.
