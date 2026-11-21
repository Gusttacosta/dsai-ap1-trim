# Custo das sessões com agente

Tokens extraídos do campo `usage` das transcrições do Claude Code (mensagens do agente principal + subagentes, sem duplicar respostas em streaming). Horários em America/Sao_Paulo.

| Sessão | Início | Fim | Modelo | Input | Output | Cache (escrita) | Cache (leitura) | Total |
|---|---|---|---|---:|---:|---:|---:|---:|
| `2026-11-08-1934-claudecode.jsonl` | 08/11 19:34 | 20:10 | claude-opus-5-5 | 36 | 7,403 | 41,646 | 815,529 | 864,614 |
| `2026-11-08-2132-claudecode.jsonl` | 08/11 21:32 | 22:19 | claude-opus-5-5 | 102 | 28,120 | 66,956 | 2,956,174 | 3,051,352 |
| `2026-11-10-1933-claudecode.jsonl` | 10/11 19:33 | 20:41 | claude-haiku-5-5, claude-opus-5-5 | 106 | 57,114 | 100,742 | 3,655,302 | 3,813,264 |
| `2026-11-14-2102-claudecode.jsonl` | 14/11 21:02 | 21:52 | claude-opus-5-5 | 102 | 26,058 | 56,050 | 2,827,373 | 2,909,583 |
| `2026-11-16-2027-claudecode.jsonl` | 16/11 20:27 | 20:55 | claude-opus-5-5 | 80 | 35,207 | 89,237 | 3,318,596 | 3,443,120 |
| `2026-11-16-2059-claudecode.jsonl` | 16/11 20:59 | 21:11 | claude-opus-5-5 | 34 | 6,711 | 30,618 | 723,525 | 760,888 |
| `2026-11-16-2155-claudecode.jsonl` | 16/11 21:55 | 23:07 | claude-opus-5-5 | 50 | 20,297 | 77,523 | 1,448,697 | 1,546,567 |
| `2026-11-18-2025-claudecode.jsonl` | 18/11 20:25 | 20:52 | claude-opus-5-5 | 142 | 56,092 | 117,730 | 6,326,439 | 6,500,403 |
| `2026-11-18-2052-claudecode.jsonl` | 18/11 20:52 | 21:52 | claude-opus-5-5 | 164 | 56,175 | 69,974 | 12,434,366 | 12,560,679 |
| `2026-11-19-0143-claudecode.jsonl` | 19/11 01:43 | 01:51 | claude-opus-5-5 | 34 | 19,645 | 61,665 | 1,063,979 | 1,145,323 |
| `2026-11-19-2011-claudecode.jsonl` | 19/11 20:11 | 20:24 | claude-opus-5-5 | 82 | 29,595 | 93,482 | 2,633,167 | 2,756,326 |
| `2026-11-19-2024-claudecode.jsonl` | 19/11 20:24 | 20:32 | claude-opus-5-5 | 52 | 15,130 | 24,919 | 3,048,522 | 3,088,623 |
| `2026-11-19-2032-claudecode.jsonl` | 19/11 20:32 | 21:00 | claude-opus-5-5 | 96 | 27,692 | 34,250 | 6,553,864 | 6,615,902 |
| `2026-11-19-2100-claudecode.jsonl` | 19/11 21:00 | 21:21 | claude-opus-5-5 | 44 | 16,997 | 39,660 | 4,100,879 | 4,157,580 |
| `2026-11-19-2121-claudecode.jsonl` | 19/11 21:21 | 21:31 | claude-opus-5-5 | 32 | 9,051 | 10,890 | 2,997,749 | 3,017,722 |
| `2026-11-21-1609-claudecode.jsonl` | 21/11 16:09 | 16:48 | claude-opus-5-5 | 142 | 41,169 | 81,416 | 4,617,099 | 4,739,826 |
| `2026-11-21-1648-claudecode.jsonl` | 21/11 16:48 | 17:19 | claude-opus-5-5 | 84 | 36,078 | 54,462 | 4,840,244 | 4,930,868 |
| **Total** | | | | **1,382** | **488,534** | **1,051,220** | **64,361,504** | **65,902,640** |



Segredos mascarados na exportação: tokens JWT locais e e-mail pessoal (substituídos por `[jwt-removido]` / `[email-removido]`). Nenhuma outra alteração foi feita no texto. Nas sessões de 08/11 e 10/11, os commits foram reescritos depois com o e-mail noreply do GitHub (`<id>+Severino-Sobrinho@users.noreply.github.com`), que é público e por isso aparece nas transcrições sem máscara.

Sessões de 16/11: exportadas pelo terminal, com o mascaramento feito pelo `jq` dentro dos textos do JSON, o que mantém o arquivo válido. A senha do banco local também foi mascarada (`[senha-removida]`). Nessa data, as tentativas de pedir a exportação ao próprio agente foram bloqueadas pelo filtro de segurança do modelo (`reasoning_extraction`), inclusive com o Sonnet, que por isso não registrou consumo.

