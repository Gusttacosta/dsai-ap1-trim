# Testes de integração da fila de espera (walk-in), no lugar dos testes gerados (2026-11-24)

> Complementa: SPEC/2026-11-21-testes-integracao-auth.md (plano da #3, um módulo por PR) e
> SPEC/2026-09-29-walkin.md (descreve o comportamento que os testes conferem)
> Issue: #3

## O quê e por quê

Décimo módulo do plano da #3. O `tests/test_walkin.py` herdado da AP1 tem 1.000 funções geradas
que conferem um dict fixo e não importam a aplicação. Ele é trocado por testes de integração pela
API (`/api/queue`), com o PostgreSQL de teste e as fixtures de `tests/agenda_fixtures.py` e
`tests/api_helpers.py`.

As 4 rotas do módulo são:
- **público:** a fila ao vivo para a TV, com os nomes mascarados;
- **barbeiro ou admin:** entrar na fila, puxar o cliente para a cadeira (vira agendamento) e
  cancelar.

O código da aplicação não muda.

Valor: a fila organiza quem chega sem horário. A ordem errada, um nome exposto na TV ou um
atendimento sem agendamento (que o caixa não consegue cobrar) passam a quebrar a CI.

## Critérios de aceitação

Testes em `tests/test_walkin_integracao.py`, com o PostgreSQL de `TEST_DATABASE_URL`:

- [ ] **Entrar na fila:**
  - responde 201 com o status `waiting`, a posição, o nome, o serviço pedido, o barbeiro pedido
    (opcional), o cliente (opcional), `joined_at` e `finished_at` nulo;
  - as posições do dia são 1, 2, 3…, e quem sai da fila não devolve a posição (o próximo continua
    na sequência);
  - nome com mais de 150 caracteres, ou nome ou serviço faltando, responde 422.
- [ ] **Fila ao vivo (`/live`):**
  - lista só quem está `waiting`, pela posição, com o nome mascarado (as 3 primeiras letras do
    primeiro nome e `***`; nomes curtos ficam inteiros, mais `***`), a posição e `joined_at`;
  - não mostra o sobrenome, o cliente nem o serviço;
  - quem foi atendido ou cancelou sai da fila;
  - sem ninguém, devolve uma lista vazia.
- [ ] **Puxar para a cadeira (`/assign`), de um cliente com conta:**
  - o registro vai para `attending`, com `finished_at`;
  - nasce um agendamento `confirmed` do cliente com o barbeiro informado, com o preço do serviço
    pedido e começando agora;
  - puxar de novo, ou puxar quem cancelou, responde 400 `Este registro já está com status
    <status>.`, e nenhum agendamento novo nasce;
  - um registro desconhecido responde 400 `Registro na fila não encontrado.`.
- [ ] **Cancelar:**
  - o registro vai para `cancelled`, com `finished_at`, e nenhum agendamento nasce;
  - cancelar de novo, ou cancelar quem já está sendo atendido, responde 400 `Apenas registros
    aguardando podem ser cancelados.`;
  - um registro desconhecido responde 400 `Registro na fila não encontrado.`.
- [ ] **Permissões:**
  - sem token, ou com token de cliente, entrar, puxar e cancelar respondem 403, e nada muda no
    banco;
  - barbeiro e admin podem usar as três rotas;
  - a fila ao vivo é pública.
- [ ] **Os testes testam:** se o corpo de qualquer método de `WalkInService` for trocado por um
      `raise`, algum teste novo falha.
- [ ] `tests/test_walkin.py` (gerado) é apagado, e `walkin` sai da lista `MODULES` de
      `tests/generate_tests.py`.

## Fora do escopo

Mudar o comportamento do módulo. As diferenças encontradas vão para uma issue própria e não são
fixadas pelos testes:
- puxar para a cadeira alguém **sem conta** (`user_id` nulo, o caso comum de quem chega sem horário)
  responde 500, porque o agendamento exige `client_id`;
- um nome só com espaços é aceito e derruba a fila ao vivo inteira (500 no `split()[0]`);
- serviço pedido ou barbeiro desconhecidos respondem 500 (FK), e não 400 ou 404;
- o agendamento criado no `/assign` tem duração zero (`end_datetime = start_datetime`), não tem
  itens (`AppointmentItem`) e ignora o barbeiro pedido na fila. Qualquer barbeiro pode puxar para
  outro barbeiro;
- o "dia" da fila usa `date.today()` do servidor contra `func.date(joined_at)` no fuso da sessão do
  PostgreSQL, sem o fuso da barbearia.
