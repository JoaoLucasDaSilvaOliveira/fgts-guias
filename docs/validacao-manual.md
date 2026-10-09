# Próxima etapa: validação pelo operador

Não foram executados testes, builds nem emissão real nesta implementação, a pedido do usuário. O código ainda não está aprovado para uso operacional. Não confundir implementação multiplataforma com execução comprovada nos três sistemas.

1. Seguir README, abrir janela e conferir redimensionamento, rolagem, tabela e pasta.
2. Salvar template CSV/XLSX, preencher dados fictícios, importar/exportar. Conferir zeros iniciais do CNPJ, acentos, decimal com vírgula, entradas inválidas e cabeçalhos.
3. Fechar/reabrir app e conferir persistência de configuração e tabela.
4. Conferir que Chrome ausente bloqueia o início; botão não opera outro navegador.
5. Conferir seleção de empresas, pausa, correção, retomada, ignorar e encerramento.
6. Depois do GREEN da interface, autorizar uma empresa real. Conferir seletores atuais, certificado A1/A3, CAPTCHA, perfil e competência. Portal alterado deve pausar, não adivinhar.
7. Validar resumos novos e progresso salvo, consignado zero e positivo, débitos escondidos e guias pendentes.
8. Validar vencimento, divergência e encargos. Não autorizar emissão com valor diferente.
9. Validar PDF salvo, número, nome, pasta, colisão, download interrompido e recuperação sem nova emissão.
10. Repetir nos sistemas pretendidos antes de distribuir binários.

Somente após a validação manual, definir testes automatizados úteis para regras financeiras, protocolo e recuperação. Automação real não deve rodar em CI.

## Correções após o primeiro teste de interface

Conferir o histórico expandido sem aviso de ListTile; campos com controllers e filtros monetários; calendário pt-BR que grava MM/AAAA; máscara de CNPJ no escritório, tabela, colagem e importação. Conferir dígitos/centavos e edição no meio do texto.

Experimentar primeiro **Abrir / conectar Chrome**, concluir o login e então iniciar o lote. Conferir que CAPTCHA resolvido e autenticação pendente não são confundidos. Validar os dois modos Chrome, downloads e desconexão do modo externo preservando a janela. Não houve teste real do GOV.BR nesta correção.

Nesta correção, foram feitas somente análise estática Flutter e leitura de sintaxe Python, sem executar testes, build ou emissão. A validação visual e o login GOV.BR permanecem com o operador.

## Correção do overflow no seletor de Chrome

A pedido do operador, o app foi aberto no Linux e o terminal mostrou `RenderFlex overflowed by 30 pixels on the right` no DropdownButtonFormField. O seletor agora expande seu conteúdo na largura disponível e limita o texto a uma linha com reticências. Após recompilar e reabrir o app, o overflow não apareceu no terminal. A inicialização ainda apresenta um aviso nativo ATK (`atk_socket_embed`), sem exceção de layout Dart observada. Não foi feita emissão de guia.

## Última rodada de UI

Retirada a escolha de sessão/porta e a conexão ao Chrome externo. Conferir **Abrir Chrome** e fechamento da janela/aba usada: lote ativo ou pausado deve encerrar imediatamente, sem avançar para outra empresa nem abrir nova janela. Conferir o diário após fechamento no intervalo entre solicitação da emissão e download, sem reemitir. Identificação do titular está adiada em [pendências](pendencias.md).

## Teste autorizado no Linux — 09/10/2026

Login concluído pelo operador. O teste pelo app confirmou leitura do titular, seleção de Procurador, empregador, competência e filtros (somente Mensal, Sem guia emitida desmarcado). Corrigidos seletores de opções e cliques em checkboxes customizados por seus rótulos. Ao encontrar guias aguardando pagamento, o app pausou antes de adicionar débitos ou emitir.

Uma guia existente foi reimpressa pela interface do portal, conferida e enviada ao comando de recuperação do motor usado pelo app. Validado PDF no destino escolhido, nome da empresa, número, competência, vencimento e total, registro salvo e retomada sem reemissão. O PDF oficial observado informa a raiz do CNPJ no campo CPF/CNPJ do Empregador; o validador aceita a raiz exata ou o CNPJ completo nesse campo e rejeitou outra raiz.

