# Emissão de guias INSS — aprendizagem do fluxo

Fluxo em levantamento com o operador na branch `feat/emissao-inss`. Os passos abaixo foram observados no navegador; a automação INSS ainda não está implementada.

## Sessão do navegador

Toda alternância FGTS ↔ INSS exige encerrar completamente a instância Chrome do app, confirmar o término dos processos e abrir uma instância nova para permitir escolher o certificado novamente. Não reutilizar uma aba, janela ou conexão da instância anterior. Certificado, PIN e CAPTCHA permanecem sob controle do operador. Veja [Chrome e autenticação](chrome.md).

## 1. Abrir o portal da Receita Federal

URL base: https://servicos.receitafederal.gov.br/

Na primeira abertura:

1. No componente de cookies, clicar no botão **Aceitar**.
2. No convite de apresentação do portal, clicar no link **Pular Tutorial**.

Ambos são passos opcionais: o banner e o tutorial podem já ter sido dispensados. Se o controle estiver ausente ou uma tentativa falhar porque o aviso já desapareceu, considerar o passo dispensado e prosseguir. Não pausar o lote somente pela ausência desses avisos. Verificar a tela resultante; falhas reais de carregamento ou avisos ainda bloqueando a página não devem ser ocultados por um tratamento genérico de exceções.

Observação em 13/10/2026: ambos estavam presentes. Após **Aceitar**, o componente de cookies desapareceu. Após **Pular Tutorial**, o convite desapareceu. A página permaneceu na URL base e o botão **Entrar com gov.br** estava disponível. Nenhum login ou emissão foi iniciado nesta etapa.

Preferir seletores semânticos: botão com nome exato `Aceitar` e link com nome exato `Pular Tutorial`. Os índices usados durante a observação não são seletores permanentes para o app.

## 2. Entrar com GOV.BR e reconhecer intervenção

Na página inicial, clicar uma vez no botão **Entrar com gov.br** (nome observado no portal; o operador o descreve como "Entrar com o gov.br"). Aguardar o redirecionamento por até **10 segundos**, prazo definido pelo operador para tolerar latência.

Se um desafio CAPTCHA estiver visível, pausar imediatamente e entregar o navegador ao operador. Se, após 10 segundos, a página não tiver redirecionado, tratar como possível CAPTCHA ou impedimento no acesso e solicitar a verificação do operador. A ausência de redirecionamento é um sinal operacional, não uma confirmação isolada de CAPTCHA: observar a tela para diferenciar desafio, mensagem de erro e espera de carregamento.

Não clicar repetidamente no botão, resolver o desafio ou avançar automaticamente enquanto ele estiver pendente. Quando o operador concluir, observar o redirecionamento e a página resultante antes de seguir.

Observação em 13/10/2026: ao retomar a inspeção, o portal já exibia o componente **Desafio hCaptcha**, com opções de imagens e **Verificar respostas**, mantendo a URL base. Não houve novo clique em login porque o desafio já estava em andamento. Controle entregue ao operador; não foram selecionadas imagens nem submetidas respostas pela automação.

## 3. Solicitar certificado digital no GOV.BR

Após o CAPTCHA, o operador confirmou o redirecionamento para `https://sso.acesso.gov.br/login`, com `client_id=p-servicos.receitafederal.gov.br`. O parâmetro `authorization_id` pertence à tentativa de autenticação e não deve ser fixado na automação.

Na tela de identificação, clicar no botão **Seu certificado digital**, observado com ID `login-certificate`. Não confundir com **Seu certificado digital em nuvem**.

Entregar o controle ao operador para selecionar o certificado no diálogo do navegador/sistema e informar PIN, quando necessário. Não selecionar certificado nem preencher PIN automaticamente. O diálogo externo pode não aparecer na árvore da página; aguardar a confirmação do operador e observar a navegação resultante antes de continuar. Não repetir o clique enquanto a solicitação estiver pendente.

Também pode surgir CAPTCHA nesta etapa do GOV.BR. Após solicitar o certificado, manter o controle com o operador durante seleção, PIN e desafios. A automação só pode retomar quando a página retornar a **`https://servicos.receitafederal.gov.br/`**. Não retomar por um prazo fixo, pelo desaparecimento do seletor de certificados ou apenas pela confirmação verbal enquanto ainda estiver no GOV.BR. Se houver desafio visível após o retorno, continuar aguardando o operador. O retorno deve pertencer a esta tentativa de login; a mesma URL antes de iniciar a autenticação não indica que ela foi concluída.

