# Estoque no painel: quantidade, estoque baixo, histórico e movimentação (2026-11-26)

> Complementa: SPEC/2026-09-29-produtos.md (o estoque e a trilha de auditoria) e
> SPEC/2026-11-25-produtos-validacoes.md (#61: o sinal pelo tipo e o produto desativado)
> Issue: #112

## O quê e por quê

O backend do estoque está pronto, mas a tela "Loja & Estoque" do painel carrega a vitrine pública
(`GET /api/products`): o produto sem estoque e o desativado somem da tela do admin, justamente os
que ele precisa repor. Não há histórico nem como registrar uma entrada ou saída, e os botões
"+ Novo Produto", "Editar" e "Excluir" não fazem nada.

| Ação | Rota | Quem |
|---|---|---|
| Produtos (ativos e desativados, por nome) | `GET /api/products/admin/all` | admin |
| Histórico (a mais nova primeiro) | `GET /api/products/{id}/inventory` | admin |
| Registrar movimentação (devolve o produto) | `POST /api/products/{id}/inventory` | admin |

Valor: o dono vê o que acabou ou está acabando, registra a reposição e a perda com o motivo, e
confere depois quem mexeu no estoque e quando.

Não há backend novo.

## Regras da tela (`/admin/loja`)

### Menu e acesso

- O item "Loja & Estoque" e a rota continuam só do **admin**. O barbeiro e o cliente não veem o
  item nem a tela, e nada chama `/products/admin/all`.

### Produtos

- Tabela com o produto (nome e SKU), a situação (`StatusBadge`: "Ativo" ou "Desativado"), o preço
  (`R$ 45,00`), o estoque (`12 un`) e as ações, na ordem do backend (nome). Vazio:
  "Nenhum produto cadastrado.".
- **Estoque baixo:** produto ativo com 1 a 5 unidades mostra "Estoque baixo" ao lado da
  quantidade; com 0, "Sem estoque". O desativado não tem aviso.
- Acima da tabela, um resumo dos ativos que precisam de reposição:
  "2 produtos com estoque baixo ou zerado: Óleo, Pomada." (ou "1 produto ..."). Sem nenhum, o
  resumo não aparece.
- Carregando, erro com a mensagem da API e "Tentar de novo".

### Histórico

- "Histórico" abre, abaixo do topo, a tabela "Histórico de <produto>": data e hora no fuso da
  barbearia (`qui., 26/11/2026 às 14:30`), o tipo ("Reposição", "Venda", "Perda", "Ajuste"), a
  quantidade com o sinal (`+10 un`, `-2 un`) e a observação ("—" sem ela), na ordem do backend.
  Vazio: "Nenhuma movimentação ainda.". Carregando, erro e "Tentar de novo" como na lista.
  "Fechar histórico" fecha.

### Movimentação

- "Movimentar" abre o formulário (`AdminForm`) "Movimentar estoque de <produto>", com o estoque
  atual:
  - tipo, numa lista: "Entrada: reposição" (`restock`, +), "Entrada: ajuste de inventário"
    (`adjustment`, +), "Saída: venda" (`sale`, −), "Saída: perda ou avaria" (`loss`, −) e
    "Saída: ajuste de inventário" (`adjustment`, −). O produto desativado oferece só perda e
    ajuste, como o backend (#61);
  - quantidade, inteiro de 1 a 10.000, sem sinal: `Quantidade deve ser um número inteiro de 1 a
    10.000`. O sinal sai do tipo;
  - observação (opcional), aparada, até 500 caracteres; vazia vai como `null`:
    `Observação deve ter até 500 caracteres`.
- A saída maior que o estoque é recusada na tela: `Estoque insuficiente: há só 3 un.`.
- Com os campos válidos, o formulário **pede confirmação** (`confirm` do `AdminForm`):
  "Registrar saída de 2 un de Pomada (perda ou avaria)? O estoque passa de 10 para 8 un.", com
  "Confirmar" e "Voltar". "Voltar", ou mudar um campo, volta ao formulário sem chamar a API.
- "Confirmar" manda `{movement_type, quantity, notes}` com o sinal, põe na linha o produto que o
  backend devolveu e mostra "Movimentação registrada.". O histórico aberto do mesmo produto é
  recarregado.
- O erro da API (400 do estoque insuficiente ou do produto desativado, a lista do 422) aparece no
  formulário, e o estoque da linha não muda.

### Reaproveitamento (jscpd ≤ 5%)

- Carga e ações: `useApiResource` e o `upsert` da lista de nomes; tela: `LoadState`,
  `ActionFeedback`, `AdminForm` (com `confirm`), `FormField`, `StatusBadge` e
  `AdminShared.module.css`.
- O inteiro positivo (os pontos da fidelidade e a quantidade) usa a mesma conferência, com o teto
  de cada um.

## Critérios de aceitação

Frontend (vitest, com a API simulada), que falham se a tela for desfeita:

- [ ] O admin vê "Loja & Estoque" e a tela em `/admin/loja`, que chama `/products/admin/all`; o
      barbeiro e o cliente não.
- [ ] A lista mostra os produtos sem estoque e os desativados, com a situação, o preço e o
      estoque; "Estoque baixo" e "Sem estoque" só nos ativos, e o resumo lista os ativos assim.
- [ ] "Histórico" mostra a data, o tipo, a quantidade com sinal e a observação; vazio e falha
      (com "Tentar de novo") têm mensagem.
- [ ] Quantidade vazia, zero, fracionária ou acima de 10.000, observação longa e saída maior que o
      estoque são recusadas sem chamada.
- [ ] O movimento válido mostra a pergunta; só "Confirmar" chama o `POST` com o tipo e o sinal
      certos; "Voltar" não chama. O estoque novo aparece na linha, e o histórico aberto recarrega.
- [ ] Produto desativado oferece só perda e ajuste.
- [ ] O 400 e o 422 da API aparecem no formulário, e o estoque da linha continua.

## Fora do escopo

- Criar, editar, desativar e reativar produtos: os botões que não faziam nada saem da tela.
- Mostrar quem registrou cada movimentação: a resposta só traz o `user_id`.
- Alerta de estoque baixo por notificação ou e-mail (SPEC/2026-09-29-produtos.md).
- Os limites de 10.000 unidades e de 500 caracteres na observação são só da tela.
- Filtros, busca e paginação dos produtos e do histórico.
