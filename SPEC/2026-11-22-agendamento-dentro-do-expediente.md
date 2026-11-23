# Agendamento só dentro do expediente e fora do almoço (2026-11-22)

> Complementa: SPEC/2026-09-29-agendamentos.md (regra 2) e
> SPEC/2026-11-18-agendamento-fuso-horario.md (expediente em hora local)
> Issue: #23

## O quê e por quê

A regra 2 da spec da AP1 diz que o horário do agendamento "deve estar contido estritamente no
WorkSchedule ... não sobrepondo o horário de almoço". O `create_appointment` só confere se o
barbeiro trabalha **no dia** (`is_working`). Com um barbeiro que trabalha das 09:00 às 18:00 e
almoça das 12:00 às 13:00, a API aceita (#23):

- um agendamento às 03:00;
- um agendamento às 12:15, no meio do almoço;
- um agendamento às 17:45 com um serviço de 30 minutos, que termina às 18:15.

A tela só oferece os horários da disponibilidade, mas o `POST /api/appointments` e o
`POST /api/appointments/guest` aceitam qualquer horário enviado direto.

Solução: o `create_appointment` passa a conferir, no fuso da barbearia, se o atendimento inteiro
(início mais a duração somada dos serviços) cabe no expediente do dia e não encosta no almoço. As
regras são as mesmas do cálculo de disponibilidade, que passa a usar a mesma função.

Valor: o barbeiro não recebe clientes de madrugada nem no almoço, e a agenda do dia continua batendo
com o expediente dele.

## Regras

- O início precisa ser igual ou posterior ao `start_time`, e o fim igual ou anterior ao `end_time`,
  no dia local do início. Terminar exatamente no `end_time` é permitido.
- Se o dia tem almoço (`break_start` e `break_end`), o atendimento não pode sobrepor esse
  intervalo. Terminar exatamente no `break_start` e começar exatamente no `break_end` são
  permitidos.
- O início **não** precisa cair na grade de 30 minutos da disponibilidade. Um horário como 09:15
  cabe no expediente e é aceito. A grade é só a sugestão da tela.
- Mensagens (400), com as horas no fuso da barbearia:
  - fora do expediente: `Horário fora do expediente do barbeiro nesse dia (09:00 às 18:00).`
  - no almoço: `Horário cai no intervalo de almoço do barbeiro (12:00 às 13:00).`
- A ordem das recusas não muda para os casos que já existiam: horário passado, além da janela de
  dias, conflito com outro agendamento e dia sem expediente vêm antes.
- Nada é gravado quando a criação é recusada. No visitante, isso inclui o usuário fantasma.

## Critérios de aceitação

Testes em `tests/test_agendamento_expediente.py`, pelo `POST /api/appointments/guest` e pelo
`POST /api/appointments`, que falham com o código de antes desta spec:

- [ ] Os três casos da #23 (03:00, 12:15 e 17:45 com 30 minutos) respondem 400 com a mensagem
      certa, e nenhum agendamento ou usuário é gravado.
- [ ] Início antes do `start_time` (08:59) e atendimento que passa do `end_time` com dois serviços
      somados respondem 400.
- [ ] Atendimento que começa antes do almoço e entra nele (11:45 com 30 minutos) responde 400.
- [ ] Os limites são aceitos: 09:00, 17:30 com 30 minutos (termina às 18:00), 11:30 (termina às
      12:00, quando começa o almoço) e 13:00. 09:15, fora da grade, também é aceito.
- [ ] Sem almoço cadastrado, o horário do meio-dia é aceito.
- [ ] Um expediente em fuso local é conferido no fuso local: com `start_datetime` em UTC, vale a
      hora de Brasília.
- [ ] O cliente logado (`POST /api/appointments`) tem as mesmas recusas.
- [ ] A disponibilidade (`GET /availability`) continua devolvendo os mesmos horários.

## Fora do escopo

- Validar o próprio expediente ao cadastrá-lo (almoço fora do expediente, `break_start` sem
  `break_end`). Isso é da #37.
- Expediente que atravessa a meia-noite.
- Exigir que o início caia na grade de 30 minutos.