Sessões de 14/11 e 18/11: o mascaramento foi feito nas strings do JSON já interpretado, e o arquivo continua válido. Foram mascarados os e-mails pessoais (do Severino e de terceiros que apareceram no histórico do git), inclusive quando escritos como padrão de `sed`/`grep`, e também a parte antes do `@`. O e-mail noreply do GitHub, os e-mails fictícios de teste (`@trim.com`, `@teste.com`) e o login público `Severino-Sobrinho` foram mantidos. A transcrição de 18/11 foi exportada durante a sessão, então os minutos finais (o commit das sessões) não estão no arquivo nem na contagem.

Sessão de 18/11 a partir das 20:52 (PR #25): é a continuação da sessão de 18/11 20:25, separada pelo `timestamp` (entradas a partir de `2026-11-18T23:52:00Z`), para não alterar o arquivo que já está na `main`. Mesmo mascaramento das sessões de 14/11 e 18/11; como nesta parte não aparece nenhum e-mail completo, os prefixos dos e-mails pessoais foram mascarados à parte. A exportação vai até 21:52 e não inclui o commit desta sessão.

Sessão de 19/11 às 20:11 (issue #2): exportada pelo agente durante a sessão, com o mesmo mascaramento das sessões de 14/11 e 18/11 (e-mail pessoal e senhas em URLs do PostgreSQL, inclusive a da CI). A exportação vai até 20:24 e não inclui o commit desta sessão.

Sessão de 19/11 a partir das 20:24 (issue #26): é a continuação da sessão das 20:11, separada pelo `timestamp` (entradas depois de `2026-11-19T23:24:54.027Z`), porque a primeira parte foi para o PR da #2. Mesmo mascaramento, agora também com o prefixo do e-mail pessoal escrito pela metade em padrões de busca. A linha da sessão das 20:11 também está aqui, igual à do PR da #2, para o total ficar certo depois dos dois merges. A exportação vai até 20:32 e não inclui o commit desta sessão.

Sessão de 19/11 a partir das 20:32 (merges dos PRs #28 e #29, issue #30): terceira parte da mesma sessão, separada pelo `timestamp` (entradas depois de `2026-11-19T23:32:53.223Z`). Mesmo mascaramento, agora também com o sobrenome do e-mail pessoal, que aparecia sozinho em padrões de busca. A exportação vai até 21:00 e não inclui o commit desta sessão.

Sessão de 19/11 a partir das 21:00 (README do Windows): quarta parte da mesma sessão, separada pelo `timestamp` (entradas depois de `2026-11-20T00:00:16.570Z`). Mesmo mascaramento; as senhas de exemplo do README (`senha-de-exemplo`) também saíram mascaradas nas URLs do PostgreSQL. A linha da parte das 20:32 também está aqui, igual à do PR #31, para o total ficar certo depois dos dois merges. A exportação vai até 21:21 e não inclui o commit desta sessão.

Sessão de 19/11 a partir das 21:21 (fechamento do dia): quinta e última parte da mesma sessão, separada pelo `timestamp` (entradas depois de `2026-11-20T00:21:02.255Z`), com o rerun da CI do PR #31 e o merge da `main` no PR #32. Mesmo mascaramento. A exportação vai até 21:31 e não inclui o commit desta parte nem o merge do PR #32.

Sessão de 21/11 a partir das 16:09 (retrato das métricas e issue #33): os tokens foram somados do `message.usage` das respostas do agente na transcrição, uma vez por mensagem, até 19:48:56Z (16:48). Ficaram de fora os cerca de 10 mil tokens do subagente que leu o slide da aula 09. A exportação foi feita com um script que mantém só as mensagens `user`/`assistant` até o corte, descarta os blocos de raciocínio (`thinking`) e mascara com `***` e-mails, senhas, tokens e senhas em URLs. O prefixo do e-mail pessoal, que aparece sozinho, também foi mascarado. Com o corte em 19:48:56Z, foram 50 blocos de raciocínio descartados e 57 máscaras. O `gitleaks` (com o `.gitleaks.toml`) não encontrou nada no arquivo exportado. A exportação não inclui o commit desta sessão.

Sessão de 21/11 a partir das 16:48 (testes de integração do auth, #3, e issue #35): segunda parte da mesma sessão, separada pelo `timestamp` (entradas depois de `2026-11-21T19:48:56.875Z`). A exportação e o mascaramento foram iguais aos da parte das 16:09, e os tokens foram somados do mesmo jeito. Nesta parte, nenhum e-mail ficou sem máscara: os textos com `@` que sobraram são decoradores de código (`@pytest.fixture`, `@router.post`). O `gitleaks` não encontrou nada. A linha da parte das 16:09 também está aqui, igual à do PR #34, para o total ficar certo depois dos dois merges. A exportação vai até 17:19 e não inclui o commit desta parte.