A emissão nova (etapas 2–4, clique Emitir Guia e captura automática do download) não foi executada: a empresa escolhida já tinha guia pendente. Não considerar o fluxo completo aprovado. Dados reais e PDF permaneceram locais. O terminal não apresentou exceções Dart ou overflow nesta rodada; permaneceu o aviso nativo ATK na inicialização.

## Correção do teste de salvamento automático

O teste anterior usou reimpressão manual e comando Recuperar PDF, portanto não comprovava a automação do download. A reimpressão pelo indicador azul foi integrada ao motor. No teste seguinte, preservou-se o PDF anterior como backup, deixando ausente o destino registrado; iniciar o lote no app percorreu pesquisa, indicador, diálogo, reimpressão, eventos de download Chrome, validação e gravação sozinho. Conferidos arquivo novo no destino, diário salvo e lote encerrado, sem comandos manuais de download/recuperação. Divergências de FGTS e consignado (mantendo a soma), total e CNPJ foram rejeitadas pelo validador. A emissão de guia nova continua não exercitada.

Na repetição, corrigida a espera pelo campo de competência após navegação. A execução final terminou automaticamente com PDF validado no destino e lote encerrado.

## Lote autorizado de cinco empresas — 09/10/2026

Lidos os cinco registros visíveis a partir da linha indicada pelo operador, preservando filtros e valores da planilha. Dados carregados somente no workspace local do app; configuração anterior preservada localmente. Login concluído pelo operador. Corrigidos durante o teste: clique no rótulo de Selecionar todos; leitura e espera dos valores dos resumos; reconhecimento do resumo persistido sem aviso; espera das etapas ativas; leitura da tabela final pelos papéis acessíveis; espera da atualização do CNPJ após troca de perfil; número da guia extraído do campo Identificador do PDF; ausência explícita de consignado quando esperado zero.

Resultado: cinco novas guias emitidas pelo app (quatro sem consignado, uma com consignado), PDFs salvos automaticamente na pasta configurada com os nomes das empresas, diário salvo para cada empresa e lote encerrado sem pendências. Validação final dos cinco PDFs confirmou empregador, competência, vencimento, número, FGTS, consignado e total. As demoras/downloads iniciais sem confirmação acionaram reimpressão da guia existente; essa recuperação também foi automatizada, sem novo clique em Emitir Guia para o mesmo registro. O portal não foi usado para pagamentos.

O teste demandou correções e reinícios durante a primeira parte; depois das correções, as empresas restantes concluíram em sequência sem download manual. O terminal não apresentou exceções Dart ou overflow; permanece o aviso ATK na inicialização. Este resultado comprova o fluxo exercitado no Linux; não aprova todas as exceções, estruturas de PDF, feriados, certificados ou demais plataformas. Nenhum dado real ou documento do lote foi incluído no repositório.


## Segunda rodada de lote e Consulta de Guias

Cinco empresas adicionais foram carregadas por leitura da planilha filtrada, sem editar conteúdo nem filtro. Quatro guias novas foram emitidas, recuperadas automaticamente pela Consulta de Guias após o limite de 5 segundos e salvas/validadas no destino. Foram exercitados consignados positivos e zero. A quinta empresa apresentou **Não há débitos de interesse**; por orientação explícita do operador, registrou-se a ocorrência no diário e prosseguiu-se para a próxima empresa, sem ajustar valores importados. O lote terminou com quatro salvas e uma ignorada. Ao reiniciar para carregar a correção, as guias já salvas foram reutilizadas sem nova emissão. Terminal sem exceções Dart ou overflow; permanece a mensagem nativa ATK conhecida na inicialização.


## Lote final da planilha filtrada

