# Testes de integração dos agendamentos, no lugar dos testes gerados (2026-11-24)

> Complementa: SPEC/2026-11-21-testes-integracao-auth.md (plano da #3, um módulo por PR) e
> SPEC/2026-09-29-agendamentos.md (descreve o comportamento que os testes conferem)
> Issue: #3

## O quê e por quê

Quarto módulo do plano da #3. O `tests/test_appointments.py` herdado da AP1 tem 1.000 funções
geradas (28 mil linhas) que conferem um dict fixo e não importam a aplicação. Ele é trocado por
testes de integração pela API (`/api/appointments`), com o PostgreSQL de teste e as fixtures de
`tests/agenda_fixtures.py` e `tests/api_helpers.py`.

Os PRs da AP2 já cobrem partes do módulo, e essas partes não se repetem aqui:
- expediente e almoço (`test_agendamento_expediente.py`, #23);
- fuso e janela de agendamento (`test_agendamento_fuso.py`);
- cancelamento pelo cliente (`test_cancelamento_agendamento.py`);
- transições de status (`test_status_agendamento.py`);
- nome do visitante (`test_nome_do_visitante.py`);
- barbeiro desativado (`test_barbeiros_admin.py`).

Este PR cobre o que falta nas 7 rotas: disponibilidade, criação, visitante, listas do cliente e do
barbeiro, cobrança ao concluir e permissões. O código da aplicação não muda.

Valor: é o fluxo central da barbearia, citado na própria #3 (agendamento, finalizar atendimento,
faturamento e comissão). Um erro no preço, na agenda ou na comissão passa a quebrar a CI.

## Critérios de aceitação

Testes em `tests/test_appointments_integracao.py`, com o PostgreSQL de `TEST_DATABASE_URL` e
"agora" fixado (`set_now`):

- [ ] **Disponibilidade:**
  - num dia livre de 09:00 às 18:00, devolve os horários de 30 em 30 minutos, de 09:00 até o
    último início que cabe a duração pedida (17:30 para 30 min, 17:00 para 60 min);
  - um agendamento `pending`, `confirmed` ou `completed` tira os horários que ele sobrepõe, e um
    `cancelled` ou `no_show` não tira;
  - agendamento de outro barbeiro não interfere;
  - dia de folga devolve uma lista vazia;
  - barbeiro desconhecido responde 404;
  - faltando `barber_id`, `target_date` ou `duration_minutes`, ou com data inválida, responde 422.
- [ ] **Criação pelo cliente:**
  - responde 201 com `status` `confirmed` e o `client_id` do token;
  - com dois serviços, `total_price` é a soma dos preços e `end_datetime` é o início mais a soma
    das durações;
  - cada item guarda o nome, o preço e a duração do serviço naquele momento (*snapshot*): mudar o
    preço ou o nome do serviço depois não muda o agendamento;
  - `notes` é gravado;
  - repetir o mesmo serviço em `service_ids` conta o serviço uma vez.
- [ ] **Serviços inválidos:** um serviço desconhecido, desativado ou não prestado pelo barbeiro
      responde 400 `Um ou mais serviços são inválidos ou não são prestados por este barbeiro.`, e
      nada é gravado. `service_ids` vazio responde 422.
- [ ] **Conflito:**
  - um horário que sobrepõe um agendamento `pending`, `confirmed` ou `completed` do mesmo barbeiro
    responde 400 `Conflito de horário. O barbeiro já possui um agendamento nesse período.`;
  - encostar no fim do anterior (início igual ao fim dele) é aceito;
  - um `cancelled` ou `no_show` no mesmo horário não bloqueia;
  - outro barbeiro no mesmo horário não bloqueia.
- [ ] **Dia de folga:** responde 400 `O barbeiro não trabalha nesse dia.`.
- [ ] **Visitante:**
  - responde 201 e cria um usuário `client` com e-mail `guest_<8 hex>@trim.local` e o nome
    informado;
  - o agendamento fica no nome desse usuário, com `notes` `Visitante: <nome>`;
  - não exige token;
  - quando o agendamento é recusado (conflito ou serviço inválido), responde 400 e o usuário
    fantasma não fica no banco.
- [ ] **Agendamentos do cliente (`/me`):** só os do cliente do token, do mais recente para o mais
      antigo, com os itens. Um cliente sem agendamentos recebe uma lista vazia.
- [ ] **Agenda do barbeiro (`/barber/me`):**
  - só os agendamentos do barbeiro do token, do mais recente para o mais antigo;
  - um admin sem perfil de barbeiro recebe 404 `Perfil de barbeiro não encontrado.`;
  - um cliente recebe 403.
- [ ] **Cobrança ao concluir:**
  - ao marcar `completed`, nasce uma transação `appointment` com `reference_id` do agendamento,
    valor `total_price`, pagamento `cash` e o cliente como `user_id`;
  - nasce uma comissão não paga de `total_price × commission_rate / 100` para o barbeiro (por
    exemplo, 30% de 75,00 = 22,50);
  - `no_show` e `cancelled` não geram cobrança.
- [ ] **Permissões:** sem token, as rotas do cliente e do barbeiro respondem 403
      `Not authenticated`; a disponibilidade e o visitante são públicos.
- [ ] **Os testes testam:** se o corpo de qualquer método de `AppointmentService` for trocado por um
      `raise`, algum teste do módulo falha (os novos ou os da AP2 listados acima).
- [ ] `tests/test_appointments.py` (gerado) é apagado, e `appointments` sai da lista `MODULES` de
      `tests/generate_tests.py`.

## Fora do escopo

Mudar o comportamento do módulo. As diferenças encontradas vão para uma issue própria. Hoje:
- `duration_minutes` zero ou negativo é aceito na disponibilidade e devolve horários;
- o usuário fantasma do visitante, que é a #21.
