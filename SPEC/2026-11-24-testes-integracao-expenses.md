# Testes de integração das despesas, no lugar dos testes gerados (2026-11-24)

> Complementa: SPEC/2026-11-21-testes-integracao-auth.md (plano da #3, um módulo por PR) e
> SPEC/2026-09-29-despesas.md (descreve o comportamento que os testes conferem)
> Issue: #3

## O quê e por quê

Oitavo módulo do plano da #3. O `tests/test_expenses.py` herdado da AP1 tem 1.000 funções geradas
que conferem um dict fixo e não importam a aplicação. Ele é trocado por testes de integração pela
API (`/api/expenses`), com o PostgreSQL de teste e as fixtures de `tests/agenda_fixtures.py` e
`tests/api_helpers.py`.

As 6 rotas do módulo são só do admin:
- **categorias:** listagem e criação;
- **despesas:** listagem com filtro de data, criação, alteração e exclusão física.

O código da aplicação não muda.

Valor: as despesas entram no fechamento do mês contra as receitas. Um erro no valor, na data ou no
filtro de período passa a quebrar a CI.

## Critérios de aceitação

Testes em `tests/test_expenses_integracao.py`, com o PostgreSQL de `TEST_DATABASE_URL`:

- [ ] **Categorias:**
  - a criação responde 201 com o nome e a data;
  - a listagem devolve todas, em ordem alfabética, ou uma lista vazia;
  - um nome já usado responde 400 `Já existe uma categoria chamada '<nome>'.`;
  - nome com mais de 100 caracteres, ou faltando, responde 422.
- [ ] **Criação de despesa:**
  - responde 201 com a descrição, o valor (duas casas no banco), a data de pagamento, se é
    recorrente (falso por padrão) e a categoria completa;
  - sem categoria, `category` vem nulo;
  - uma categoria desconhecida responde 400 `Categoria informada não existe.`, e nada é gravado;
  - valor zero ou negativo, descrição com mais de 255 caracteres, data inválida, ou descrição,
    valor ou data faltando respondem 422.
- [ ] **Listagem de despesas:**
  - da data de pagamento mais recente para a mais antiga, com a categoria de cada uma;
  - `start_date` e `end_date` filtram pelo período, com as duas pontas incluídas, e funcionam
    sozinhos;
  - sem despesas, ou sem nenhuma no período, devolve uma lista vazia.
- [ ] **Alteração de despesa:**
  - muda só os campos enviados, inclusive trocar ou tirar a categoria (`category_id` nulo);
  - uma categoria desconhecida responde 400, e nada muda;
  - despesa desconhecida responde 404 `Despesa não encontrada.`;
  - valores inválidos respondem 422.
- [ ] **Exclusão:**
  - responde 204 e apaga a despesa do banco (exclusão física), sem mexer nas outras nem na
    categoria;
  - excluir de novo, ou uma despesa desconhecida, responde 404.
- [ ] **Permissões:** sem token, ou com token de cliente ou de barbeiro, as 6 rotas respondem 403, e
      nada muda no banco.
- [ ] **Os testes testam:** se o corpo de qualquer método de `ExpenseService` for trocado por um
      `raise`, algum teste novo falha.
- [ ] `tests/test_expenses.py` (gerado) é apagado, e `expenses` sai da lista `MODULES` de
      `tests/generate_tests.py`.

## Fora do escopo

Mudar o comportamento do módulo. As diferenças encontradas ficam registradas aqui e no PR para
uma issue própria, e não são fixadas pelos testes:
- `PUT /{id}` com `description`, `amount`, `payment_date` ou `is_recurring` nulos responde 500
  (`IntegrityError`);
- nome de categoria e descrição vazios são aceitos;
- não há como renomear nem apagar uma categoria;
- um período invertido (`start_date` depois de `end_date`) devolve uma lista vazia, sem aviso;
- a resposta da criação devolve o valor como foi enviado (`100.5`), e não com as duas casas
  gravadas no banco (`100.50`).
