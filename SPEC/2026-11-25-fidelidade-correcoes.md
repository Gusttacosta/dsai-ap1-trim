# Fidelidade: erros 500, nomes de prêmio, trava no resgate e operações do admin (2026-11-25)

> Complementa: SPEC/2026-09-29-fidelidade.md e SPEC/2026-11-24-testes-integracao-loyalty.md (PR #74)
> Issue: #73

## O quê e por quê

Os testes de integração da fidelidade (PR #74) acharam cinco problemas:
1. dar pontos a um usuário inexistente responde 500;
2. o `PUT` de prêmio com `null` em campo obrigatório responde 500;
3. nome de prêmio vazio é aceito, e dois prêmios podem ter o mesmo nome;
4. o resgate lê o saldo, compara e debita sem trava: dois resgates simultâneos passam com saldo
   para um só, e o saldo fica negativo;
5. o admin não consegue tirar pontos, os resgates não dizem de quem são, e as carteiras não podem
   ser listadas.

Valor: pontos são dinheiro para o cliente. Saldo negativo e resgate em dobro são prejuízo, e o
dono precisa conseguir corrigir um lançamento errado.

## Critérios de aceitação

1. [ ] `POST /api/loyalty/wallet/{id}/add` e `/remove` com um usuário desconhecido respondem
   **404** `Usuário não encontrado.`, sem criar carteira. Pontos ≤ 0 continuam respondendo 400,
   antes da busca pelo usuário.
2. [ ] `PUT /api/loyalty/rewards/{id}` com `name`, `points_cost` ou `is_active` nulos responde
   **422**, e nada muda. `description: null` continua apagando a descrição.
3. [ ] O nome do prêmio é aparado e exige pelo menos 1 caractere (422). Um nome igual ao de outro
   prêmio, **sem diferenciar maiúsculas**, responde **400** `Já existe um prêmio chamado '<nome>'.`
   na criação e na alteração. Manter o próprio nome, mesmo mudando as maiúsculas, é aceito.
4. [ ] **Trava:**
   - o resgate, o crédito e o débito leem a carteira com `SELECT ... FOR UPDATE`. Com saldo para
     um prêmio, quatro resgates simultâneos dão um 201 e três 400, e o saldo termina em 0;
   - `CheckConstraint("balance >= 0")` na carteira, como última defesa. Ele vale nos bancos
     criados a partir de agora; o de produção só ganha a restrição com uma migração (#6).
5. [ ] **Admin:**
   - `POST /api/loyalty/wallet/{user_id}/remove?points=N` tira pontos do saldo, sem mexer no
     `lifetime_points`. Pedir mais que o saldo responde 400, e nada muda;
   - `GET /api/loyalty/wallets` lista as carteiras com o nome e o e-mail do cliente, do maior saldo
     para o menor;
   - os resgates (o de `/redeem` e a lista `/redemptions`) trazem o `user_id`;
   - as rotas novas são só para o admin (403).

## Testes

`tests/test_fidelidade_correcoes.py`, pela API, com o PostgreSQL de `TEST_DATABASE_URL`.
