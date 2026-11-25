# Galeria: barbeiro sem perfil não apaga foto alheia, e envios inválidos param de dar 500 (2026-11-25)

> Complementa: SPEC/2026-11-24-testes-integracao-gallery.md (PR #72, onde os achados apareceram)
> Issue: #71 (todos os itens)

## O quê e por quê

**Falha de segurança (item 1 da #71).** `DELETE /api/gallery/{id}` procura o perfil de barbeiro
do usuário quando ele não é admin. Se o perfil não existir, `requesting_barber_id` fica `None`.
`GalleryService.delete_image` só confere a posse quando esse valor é verdadeiro
(`if requesting_barber_id and ...`), então o pedido passa como se viesse do admin. Hoje, uma conta
com `role=barber` e sem linha em `barbers` apaga a foto de qualquer barbeiro e recebe 204. Isso
acontece, por exemplo, com uma conta promovida a barbeiro antes de ganhar o perfil.

**Erros 500 no envio (item 3 da #71, primeira parte).**
- Um `service_id` que não existe estoura a FK no commit e responde 500.
- Uma `image_url` com mais de 1.000 caracteres responde 500. A coluna é `String(1000)`, e o
  `HttpUrl` aceita até 2.083 caracteres.

Valor: a galeria pública é a vitrine da barbearia. Uma conta com permissões pela metade não
pode apagar o portfólio dos colegas, e um erro de digitação no painel precisa voltar como uma
mensagem, e não como um erro do servidor.

## Critérios de aceitação

- [ ] **Exclusão por barbeiro sem perfil:** um usuário `barber` sem perfil de barbeiro recebe
  **403** `Perfil de barbeiro não encontrado.` ao tentar apagar qualquer foto, e a foto continua
  no banco.
- [ ] **Defesa no serviço:** a checagem de posse em `delete_image` deixa de depender de o id ser
  verdadeiro. Ela passa a ser feita sempre que o pedido não vem do admin (`is_admin=False`).
- [ ] **Sem regressão nas exclusões:**
  - o barbeiro continua apagando as próprias fotos (204);
  - o barbeiro continua recebendo 403 na foto de outro barbeiro;
  - o admin continua apagando qualquer foto, com ou sem perfil;
  - um id desconhecido continua respondendo 404.
- [ ] **Serviço desconhecido:** `POST /api/gallery` com um `service_id` que não existe responde
  **404** `Serviço não encontrado.` e não grava a foto.
- [ ] **URL longa:** uma `image_url` com mais de 1.000 caracteres responde **422** na validação, e
  nada é gravado. Com exatamente 1.000 caracteres, a foto é aceita.
- [ ] Os testes falham quando as mudanças são revertidas (mutação manual: tirar cada checagem nova).

## Ampliação: o resto da #71 (mesmo dia)

Para fechar a #71 inteira, este PR também cobre os itens 2, 3 e 4. O motivo da recusa vai para o
barbeiro como uma notificação (o módulo `notifications` já existe), e não numa coluna nova. Assim
não é preciso migrar o banco de produção.

- [ ] **Item 2: envio pelo admin.**
  - `POST /api/gallery` aceita `barber_id`. O admin envia em nome de qualquer barbeiro ativo,
    mesmo sem perfil próprio, e a foto já entra aprovada;
  - admin sem perfil e sem `barber_id` responde 400 `Informe o barbeiro da foto (barber_id).`;
  - barbeiro desconhecido ou desativado responde 404;
  - um barbeiro que informa outro `barber_id` recebe 403. O próprio `barber_id` é aceito;
  - o barbeiro sem perfil continua recebendo 404, como fixam os testes do PR #72.
- [ ] **Item 3: tags.**
  - `tag_ids` desconhecidos respondem 404 `Uma ou mais tags não existem.`, sem gravar a foto. Um
    id repetido conta uma vez;
  - o nome da tag é aparado e exige pelo menos 1 caractere (422);
  - `PUT /api/gallery/tags/{id}` renomeia, e um nome repetido responde 400;
  - `DELETE /api/gallery/tags/{id}` apaga a tag, e as fotos continuam sem ela;
  - uma tag desconhecida responde 404 `Tag não encontrada.`;
  - as rotas de tag são só para o admin.
- [ ] **Item 4: moderação.**
  - `PUT /api/gallery/{id}/reject` com `reason` (de 1 a 500 caracteres) apaga a foto pendente e
    cria uma notificação para o barbeiro: título `Foto recusada na galeria` e o motivo na
    mensagem;
  - uma foto já aprovada não é recusada (400);
  - `PUT /api/gallery/{id}/unapprove` tira a foto da galeria pública, e ela volta para
    `/pending`;
  - as duas rotas são só para o admin, e um id desconhecido responde 404;
  - as fotos de um barbeiro com o perfil ou a conta desativados saem da galeria pública, também
    no filtro por barbeiro.

## Testes

- `tests/test_galeria_permissoes.py` (itens 1 e 3, primeira parte) e
  `tests/test_galeria_moderacao.py` (itens 2, 3 e 4);
- os dois usam o PostgreSQL de `TEST_DATABASE_URL` e as fixtures de `tests/agenda_fixtures.py` e
  `tests/api_helpers.py`;
- todo teste de API pede o `sessionmaker`, que é onde fica o override do `get_db`.
