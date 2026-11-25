# Testes de integração dos produtos e do estoque, no lugar dos testes gerados (2026-11-24)

> Complementa: SPEC/2026-11-21-testes-integracao-auth.md (plano da #3, um módulo por PR) e
> SPEC/2026-09-29-produtos.md (descreve o comportamento que os testes conferem)
> Issue: #3

## O quê e por quê

Sexto módulo do plano da #3. O `tests/test_products.py` herdado da AP1 tem 1.000 funções geradas
que conferem um dict fixo e não importam a aplicação. Ele é trocado por testes de integração pela
API (`/api/products`), com o PostgreSQL de teste e as fixtures de `tests/agenda_fixtures.py` e
`tests/api_helpers.py`.

As 8 rotas do módulo são:
- **vitrine pública:** listagem e detalhes;
- **admin:** listagem completa, criação, alteração, desativação, movimentação de estoque e
  histórico.

A venda no balcão, que baixa o estoque pelo `ProductService`, já é testada em
`test_finance_integracao.py`. O código da aplicação não muda.

Valor: a vitrine não pode mostrar o preço de custo, e o estoque não pode ficar negativo nem mudar
sem deixar rastro. Um erro nisso passa a quebrar a CI.

## Critérios de aceitação

Testes em `tests/test_products_integracao.py`, com o PostgreSQL de `TEST_DATABASE_URL`:

- [ ] **Vitrine:**
  - lista só os produtos ativos com estoque, em ordem alfabética;
  - com `show_out_of_stock=true`, também os ativos sem estoque;
  - nunca mostra os desativados;
  - a resposta não tem `cost_price`, `created_at` nem `updated_at`;
  - sem produtos, devolve uma lista vazia.
- [ ] **Detalhes públicos:**
  - devolvem o produto ativo, mesmo sem estoque, sem `cost_price`;
  - produto desconhecido ou desativado responde 404 `Produto não encontrado ou indisponível.`.
- [ ] **Listagem do admin:** todos os produtos (ativos e desativados, com e sem estoque), em
      ordem alfabética, com `cost_price` e as datas.
- [ ] **Criação:**
  - responde 201 com o produto ativo e o estoque em 0, mesmo que o corpo mande `stock_quantity`
    ou `is_active` (campos que o schema ignora);
  - grava nome, descrição, SKU, preço e custo com duas casas, e a foto;
  - nome ou SKU já usados respondem 400 `Já existe um produto com o nome '<nome>'.` /
    `Já existe um produto com o SKU '<sku>'.`, inclusive de um produto desativado;
  - preço ou custo negativos, nome com mais de 150 caracteres, SKU com mais de 50, ou nome ou
    preço faltando respondem 422.
- [ ] **Alteração:**
  - muda só os campos enviados e não mexe no estoque (o corpo com `stock_quantity` é ignorado);
  - trocar para um nome ou SKU de outro produto responde 400, e manter os próprios é aceito;
  - produto desconhecido responde 404 `Produto não encontrado.`;
  - valores inválidos respondem 422.
- [ ] **Desativação:**
  - responde 204;
  - o produto sai da vitrine e dos detalhes públicos, mas continua na listagem do admin, com o
    mesmo estoque e preço;
  - desativar de novo também responde 204;
  - produto desconhecido responde 404.
- [ ] **Movimentação de estoque:**
  - uma entrada positiva (`restock`) soma ao estoque, e uma saída negativa (`loss`, `sale`,
    `adjustment`) subtrai;
  - responde com o produto atualizado;
  - cada movimentação grava a quantidade, o tipo, a nota e o admin que a fez;
  - uma saída que deixaria o estoque negativo responde 400 `Estoque insuficiente. Tentativa de
    remover <n>, mas só existem <m> unidades.`, e nem o estoque nem o histórico mudam;
  - zerar o estoque exatamente é aceito;
  - produto desconhecido responde 400 `Produto não encontrado.`;
  - tipo fora da lista ou quantidade faltando responde 422.
- [ ] **Histórico:**
  - lista as movimentações do produto, da mais recente para a mais antiga, só daquele produto;
  - um produto sem movimentações devolve uma lista vazia;
  - produto desconhecido responde 404 `Produto não encontrado.`.
- [ ] **Permissões:**
  - sem token, as 6 rotas do admin respondem 403;
  - com token de cliente ou de barbeiro, também respondem 403, e nada muda no banco;
  - a vitrine e os detalhes são públicos.
- [ ] **Os testes testam:** se o corpo de qualquer método de `ProductService` for trocado por um
      `raise`, algum teste novo falha.
- [ ] `tests/test_products.py` (gerado) é apagado, e `products` sai da lista `MODULES` de
      `tests/generate_tests.py`.

## Fora do escopo

Mudar o comportamento do módulo. As diferenças encontradas vão para uma issue própria e não são
fixadas pelos testes:
- `PUT` com `name` ou `price` nulo responde 500 (`IntegrityError`);
- `image_url` com mais de 500 caracteres, na criação ou na alteração, responde 500;
- um segundo produto com `sku` vazio (`""`) responde 500: a checagem trata `""` como ausente, mas
  a coluna é única;
- nome vazio é aceito, e a unicidade do nome diferencia maiúsculas de minúsculas;
- a movimentação aceita quantidade 0, e o sinal não depende do tipo: `sale` e `loss` positivos
  aumentam o estoque, e `restock` negativo diminui;
- produto desativado aceita movimentação;
- não há como reativar um produto: o `PUT` ignora `is_active` sem avisar.