Processadas 17 empresas no intervalo autorizado, excluindo explicitamente uma empresa solicitada pelo operador e preservando o conteúdo/filtro da planilha. Resultado: 16 guias salvas e validadas e uma ocorrência explícita de ausência de débitos registrada no diário, com avanço automático. A última empresa do intervalo foi concluída. Todos os PDFs finais passaram novamente pela conferência de empregador, competência, vencimento, número, FGTS, consignado e total.

O lote revelou três problemas corrigidos: o vencimento precisava ser aguardado até conter uma data completa; a barra de rolagem da tabela precisava compartilhar um controlador explícito com sua área rolável; o Chrome com janela coberta suspendia quadros de renderização e impedia a verificação de estabilidade dos cliques. A sessão CDP da página agora mantém foco emulado conectado. As retomadas reutilizaram PDFs salvos e recuperaram emissão pendente sem repetir Emitir Guia. Após as correções, o restante do lote foi concluído sem exceções Flutter no terminal; permanece a mensagem nativa ATK de inicialização.


## Chrome minimizado e intervenção

Operador confirmou segundo plano com a mesma janela minimizada, em vez de reiniciar entre headless e modo visível. Carregadas cinco empresas visíveis a partir da linha solicitada do novo filtro, preservando a planilha. A primeira guia foi validada e reutilizada pelo diário. Na empresa seguinte, a conferência encontrou uma divergência real de FGTS; o lote pausou, a janela foi restaurada automaticamente e nenhuma emissão foi solicitada para a empresa divergente. Após a retomada pelo operador, o lote avançou e três guias adicionais foram salvas. A última empresa pausou na recuperação porque o vencimento registrado diferia da guia exibida na consulta. O operador pediu ignorá-la; o lote terminou com quatro PDFs validados e uma empresa ignorada. Sua intenção de emissão permaneceu no diário para recuperação futura, sem nova emissão automática. Ao concluir, o Chrome confirmou estado minimizado. Verificada separadamente a rotina de conclusão de autenticação: minimiza antes de liberar a retomada. Análise Flutter sem problemas e terminal sem novas exceções. Compatibilidade de minimização/restauração exercitada no Linux; Windows/macOS ainda exigem validação em suas plataformas.


## Aceitar divergência uma vez

Adicionado botão contextual junto a Retomar, com dados esperados/encontrados, etapa, data e número da guia quando conhecido. Sete testes locais verificam consumo único e auditoria, rejeição de token antigo/entrada alterada, ausência de autorização entre etapas, invalidação por retomada/cancelamento, nova decisão após alteração do portal, integração do comando com a chamada suspensa e impossibilidade de aceitar identidade incorreta no PDF. Flutter analyze sem problemas; app reaberto e terminal sem novas exceções. Nenhuma emissão real foi solicitada para esta implementação; a aceitação pelo operador em uma divergência real ainda requer validação manual.


## Inicialização no Windows — v0.2.0 (09/10/2026)

Testado o pacote distribuído em um computador Windows do operador, por SSH e tarefa temporária na sessão gráfica ativa. Google Chrome instalado foi localizado, o motor congelado respondeu ao bootstrap e o driver Playwright iniciou. Os comandos open_browser e close_browser concluíram com sucesso: a sessão CDP conectou, a janela foi minimizada/restaurada no fluxo de abertura e o navegador foi encerrado pelo motor. O processo do motor terminou com código zero.

O app abriu sua janela FGTS Guias na sessão gráfica, com o motor em execução. Captura local da janela confirmou a interface renderizada, tabela e controles visíveis, sem overflow observado nessa tela. O terminal apresentou somente a informação de inicialização do renderizador Impeller, sem novas exceções. A captura, os dados do operador e as credenciais não foram publicados. Tarefa e scripts temporários foram removidos; o app ficou aberto para o operador.

A tentativa de isolar dados somente por APPDATA/LOCALAPPDATA não altera o diretório nativo retornado por platformdirs no Windows. A abertura final usou o diretório normal do app, sem alterar empresas ou configurações e sem iniciar lote. Não houve login com certificado, CAPTCHA, emissão, download de guias, validação de divergências ou pagamento. Esses fluxos financeiros e a compatibilidade A1/A3 no Windows continuam pendentes de teste autorizado.
