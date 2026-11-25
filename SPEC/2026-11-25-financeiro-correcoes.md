# Financeiro: venda atômica, regras do caixa, Trim Club, comissões pendentes e extrato por data (2026-11-25)

> Complementa: SPEC/2026-09-29-financeiro.md, SPEC/2026-11-18-status-agendamento.md e
> SPEC/2026-11-24-testes-integracao-finance.md (PR #60)
> Issue: #59

## O quê e por quê

Os testes de integração do financeiro (PR #60) acharam seis problemas no caixa:
1. uma venda com cliente inexistente baixa o estoque e só depois falha com 500;
2. produto desativado é vendido;
3. o caixa cobra agendamento pendente ou que ainda não começou;
4. o crédito do Trim Club é aceito sem assinatura;
5. faltam o relatório de comissões pendentes e o filtro de datas no extrato;
6. um agendamento desconhecido responde 400.

Valor: é o dinheiro da barbearia. Estoque que some sem receita, atendimento de graça e cobrança
adiantada distorcem o caixa e as comissões.

## Decisões

- **Item 3:** o caixa segue as regras da conclusão pelo barbeiro (#26). Só cobra um agendamento
  `confirmed` que já começou (início ≤ agora). Para cobrar adiantado, o agendamento precisa ser
  confirmado e começar.
- **Item 4:** o crédito do Trim Club exige uma assinatura `active` cuja vigência
  (`start_date` a `end_date`) inclua o dia de hoje no fuso da barbearia. A cota de cortes fica
  para quando a #16 definir os limites.

## Critérios de aceitação

1. [ ] `POST /api/finance/checkout/product` com um `user_id` desconhecido responde **404**
   `Cliente não encontrado.`, sem baixar o estoque, sem gravar movimentação e sem gravar
   transação. A baixa do estoque e a transação entram no mesmo commit (`register_movement(...,
   commit=False)`).
2. [ ] A venda de um produto desativado responde **400** `Produto desativado não pode ser
   vendido.`, e o estoque não muda.
3. [ ] `POST /checkout/appointment/{id}`:
   - agendamento `pending` responde 400 `Só é possível cobrar um agendamento confirmado.`;
   - agendamento confirmado que ainda não começou responde 400 `Só é possível cobrar depois do
     início do agendamento.`;
   - agendamento que começa exatamente agora pode ser cobrado.
4. [ ] O crédito do Trim Club sem assinatura válida hoje responde 400 `O cliente não tem
   assinatura ativa do Trim Club.` A assinatura não vale se estiver cancelada, `past_due`, vencida
   ou ainda não iniciada. Com assinatura válida, o atendimento sai a 0,00, como hoje.
5. [ ] **Relatório e extrato:**
   - `GET /api/finance/commissions` (admin) lista as comissões pendentes agrupadas por barbeiro
     (`barber_id`, `barber_name`, `pending_count`, `pending_amount`), do maior valor para o menor;
   - `GET /api/finance/transactions?start_date=&end_date=` filtra pelo dia no fuso da barbearia,
     com `end_date` inclusivo;
   - um período invertido responde 422.
6. [ ] Um agendamento desconhecido no caixa responde **404** `Agendamento não encontrado.`

O teste do PR #60 que cobrava com crédito do Trim Club sem assinatura passa a criar uma
assinatura ativa. Isso funciona com ou sem esta correção.

## Testes

`tests/test_financeiro_correcoes.py`, com o "agora" fixado em 01/12/2026 às 14:00 de Brasília.
