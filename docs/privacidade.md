# Dados e publicação

Repositório público contém somente código, documentação e template vazio. Não publicar documentos usados no treinamento, nomes/CNPJs reais, valores reais, PDFs, planilhas preenchidas, certificados, PIN, cookies, perfil Chrome ou banco local.

Dados ficam no diretório do usuário calculado por platformdirs (FGTSGuias). PDFs ficam na pasta escolhida. Histórico exibido na interface é local. O app não coleta telemetria; o Chrome acessa os portais oficiais para operar. Utiliza somente o perfil persistente do Chrome do app e um cache local de downloads. Veja [Chrome](chrome.md). O perfil persiste a sessão GOV.BR: proteger a conta do sistema e encerrar o Chrome para trocar certificado. Remover os dados locais encerra a persistência do app, mas não exclui PDFs do destino escolhido.

Exportações contêm os dados do operador e devem ser tratadas como documentos privados. Não versionar dist preenchido nem capturas de sessão. A validação de PDF é conservadora e não substitui a conferência do operador.

A consulta de atualizações acessa a API pública e os assets do repositório oficial no GitHub. Envia a versão no User-Agent; não envia empresas, dados do lote, documentos, certificados ou cookies. Pode ser desativada na interface. Instaladores não removem dados privados nem PDFs ao atualizar ou desinstalar.
