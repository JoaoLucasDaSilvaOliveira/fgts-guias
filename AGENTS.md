# FGTS Guias

App desktop Flutter com motor Python/Playwright. Use Chrome instalado e um perfil exclusivo. Valores monetários no motor são centavos inteiros; entradas e arquivos usam reais.

- Antes de mudar sessão Chrome, leia [docs/chrome.md](docs/chrome.md).
- Antes de mudar navegação, emissão ou recuperação, leia [docs/fluxo-fgts.md](docs/fluxo-fgts.md).
- Antes de mudar modelos, comunicação ou distribuição, leia [docs/arquitetura.md](docs/arquitetura.md).
- Antes de publicar arquivos ou logs, leia [docs/privacidade.md](docs/privacidade.md).
- Para a próxima validação pelo operador, siga [docs/validacao-manual.md](docs/validacao-manual.md).

Nunca resolver CAPTCHA, escolher certificado/PIN, pagar guias ou corrigir valores financeiros silenciosamente. Divergências pausam o lote inteiro. Persistir a intenção antes de emitir; resultado incerto exige recuperação, nunca nova emissão automática. Salvo exige PDF validado no destino, sem sobrescrever guia diferente.

Nesta primeira implementação, o usuário pediu para não executar testes, builds ou emissão real. Aguardar sua validação da interface e autorização para testar uma empresa. Não incluir dados reais, certificados, sessões, PDFs ou planilhas no repositório.
