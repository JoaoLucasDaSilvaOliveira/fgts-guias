# Conhecimento observado no treinamento

Estas notas descrevem o fluxo ensinado pelo operador. Não são um parecer sobre regras tributárias. O portal pode mudar; controles desconhecidos interrompem a automação.

## Entrada e perfil

1. Abrir https://fgtsdigital.sistema.gov.br/ → `/portal/login` → **Entrar com GOV.BR**.
2. Nunca autorizar localização. **Seu certificado digital** abre seleção nativa: operador escolhe certificado e informa PIN quando necessário. CAPTCHA sempre fica com o operador.
3. Autenticação pode demorar. Reabrir a URL base costuma reutilizar a sessão. Para trocar certificado, fechar todo o Chrome controlado; fechar somente a aba não basta, conforme observado pelo operador.
4. Aceitar cookies. Em `/portal/escolhaPerfil`, **Definir Perfil**: **Meu Perfil** quando o CNPJ da empresa coincide com o escritório/titular configurado; **Procurador** para as demais. Informar empregador e confirmar. Validar titular e empregador.
5. `/portal/servicos`: **GESTÃO DE GUIAS** → `/portal/servicos/gestao-guias` → **EMISSÃO DE GUIA PARAMETRIZADA**.
6. Trabalho principal: https://fgtsdigital.sistema.gov.br/cobranca/#/gestao-guias/emissao-guia-parametrizada.

## Etapa 1 — FGTS

Competências Inicial e Final vêm do operador, em MM/AAAA. Tipo de débito: somente **Mensal**. Desmarcar **Sem guia emitida** e **Pesquisar**. Essa opção marcada esconde todos ou parte dos débitos com guia emitida; vale também para consignados. Sempre repetir a busca desmarcada antes de declarar ausência ou divergência.

O símbolo azul, com texto **Existem guias aguardando pagamento para este débito**, indica guia pendente, não dívida paga nem autorização para duplicar emissão. Reimprimir automaticamente uma guia única e validar o PDF; ambiguidades pausam o lote.

Checkbox do cabeçalho seleciona todos os débitos encontrados (inclusive além da página visível). **Adicionar à guia** exibe **Resumo dos débitos adicionados à guia**. Conferir **Total FGTS** contra FGTS MENSAL importado. Nesta etapa nova, **Total da Guia** deve ser o FGTS, sem consignados. Só então **Avançar**.

Mensagem **Há um ou mais débitos já adicionados à guia anteriormente.** significa progresso persistido pelo portal. Continuar apenas após conferir empresa, período e valores. Pode avançar pelas etapas 1/2 quando o resumo já bate. Lixeira descarta o progresso; não utilizá-la automaticamente.

## Etapa 2 — consignados

O portal normalmente integra os consignados automaticamente. Não adicionar novamente sem verificar o resumo. **Não há débitos de consignados** é esperado apenas quando a entrada tem consignado zero.

Comparar **Total FGTS**, **Total dos Consignados**, **Total da Guia** com FGTS MENSAL, CONSIGNADO e TOTAL. Se incompleto, desmarcar **Sem guia emitida** e repetir **Pesquisar**. Persistindo **Nenhum item encontrado** ou divergência, pausar o lote. Revisar Extrato Mensal (`Valor do FGTS:` sob `FGTS, PIS e ISS`) e relatório de consignados (linha **Total**, somente **Parcela paga**). Se transcrição estiver correta, operador investiga o sistema de folha. Importação atual recebe planilhas; não extrai esses PDFs automaticamente.

## Etapa 3 — vencimento

Manter vencimento válido sugerido pelo portal. O operador descreveu vencimento mensal normalmente próximo ao dia 20, antecipado em dias não úteis. Não calcular feriados por suposição. Para vencidos, quando o padrão é hoje, propor amanhã e conferir novamente os totais recalculados; encargos diferentes do TOTAL interrompem o lote.

## Etapa 4 — emissão e arquivo

Conferir total final com TOTAL. Registrar intenção local antes de **Emitir Guia**. Capturar download iniciado por esse clique, não os PDFs de detalhamento. Registrar número da guia. Salvar primeiro temporário no destino escolhido; conferir CNPJ, competências, vencimento, número e total no PDF. Nome final: EMPRESA.pdf com caracteres incompatíveis substituídos. Nunca sobrescrever outro documento. Guia emitida não significa PDF salvo.

Timeout ou resultado incerto: recuperar, nunca emitir outra automaticamente. Número emitido pode permitir reimpressão. **CONSULTA DE GUIAS** existe para recuperação; sua navegação detalhada não foi demonstrada, a reimpressão pelo indicador azul dos débitos é automática quando existe uma única guia. A consulta continua como alternativa manual, usando **Recuperar PDF**. PDF com formato não reconhecido permanece pendente.

Após concluir: logo **FGTS Digital** retorna `/portal/servicos`; **Trocar Perfil** começa a próxima empresa.

## Diferenças entre a planilha de treinamento e o app

A planilha original usava B (nome), L (FGTS), N (consignado) e P (total). O app usa cabeçalhos próprios, incluindo CNPJ obrigatório, e não depende de planilha Google ou cadastro real. Empresas sem funcionários não são automaticamente tratadas como zero por ausência em relatório; os dados importados são a referência explícita.

## Controles observados no teste de 09/10/2026

O titular aparece no nome acessível do botão de usuário. Em escolhaPerfil, aguardar o diálogo **Definir Perfil**; em serviços, abrir **Trocar Perfil**. Escopar controles pelo diálogo correspondente e selecionar opções pelo papel `option`, pois textos iguais aparecem em outros componentes. Checkboxes customizados têm rótulos sobre o input: clicar no rótulo associado e confirmar o estado.

O indicador azul contém o atributo `tooltip` com o texto de guias aguardando pagamento. Seu clique abre **Guias Aguardando Pagamento**, com números clicáveis e tooltip **Reimprimir guia**. A reimpressão foi integrada ao motor e validada pelo app: clicar no indicador, exigir um único número, capturar o download completo, validar o PDF e salvar. Havendo número registrado, exigir que coincida. O PDF reimpresso pode mostrar apenas a raiz de oito dígitos do CNPJ no campo de identificação do empregador.

## Emissão nova e atualização das etapas

As checkboxes da tabela usam rótulos sobre o input, inclusive **Selecionar todos**. Os resumos nas etapas 1 e 2 usam **Total Consignados**, e a etapa 3 usa **Total Consignado**. O valor monetário está no próximo elemento irmão após eventuais quebras de linha; esperar que esse elemento contenha dinheiro antes de ler. A última etapa usa tabelas com papéis acessíveis columnheader/row/cell e uma linha Total para FGTS e, quando presente, consignado. Somar somente os totais identificados, comparar com a entrada e pausar em estrutura desconhecida.

Esperar a etapa ativa do breadcrumb e o indicador de carregamento. A troca de perfil mantém a URL de serviços: esperar fechar o diálogo e aparecer o CNPJ esperado, pois esperar somente a URL pode ler o empregador anterior. Resumo persistido também pode existir sem o aviso textual; conferir antes de tentar selecionar/adicionar novamente.

O PDF emitido fornece o número no campo **Identificador**; não depender da exposição desse número na tela. Se não houver download confirmado após emissão, executar a recuperação da guia existente, sem novo clique em Emitir Guia. O PDF sem consignado declara explicitamente **Não há informações de recolhimentos do Consignado**: aceitar ausência do total de consignado somente com essa mensagem e valor esperado zero.
