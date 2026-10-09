# Chrome do app e autenticação

O app abre o Google Chrome instalado pela linha de comando convencional, com perfil persistente `chrome-profile` no diretório local do app. Conecta pela depuração local (CDP), internamente. Não há seletor de sessão, porta configurável ou conexão a Chrome externo. Configurações antigas dessas opções são ignoradas.

O lote opera com a janela do Chrome minimizada. **Abrir Chrome** restaura a mesma janela para inspeção ou login. Ao encontrar autenticação, CAPTCHA, divergência ou outra pendência, o app pausa e restaura o navegador. Após reconhecer a autenticação concluída no FGTS Digital, com titular esperado e sem CAPTCHA pendente, minimiza e retoma automaticamente. Para divergências e outras pendências, o operador usa **Retomar** ou **Ignorar empresa**; a janela volta a minimizar antes da nova conferência. Se a pendência continuar, aparece novamente. Cookies e histórico desse perfil são reutilizados nas próximas execuções. O operador confirmou que o GOV.BR deixou de bloquear essa abertura; certificado, PIN e CAPTCHA continuam manuais.

Ao fechar a aba utilizada ou o Chrome, o app cancela imediatamente o lote, inclusive se estiver pausado ou aguardando uma ação do portal. Não abre outra janela nem passa à próxima empresa automaticamente. Uma desconexão do controle do navegador também encerra o lote. Emissões já solicitadas permanecem no diário para recuperação; não são repetidas automaticamente.

**Fechar Chrome para trocar certificado** fecha o navegador inteiro e encerra um lote pausado. Abrir novamente e começar um novo lote são ações explícitas. Fechar somente uma aba não basta para trocar o certificado em uma sessão ainda aberta.

Downloads ficam no cache local antes da validação e gravação no destino escolhido. O motor acompanha os eventos Chrome downloadWillBegin/downloadProgress da página utilizada, aguarda conclusão e copia o arquivo pelo identificador do download. O mesmo mecanismo atende emissão e reimpressão; não depende do diálogo Salvar como nem da escolha manual do arquivo. A localização é negada nos portais FGTS/GOV.BR. Nenhum cookie, certificado, perfil ou documento é enviado ao repositório.

Referência técnica: [Playwright connect_over_cdp](https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp).

A sessão de controle da página mantém `Emulation.setFocusEmulationEnabled` ativo durante o uso do app. No teste com outras janelas cobrindo o Chrome, `requestAnimationFrame` deixou de responder e os cliques aguardavam estabilidade indefinidamente, mesmo com elementos visíveis e habilitados. Manter essa sessão CDP conectada permite continuar a renderização sem exigir que o operador mantenha foco na janela. Não modifica CAPTCHA nem escolhe certificado. Fechar a janela continua encerrando o lote.

## Segundo plano e intervenção

O modo de segundo plano é Chrome convencional **minimizado**, não headless real. A escolha foi confirmada pelo operador para preservar certificado, cookies, aba, progresso e downloads sem reiniciar o processo. Headless é uma opção de inicialização (`--headless`), não uma alternância de janela do processo existente. A minimização/restauração usa `Browser.getWindowForTarget` e `Browser.setWindowBounds`, exigindo confirmação do estado pelo Chrome. A sessão CDP que mantém renderização ativa continua conectada. O app também minimiza ao terminar o lote. O operador pode restaurar pelo botão Abrir Chrome, inclusive durante o lote.

A detecção automática de conclusão é restrita à autenticação/CAPTCHA: a URL precisa ser do FGTS Digital, fora do login, sem desafio pendente e com o CNPJ do titular esperado no cabeçalho. Essa observação não escolhe certificado nem resolve o desafio. Não retomar automaticamente divergências financeiras. A monitoração é cancelada ao pausar manualmente, retomar, ignorar, encerrar ou fechar o navegador. Se falhar, a pendência permanece e Retomar segue disponível.

Referências: [Chrome Headless](https://developer.chrome.com/docs/automation-and-testing/headless), [Browser.setWindowBounds](https://chromedevtools.github.io/devtools-protocol/tot/Browser/#method-setWindowBounds).

## Chrome no pacote distribuído

O motor PyInstaller modifica a busca de bibliotecas. Ao iniciar o Chrome instalado, `external.py` restaura o `LD_LIBRARY_PATH_ORIG` (ou remove o caminho privado se não existia antes) apenas no subprocesso. No Windows, restaura temporariamente a busca padrão de DLLs e recompõe a busca do motor imediatamente após iniciar o processo. O Playwright continua com suas bibliotecas empacotadas. Sem isso, o launcher Bash do Chrome no CachyOS falhava com conflito de readline.

O empacotamento verifica o motor congelado, um comando externo e a inicialização do driver Playwright. No Linux, executa o launcher real do Chrome com `--version`; no Windows, verifica que o Chrome foi localizado e inicia `cmd /c ver`, pois o launcher gráfico não fornece `--version`. Esse teste não autentica nem emite guias.

Referência: [PyInstaller: programas externos](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#launching-external-programs-from-the-frozen-application).
