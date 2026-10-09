# Arquitetura e domínio

- `app/`: janela Flutter desktop. Tabela editável, importação/exportação, escritório, período, destino e intervenção humana.
- `engine/fgts_guias/domain.py`: CNPJ numérico com dígitos verificadores, dinheiro exato em centavos, competências, nomes de arquivo.
- `files.py`: CSV/XLSX com cabeçalhos normalizados; validação conservadora do PDF.
- `chrome.py`: abertura convencional do Chrome e conexão CDP local, preservando sessão.
- `browser.py`: adaptador da interface pública FGTS Digital, Google Chrome visível via Playwright.
- `storage.py`: SQLite no diretório de dados do usuário, fora do projeto. Workspace e diário por CNPJ/período.
- `__main__.py`: processo local, protocolo JSON por linha. Sem servidor HTTP ou dependência de uma planilha externa.

Comandos: bootstrap, save, import, export, template, start, pause, resume, skip, stop, recover, open_browser, close_browser, accept_difference. Respostas contêm id, ok e data/error. Eventos: progress, attention, saved, skipped, finished, diagnostic, browser_visibility. Não encaminhar stdout Python para texto livre.

**Empresa** contém COD, EMPRESA, CNPJ, FGTS MENSAL, CONSIGNADO, TOTAL, OBSERVAÇÕES. COD é identificação humana; CNPJ decide perfil e é chave financeira. O TOTAL informado deve igualar FGTS + consignado; não é corrigido automaticamente. O titular configura nome/CNPJ na própria interface, sem .env.

**Lote** é sequencial. Configuração de escritório/período/destino fica fixa enquanto roda. Tabela pode ser corrigida durante pausa, e a empresa é normalizada novamente antes de retomar. Uma divergência pausa todo o lote; ignorar é ação explícita do operador.

**Guia**: intenção `issuing` → `download_pending` → `saved`. Antes de clicar na emissão, intenção fica durável. Após falha ou reinício nesse intervalo, somente recuperação. Um salvo é revalidado antes de ser reutilizado. Chave: CNPJ + competência inicial + final. Arquivo com mesmo nome e outro conteúdo exige intervenção, sem substituição automática.

**Chrome**: instalação Google Chrome obrigatória em caminho padrão. Abertura convencional com CDP, sem flags padrão do Playwright; o navegador é sempre o Chrome do app. Fechamento da aba utilizada ou desconexão cancela imediatamente o lote, inclusive em pausa. Veja [sessão Chrome](chrome.md). Perfil dedicado no diretório de dados do app, sem acesso ao perfil pessoal. Certificado/token e CAPTCHA são controlados pelo operador. Trocar certificado fecha o Chrome iniciado pelo app inteiro e encerra o lote pausado. Sessão local não é enviada ao repositório.

## Distribuição

Cada plataforma deve ser empacotada no seu sistema operacional, com Flutter e PyInstaller. O motor fica ao lado do executável em `engine/`, ou `Contents/Resources/engine/` no macOS. Desenvolvimento aceita `--dart-define=ENGINE_SOURCE=...` e `--dart-define=PYTHON=...` para localizar o motor e seu ambiente virtual.

macOS usa distribuição desktop fora do App Store, sem sandbox: subprocesso, Chrome externo, dados e certificados do sistema precisam desse acesso. Assinatura/notarização e instaladores não foram produzidos. A1/A3 dependem do middleware do fabricante e do Chrome no sistema; compatibilidade não foi validada.

Fontes de implementação: [Flutter desktop](https://docs.flutter.dev/platform-integration/desktop), [Playwright Chrome instalado](https://playwright.dev/python/docs/browsers), [contexto persistente](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch-persistent-context).

## Aceitação de uma divergência específica

`decisions.py` mantém uma única chamada de conferência suspensa com identificador aleatório, cópia da entrada da empresa, contexto (competência, etapa e guia), esperado e encontrado. O comando `accept_difference` exige lote pausado, identificador atual e entrada inalterada. Registra a decisão na tabela SQLite `decisions` antes de liberar aquela chamada. O identificador é consumido; não há whitelist, preferência de ignorar inconsistências nem permissão compartilhada entre etapas/empresas.

Após o clique, o adaptador confirma novamente empregador e dados daquela conferência. Se mudaram, abre outra decisão. Retomar/ignorar invalidam o identificador; encerrar/cancelar descarta a espera. A planilha permanece intacta. PDFs cuja diferença numérica foi aceita guardam `verified_company` no registro da própria guia, conservando a entrada original em `company`: a revalidação do arquivo utiliza aqueles dados exatos, número, competência e vencimento, sem autorizar outros documentos. Identidade, competência, estrutura válida, identificação única e ausência de reemissão continuam obrigatórias.
