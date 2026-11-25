# Testes de integração dos relatórios (dashboard), no lugar dos testes gerados (2026-11-24)

> Complementa: SPEC/2026-11-21-testes-integracao-auth.md (plano da #3, um módulo por PR) e
> SPEC/2026-09-29-dashboard.md (descreve o comportamento que os testes conferem)
> Issue: #3

## O quê e por quê

Nono módulo do plano da #3. O `tests/test_dashboard.py` herdado da AP1 tem 1.000 funções geradas
que conferem um dict fixo e não importam a aplicação. Ele é trocado por testes de integração pela
API (`/api/reports`), com o PostgreSQL de teste e as fixtures de `tests/agenda_fixtures.py` e
`tests/api_helpers.py`.

O módulo só lê dados de outros módulos (transações, comissões, despesas e agendamentos). As 4 rotas
são:
- **admin:** resumo financeiro, visão do dia e ranking dos barbeiros;
- **barbeiro:** o próprio desempenho.

Os testes gravam os dados direto no banco, com datas fixas ao meio-dia UTC, para o resultado não
depender do fuso do servidor do PostgreSQL. O código da aplicação não muda.

Valor: é o painel que o dono usa para saber se a barbearia dá lucro e quem mais fatura. Uma soma
errada, um período que deixa algo de fora ou de lado trocado passa a quebrar a CI.

## Critérios de aceitação

Testes em `tests/test_dashboard_integracao.py`, com o PostgreSQL de `TEST_DATABASE_URL`:

- [ ] **Resumo financeiro (`/financial-summary`):**
  - `total_revenue` soma as transações (agendamento, produto e assinatura) criadas no período;
  - `total_commissions` soma as comissões criadas no período, pagas ou não;
  - `total_expenses` soma as despesas com `payment_date` no período;
  - `net_profit` = receitas − comissões − despesas, e pode ser negativo;
  - as duas pontas do período entram, e o que está fora dele não entra;
  - sem dados, tudo é 0;
  - sem datas, o período é o mês corrente;
  - uma data inválida responde 422.
- [ ] **Visão do dia (`/daily-overview`):**
  - conta os agendamentos que começam no dia, no total e por status (`completed`, `no_show`,
    `cancelled`);
  - `ticket_medio` é a média das transações de agendamento criadas no dia, com duas casas; as
    vendas de produto não entram;
  - agendamentos e transações de outros dias não entram;
  - sem dados, tudo é 0;
  - sem data, o dia é hoje.
- [ ] **Desempenho e ranking:**
  - para cada barbeiro: o nome, os atendimentos `completed` no período, a soma das comissões dele
    e o faturamento (o valor das transações que geraram essas comissões);
  - o ranking traz todos os barbeiros, do maior faturamento para o menor, inclusive os que não
    faturaram (com zeros);
  - em `/me`, o barbeiro do token vê só os próprios números, com o mesmo período;
  - um admin sem perfil de barbeiro recebe 404 `Perfil de barbeiro não encontrado.`.
- [ ] **Permissões:**
  - sem token, as 4 rotas respondem 403;
  - com token de cliente ou de barbeiro, as 3 rotas do admin respondem 403;
  - um cliente em `/me` também recebe 403.
- [ ] **Os testes testam:** se o corpo de qualquer método de `DashboardService` for trocado por um
      `raise`, algum teste novo falha.
- [ ] `tests/test_dashboard.py` (gerado) é apagado, e `dashboard` sai da lista `MODULES` de
      `tests/generate_tests.py`.

## Fora do escopo

Mudar o comportamento do módulo. As diferenças encontradas vão para uma issue própria e não são
fixadas pelos testes:
- a visão do dia calcula `total_revenue`, mas o `DailyOverviewResponse` não tem esse campo, então
  ele some da resposta;
- os dias são calculados com `func.date()` no fuso da sessão do PostgreSQL, e o padrão (mês
  corrente, hoje) usa `date.today()` do servidor. Nenhum dos dois usa o fuso da barbearia
  (`settings.shop_timezone`), então um atendimento às 22:00 em Brasília pode cair no dia seguinte;
- o ranking inclui barbeiros desativados;
- não há ocupação da agenda, prevista na spec da AP1 (`Visão operacional de um dia (Ocupação,
  Ticket médio)`);
- um período invertido devolve zeros, sem aviso.
