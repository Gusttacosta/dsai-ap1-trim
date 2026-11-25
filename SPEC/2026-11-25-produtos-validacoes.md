# Produtos: validações, sinal da movimentação, produto desativado e reativação (2026-11-25)

> Complementa: SPEC/2026-09-29-produtos.md e SPEC/2026-11-24-testes-integracao-products.md (PR #62)
> Issue: #61

## O quê e por quê

Os testes de integração dos produtos (PR #62) acharam três erros 500, validações frouxas, uma
movimentação de estoque que aceita o sinal trocado e a falta de reativação. Este PR corrige
todos os itens da #61. As perguntas ao cliente ficaram sem resposta, então foram adotadas as
decisões abaixo.

## Decisões

- **Nome único sem diferenciar maiúsculas:** "Pomada" e "pomada" são o mesmo produto na vitrine.
- **Sinal pela regra da spec da AP1:**
  - `restock` é entrada (positivo);
  - `sale` e `loss` são saídas (negativos);
  - `adjustment` vale para os dois lados, porque é uma correção de inventário;
  - zero não é movimentação.
- **Produto desativado:** recusa `sale` e `restock`, mas aceita `loss` e `adjustment`. Assim dá
  para zerar o que sobrou no estoque de um produto que saiu de linha. Uma devolução de um produto
  desativado entra como `adjustment`. Com isso, o caixa também deixa de vender produto desativado
  (item 2 da #59).

## Critérios de aceitação

1. [ ] `PUT /api/products/{id}` com `name`, `price` ou `is_active` nulos responde **422**, e nada
   muda. `null` em `description`, `sku`, `cost_price` e `image_url` limpa o campo.
2. [ ] `image_url` com mais de 500 caracteres (o tamanho da coluna) responde **422** na criação e
   na alteração. Com 500 caracteres, é aceita.
3. [ ] SKU vazio ou só com espaços vira `null`, na criação e na alteração. Vários produtos sem SKU
   convivem.
4. [ ] O nome é aparado e exige pelo menos 1 caractere (422), no `POST` e no `PUT`.
5. [ ] Um nome igual ao de outro produto, sem diferenciar maiúsculas, responde 400 com a mesma
   mensagem de hoje. Mudar só as maiúsculas do próprio nome é aceito.
6. [ ] `POST /{id}/inventory` responde **422** nestes casos, sem mudar nada:
   - quantidade 0;
   - `restock` negativo;
   - `sale` ou `loss` positivos.

   `adjustment` aceita os dois sinais.
7. [ ] Produto desativado: `sale` e `restock` respondem **400** `Produto desativado: só aceita
   perda ou ajuste de estoque.`, e `loss` e `adjustment` funcionam. No caixa,
   `POST /api/finance/checkout/product` de um produto desativado responde 400, e o estoque não
   muda.
8. [ ] `PUT` com `is_active: true` reativa o produto, que volta à vitrine. Com `false`, desativa.

Os testes do PR #62 continuam passando: as mensagens e os status de hoje se mantêm, e o
movimento de um produto desconhecido continua respondendo 400.

## Testes

`tests/test_produtos_validacoes.py`, pela API, com o PostgreSQL de `TEST_DATABASE_URL`.
