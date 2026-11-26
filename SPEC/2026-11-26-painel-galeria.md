# Galeria: envio de fotos, moderação no painel e filtro por tag (2026-11-26)

> Complementa: SPEC/2026-11-25-galeria-permissoes.md (as rotas, as regras e as permissões que
> estas telas usam) e SPEC/2026-09-29-galeria.md
> Issue: #106

## O quê e por quê

O backend da galeria está pronto (#71), mas nenhuma tela usa as rotas. A página pública
`/galeria` mostra fotos e tags fixas (`MOCK_PHOTOS` e `MOCK_TAGS` em `pages/Gallery.tsx`), e o
painel não tem aba de galeria: o barbeiro não envia foto, e o admin só modera chamando a API à
mão.

Esta spec entrega, só no frontend:

| Ação | Rota | Quem |
|---|---|---|
| Galeria pública e filtro por tag | `GET /api/gallery?tag_id=` | todos |
| Tags (filtro e formulário) | `GET /api/gallery/tags` | todos |
| Nome dos barbeiros e escolha do barbeiro | `GET /api/barbers` (só os ativos) | todos |
| Enviar foto | `POST /api/gallery` | barbeiro e admin |
| Fotos pendentes | `GET /api/gallery/pending` | admin |
| Aprovar, recusar, desaprovar | `PUT /api/gallery/{id}/approve`, `/reject`, `/unapprove` | admin |
| Excluir foto | `DELETE /api/gallery/{id}` | admin (nesta tela) |
| Criar, renomear, excluir tag | `POST /api/gallery/tags`, `PUT` e `DELETE /api/gallery/tags/{id}` | admin |

Valor: o barbeiro mostra o próprio trabalho, o dono decide o que vai para a vitrine, e o cliente
vê fotos reais e filtra pelo estilo que procura.

## Regras da tela

### Menu e acesso (`/admin/galeria`)

- O item "Galeria" e a rota aparecem para o **admin e o barbeiro** (os dois enviam fotos).
- O barbeiro vê só o botão de envio. Pendentes, publicadas e tags aparecem só para o admin, e a
  tela do barbeiro não chama as rotas de admin (`/gallery/pending`).
- O cliente não vê o item nem a tela: o login não o leva ao painel, mas `/admin` abre para
  qualquer conta, então a aba confere o perfil.

### Enviar foto ("+ Enviar foto")

- Campos: URL da imagem, descrição (opcional), tags (caixas de marcar, opcionais) e, só para o
  admin, o barbeiro (lista dos barbeiros ativos de `GET /barbers`, obrigatório).
- Antes da API, com as regras do backend:
  - URL obrigatória, começando com `http://` ou `https://`, até 1.000 caracteres:
    `Informe a URL da imagem (http ou https, até 1.000 caracteres)`
  - descrição até 500 caracteres: `Descrição deve ter até 500 caracteres`
  - admin sem barbeiro escolhido: `Escolha o barbeiro da foto`
- A descrição é aparada, e vazia não é enviada. O barbeiro não manda `barber_id` (o backend usa o
  perfil dele).
- Depois de enviar: o barbeiro vê "Foto enviada. Ela aparece na galeria depois da aprovação."; o
  admin vê "Foto publicada." e a foto entra na lista de publicadas.
- O erro da API (400, 403, 404 ou a lista do 422) aparece no formulário.

### Fotos pendentes e publicadas (só admin)

- Duas listas: "Pendentes" (`GET /gallery/pending`) e "Publicadas" (`GET /gallery`), cada uma
  com a miniatura, o barbeiro (nome de `GET /barbers`, ou "Barbeiro inativo" quando não está
  lá), a descrição, as tags e a data de envio (`26/11/2026`).
- Carregando, erro com a mensagem da API e "Tentar de novo", e "Nenhuma foto pendente." /
  "Nenhuma foto publicada.".
- Pendente: "Aprovar" (vai para as publicadas), "Recusar" e "Excluir".
- "Recusar" abre, na linha, o campo "Motivo da recusa" com "Confirmar recusa" e "Voltar". O
  motivo tem de 1 a 500 caracteres sem contar os espaços das pontas
  (`O motivo deve ter entre 1 e 500 caracteres`), conferido antes da API, e vai aparado como
  `reason`. A foto sai da lista (o backend a apaga e avisa o barbeiro).
- Publicada: "Desaprovar" (volta para as pendentes) e "Excluir".
- "Excluir" pede confirmação na linha ("Excluir a foto? Não dá para desfazer.").
- O resultado de cada ação aparece no topo; a falha mostra a mensagem da API e a foto continua
  onde estava.

### Tags (só admin)

- Seção "Tags" com a lista em ordem alfabética (a do backend): "Adicionar", "Renomear" na
  própria linha e "Excluir" com confirmação ("Excluir a tag? As fotos ficam sem ela.").
- Nome de 1 a 50 caracteres sem contar os espaços das pontas
  (`Nome da tag deve ter entre 1 e 50 caracteres`), conferido antes da API. O nome repetido
  (400) mostra a mensagem da API.
- O formulário de envio usa a mesma lista de tags, já atualizada.

### Galeria pública (`/galeria`)

- As fotos aprovadas da API, da mais recente para a mais antiga, com o nome do barbeiro e as tags.
- Filtro: "Todas" e cada tag de `GET /gallery/tags`. Escolher uma tag chama
  `GET /gallery?tag_id=<id>`; "Todas" chama sem filtro. O botão escolhido fica marcado
  (`aria-pressed`).
- Carregando, "Nenhuma foto por aqui ainda." e o erro com "Tentar de novo".

### Reaproveitamento (jscpd ≤ 5%)

- A gestão das categorias de despesa (`ExpenseCategories`, `CategoryRow` e
  `useExpenseCategories`) vira um componente e um hook genéricos de "lista de nomes", usados
  pelas categorias e pelas tags. O comportamento das categorias não muda (os testes delas
  continuam passando).
- Carga e ações: `useApiResource` e `useRowAction`; tela: `LoadState`, `ActionFeedback`,
  `ConfirmButton`, `AdminForm`, `FormField` e `AdminShared.module.css`.

## Critérios de aceitação

Testes vitest (com a API simulada) que falham se a tela for desfeita:

- [ ] Admin e barbeiro veem "Galeria" no menu e a tela em `/admin/galeria`, e o cliente não; o
      barbeiro não vê pendentes, publicadas nem tags, e a tela dele não chama `/gallery/pending`.
- [ ] Enviar: o barbeiro manda URL, descrição e tags, sem `barber_id`, e vê o aviso da
      aprovação; o admin manda o `barber_id` escolhido e a foto entra nas publicadas.
- [ ] URL vazia, sem http(s) ou com mais de 1.000 caracteres, descrição longa e admin sem
      barbeiro são recusados na tela, sem chamada. O erro da API aparece no formulário.
- [ ] Aprovar chama `PUT /gallery/{id}/approve` e move a foto para as publicadas; desaprovar
      chama `/unapprove` e a devolve às pendentes.
- [ ] Recusar pede o motivo, recusa o vazio sem chamada, manda `{ reason }` aparado e tira a foto.
- [ ] Excluir pede confirmação, chama `DELETE /gallery/{id}` e tira a foto; a falha mostra a
      mensagem da API e a foto continua.
- [ ] Tags: criar, renomear e excluir com confirmação; nome vazio ou com mais de 50 caracteres
      recusado na tela; nome repetido mostra o 400 da API.
- [ ] `/galeria` mostra as fotos da API com o nome do barbeiro; a tag escolhida vai como
      `tag_id`, e "Todas" tira o filtro. Falha na carga mostra a mensagem e "Tentar de novo".
- [ ] As categorias de despesa continuam funcionando como antes (testes existentes).

## Fora do escopo

- Backend: nenhuma rota nova ou alterada.
- Envio de arquivo (upload binário): a API recebe a URL da imagem.
- Escolha do serviço da foto (`service_id`).
- Lista "minhas fotos" para o barbeiro e a exclusão das próprias fotos por ele (não há rota que
  liste as fotos de um barbeiro, inclusive as pendentes).
- Botão de envio na página pública: o envio fica no painel, que só barbeiro e admin acessam.