Observação em 13/10/2026: o clique foi executado e o botão passou a desabilitado; a página permaneceu no login GOV.BR. A seleção do certificado ficou a cargo do operador. O estado desabilitado confirma a solicitação em andamento, não a conclusão da autenticação nem a abertura do diálogo externo.

## 4. Preencher empresa e tipo de representação

Após retornar ao portal autenticado, clicar no botão do usuário no cabeçalho, observado com ID `avatar-dropdown-trigger`. Esse botão abre a sidebar com a seção **Representar**.

Preencher o CNPJ da empresa no campo **Digite o CPF ou CNPJ**, observado com ID `input-representar-cpfcnpj`. Usar o CNPJ da linha do lote, sem fixar dados reais no código ou nos exemplos públicos.

Escolher o perfil de representação conforme o mesmo critério de identidade do FGTS:

- Se o CNPJ da empresa for igual ao CNPJ do escritório configurado no app, escolher **Representante no CNPJ**.
- Para outras empresas, escolher **Procurador**.

Comparar CNPJs pelos dígitos, independentemente da máscara. A opção **Agente Público**, também presente, não faz parte desse fluxo.

O seletor é um combobox pesquisável. Na interação observada, clicar no campo de texto somente focou o controle e mostrou a validação de perfil obrigatório; clicar na seta expandiu a lista. Selecionar a opção e verificar o nome escolhido antes de prosseguir. Seu ID aparenta ser gerado dinamicamente: não fixá-lo na implementação.

Observação em 13/10/2026: o CNPJ informado pelo operador foi preenchido e **Procurador** foi selecionado. O botão **Representar** ficou habilitado. Ainda não foi clicado; preencher o formulário não confirma que a empresa já está representada.

## 5. Confirmar a representação

Com CNPJ e perfil conferidos, clicar no botão **Representar** do formulário, distinguindo-o do controle que expande a seção com o mesmo texto. Aguardar o processamento sem repetir o clique.

Essa ação também pode abrir CAPTCHA, mesmo com o usuário já autenticado. Se surgir, pausar e entregar o controle ao operador. Nesta etapa a URL pode continuar na base da Receita tanto durante o desafio quanto após a representação; não usar somente a URL como confirmação de sucesso. Após o operador resolver, observar a identificação da empresa representada e eventuais erros antes de acessar o serviço.

Observação em 13/10/2026: **Representar** foi clicado. O portal exibiu **Carregando** e depois um **Desafio hCaptcha**. A representação ainda não foi confirmada; o desafio ficou sob controle do operador.

## 6. Conferir a representação atual e fechar a sidebar

A representação concluída aparece na seção **Representação Atual**, contendo o tipo de representação, nome da empresa e CNPJ. Conferir que o CNPJ coincide com o da linha do lote e que o perfil corresponde à escolha esperada. Não confundir esse bloco com **Representações Recentes**, que é histórico e não confirma o contexto ativo. Em caso de ausência ou divergência, não prosseguir para emissão; avisar o operador.

Após confirmar, fechar a sidebar pelo **X**, observado como botão **Fechar Menu**. Não clicar em **Encerrar representação** ou **Sair**: esses controles alteram a sessão, enquanto o X somente fecha o painel.

Observação em 13/10/2026: **Representação Atual** mostrou o perfil **Procurador de:** e o CNPJ esperado para a empresa informada. O botão **Fechar Menu** foi clicado; a sidebar desapareceu e o cabeçalho continuou mostrando a empresa representada. Nenhuma guia foi emitida nesta etapa.

## 7. Acessar DCTFWeb pela aba Negócios

Com a representação confirmada e a sidebar fechada, selecionar a aba **Negócios**. Conferir que ela ficou selecionada e localizar o link/card **DCTFWeb**. **Abrir DCTFWeb em nova aba**, no mesmo navegador/contexto autenticado, preservando a aba do portal da Receita Federal. Preparar a captura da nova aba antes da abertura e acompanhar os redirecionamentos nela. Manter referências separadas para a aba RFB e a aba DCTFWeb.

