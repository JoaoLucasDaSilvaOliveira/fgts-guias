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
