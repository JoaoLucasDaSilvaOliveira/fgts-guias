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
