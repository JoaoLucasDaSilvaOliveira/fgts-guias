# Arquitetura e domínio

- `app/`: janela Flutter desktop. Tabela editável, importação/exportação, escritório, período, destino e intervenção humana.
- `engine/fgts_guias/domain.py`: CNPJ numérico com dígitos verificadores, dinheiro exato em centavos, competências, nomes de arquivo.
- `files.py`: CSV/XLSX com cabeçalhos normalizados; validação conservadora do PDF.
- `chrome.py`: abertura convencional do Chrome e conexão CDP local, preservando sessão.
- `browser.py`: adaptador da interface pública FGTS Digital, Google Chrome visível via Playwright.
- `storage.py`: SQLite no diretório de dados do usuário, fora do projeto. Workspace e diário por CNPJ/período.
- `__main__.py`: processo local, protocolo JSON por linha. Sem servidor HTTP ou dependência de uma planilha externa.
- `updates.py`: consulta de releases oficiais, comparação de versões e download com integridade confirmada. Metadados passam pela thread de rede, mas as preferências SQLite são gravadas no event loop.
- `installation.py`: instalação Linux por usuário, registro desktop e recuperação da pasta anterior. `packaging/windows/installer.iss` define instalação/desinstalação Windows.

Comandos: bootstrap, save, import, export, template, start, pause, resume, skip, stop, recover, open_browser, close_browser, accept_difference, reject_difference. Respostas contêm id, ok e data/error. Eventos: progress, attention, saved, skipped, finished, diagnostic, browser_visibility. Não encaminhar stdout Python para texto livre.

**Empresa** contém COD, EMPRESA, CNPJ, FGTS MENSAL, CONSIGNADO, TOTAL, OBSERVAÇÕES. COD é identificação humana; CNPJ decide perfil e é chave financeira. Na interface, TOTAL é calculado em centavos como FGTS + consignado e não é editável, inclusive após importação. Campos monetários vazios são enviados como 0,00; o motor continua verificando a igualdade. O titular configura nome/CNPJ na própria interface, sem .env.

**Lote** é sequencial. Configuração de escritório/período/destino fica fixa enquanto roda. Tabela pode ser corrigida durante pausa, e a empresa é normalizada novamente antes de retomar. Uma divergência pausa todo o lote; ignorar é ação explícita do operador.

**Guia**: intenção `issuing` → `download_pending` → `saved`. Antes de clicar na emissão, intenção fica durável. Após falha ou reinício nesse intervalo, somente recuperação. Um salvo é revalidado antes de ser reutilizado. Chave: CNPJ + competência inicial + final. Arquivo com mesmo nome e outro conteúdo exige intervenção, sem substituição automática.

**Chrome**: instalação Google Chrome obrigatória em caminho padrão. Abertura convencional com CDP, sem flags padrão do Playwright; o navegador é sempre o Chrome do app. Fechamento da aba utilizada ou desconexão cancela imediatamente o lote, inclusive em pausa. Veja [sessão Chrome](chrome.md). Perfil dedicado no diretório de dados do app, sem acesso ao perfil pessoal. Certificado/token e CAPTCHA são controlados pelo operador. Trocar certificado fecha o Chrome iniciado pelo app inteiro e encerra o lote pausado. Sessão local não é enviada ao repositório.

## Distribuição

Cada plataforma deve ser empacotada no seu sistema operacional, com Flutter e PyInstaller. O motor fica ao lado do executável em `engine/`, ou `Contents/Resources/engine/` no macOS. Desenvolvimento aceita `--dart-define=ENGINE_SOURCE=...` e `--dart-define=PYTHON=...` para localizar o motor e seu ambiente virtual.

macOS usa distribuição desktop fora do App Store, sem sandbox: subprocesso, Chrome externo, dados e certificados do sistema precisam desse acesso. Assinatura/notarização e instaladores não foram produzidos. A1/A3 dependem do middleware do fabricante e do Chrome no sistema; compatibilidade não foi validada.

