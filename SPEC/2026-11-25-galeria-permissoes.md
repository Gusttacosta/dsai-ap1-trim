# Galeria: barbeiro sem perfil não apaga foto alheia, e envios inválidos param de dar 500 (2026-11-25)

> Complementa: SPEC/2026-11-24-testes-integracao-gallery.md (PR #72, onde os achados apareceram)
> Issue: #71 (itens 1 e 3, primeira parte)

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

## Fora do escopo (continuam na #71)

- Admin sem perfil enviar foto em nome de um barbeiro (item 2).
- `tag_ids` desconhecidos ignorados, tag com nome vazio, renomear e apagar tags (resto do item 3).
- Recusar uma foto com motivo, tirar a aprovação e esconder as fotos de barbeiro desativado (item 4).

## Testes

`tests/test_galeria_permissoes.py`, com o PostgreSQL de `TEST_DATABASE_URL` e as fixtures de
`tests/agenda_fixtures.py` e `tests/api_helpers.py`. Todo teste de API pede o `sessionmaker`, que
é onde fica o override do `get_db`.
