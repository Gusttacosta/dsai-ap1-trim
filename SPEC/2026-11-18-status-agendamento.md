# Mudança de status pelo barbeiro e pelo admin: só o próprio agendamento, só transições válidas, uma cobrança por atendimento (2026-11-18)

> Complementa: SPEC/2026-09-29-agendamentos.md (somente leitura; esta spec define as transições
> de status que ela não detalha), SPEC/2026-11-18-agendamento-fuso-horario.md (relógio injetável)
> e SPEC/2026-11-18-cancelamento-agendamento.md (mesmo padrão de 404)
> Issue: #26

## O quê e por quê

`PUT /api/appointments/{id}/status` (`src/backend/modules/appointments/router.py`,
`update_appointment_status`) exige só que o usuário seja barbeiro ou admin e chama
`AppointmentService.update_status` direto. Na prática (#26):

1. **Não confere de quem é o agendamento.** Um barbeiro marca como `COMPLETED`, `NO_SHOW` ou
   `CANCELLED` o agendamento de outro barbeiro. Marcar `COMPLETED` cria a transação e a comissão.
2. **Aceita qualquer transição.** `COMPLETED` pode voltar a `CONFIRMED`, `PENDING` ou `CANCELLED`, e a
   transação e a comissão continuam no financeiro.
3. **Cobrança em dobro.** A transação é criada sempre que o status muda para `COMPLETED`. Assim,
   `COMPLETED → CONFIRMED → COMPLETED` gera duas transações e duas comissões para o mesmo
   atendimento. O mesmo acontece com `COMPLETED → CONFIRMED` seguido do checkout do financeiro
   (`POST /api/finance/checkout/appointment/{id}`), que só recusa um agendamento cujo status
   *atual* é `COMPLETED`.
4. **Conclui o futuro.** Um agendamento que ainda não aconteceu pode ser marcado `COMPLETED` ou
   `NO_SHOW`.

O painel do barbeiro (`src/frontend/src/pages/Dashboard.tsx`) mostra "Finalizar" em todo
agendamento do dia que não está `completed` nem `cancelled`, inclusive os que ainda não começaram e
os `no_show`. Em caso de erro, a tela só escreve no console.

Solução:

- **Transições permitidas.** Qualquer outra recebe 400 "Transição de status inválida: `<atual>` →
  `<novo>`.", inclusive para o mesmo status:

  | De | Para | Condição de horário |
  | :--- | :--- | :--- |
  | `PENDING` | `CONFIRMED` | — |
  | `PENDING` | `CANCELLED` | antes do início |
  | `CONFIRMED` | `CANCELLED` | antes do início |
  | `CONFIRMED` | `COMPLETED` | a partir do início |
  | `CONFIRMED` | `NO_SHOW` | a partir do início |
  | `COMPLETED`, `NO_SHOW`, `CANCELLED` | — | finais: não saem mais desses status |

  "Início" é `start_datetime` comparado com `AppointmentService.now()`, em UTC, como em
  SPEC/2026-11-18-agendamento-fuso-horario.md. Uma transição permitida fora do horário recebe 400:
  "Só é possível concluir ou marcar falta depois do início do agendamento." ou "Não é possível
  cancelar um agendamento que já começou." (a mesma mensagem do cancelamento pelo cliente).
  `PENDING → COMPLETED` não é permitido: o agendamento precisa ser confirmado antes. Hoje todo
  agendamento já nasce `CONFIRMED`.
- **Dono.**
  - O **barbeiro** só altera os agendamentos em que `appointment.barber_id` é o seu perfil
    (`Barber.user_id == current_user.id`). O agendamento de outro barbeiro recebe 404 "Agendamento
    não encontrado.", a mesma resposta de um `id` inexistente, como no PR #25.
  - O **admin** altera qualquer agendamento, com as mesmas transições.
  - Um barbeiro sem perfil de barbeiro recebe 404.
- **Uma cobrança por atendimento.** A transição para `COMPLETED` só cria transação e comissão se
  ainda não existir uma `Transaction` com `type = APPOINTMENT` e `reference_id = appointment.id`.
  Com `COMPLETED` final, isso não deveria acontecer, mas a checagem protege os dados antigos e
  qualquer caminho futuro. O valor, a forma de pagamento (`CASH`) e o cálculo da comissão não
  mudam.
- **Serviço.**
  - `update_status` é substituído por `change_status_by_staff(appointment_id, new_status, user)`.
  - O erro sai do serviço como exceção, como no PR #25: `LookupError` vira 404 na rota, e
    `ValueError` vira 400.
  - O cancelamento pelo cliente (`cancel_by_client`) continua separado e não muda.
- **Painel do barbeiro.**
  - "Finalizar" só aparece para agendamentos `pending` ou `confirmed` que já começaram. A regra fica
    numa função pura, `canFinish(appointment, now)`, em `src/frontend/src/utils/appointmentStatus.ts`.
  - Se a API recusar, a tela mostra a mensagem do backend num `alert`.

Valor: um barbeiro deixa de mexer na agenda e no financeiro de outro, um atendimento é cobrado e
comissionado uma vez só, e o painel não oferece uma ação que o backend vai recusar.

## Critérios de aceitação

Backend, em `tests/test_status_agendamento.py`, com o PostgreSQL da CI, "agora" fixo e os fixtures
de `tests/agenda_fixtures.py`:

- [ ] O barbeiro conclui o próprio agendamento `CONFIRMED` que já começou: 200, `status =
      completed`, 1 transação e 1 comissão.
- [ ] O barbeiro altera o agendamento de outro barbeiro: 404 "Agendamento não encontrado.", e nada
      muda (status, transações, comissões).
- [ ] O admin conclui o agendamento de qualquer barbeiro: 200.
- [ ] Cada transição permitida da tabela, dentro do horário: 200.
- [ ] `COMPLETED`, `NO_SHOW` e `CANCELLED` para qualquer status: 400, e nada muda.
- [ ] `COMPLETED → CONFIRMED → COMPLETED`: a primeira volta recebe 400, e continua existindo 1
      transação e 1 comissão.
- [ ] `PENDING → COMPLETED` e o mesmo status (`CONFIRMED → CONFIRMED`): 400.
- [ ] `CONFIRMED → COMPLETED` ou `NO_SHOW` antes do início: 400.
- [ ] `CONFIRMED → CANCELLED` depois do início: 400.
- [ ] Já existe uma transação para o agendamento (dado antigo) e ele é concluído: nenhuma transação
      nem comissão nova é criada.
- [ ] Cliente sem papel de barbeiro ou admin: 403, como hoje (`get_current_barber_or_admin`).
- [ ] Os testes falham se a correção for revertida. Isso é conferido revertendo `router.py` e
      `service.py` localmente antes do PR e registrado na sessão.

Frontend:

- [ ] `canFinish` devolve `true` só para `pending`/`confirmed` com `start_datetime <= now`, e
      `false` para futuros, `completed`, `cancelled` e `no_show`. Teste em
      `src/frontend/src/utils/appointmentStatus.test.ts`, com `vitest`.
- [ ] O painel usa `canFinish` e mostra a mensagem do backend quando a API recusa.
- [ ] `npm run build` continua passando.

## Fora do escopo

Cada item abaixo vira uma issue própria:

- O admin desfazer uma conclusão (marcada por engano) com estorno explícito da transação e da
  comissão. Depende da resposta do cliente (#15).
- Corrigir os dados que já existem com transação duplicada. Precisa de uma consulta no banco de
  produção primeiro.
- O checkout do financeiro (`/api/finance/checkout/appointment/{id}`) não confere o dono, o horário
  nem a transição `CONFIRMED → COMPLETED`. Com `COMPLETED` final, ele deixa de cobrar em dobro, mas
  as outras regras desta spec não valem lá.
- `PUT /api/appointments/{id}` do admin (prevista em SPEC/2026-09-29-agendamentos.md), que não
  existe.
- Os botões de "Falta" e "Cancelar" no painel. Esta spec só ajusta o "Finalizar".
- O filtro "Hoje" do painel usa a data do navegador (`toDateString()`), e não o fuso da barbearia.

## Dependência

O código depende do PR #25 (`tests/agenda_fixtures.py`, padrão de 404). Ele só começa depois do
merge do #25 na `main`, trazida para este branch antes do primeiro push.