Linux e Windows agora têm instaladores nativos além dos pacotes portáteis. Atualizações são consultadas no cabeçalho e baixadas com SHA-256; a aplicação da atualização exige fechar o app e executar o instalador. Nenhum lote ativo ou pausado pode atualizar. Veja [instalação](instalacao.md). macOS não recebe instalador nesta versão.

Fontes de implementação: [Flutter desktop](https://docs.flutter.dev/platform-integration/desktop), [Playwright Chrome instalado](https://playwright.dev/python/docs/browsers), [contexto persistente](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch-persistent-context).

## Aceitação de uma divergência específica

`decisions.py` mantém uma única chamada de conferência suspensa com identificador aleatório, cópia da entrada da empresa, contexto (competência, etapa e guia), esperado e encontrado. O comando `accept_difference` exige lote pausado, identificador atual e entrada inalterada. Registra a decisão na tabela SQLite `decisions` antes de liberar aquela chamada. O identificador é consumido; não há whitelist, preferência de ignorar inconsistências nem permissão compartilhada entre etapas/empresas.

Após o clique, o adaptador confirma novamente empregador e dados daquela conferência. Se mudaram, abre outra decisão. Retomar/ignorar invalidam o identificador; encerrar/cancelar descarta a espera. A planilha permanece intacta. PDFs cuja diferença numérica foi aceita guardam `verified_company` no registro da própria guia, conservando a entrada original em `company`: a revalidação do arquivo utiliza aqueles dados exatos, número, competência e vencimento, sem autorizar outros documentos. Identidade, competência, estrutura válida, identificação única e ausência de reemissão continuam obrigatórias.

Durante uma decisão específica, a interface mostra Aceitar e Negar, sem Retomar. `reject_difference` valida e consome o identificador, registra a negativa e mantém o lote pausado. A pausa passa a ser de revisão, com Retomar, Ignorar empresa e Recuperar PDF. Retomar executa novamente a conferência; a negativa não autoriza nenhum valor.

A configuração `downloadSaved` permite baixar novamente guias em estado `saved` pela consulta, usando o número já registrado. Sem essa opção, o PDF é revalidado e emitido o evento `saved` com `reused: true`. A UI limpa os estados ao iniciar e distingue arquivos baixados de já salvos no resumo final (`finished.completed`). Uma entrada financeira alterada continua bloqueando; o modo não autoriza diferenças nem nova emissão.

A interface oferece Baixar mesma guia (`downloadSaved: false`) e Baixar nova guia (`downloadSaved: true`), com a escolha visível ao lado de Baixar selecionadas. Nova significa novo download da guia existente, não nova emissão. A opção anterior Reiniciar emissão foi removida após esclarecimento do operador; start não aceita essa autorização. O histórico de solicitações antigas permanece no banco.

A tabela usa colunas de largura fixa, cabeçalho separado e ListView.builder com linhas de altura fixa. Apenas linhas visíveis e uma pequena margem são renderizadas; os controllers e os dados editados permanecem no estado do workspace. Não usar DataTable com todas as linhas dentro de uma área cuja altura muda a cada quadro de animação.

A configuração abre em Drawer lateral sobre a área de trabalho, evitando mudar a altura da tabela durante a animação. O histórico anima apenas dentro do painel. Medição no app Linux em debug, com três aberturas/fechamentos: p95 de LAYOUT passou de aproximadamente 31 ms para 4 ms; p95 do processamento do quadro passou de 42 ms para 17 ms. A primeira abertura ainda tem custo de criação dos campos e os números não equivalem a uma medição em release.

O acompanhamento mostra COD e EMPRESA a partir do CNPJ da empresa ativa. O motor anuncia a empresa antes de abrir o portal; a identificação permanece durante pausas e é removida ao concluir ou interromper o lote. Cada atividade no histórico é associada à empresa. O resumo final usa guias salvas, guias reutilizadas e empresas ignoradas, com concordância e omissão das contagens zeradas.

O protocolo JSON por linha utiliza UTF-8 explicitamente em stdin, stdout e stderr do motor, inclusive no executável congelado. Não depender da página de códigos do Windows. O empacotamento verifica uma resposta com acento após uma entrada inválida, antes de qualquer navegação ou emissão.
