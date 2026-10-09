# Sessão Chrome e autenticação

## Chrome do app

Modo padrão: abre o Google Chrome instalado pela linha de comando convencional, com perfil persistente `chrome-profile` no diretório local do app. Conecta pela depuração local (CDP). Não usa a lista de flags de lançamento do Playwright, não falsifica identificação do navegador e não resolve CAPTCHA automaticamente.

Clique **Abrir / conectar Chrome**, conclua o login manualmente e aguarde a página do FGTS Digital. Só depois inicie o lote. Cookies e histórico desse perfil são reutilizados nas próximas execuções. Se já usou a versão anterior do app, o mesmo diretório de perfil é mantido.

A alteração de abertura é uma tentativa de compatibilidade, não garantia de aceitação pelo GOV.BR. Rejeição explícita do CAPTCHA pelo site é diferente da pausa do app por login ainda incompleto. A mensagem da pausa agora distingue os dois estados. O operador continua responsável por CAPTCHA, certificado e PIN.

## Chrome já aberto

A conexão a uma sessão existente exige que ela tenha sido iniciada com depuração. Não é possível anexar automaticamente a qualquer Chrome pessoal que já esteja aberto. Desde Chrome 136, a depuração por porta não funciona no diretório padrão de dados: precisa de perfil separado. Não copiamos cookies nem o perfil pessoal.

Para preparar uma sessão reutilizável, execute uma das opções abaixo. A pasta escolhida mantém seus próprios cookies e histórico. Não compartilhe essa pasta ou exponha a porta na rede.

Linux:
```bash
google-chrome --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir="$HOME/.fgts-chrome" https://fgtsdigital.sistema.gov.br/
```
macOS:
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir="$HOME/.fgts-chrome" https://fgtsdigital.sistema.gov.br/
```
Windows (PowerShell, ajuste o caminho se a instalação for diferente):
```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 "--user-data-dir=$env:LOCALAPPDATA\FGTSChrome" https://fgtsdigital.sistema.gov.br/
```

Entre normalmente no GOV.BR nessa janela. No app, escolha **Chrome já aberto (depuração)**, porta **9222**, e **Abrir / conectar Chrome**. Mantenha somente uma aba FGTS/GOV.BR para evitar selecionar a sessão errada. A conexão aceita somente `127.0.0.1` e verifica identificação Chrome no endpoint.

O app reutiliza o contexto e a aba já autenticados. Enquanto conectado, direciona os downloads para seu cache local, para validar e salvar o PDF no destino escolhido, e nega localização nos portais FGTS/GOV.BR. Ao desconectar, restaura a política padrão de download e mantém o Chrome externo aberto. Para trocar certificado, desconecte e feche todo esse Chrome manualmente; fechar somente a aba não basta.

A conexão CDP tem diferenças em relação ao protocolo nativo do Playwright. Downloads e autenticação ainda precisam de validação pelo operador nessa configuração. Emissão incerta permanece no diário para recuperação; nunca tentar reemitir automaticamente.

Referências: [mudança do Chrome 136](https://developer.chrome.com/blog/remote-debugging-port), [Playwright connect_over_cdp](https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp).
