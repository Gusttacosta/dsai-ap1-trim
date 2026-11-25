# Testes de integração do Trim Club (planos e assinaturas), no lugar dos testes gerados (2026-11-24)

> Complementa: SPEC/2026-11-21-testes-integracao-auth.md (plano da #3, um módulo por PR) e
> SPEC/2026-09-29-assinaturas.md (descreve o comportamento que os testes conferem)
> Issue: #3

## O quê e por quê

Sétimo módulo do plano da #3. O `tests/test_subscriptions.py` herdado da AP1 tem 1.000 funções
geradas que conferem um dict fixo e não importam a aplicação. Ele é trocado por testes de
integração pela API (`/api/subscriptions`), com o PostgreSQL de teste e as fixtures de
`tests/agenda_fixtures.py` e `tests/api_helpers.py`.

As 8 rotas do módulo são:
- **planos:** listagem pública, mais criação, alteração e desativação pelo admin;
- **assinaturas:** a do usuário logado (consultar, assinar e cancelar) e a lista do admin.

O código da aplicação não muda.

Valor: o plano define o preço e os benefícios do clube, e a assinatura diz quem é sócio. Um erro
no preço, na desativação ou no ciclo de 30 dias passa a quebrar a CI.

## Critérios de aceitação

Testes em `tests/test_subscriptions_integracao.py`, com o PostgreSQL de `TEST_DATABASE_URL`:

- [ ] **Planos públicos:** só os ativos, do mais barato para o mais caro, com nome, descrição,
      preço, cortes, barbas e desconto. Sem planos, devolve uma lista vazia.
- [ ] **Criação de plano:**
  - responde 201 com o plano ativo;
  - o preço e o desconto têm duas casas, e cortes, barbas e desconto valem 0 quando omitidos;
  - um nome já usado responde 400 `Já existe um plano com esse nome.`, inclusive o de um plano
    desativado;
  - preço zero ou negativo, cortes ou barbas negativos, desconto fora de 0–100, nome com mais de
    100 caracteres, ou nome ou preço faltando respondem 422.
- [ ] **Alteração de plano:**
  - muda só os campos enviados;
  - trocar para o nome de outro plano responde 400, e manter o próprio é aceito;
  - plano desconhecido responde 404 `Plano não encontrado.`;
  - valores inválidos respondem 422.
- [ ] **Desativação de plano:**
  - responde 204, e o plano sai da lista pública;
  - quem já assinou continua com a assinatura, que mostra o plano com `is_active` falso;
  - plano desconhecido responde 404.
- [ ] **Assinar:**
  - responde 201 com a assinatura `active`, `start_date` igual a hoje e `end_date` 30 dias depois;
  - a resposta traz o plano completo;
  - um plano desconhecido ou desativado responde 400 `Plano inválido ou indisponível.`;
  - quem já tem assinatura, ativa ou cancelada, recebe 400, e nada muda.
- [ ] **Minha assinatura:**
  - devolve a assinatura do usuário do token, com o plano;
  - quem não tem assinatura recebe 404 `Você não possui uma assinatura.`.
- [ ] **Cancelar:**
  - muda o status para `canceled` e mantém as datas (vale até o `end_date`);
  - cancelar de novo responde 400 `Esta assinatura já está cancelada.`;
  - quem não tem assinatura recebe 404 `Assinatura não encontrada.`.
- [ ] **Lista do admin:** todas as assinaturas (ativas e canceladas), da mais recente para a mais
      antiga, cada uma com o seu plano.
- [ ] **Permissões:**
  - sem token, as 4 rotas do admin e as 3 do usuário respondem 403;
  - com token de cliente ou de barbeiro, as 4 rotas do admin respondem 403, e nada muda no banco;
  - a lista de planos é pública.
- [ ] **Os testes testam:** se o corpo de qualquer método de `SubscriptionService` for trocado por
      um `raise`, algum teste novo falha.
- [ ] `tests/test_subscriptions.py` (gerado) é apagado, e `subscriptions` sai da lista `MODULES`
      de `tests/generate_tests.py`.

## Fora do escopo

Mudar o comportamento do módulo. As diferenças encontradas ficam registradas aqui e no PR para
uma issue própria, e não são fixadas pelos testes:
- `PUT /plans/{id}` com `name` ou `monthly_price` nulo responde 500 (`IntegrityError`);
- um nome vazio é aceito, e a unicidade do nome diferencia maiúsculas de minúsculas;
- quem cancelou, ou cuja assinatura venceu, nunca mais consegue assinar: `user_id` é único e o
  `subscribe` recusa qualquer registro existente, sem renovação nem expiração;
- nada muda o status depois do `end_date` (`past_due` nunca é usado);
- assinar não gera `Transaction`, e a spec do financeiro diz que mensalidades geram;
- barbeiros e admins podem assinar;
- `start_date` usa `date.today()` do servidor, e não o fuso da barbearia;
- não há como reativar um plano: o `PUT` ignora `is_active` sem avisar.
