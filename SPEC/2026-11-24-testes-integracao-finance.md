# Testes de integração do financeiro, no lugar dos testes gerados (2026-11-24)

> Complementa: SPEC/2026-11-21-testes-integracao-auth.md (plano da #3, um módulo por PR) e
> SPEC/2026-09-29-financeiro.md (descreve o comportamento que os testes conferem)
> Issue: #3

## O quê e por quê

Quinto módulo do plano da #3. O `tests/test_finance.py` herdado da AP1 tem 1.000 funções geradas
que conferem um dict fixo e não importam a aplicação. Ele é trocado por testes de integração pela
API (`/api/finance`), com o PostgreSQL de teste e as fixtures de `tests/agenda_fixtures.py` e
`tests/api_helpers.py`.

As 6 rotas do módulo são o caixa (PDV) e as comissões:
- **admin:** cobrança de agendamento, venda de produto no balcão, extrato, comissões de um barbeiro
  e acerto de contas;
- **barbeiro:** as próprias comissões.

A cobrança que nasce quando o barbeiro marca um agendamento como `completed`
(`AppointmentService._charge_once`) já é testada em `test_status_agendamento.py` e
`test_appointments_integracao.py`. Aqui entra a cobrança pelo caixa, que é outro caminho
(`FinanceService.checkout_appointment`). O código da aplicação não muda.

Valor: é o dinheiro da barbearia e do barbeiro. Um erro no valor cobrado, na comissão, na baixa
do estoque ou no acerto passa a quebrar a CI.

## Critérios de aceitação

Testes em `tests/test_finance_integracao.py`, com o PostgreSQL de `TEST_DATABASE_URL`:

- [ ] **Cobrança de agendamento pelo caixa:**
  - responde 201 com uma transação `appointment` com `reference_id` do agendamento, valor
    `total_price`, o método de pagamento enviado e o cliente como `user_id`;
  - o agendamento passa para `completed`;
  - nasce uma comissão não paga de `total_price × commission_rate / 100`, arredondada a 2 casas
    (por exemplo, 30% de 75,00 = 22,50 e 33,33% de 40,00 = 13,33);
  - vale para `cash`, `credit_card`, `debit_card` e `pix`.
- [ ] **Trim Club no agendamento:** com `trim_club_credit`, a transação e a comissão são gravadas
      com valor 0,00 (decisão da spec da AP1), e o agendamento passa para `completed`.
- [ ] **Cobrança recusada:** responde 400 e nada é gravado quando:
  - o agendamento já está `completed` (`Este agendamento já foi finalizado e cobrado.`), inclusive
    depois de uma cobrança pelo caixa (não cobra duas vezes);
  - o agendamento está `cancelled` ou `no_show` (`Não é possível cobrar um agendamento com status
    <status>.`).

  Um agendamento desconhecido é recusado com `Agendamento não encontrado.` (o teste aceita 400 ou
  404, ver "Fora do escopo"), e nada é gravado. Um método de pagamento fora da lista, ou faltando,
  responde 422.
- [ ] **Venda de produto no balcão:**
  - responde 201 com uma transação `product_sale` com `reference_id` do produto e valor
    `preço × quantidade`;
  - o estoque baixa a quantidade vendida, e nasce uma movimentação `sale` de `-quantidade` no
    nome do admin, com a nota `Venda no balcão`;
  - `user_id` é opcional: sem ele, a transação fica sem cliente; com um cliente existente, fica no
    nome dele;
  - vender exatamente o estoque que existe é aceito e deixa o estoque em zero;
  - a venda não gera comissão.
- [ ] **Venda recusada:**
  - estoque insuficiente responde 400 com a mensagem do estoque, e o estoque, as movimentações e
    as transações não mudam;
  - `trim_club_credit` responde 400 `Produtos não podem ser pagos com créditos Trim Club nesta
    versão.`, e o estoque não muda;
  - produto desconhecido responde 400 `Produto não encontrado.`;
  - quantidade zero ou negativa, ou campo obrigatório faltando, responde 422.
- [ ] **Extrato:** lista todas as transações (agendamentos e produtos), da mais recente para a mais
      antiga. Sem transações, devolve uma lista vazia.
- [ ] **Comissões de um barbeiro (admin):**
  - por padrão, só as pendentes;
  - com `only_pending=false`, todas, da mais recente para a mais antiga;
  - só as do barbeiro pedido.
- [ ] **Minhas comissões (barbeiro):**
  - as pendentes e as pagas, só as do barbeiro do token;
  - um admin sem perfil de barbeiro recebe 404 `Perfil de barbeiro não encontrado.`.
- [ ] **Acerto de contas:**
  - marca as comissões pedidas como pagas, com `paid_at`, e devolve só elas;
  - as outras pendentes continuam pendentes;
  - um ID de outro barbeiro ou desconhecido no lote é ignorado;
  - pagar de novo, ou um lote sem nenhuma pendente do barbeiro, responde 400 `Nenhuma comissão
    pendente encontrada com esses IDs.`;
  - lote vazio responde 422.
- [ ] **Permissões:**
  - sem token, as 6 rotas respondem 403;
  - com token de cliente ou de barbeiro, as 5 rotas do admin respondem 403 e nada muda no banco;
  - um cliente em `/commissions/me` também recebe 403.
- [ ] **Os testes testam:** se o corpo de qualquer método de `FinanceService` for trocado por um
      `raise`, algum teste novo falha.
- [ ] `tests/test_finance.py` (gerado) é apagado, e `finance` sai da lista `MODULES` de
      `tests/generate_tests.py`.

## Fora do escopo

Mudar o comportamento do módulo. As diferenças encontradas vão para uma issue própria e não são
fixadas pelos testes:
- venda com um `user_id` que não existe responde 500 depois de baixar o estoque e gravar a
  movimentação, sem gravar a transação;
- um produto desativado pode ser vendido;
- o caixa cobra um agendamento `pending` ou que ainda não começou, sem as regras de status da #26;
- `trim_club_credit` é aceito sem conferir se o cliente tem uma assinatura ativa;
- faltam o relatório de comissões pendentes agrupado por barbeiro (`GET /commissions`) e o filtro
  de data do extrato, previstos na spec da AP1;
- agendamento desconhecido responde 400, e não 404.
