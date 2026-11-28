# Trim Club: planos e assinantes no painel, assinatura na conta do cliente (2026-11-26)

> Complementa: SPEC/2026-11-25-trim-club-ciclo.md (as rotas, as regras e as mensagens que estas
> telas usam) e SPEC/2026-09-29-assinaturas.md
> Issue: #108

## O quê e por quê

O backend do Trim Club está pronto (#64), mas só a vitrine `/club` usa a API. O painel não tem aba
de Trim Club, então o admin cria, edita e desativa planos chamando a API à mão e não vê quem
assina. Na conta, o cliente não vê a própria assinatura nem consegue cancelá-la.

Esta spec entrega, só no frontend:

| Ação | Rota | Quem |
|---|---|---|
| Planos (lista) | `GET /api/subscriptions/plans` (só os ativos) | admin, nesta tela |
| Criar plano | `POST /api/subscriptions/plans` | admin |
| Editar plano | `PUT /api/subscriptions/plans/{id}` | admin |
| Excluir plano | `DELETE /api/subscriptions/plans/{id}` (desativa) | admin |
| Assinantes | `GET /api/subscriptions/users` | admin |
| Nome do assinante | `GET /api/auth/users/{id}` | admin |
| Minha assinatura | `GET /api/subscriptions/me` | cliente |
| Cancelar | `PUT /api/subscriptions/me/cancel` | cliente |

Valor: o dono monta e ajusta os planos sem mexer na API e acompanha os sócios; o cliente sabe até
quando a assinatura vale e cancela sozinho.

## Regras da tela

### Menu e acesso (`/admin/trim-club`)

- O item "Trim Club" e a rota aparecem só para o **admin**, como as outras abas de admin. O
  barbeiro e o cliente não veem o item nem a tela, e nada chama `/subscriptions/users`.

### Planos

- Tabela com nome (e descrição), preço mensal (`R$ 49,90`), benefícios e ações, na ordem do
  backend (preço crescente). Vazio: "Nenhum plano cadastrado.".
- Benefícios, como na vitrine: "Cortes: 2 por mês" ou "Cortes: Ilimitados" (nada quando é 0), o
  mesmo para "Barbas", e "Desconto: 10%" quando o desconto é maior que zero.
- "+ Novo plano" e "Editar" abrem o formulário (`AdminForm`):
  - nome, de 1 a 100 caracteres sem contar os espaços das pontas:
    `Nome do plano deve ter entre 1 e 100 caracteres`;
  - descrição (opcional), aparada; vazia vai como `null`;
  - preço mensal maior que zero, com até 2 casas:
    `Preço mensal deve ser maior que zero, com até 2 casas decimais`;
  - cortes e barbas inclusos: inteiro de 0 a 999, ou a caixa "Ilimitados" marcada (vai `null`):
    `Cortes inclusos deve ser um número inteiro de 0 a 999` (e o mesmo para "Barbas inclusas");
  - desconto de 0 a 100%, com até 2 casas (vazio = 0):
    `Desconto deve ser de 0 a 100%, com até 2 casas decimais`.
- Tudo é conferido antes da API. A edição manda só os campos que mudaram ("Nada mudou." quando
  nenhum mudou). O erro da API (nome repetido, 400, ou a lista do 422) aparece no formulário.
- "Excluir" pede confirmação na linha ("Excluir o plano? Ele sai da vitrine, e quem já assina
  continua com ele."), chama o `DELETE` e tira o plano da lista. A falha mostra a mensagem da API
  e o plano continua.

### Assinantes

- Tabela com cliente (nome e e-mail de `GET /auth/users/{id}`, ou "Cliente não encontrado"
  quando a consulta falha), plano, início, fim (`26/11/2026`) e situação: "Ativa", "Cancelada" ou
  "Vencida" (`active`, `canceled`, `past_due`), na ordem do backend (mais nova primeiro).
- Carregando, erro com a mensagem da API e "Tentar de novo", e "Nenhum assinante ainda.".
- A lista é só de leitura.

### Minha assinatura (`/conta`, só cliente)

- Seção "Trim Club" acima de "Meus agendamentos". Admin e barbeiro não veem a seção nem chamam
  `/subscriptions/me`.
- Com assinatura: o plano, o preço, os benefícios (as mesmas frases dos planos), a situação e a
  validade:
  - ativa: "Renova em 26/12/2026." e o botão "Cancelar assinatura";
  - cancelada: "Cancelada. Seus benefícios valem até 26/12/2026.";
  - vencida: "Venceu em 26/12/2026." e o link "Assinar de novo" para `/club`.
- "Cancelar assinatura" pede confirmação ("Cancelar a assinatura? Os benefícios valem até
  26/12/2026."), chama o `PUT /me/cancel` e mostra a assinatura como o backend devolveu, com o
  aviso "Assinatura cancelada.". A falha mostra a mensagem da API e a assinatura continua ativa.
- Sem assinatura (404): "Você ainda não é sócio do Trim Club." e o link "Conhecer os planos"
  para `/club`. Outro erro: a mensagem da API e "Tentar de novo".

### Reaproveitamento (jscpd ≤ 5%)

- Carga e ações: `useApiResource` e `useRowAction`; tela: `LoadState`, `ActionFeedback`,
  `ConfirmButton`, `AdminForm`, `FormField`, `StatusBadge` e `AdminShared.module.css`; conta:
  `Account.module.css`.
- Os benefícios do plano (`quantityLabel` da vitrine) viram um utilitário usado pela vitrine,
  pelo painel e pela conta. O preço usa `parsePrice` e `formatPrice` dos serviços.
- `StatusBadge` passa a aceitar um texto, para a situação da assinatura; sem o texto, continua
  "Ativo" e "Desativado".

## Critérios de aceitação

Testes vitest (com a API simulada) que falham se as telas forem desfeitas:

- [ ] O admin vê "Trim Club" no menu e a tela em `/admin/trim-club`; o barbeiro e o cliente não,
      e nenhum dos dois chama `/subscriptions/users`.
- [ ] Criar manda todos os campos no formato da API, com `null` nos ilimitados, e põe o plano na
      lista; editar manda só o que mudou e atualiza a linha.
- [ ] Nome vazio ou longo, preço zero ou inválido, quantidade negativa ou fracionária e desconto
      acima de 100 são recusados na tela, sem chamada. O 400 e o 422 da API aparecem no formulário.
- [ ] Excluir pede confirmação, chama `DELETE /subscriptions/plans/{id}` e tira o plano; a falha
      mostra a mensagem da API e o plano continua.
- [ ] Assinantes mostram o nome do cliente, o plano, as datas e a situação; a falha na carga mostra
      a mensagem e "Tentar de novo".
- [ ] Na conta, o cliente vê a assinatura ativa; cancelar pede confirmação, chama
      `PUT /subscriptions/me/cancel` e mostra a validade; a falha mostra a mensagem da API. O 404
      mostra o convite para `/club`. Admin e barbeiro não veem a seção.
- [ ] A vitrine `/club` continua mostrando os benefícios como antes (testes existentes).

## Fora do escopo

- Backend: nenhuma rota nova ou alterada.
- Listar e reativar planos desativados: o `GET /plans` só devolve os ativos, e não há rota de
  admin que liste os desativados (o `PUT` com `is_active: true` existe, mas a tela não tem como
  achar o plano).
- Assinar ou trocar de plano pela conta (continua em `/club`).
- Filtros, busca e paginação da lista de assinantes.