Na observação, o link apontava para `https://cav.receita.fazenda.gov.br/autenticacao/login/index/10015`. Clicar no serviço e acompanhar a navegação efetiva, preservando o contexto de representação; não assumir que o destino final seja igual ao endereço do card.

Observação em 13/10/2026: **Negócios** foi selecionado e **DCTFWeb** foi clicado. A navegação chegou a `https://dctfweb.cav.receita.fazenda.gov.br/AplicacoesWeb/DCTFWeb/Paginas/Captcha.aspx`. A tela exibia a caixa hCaptcha **Sou humano** e o controle **Prosseguir**. Esse é outro ponto de intervenção do operador, independente dos desafios anteriores. Nenhum controle do CAPTCHA nem **Prosseguir** foi acionado nesta etapa. Nesta demonstração o serviço abriu na mesma aba; o operador corrigiu posteriormente o fluxo esperado para a automação: abrir em nova aba, conforme a regra acima.

## 8. Aguardar a verificação hCaptcha e prosseguir

O operador realiza a interação com **Sou humano** e resolve eventual desafio adicional. A automação não simula trajetórias, curvas de velocidade ou irregularidades humanas para evitar a detecção do CAPTCHA.

O operador definiu uma janela de **7 a 10 segundos** após a interação para observar se a verificação foi aceita e **Prosseguir** ficou disponível. Usar 10 segundos como limite de observação; se houver desafio visível, continuar com o controle do operador imediatamente. Não repetir a interação nem concluir que a verificação foi aceita apenas porque passou o prazo.

Após a verificação aceita e o controle **Prosseguir** disponível, clicar uma vez e conferir a página resultante. A aparência ou disponibilidade isolada de **Prosseguir** não é prova suficiente: na primeira inspeção ele já aparecia na árvore como link, antes da verificação.

Observação em 13/10/2026: após a intervenção do operador, a caixa do hCaptcha estava marcada e sua descrição informava **Você está verificado**. **Prosseguir** foi clicado uma vez, no link com ID `ctl00_cphConteudo_btnProsseguir`. A primeira observação ainda mostrou a tela anterior; a observação seguinte confirmou o redirecionamento para `https://dctfweb.cav.receita.fazenda.gov.br/AplicacoesWeb/DCTFWeb/Paginas/ListaDctfs.aspx`, com **Filtros** e **Relação de Declarações**. Nenhum filtro foi alterado e nenhuma declaração ou emissão foi acionada.

O ponto reservado no código para integrar essa etapa está em `engine/fgts_guias/inss.py`, marcado como `TODO(INSS, operador)`. O módulo ainda não está conectado ao lote do aplicativo.

## 9. Conferir Saldo a Pagar e abrir a declaração

Em **Relação de Declarações**, localizar a declaração correspondente à competência pretendida. Comparar o valor da coluna **Saldo a Pagar** com o INSS esperado para a empresa na tabela do app, em centavos inteiros. Não usar a coluna **Débito Apurado** nessa conferência: ela pode ter valor diferente do saldo.

Se houver divergência ou ambiguidade na seleção da declaração, interromper e avisar o operador. Não escolher automaticamente outra linha apenas porque seu valor coincide. O levantamento das regras dos filtros, categorias e situações ainda está pendente.

Com a conferência aprovada, clicar no ícone de olho da mesma linha, identificado como **Visualizar**. Não confundir com **Retificar**, **Visualizar Recibo** ou **Visualizar Extrato de Processamento**. O ID observado termina em `_lbkVisualizarDctf`; o índice da linha não deve ser fixado na implementação.

Observação em 13/10/2026: o saldo foi lido na página e o operador confirmou que coincidia com a planilha do app. Essa aprovação veio do operador; não houve comparação automática com os dados do app nesta etapa. **Visualizar** foi clicado e abriu `https://dctfweb.cav.receita.fazenda.gov.br/AplicacoesWeb/DCTFWeb/Paginas/ResumoVinculacoes/VinculacoesCompleta.aspx`, mostrando CNPJ, competência, categoria, débitos, créditos vinculados e saldo. Nenhuma emissão, retificação ou pagamento foi acionado.

## 10. Emitir DARF e acompanhar o download

