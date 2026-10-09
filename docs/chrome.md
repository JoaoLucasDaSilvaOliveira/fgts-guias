# Chrome do app e autenticação

O app abre o Google Chrome instalado pela linha de comando convencional, com perfil persistente `chrome-profile` no diretório local do app. Conecta pela depuração local (CDP), internamente. Não há seletor de sessão, porta configurável ou conexão a Chrome externo. Configurações antigas dessas opções são ignoradas.

Clique **Abrir Chrome**, conclua o login manualmente e aguarde a página do FGTS Digital. Depois inicie o lote. Cookies e histórico desse perfil são reutilizados nas próximas execuções. O operador confirmou que o GOV.BR deixou de bloquear essa abertura; certificado, PIN e CAPTCHA continuam manuais.

Ao fechar a aba utilizada ou o Chrome, o app cancela imediatamente o lote, inclusive se estiver pausado ou aguardando uma ação do portal. Não abre outra janela nem passa à próxima empresa automaticamente. Uma desconexão do controle do navegador também encerra o lote. Emissões já solicitadas permanecem no diário para recuperação; não são repetidas automaticamente.

**Fechar Chrome para trocar certificado** fecha o navegador inteiro e encerra um lote pausado. Abrir novamente e começar um novo lote são ações explícitas. Fechar somente uma aba não basta para trocar o certificado em uma sessão ainda aberta.

Downloads ficam no cache local antes da validação e gravação no destino escolhido. O motor acompanha os eventos Chrome downloadWillBegin/downloadProgress da página utilizada, aguarda conclusão e copia o arquivo pelo identificador do download. O mesmo mecanismo atende emissão e reimpressão; não depende do diálogo Salvar como nem da escolha manual do arquivo. A localização é negada nos portais FGTS/GOV.BR. Nenhum cookie, certificado, perfil ou documento é enviado ao repositório.

Referência técnica: [Playwright connect_over_cdp](https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp).
