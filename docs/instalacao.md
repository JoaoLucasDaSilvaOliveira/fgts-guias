# Instalação e atualizações — v0.3.0

## Linux

O pacote `.run` contém o mesmo bundle do tarball e verifica o SHA-256 do payload antes de extraí-lo para uma pasta temporária. O aplicativo extraído abre em modo `--install`, com assistente Flutter; não depende de Zenity, KDialog, Flutter ou Python instalados. Requer as bibliotecas desktop GTK do sistema, como o app portátil.

O destino padrão é `~/.local/opt/fgts-guias`. Pode ser alterado no assistente. O instalador copia para uma pasta de preparação no mesmo sistema de arquivos e troca a pasta por renomeação. Uma atualização mantém a instalação anterior em `fgts-guias.previous-*`; erros ao registrar os atalhos restauram a pasta anterior. Instalações concorrentes no mesmo destino são bloqueadas por flock. Pastas que não pertencem ao aplicativo e o diretório de dados privados são recusados.

O menu usa `${XDG_DATA_HOME:-~/.local/share}/applications/fgts-guias.desktop`, com ícone SVG e caminho absoluto para o executável. O atalho de área de trabalho é opcional e respeita a pasta localizada retornada por xdg-user-dir. Alguns ambientes exigem marcar o atalho como confiável no gerenciador de arquivos.

Feche o aplicativo antes de atualizar. O instalador verifica processos do FGTS Guias, inclusive versões portáteis. O assistente de instalação não inicia emissão nem abre Chrome.

Para recuperar manualmente uma instalação anterior, feche o app, mova a pasta atual e renomeie a pasta `fgts-guias.previous-*` desejada para o destino original. Os atalhos continuam apontando para o mesmo caminho. Para remover o aplicativo, exclua somente a pasta instalada e os atalhos; dados em FGTSGuias e PDFs ficam preservados.

## Windows

O instalador Inno Setup instala por usuário, sem solicitar administrador, em `%LOCALAPPDATA%\Programs\FGTS Guias`. Inclui menu Iniciar, atalho opcional da área de trabalho e desinstalador. O identificador da instalação permanece estável entre versões.

O app mantém o mutex Local\FGTSGuiasRunning. O instalador recusa substituição com o app aberto e também verifica a janela das versões antigas. Não encerra automaticamente um lote. A desinstalação remove arquivos do programa e atalhos, sem remover o diretório de dados separado ou os PDFs.

Google Chrome e o runtime Microsoft Visual C++ x64 continuam requisitos externos. Certificados e middleware permanecem sob controle do operador. Instaladores e binários ainda não são assinados digitalmente.

## Atualização pelo aplicativo

O botão Atualizações fica no cabeçalho. Ao abrir, consulta uma vez por dia a release estável mais recente do repositório oficial. É possível desativar a consulta automática. Uma consulta manual sempre tenta a rede; falhas são mostradas sem serem confundidas com versão atualizada. Não há consulta, download ou instalação durante um lote ativo, inclusive pausado.

O motor compara versões numericamente, exige instalador da plataforma e arquitetura x64 e aceita somente URLs de assets do repositório oficial. O download usa HTTPS, prazo e tamanho limitados, arquivo temporário exclusivo e SHA-256 informado pelo GitHub ou por checksum publicado. Um arquivo diferente já existente não é substituído; um temporário de outro download não é removido. Só anuncia conclusão após tamanho e hash coincidirem.

Depois do download, o operador fecha o app e executa o instalador. Não há troca silenciosa dos arquivos em uso. Nenhum workspace, CNPJ, documento, cookie ou certificado é enviado ao GitHub; a consulta transmite apenas o acesso normal à API pública e a versão no User-Agent.

## Distribuição

scripts/package.py produz bundle portátil, instalador e respectivos checksums. Linux gera `.tar.gz` e `.run`; Windows gera `.zip` e `-setup.exe` com Inno Setup 6. Os builds são feitos nativamente em cada plataforma. workflow_dispatch valida e gera artifacts sem publicar; tags v* anexadas a uma release draft publicam os pacotes após ambos os builds passarem. A assinatura digital e a atualização totalmente automática ficam fora desta versão.

Referências: [API de releases do GitHub](https://docs.github.com/en/rest/releases/releases), [instalação por usuário no Inno Setup](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm), [especificação de atalhos desktop](https://specifications.freedesktop.org/desktop-entry-spec/latest/).

## Validação da v0.3.0

Os [builds Linux e Windows](https://github.com/JoaoLucasDaSilvaOliveira/fgts-guias/actions/runs/38010256198) passaram antes da publicação. Foram verificados os testes do motor e da interface, a análise Flutter, o protocolo do motor empacotado, a instalação Linux isolada e a instalação, reinstalação e desinstalação Windows isoladas. O atalho Linux também foi executado em uma pasta com espaços, acentos e caracteres especiais. Caminhos com `%`, `=` ou quebras de linha são recusados para evitar atalhos incompatíveis.

Após publicar, a rotina de atualização consultou a API real do GitHub e baixou o instalador Linux da v0.3.0, conferindo tamanho, SHA-256 e reutilização do arquivo íntegro já baixado. Houve uma falha transitória de DNS na primeira tentativa; a rotina mostrou erro de conexão e a repetição concluiu. Nenhuma emissão real foi executada nessa validação de distribuição.
