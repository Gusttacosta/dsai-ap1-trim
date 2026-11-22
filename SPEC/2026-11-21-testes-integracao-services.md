# Testes de integração do catálogo de serviços, no lugar dos testes gerados (2026-11-21)

> Complementa: SPEC/2026-11-21-testes-integracao-auth.md (plano da #3, um módulo por PR) e
> SPEC/2026-09-29-servicos.md (descreve o comportamento que os testes conferem)
> Issue: #3

## O quê e por quê

Terceiro módulo do plano da #3. O `tests/test_services.py` herdado da AP1 tem 1.000 funções
geradas que conferem um dict fixo e não importam a aplicação. Ele é trocado por testes de
integração que passam pela API (`/api/services`) e usam o PostgreSQL de teste, com o
`tests/api_helpers.py` do módulo de barbeiros (PR #38).

Os testes descrevem o comportamento **atual** das 8 rotas do módulo:
- públicas: listagem, detalhes com os barbeiros e serviços de um barbeiro;
- do admin: criação, alteração, desativação, vínculo e desvínculo de um barbeiro.

O código da aplicação não muda.

Valor: o agendamento usa o preço, a duração e os vínculos daqui. Um erro no catálogo, na
desativação (*soft delete*) ou nos vínculos passa a quebrar a CI.

## Critérios de aceitação

Testes em `tests/test_services_integracao.py`, com o PostgreSQL de `TEST_DATABASE_URL`:

- [ ] **Listagem pública:** devolve só os serviços ativos, em ordem alfabética, com nome,
      descrição, preço, duração e datas. Sem serviços, devolve uma lista vazia.
- [ ] **Detalhes públicos:** devolvem o serviço e os barbeiros vinculados que estão ativos (perfil e
      conta), sem a comissão. Serviço desconhecido ou desativado responde 404
      `Serviço não encontrado ou inativo.`.
- [ ] **Serviços de um barbeiro:** devolvem os serviços ativos vinculados a ele, em ordem
      alfabética. Um barbeiro desconhecido ou sem vínculos recebe uma lista vazia.
- [ ] **Criação pelo admin:** responde 201 e grava o serviço ativo. O preço é guardado com duas
      casas decimais. Um nome já usado responde 400, inclusive o de um serviço desativado. Preço
      negativo, duração zero ou negativa, nome com mais de 100 caracteres ou campo obrigatório
      faltando respondem 422.
- [ ] **Alteração pelo admin:** muda só os campos enviados. Trocar para um nome que já existe
      responde 400, e manter o próprio nome é aceito. Um serviço desconhecido responde 404
      `Serviço não encontrado.`. Valores inválidos respondem 422.
- [ ] **Desativação pelo admin:** responde 204. O serviço sai da listagem, dos detalhes e da lista
      do barbeiro, mas continua no banco com o mesmo preço. Um serviço desconhecido responde 404.
- [ ] **Vínculos:** vincular responde 201 e faz o barbeiro aparecer nos detalhes do serviço, e o
      serviço aparecer na lista do barbeiro. Vincular de novo, ou vincular com barbeiro ou serviço
      desconhecido, responde 400 com a mensagem amigável. Desvincular responde 204 e desfaz as duas
      listas. Desvincular o que não está vinculado responde 404 `Vínculo não encontrado.`.
- [ ] **Permissões:** sem token, as 5 rotas do admin respondem 403. Com token de cliente ou de
      barbeiro, também respondem 403, e nada muda no banco.
- [ ] **Os testes testam:** se o corpo de qualquer método de `CatalogService` for trocado por um
      `raise`, algum teste novo falha.
- [ ] `tests/test_services.py` (gerado) é apagado, e `services` sai da lista `MODULES` de
      `tests/generate_tests.py`.

## Fora do escopo

- Mudar o comportamento do módulo. As diferenças encontradas ficam numa issue própria. Hoje:
  - um `null` explícito em `name`, `price` ou `duration_minutes` na alteração causa
    `IntegrityError` (500);
  - um nome vazio é aceito;
  - não há como reativar um serviço desativado;
  - um barbeiro ou serviço inativo pode ser vinculado.
