# Testes de integração da fidelidade (pontos e prêmios), no lugar dos testes gerados (2026-11-24)

> Complementa: SPEC/2026-11-21-testes-integracao-auth.md (plano da #3, um módulo por PR) e
> SPEC/2026-09-29-fidelidade.md (descreve o comportamento que os testes conferem)
> Issue: #3

## O quê e por quê

Décimo segundo módulo do plano da #3. O `tests/test_loyalty.py` herdado da AP1 tem 1.000 funções
geradas que conferem um dict fixo e não importam a aplicação. Ele é trocado por testes de
integração pela API (`/api/loyalty`), com o PostgreSQL de teste e as fixtures de
`tests/agenda_fixtures.py` e `tests/api_helpers.py`.

As 7 rotas do módulo são:
- **usuário logado:** a própria carteira e o resgate de um prêmio;
- **pública:** o catálogo de prêmios ativos;
- **admin:** criar e alterar prêmios, dar pontos a um cliente e ver os resgates.

Hoje nenhum fluxo da barbearia gera pontos (#13): eles só entram pelo admin. O código da aplicação
não muda.

Valor: o saldo é o "dinheiro" do cliente no programa. Um saldo que fica negativo, um resgate que
não debita ou pontos que somem passam a quebrar a CI.

## Critérios de aceitação

Testes em `tests/test_loyalty_integracao.py`, com o PostgreSQL de `TEST_DATABASE_URL`:

- [ ] **Carteira:**
  - no primeiro acesso a `/me`, nasce uma carteira zerada (saldo e pontos acumulados) para o
    usuário do token;
  - os acessos seguintes devolvem a mesma carteira, sem criar outra;
  - cada usuário tem a sua.
- [ ] **Pontos dados pelo admin:**
  - somam ao saldo e aos pontos acumulados, e criam a carteira se ela ainda não existir;
  - zero ou negativo responde 400 `A quantidade de pontos deve ser maior que zero.`, e nada muda;
  - sem `points`, ou com valor que não é inteiro, responde 422.
- [ ] **Catálogo:**
  - lista só os prêmios ativos, do mais barato para o mais caro;
  - sem prêmios, devolve uma lista vazia.
- [ ] **Criação e alteração de prêmio (admin):**
  - a criação responde 201 com o prêmio ativo;
  - a alteração muda só os campos enviados, e `is_active: false` tira o prêmio do catálogo
    (`true` devolve);
  - prêmio desconhecido responde 404 `Prêmio não encontrado.`;
  - custo zero ou negativo, nome com mais de 150 caracteres, descrição com mais de 500, ou nome ou
    custo faltando respondem 422.
- [ ] **Resgate:**
  - com saldo suficiente, responde 201 com o resgate (pontos gastos e o prêmio), debita o saldo e
    mantém os pontos acumulados;
  - gastar exatamente o saldo deixa zero;
  - com saldo insuficiente, responde 400 `Saldo insuficiente. Você possui <n> pts e o prêmio custa
    <m> pts.`, e nada muda;
  - um prêmio desconhecido ou inativo responde 400 `Prêmio não encontrado ou inativo.`;
  - o resgate grava o custo do momento: mudar o custo depois não muda o resgate.
- [ ] **Resgates (admin):** todos os resgates, do mais recente para o mais antigo, com o prêmio de
      cada um.
- [ ] **Permissões:**
  - sem token, a carteira e o resgate respondem 403;
  - sem token, ou com token de cliente ou de barbeiro, as 4 rotas do admin respondem 403, e nada
    muda no banco;
  - o catálogo é público.
- [ ] **Os testes testam:** se o corpo de qualquer método de `LoyaltyService` for trocado por um
      `raise`, algum teste novo falha.
- [ ] `tests/test_loyalty.py` (gerado) é apagado, e `loyalty` sai da lista `MODULES` de
      `tests/generate_tests.py`.

## Fora do escopo

Mudar o comportamento do módulo. As diferenças encontradas vão para uma issue própria e não são
fixadas pelos testes:
- nenhum fluxo gera pontos (#13): atendimento concluído, compra e assinatura não somam nada;
- dar pontos a um usuário que não existe responde 500 (FK);
- `PUT /rewards/{id}` com `name`, `points_cost` ou `is_active` nulos responde 500
  (`IntegrityError`);
- nome de prêmio vazio é aceito, e dois prêmios podem ter o mesmo nome;
- o resgate lê e debita o saldo sem trava (`SELECT ... FOR UPDATE`): dois resgates ao mesmo tempo
  podem passar com saldo para um só;
- o admin não tem como tirar pontos (estorno), nem ver de quem é cada resgate (a resposta só traz
  `wallet_id`).
