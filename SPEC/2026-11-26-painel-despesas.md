# Painel do admin: despesas e categorias (2026-11-26)

> Complementa: SPEC/2026-11-25-despesas-validacoes.md (as rotas e as regras que esta tela usa) e
> SPEC/2026-09-29-despesas.md
> Issue: #104

## O quê e por quê

O backend lista, cria, altera e apaga despesas e categorias (#65), mas nenhuma tela usa essas
rotas. O Financeiro do painel tem uma tabela de despesas que nunca é preenchida, com o texto
"Buscando despesas na API... (Você pode criar a rota GET /expenses depois)", e um botão
"+ Lançar Despesa" sem ação. O dono lança as despesas chamando a API à mão.

Esta spec entrega a aba **"Despesas"** no painel do admin (`/admin/despesas`), só no frontend:

| Ação | Rota |
|---|---|
| Lista, com o período | `GET /api/expenses?start_date=&end_date=` |
| Criar, alterar, apagar | `POST /api/expenses`, `PUT` e `DELETE /api/expenses/{id}` |
| Categorias | `GET` e `POST /api/expenses/categories`, `PUT` e `DELETE /api/expenses/categories/{id}` |

Valor: o dono registra e corrige as saídas do caixa pelo painel.

## Regras da tela

### Menu e acesso

- O item "Despesas" e a rota aparecem só para o admin, como as outras abas de gestão.
- No Financeiro, a tabela falsa e o botão sem ação saem; no lugar, um link "Gerenciar despesas"
  para a aba nova. Os cartões do resumo ficam como estão.

### Lista

- Colunas: data (`20/11/2026`), descrição, categoria ("Sem categoria" quando não tem), valor
  (`R$ 100,50`), "Recorrente" (Sim/Não) e ações. Na ordem do backend (data mais recente primeiro).
- Abaixo da tabela, o total das despesas listadas.
- Carregando, erro com a mensagem da API e "Tentar de novo", e "Nenhuma despesa no período."
- Filtros:
  - **Período:** "De" e "Até" (campos de data). Vão para a API como `start_date` e `end_date`;
    vazio não filtra. A recusa do período invertido (422 da API) aparece como erro da carga.
  - **Categoria:** "Todas", cada categoria e "Sem categoria". Filtra na tela (a API não tem esse
    filtro), e o total acompanha.
- Ações de cada linha: "Editar" e "Excluir" (pede confirmação na linha).

### Formulário (criar e editar)

- Campos: descrição, valor (R$), data do pagamento, categoria (opcional) e "Despesa recorrente".
- Criar manda todos os campos. Editar manda só o que mudou; trocar para "Sem categoria" manda
  `category_id: null`. Sem mudança, "Nada mudou." sem chamar a API.
- Antes da API, com as regras do backend:
  - descrição de 1 a 255 caracteres, sem contar os espaços das pontas:
    `Descrição deve ter entre 1 e 255 caracteres`
  - valor acima de 0, até 99.999.999,99, com até 2 casas, vírgula ou ponto:
    `Valor deve ser maior que 0 e até 99.999.999,99, com até 2 casas decimais`
  - data obrigatória: `Informe a data do pagamento`
- O erro da API (400 ou a lista do 422) aparece no formulário.

### Categorias

- Seção "Categorias" na mesma tela, com a lista em ordem alfabética (a do backend).
- "Adicionar": nome de 1 a 100 caracteres (`Nome da categoria deve ter entre 1 e 100
  caracteres`), conferido antes da API. O nome repetido (400) mostra a mensagem da API.
- "Renomear" troca o nome pelo campo, na própria linha, com "Salvar" e "Cancelar".
- "Excluir" pede confirmação ("Excluir a categoria? As despesas ficam sem categoria."). Depois de
  excluir, as despesas dela aparecem como "Sem categoria", sem recarregar a lista; o filtro que
  apontava para ela volta a "Todas". Renomear atualiza o nome nas despesas da lista.

### Reaproveitamento (jscpd ≤ 5%)

- Carga e ações: `useApiResource` e `useRowAction`; tela: `LoadState`, `ActionFeedback`,
  `ConfirmButton`, `AdminForm` e `FormField`; valor: `parsePrice` e `formatPrice` de
  `serviceValidation`.

## Critérios de aceitação

Testes vitest (com a API simulada) que falham se a tela for desfeita:

- [ ] O admin vê "Despesas" no menu e a tela em `/admin/despesas`; o barbeiro não vê nenhum dos
      dois. O Financeiro tem o link "Gerenciar despesas" e não tem mais a tabela falsa.
- [ ] A lista usa `GET /expenses` com o período; o filtro de categoria (e "Sem categoria") muda a
      lista e o total. O 422 do período invertido aparece na tela.
- [ ] Criar manda todos os campos e põe a despesa na lista; editar manda só o que mudou e `null`
      para tirar a categoria; sem mudança, "Nada mudou." sem chamada.
- [ ] Descrição vazia, valor zero, negativo, com 3 casas ou acima do limite e data vazia são
      recusados na tela, sem chamada. O erro da API aparece no formulário.
- [ ] Excluir pede confirmação, chama `DELETE /expenses/{id}` e tira a linha; a falha mostra a
      mensagem da API e a linha continua.
- [ ] Categorias: criar, renomear e excluir com confirmação; nome repetido mostra o 400 da API;
      excluir deixa as despesas dela "Sem categoria".
- [ ] Falha na carga das despesas ou das categorias mostra a mensagem da API e "Tentar de novo".

## Fora do escopo

- Backend: nenhuma rota nova ou alterada; o filtro por categoria é feito na tela.
- Lançamento automático das despesas recorrentes.
- Resumo financeiro (`/reports/financial-summary`) e os cartões do Financeiro.
