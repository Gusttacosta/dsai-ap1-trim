# Custo das sessões com agente

Tokens extraídos do campo `usage` das transcrições do Claude Code (mensagens do agente principal + subagentes, sem duplicar respostas em streaming). Horários em America/Sao_Paulo.

| Sessão | Início | Fim | Modelo | Input | Output | Cache (escrita) | Cache (leitura) | Total |
|---|---|---|---|---:|---:|---:|---:|---:|
| `2026-11-08-1934-claudecode.jsonl` | 08/11 19:34 | 20:10 | claude-opus-5-5 | 36 | 7,403 | 41,646 | 815,529 | 864,614 |
| `2026-11-08-2132-claudecode.jsonl` | 08/11 21:32 | 22:19 | claude-opus-5-5 | 102 | 28,120 | 66,956 | 2,956,174 | 3,051,352 |
| `2026-11-10-1933-claudecode.jsonl` | 10/11 19:33 | 20:41 | claude-haiku-5-5, claude-opus-5-5 | 106 | 57,114 | 100,742 | 3,655,302 | 3,813,264 |
| `2026-11-16-2027-claudecode.jsonl` | 16/11 20:27 | 20:55 | claude-opus-5-5 | 80 | 35,207 | 89,237 | 3,318,596 | 3,443,120 |
| `2026-11-16-2059-claudecode.jsonl` | 16/11 20:59 | 21:11 | claude-opus-5-5 | 34 | 6,711 | 30,618 | 723,525 | 760,888 |
| **Total** | | | | **358** | **134,555** | **329,199** | **11,469,126** | **11,933,238** |

Segredos mascarados na exportação: tokens JWT locais e e-mail pessoal (substituídos por `[jwt-removido]` / `[email-removido]`). Nenhuma outra alteração foi feita no texto.

Sessões de 16/11: exportadas pelo terminal, com o mascaramento feito pelo `jq` dentro dos textos do JSON, o que mantém o arquivo válido. A senha do banco local também foi mascarada (`[senha-removida]`). Nessa data, as tentativas de pedir a exportação ao próprio agente foram bloqueadas pelo filtro de segurança do modelo (`reasoning_extraction`), inclusive com o Sonnet, que por isso não registrou consumo.
