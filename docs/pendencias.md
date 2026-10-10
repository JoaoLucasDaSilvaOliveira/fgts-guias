# Pendências registradas pelo operador

## Identificação do titular do certificado — corrigida

No teste autorizado em 09/10/2026, o titular foi identificado no `aria-label` do botão **Abrir Menu de usuário**, em vez do texto visível do cabeçalho. O motor compara esse CNPJ com o escritório configurado e pausa quando ausente ou diferente. A seleção de Procurador e a identificação do empregador foram confirmadas no portal.

## Autenticação Chrome — observação do operador

O operador confirmou que o GOV.BR deixou de bloquear o Chrome do app. A opção Chrome já aberto foi retirada a seu pedido. Manter abertura convencional e perfil persistente.

## v0.3.0 — instalação e atualizações

Implementação autorizada pelo operador. Instalação Linux com assistente Flutter, instalação Windows com Inno Setup e consulta diária opcional das releases. Ver [instalação e atualização](instalacao.md).

- Oferecer instalação guiada no Linux e no Windows, incluindo o motor empacotado. Flutter compila o app; o instalador é uma etapa adicional de distribuição. Escolher a ferramenta de instalação ao implementar.
- Linux: instalar em um diretório permanente, fora de Downloads, e registrar um `.desktop` com ícone no menu de aplicativos. Definir o destino e permitir instalação por usuário, sem exigir privilégios de administrador quando possível. Considerar CachyOS/Arch e Ubuntu/Debian.
- Windows: oferecer assistente de instalação, diretório permanente, atalhos e desinstalação.
- Consultar as releases do repositório oficial, comparar com a versão instalada, avisar quando houver atualização e permitir baixar o pacote correto para o sistema e a arquitetura. A frequência da consulta e a aplicação da atualização serão definidas na implementação; não substituir arquivos durante um lote em andamento.
- Preservar configurações, empresas, histórico, perfil Chrome e PDFs ao instalar ou atualizar. Validar a integridade do download antes de instalar e permitir recuperação se a atualização falhar.
- Google Chrome instalado continua obrigatório. O usuário não precisa instalar Flutter ou Python.

Referências de distribuição: [Windows](https://docs.flutter.dev/platform-integration/windows/building#distributing-windows-apps) e [Linux](https://docs.flutter.dev/platform-integration/linux/building).
