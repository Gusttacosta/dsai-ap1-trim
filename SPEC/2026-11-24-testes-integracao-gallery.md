# Testes de integração da galeria, no lugar dos testes gerados (2026-11-24)

> Complementa: SPEC/2026-11-21-testes-integracao-auth.md (plano da #3, um módulo por PR) e
> SPEC/2026-09-29-galeria.md (descreve o comportamento que os testes conferem)
> Issue: #3

## O quê e por quê

Décimo primeiro módulo do plano da #3. O `tests/test_gallery.py` herdado da AP1 tem 1.000 funções
geradas que conferem um dict fixo e não importam a aplicação. Ele é trocado por testes de
integração pela API (`/api/gallery`), com o PostgreSQL de teste e as fixtures de
`tests/agenda_fixtures.py` e `tests/api_helpers.py`.

As 7 rotas do módulo são:
- **públicas:** fotos aprovadas (com filtro por barbeiro e por tag) e tags;
- **moderação:** o barbeiro envia fotos (que esperam aprovação) e apaga as próprias; o admin cria
  tags, vê as pendentes, aprova e apaga qualquer foto.

O código da aplicação não muda.

Valor: a galeria é a vitrine pública dos cortes. Uma foto que aparece sem aprovação, ou um barbeiro
que apaga a foto de outro, passa a quebrar a CI.

## Critérios de aceitação

Testes em `tests/test_gallery_integracao.py`, com o PostgreSQL de `TEST_DATABASE_URL`:

- [ ] **Tags:**
  - a criação responde 201;
  - a listagem pública traz todas, em ordem alfabética;
  - uma tag repetida responde 400 `A tag '<nome>' já existe.`;
  - nome com mais de 50 caracteres, ou faltando, responde 422.
- [ ] **Envio de foto pelo barbeiro:**
  - responde 201 com a foto pendente (`is_approved` falso), no nome do barbeiro do token, com a URL,
    a descrição, o serviço e as tags pedidas;
  - URL que não é http(s), descrição com mais de 500 caracteres ou URL faltando respondem 422;
  - um usuário `barber` sem perfil de barbeiro recebe 404 `Perfil de barbeiro não encontrado.`.
- [ ] **Envio pelo admin:** um admin com perfil de barbeiro envia a foto já aprovada.
- [ ] **Galeria pública:**
  - só as fotos aprovadas, da mais recente para a mais antiga, com as tags;
  - `barber_id` filtra pelo barbeiro, e `tag_id` filtra pelas fotos que têm a tag;
  - os dois filtros juntos combinam;
  - sem fotos aprovadas, devolve uma lista vazia.
- [ ] **Pendentes e aprovação (admin):**
  - `/pending` lista só as fotos não aprovadas, da mais recente para a mais antiga;
  - aprovar responde 200 com a foto aprovada, que sai das pendentes e entra na galeria pública;
  - aprovar de novo continua aprovado;
  - foto desconhecida responde 404 `Imagem não encontrada.`.
- [ ] **Exclusão:**
  - o barbeiro apaga a própria foto (204), e ela some do banco e da galeria, junto com o vínculo
    das tags (as tags continuam);
  - a foto de outro barbeiro responde 403 `Você não tem permissão para deletar a foto de outro
    barbeiro.`, e nada muda;
  - o admin apaga qualquer foto;
  - foto desconhecida responde 404 `Imagem não encontrada.`.
- [ ] **Permissões:**
  - sem token, ou com token de cliente, as rotas de moderação respondem 403, e nada muda no banco;
  - com token de barbeiro, criar tag, ver as pendentes e aprovar respondem 403;
  - a galeria e as tags são públicas.
- [ ] **Os testes testam:** se o corpo de qualquer método de `GalleryService` for trocado por um
      `raise`, algum teste novo falha.
- [ ] `tests/test_gallery.py` (gerado) é apagado, e `gallery` sai da lista `MODULES` de
      `tests/generate_tests.py`.

## Fora do escopo

Mudar o comportamento do módulo. As diferenças encontradas vão para uma issue própria e não são
fixadas pelos testes:
- **um usuário `barber` sem perfil de barbeiro apaga a foto de qualquer barbeiro (204)**: sem
  perfil, `requesting_barber_id` fica nulo e o serviço trata o pedido como se fosse do admin;
- um admin sem perfil de barbeiro não consegue enviar foto (404), embora a rota diga que a foto do
  admin já entra aprovada;
- tags desconhecidas em `tag_ids` são ignoradas sem aviso;
- `service_id` desconhecido e URL com mais de 1.000 caracteres respondem 500;
- nome de tag vazio é aceito, e não há como renomear nem apagar uma tag;
- não há como recusar uma foto (só aprovar ou apagar), nem tirar a aprovação;
- as fotos de um barbeiro desativado continuam na galeria pública.
