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
| **Total** | | | | **652** | **237,002** | **580,502** | **22,071,635** | **22,889,791** |


Segredos mascarados na exportação: tokens JWT locais e e-mail pessoal (substituídos por `[jwt-removido]` / `[email-removido]`). Nenhuma outra alteração foi feita no texto. Nas sessões de 08/11 e 10/11, os commits foram reescritos depois com o e-mail noreply do GitHub (`<id>+Severino-Sobrinho@users.noreply.github.com`), que é público e por isso aparece nas transcrições sem máscara.

Sessões de 16/11: exportadas pelo terminal, com o mascaramento feito pelo `jq` dentro dos textos do JSON, o que mantém o arquivo válido. A senha do banco local também foi mascarada (`[senha-removida]`). Nessa data, as tentativas de pedir a exportação ao próprio agente foram bloqueadas pelo filtro de segurança do modelo (`reasoning_extraction`), inclusive com o Sonnet, que por isso não registrou consumo.

Sessões de 14/11 e 18/11: o mascaramento foi feito nas strings do JSON já interpretado, e o arquivo continua válido. Foram mascarados os e-mails pessoais (do Severino e de terceiros que apareceram no histórico do git), inclusive quando escritos como padrão de `sed`/`grep`, e também a parte antes do `@`. O e-mail noreply do GitHub, os e-mails fictícios de teste (`@trim.com`, `@teste.com`) e o login público `Severino-Sobrinho` foram mantidos. A transcrição de 18/11 foi exportada durante a sessão, então os minutos finais (o commit das sessões) não estão no arquivo nem na contagem.