No detalhamento, após conferir empresa, competência e saldo selecionado, clicar em **Emitir DARF**, observado como link com ID `LinkEmitirDARFIntegral`. Não confundir com **Pagar online DARF**, que não faz parte da emissão/download.

Registrar a intenção antes do clique e começar a observar o download antes de acionar a emissão. Não repetir o clique durante **Aguarde um instante...** ou diante de resultado incerto. A mensagem de sucesso sozinha não confirma que um PDF foi salvo: acompanhar a conclusão do download e depois validar o arquivo antes de marcar a empresa como concluída no app. A validação do PDF INSS e a regra de destino/nome ainda serão implementadas.

Observação em 13/10/2026: **Emitir DARF** foi clicado uma vez. O portal mostrou **Aguarde um instante...** e depois **Guia gerada com sucesso em formato PDF.**, com botão **OK**. O evento de download concluiu e forneceu um arquivo PDF na pasta Downloads do operador, com nome gerado pelo portal. Nenhum pagamento foi realizado. O PDF não foi inspecionado nem marcado como validado pelo app nesta etapa.

## 11. Fechar a aba DCTFWeb e retornar à Receita

Após confirmar a conclusão do download e, no app, validar e salvar o PDF no destino, fechar somente a aba DCTFWeb aberta para essa empresa. Retornar à aba RFB preservada em `https://servicos.receitafederal.gov.br/` e observar o contexto de representação antes de iniciar a próxima empresa. A aba RFB permanece aberta durante o lote INSS. Não encerrar o navegador a cada empresa; o reinício completo é obrigatório na alternância FGTS ↔ INSS.

Se o download estiver pendente ou seu resultado for incerto, não fechar a aba nem iniciar outra empresa automaticamente. Preservar o contexto para recuperação e intervenção.

Observação em 13/10/2026: como a demonstração usou uma única aba, o operador autorizou navegar novamente até a URL base. A navegação foi executada e o portal mostrou a mesma empresa representada no cabeçalho. Esse retorno pela URL foi uma correção da demonstração; o fluxo futuro usa duas abas e fecha a do serviço ao concluir.

## Validação do ciclo assistido

Em 13/10/2026, um segundo cliente indicado pelo operador percorreu o ciclo completo com resultado **GREEN para a navegação assistida**:

- Troca de representação com CNPJ e perfil conferidos; CAPTCHA resolvido pelo operador.
- DCTFWeb aberta em nova aba por abertura do link com botão do meio, mantendo a RFB aberta.
- Verificação de entrada resolvida pelo operador, seguida de **Prosseguir**.
- Competência e saldo da listagem confirmados pelo operador antes da emissão.
- Detalhamento com identidade, competência e saldo iguais aos dados aprovados.
- **Emitir DARF** acionado uma vez; sucesso no portal e conclusão do download confirmados.
- PDF inspecionado por texto e visualmente: CNPJ, razão social, competência e total conferidos; vencimento e número do documento identificados.
- Somente a aba DCTFWeb fechada após a conferência; retorno à RFB preservada com a representação correta.

Este resultado valida o ciclo demonstrado, não uma automação já implementada nem todos os cenários do portal. O valor esperado veio da confirmação do operador; ainda não houve leitura automática da tabela do app. A implementação deve preservar os pontos de intervenção, a validação do PDF e o controle de abas. Não publicar os dados ou documentos reais desse teste no repositório.

## Ritmo de navegação e desafios

O operador levantou a hipótese de que cliques rápidos e precisos estejam contribuindo para os CAPTCHAs. A causa não foi confirmada nesta observação. Não registrar essa hipótese como diagnóstico nem prometer que mudanças no ponteiro eliminariam desafios.

A implementação deve aguardar os estados reais de carregamento, disponibilidade dos controles e resultado das ações, evitando cliques duplicados e novas solicitações enquanto a anterior estiver pendente. O prazo de 10 segundos para o redirecionamento inicial permanece um critério de intervenção, não um motivo para repetir o login. Não adotar trajetórias ou velocidades aleatórias para disfarçar a automação ou contornar a detecção do portal. CAPTCHA permanece com o operador.

## Próximas etapas

Aguardar a orientação do operador para destino/nome dos PDFs, retorno e próxima empresa. As regras de filtragem da listagem e a validação do PDF INSS ainda precisam ser definidas.
