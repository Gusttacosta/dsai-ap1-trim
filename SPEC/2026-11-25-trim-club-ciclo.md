# Trim Club: ciclo da assinatura, mensalidade no caixa e planos validados (2026-11-25)

> Complementa: SPEC/2026-09-29-assinaturas.md, SPEC/2026-09-29-financeiro.md e
> SPEC/2026-11-24-testes-integracao-subscriptions.md (PR #63)
> Issue: #64

## O quê e por quê

Os testes de integração do Trim Club (PR #63) acharam oito problemas:
1. quem cancela, ou cuja assinatura vence, nunca mais consegue assinar;
2. a assinatura não vence: continua `active` depois do `end_date`;
3. assinar não gera a `Transaction` da mensalidade;
4. barbeiros e admins podem assinar;
5. o `start_date` usa o dia do servidor (UTC);
6. o `PUT` de plano com `null` responde 500;
7. nome de plano vazio é aceito, e a unicidade diferencia maiúsculas;
8. não há como reativar um plano.

## Decisões

As perguntas ao cliente ficaram sem resposta. Foram adotadas estas regras:

- **Carência:** quem cancela continua sócio até o `end_date`, como a spec da AP1 já diz, e não
  assina de novo nesse período (400, mensagem de hoje). Esse é o comportamento que os testes do
  PR #63 fixam.
- **Renovação:** depois do `end_date`, a pessoa assina de novo, inclusive em outro plano, no
  **mesmo registro**. O `user_id` é único na tabela, e mudar isso exigiria uma migração (#6).
- **Vencimento sem tarefa agendada:** uma assinatura `active` com `end_date` no passado vira
  `past_due` quando é lida (`GET /me`, a lista do admin, ou uma nova assinatura). O último dia
  (`end_date` = hoje) ainda vale.
- **Mensalidade:**
  - assinar ou renovar grava uma `Transaction` do tipo `subscription`, com o preço do plano;
  - o corpo `{"payment_method": ...}` é opcional, e o padrão é cartão de crédito;
  - pagar a mensalidade com crédito do próprio Trim Club responde 422.
- **Só clientes assinam:** barbeiros e admins recebem 403.
- **Avisos (#75):** assinar e cancelar criam uma notificação `subscription_notice` para o sócio.

## Critérios de aceitação

1. [ ] Assinatura cancelada ou vencida, com o `end_date` no passado: assinar de novo responde 201,
   com início hoje, fim em 30 dias, status `active` e o mesmo registro. Pode trocar de plano.
   Cancelada ainda no período pago: 400.
2. [ ] Ativa com `end_date` no passado aparece como `past_due` no `/me` e na lista do admin, e
   fica gravada assim. Cancelada continua `canceled`.
3. [ ] Cada assinatura ou renovação grava uma transação `subscription`, e uma assinatura recusada
   não grava nada.
4. [ ] Barbeiro e admin recebem 403 `Apenas clientes podem assinar o Trim Club.`
5. [ ] O `start_date` é o dia em `settings.shop_timezone`. Às 22:00 de 25/11 em Brasília, ele é
   25/11.
6. [ ] `PUT /plans/{id}` com `null` em `name`, `monthly_price`, `included_cuts`,
   `included_shaves`, `discount_percentage` ou `is_active` responde 422. `description: null`
   apaga a descrição.
7. [ ] O nome do plano é aparado, exige pelo menos 1 caractere, e é único sem diferenciar
   maiúsculas.
8. [ ] `PUT` com `is_active: true` reativa o plano, que volta à lista pública.

O teste do PR #63 que compara o `start_date` com `date.today()` passa a aceitar também o dia de
Brasília. Assim ele vale com e sem esta correção, a qualquer hora.

## Testes

`tests/test_trim_club_ciclo.py`, pela API, com o PostgreSQL de `TEST_DATABASE_URL`.
