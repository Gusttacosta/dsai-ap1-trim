# Cancelamento de agendamento pelo cliente: só o dono, só o futuro, só o que está ativo (2026-11-18)

> Complementa: SPEC/2026-09-29-agendamentos.md (somente leitura; esta spec detalha a regra 5,
> "Cancelamento do Cliente") e SPEC/2026-11-18-agendamento-fuso-horario.md (relógio injetável)
> Issue: #24

## O quê e por quê

`PUT /api/appointments/{id}/cancel` (`src/backend/modules/appointments/router.py`,
`cancel_my_appointment`) chama `update_status(appointment_id, CANCELLED)` sem nenhuma checagem.
O próprio código admite: "Em uma versão avançada, faríamos a checagem se o agendamento pertence ao
usuário e se é de fato no futuro." Na prática (#24):

1. **Não confere o dono.** Qualquer usuário autenticado cancela o agendamento de qualquer outra
   pessoa, bastando saber o `id`.
2. **Não confere se é futuro.** Um agendamento que já começou ou já aconteceu vira `CANCELLED`. A
   regra 5 da spec da AP1 diz "somente se futuro".
3. **Não confere o status atual.** Um `COMPLETED`, `NO_SHOW` ou `CANCELLED` pode ser cancelado. No
   caso do `COMPLETED`, a transação e a comissão do barbeiro criadas na conclusão
   (`AppointmentService.update_status`) continuam no financeiro, apontando para um agendamento
   cancelado.

Hoje o frontend não usa essa rota (o painel só chama `/status`), então a correção é só no backend
e não muda nenhuma tela.

Solução:

- **Novo método `AppointmentService.cancel_by_client(appointment_id, client_id)`**, usado pela
  rota no lugar de `update_status`. `update_status` não muda, porque continua sendo usado pelo
  barbeiro e pelo admin em `/status`.
- **Ordem das checagens e respostas:**

  | Situação | Resposta | Banco |
  | :--- | :--- | :--- |
  | `id` não existe | 404 "Agendamento não encontrado." | nada muda |
  | Agendamento de outro cliente | 404 "Agendamento não encontrado." (a mesma resposta, para não revelar que o `id` existe) | nada muda |
  | Status diferente de `PENDING` ou `CONFIRMED` | 400 "Só é possível cancelar agendamentos pendentes ou confirmados." | nada muda |
  | `start_datetime <= agora` | 400 "Não é possível cancelar um agendamento que já começou." | nada muda |
  | Dono, ativo e futuro | 200 com o agendamento, `status = cancelled` | `status` vira `CANCELLED` |

- **O dono é `appointment.client_id == current_user.id`, qualquer que seja o papel.** Um barbeiro
  ou admin que agendou como cliente cancela o próprio agendamento por essa rota. Para alterar
  agendamentos de outras pessoas, barbeiro e admin continuam com `/status`.
- **"Agora" vem do relógio do serviço** (`AppointmentService.now()`, de
  SPEC/2026-11-18-agendamento-fuso-horario.md), e a comparação é feita em UTC. Os testes fixam
  "agora" do mesmo jeito que os da #12.
- **O erro sai do serviço como exceção**, como já acontece com a criação:
  - `LookupError` vira 404 na rota;
  - `ValueError` vira 400.

Valor: um cliente não consegue mais desmarcar o horário de outra pessoa, e o histórico e o
financeiro deixam de ter agendamentos concluídos marcados como cancelados.

## Critérios de aceitação

Testes em `tests/test_cancelamento_agendamento.py`, com o PostgreSQL da CI e "agora" fixo:

- [ ] O dono cancela um agendamento `CONFIRMED` futuro: 200, a resposta e o banco ficam com
      `status = cancelled`.
- [ ] O dono cancela um agendamento `PENDING` futuro: 200.
- [ ] Outro cliente tenta cancelar: 404, com a mesma mensagem de um `id` inexistente, e o status
      não muda no banco.
- [ ] Um `id` inexistente: 404.
- [ ] Agendamento que começa exatamente agora, ou que já passou: 400, e o status não muda.
- [ ] Agendamento `COMPLETED`, `NO_SHOW` ou `CANCELLED` (mesmo futuro): 400, e o status não muda.
      No `COMPLETED`, a transação e a comissão continuam lá.
- [ ] Sem token: 401 ou 403, como nas outras rotas autenticadas (o comportamento atual de
      `get_current_user`, que não muda).
- [ ] Os testes falham se a correção for revertida. Isso é conferido revertendo `router.py` e
      `service.py` localmente antes do PR e registrado na sessão.

## Fora do escopo

Cada item abaixo vira uma issue própria:

- `PUT /api/appointments/{id}/status`: qualquer barbeiro altera o status do agendamento de qualquer
  outro barbeiro, e um `COMPLETED` pode voltar a outro status sem estornar a transação e a
  comissão.
- Antecedência mínima para cancelar ("X horas", regra 5 da spec da AP1): depende da resposta do
  cliente (#15). Por enquanto, vale o que a regra 5 chama de versão inicial: qualquer horário no
  futuro.
- Botão de cancelar no frontend para o cliente: não existe tela de "meus agendamentos" que use
  `/api/appointments/me`.
- Avisar o barbeiro do cancelamento (módulo de notificações).
