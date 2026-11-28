# Despesas: validações que faltavam e categorias editáveis (2026-11-25)

> Complementa: SPEC/2026-09-29-despesas.md e SPEC/2026-11-24-testes-integracao-expenses.md
> Issue: #65

## O quê e por quê

Os testes de integração das despesas (PR #66) acharam cinco problemas:
- `null` no `PUT` derruba a rota com 500;
- nomes e descrições vazios são aceitos;
- não há como renomear nem apagar uma categoria;
- um período invertido devolve uma lista vazia sem aviso;
- a criação devolve o valor como foi enviado (`100.5`), e não como foi gravado (`100.50`).

Ao corrigir, apareceu mais um: um valor acima do que cabe em `Numeric(10, 2)` (por exemplo,
`100000000`) também respondia 500. Ele entra neste PR.

Valor: é a tela de despesas do painel do dono. Erros 500 e listas vazias sem explicação fazem o
dono achar que perdeu dados.

## Critérios de aceitação

- [ ] **`PUT /api/expenses/{id}`** com `description`, `amount`, `payment_date` ou `is_recurring`
  nulos responde **422**, e nada muda. `category_id: null` continua tirando a categoria.
- [ ] **Textos:** o nome da categoria e a descrição da despesa são aparados (`strip`) e exigem
  pelo menos 1 caractere. Vazio ou só com espaços responde 422, na criação e na alteração.
- [ ] **Valor:**
  - acima de 0;
  - no máximo 99.999.999,99, o limite de `Numeric(10, 2)`;
  - no máximo 2 casas decimais.

  Fora disso responde 422. A resposta da criação e a da alteração devolvem o valor com 2 casas,
  igual à listagem.
- [ ] **Período invertido:** `GET /api/expenses` com `start_date` depois de `end_date` responde
  **422** `A data inicial não pode ser depois da data final.` O mesmo dia nas duas datas continua
  valendo.
- [ ] **`PUT /api/expenses/categories/{id}`** (admin) renomeia a categoria:
  - nome repetido em outra categoria responde 400;
  - repetir o próprio nome é aceito;
  - id desconhecido responde 404 `Categoria não encontrada.`
- [ ] **`DELETE /api/expenses/categories/{id}`** (admin) apaga a categoria e responde 204. As
  despesas dela continuam, sem categoria (a FK já tem `ON DELETE SET NULL`). Um id desconhecido
  responde 404.
- [ ] Barbeiro e cliente recebem 403 nas duas rotas novas.

## Testes

`tests/test_despesas_validacoes.py`, pela API, com o PostgreSQL de `TEST_DATABASE_URL`.
