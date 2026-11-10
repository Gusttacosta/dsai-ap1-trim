# Custo das sessões com agente

Tokens extraídos do campo `usage` das transcrições do Claude Code (mensagens do agente principal + subagentes, sem duplicar respostas em streaming). Horários em America/Sao_Paulo.

| Sessão | Início | Fim | Modelo | Input | Output | Cache (escrita) | Cache (leitura) | Total |
|---|---|---|---|---:|---:|---:|---:|---:|
| `2026-11-08-1934-claudecode.jsonl` | 08/11 19:34 | 20:10 | claude-opus-5-5 | 36 | 7,403 | 41,646 | 815,529 | 864,614 |
| `2026-11-08-2132-claudecode.jsonl` | 08/11 21:32 | 22:19 | claude-opus-5-5 | 102 | 28,120 | 66,956 | 2,956,174 | 3,051,352 |
| `2026-11-10-1933-claudecode.jsonl` | 10/11 19:33 | 20:25 | claude-haiku-5-5, claude-opus-5-5 | 88 | 51,650 | 93,028 | 2,822,754 | 2,967,520 |
| **Total** | | | | **226** | **87,173** | **201,630** | **6,594,457** | **6,883,486** |

Segredos mascarados na exportação: tokens JWT locais e e-mail pessoal (substituídos por `[jwt-removido]` / `[email-removido]`). Nenhuma outra alteração foi feita no texto.
