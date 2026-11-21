# Testes de integração do módulo de barbeiros, no lugar dos testes gerados (2026-11-21)

> Complementa: SPEC/2026-11-21-testes-integracao-auth.md (plano da #3, um módulo por PR) e
> SPEC/2026-09-29-barbeiros.md (descreve o comportamento que os testes conferem)
> Issue: #3

## O quê e por quê

Segundo módulo do plano da #3. O `tests/test_barbers.py` herdado da AP1 tem 1.000 funções geradas
que conferem um dict fixo e não importam a aplicação. Ele é trocado por testes de integração que
passam pela API (`/api/barbers`) e usam o PostgreSQL de teste.

Os testes descrevem o comportamento **atual** das 6 rotas do módulo: listagem, detalhes e escala
públicos; cadastro de barbeiro e alteração de um dia da escala pelo admin; e alteração da bio pelo
próprio barbeiro. O código da aplicação não muda.

Os testes dos próximos módulos também vão precisar de usuários com perfil e de cabeçalhos com
token. Para isso, um arquivo de apoio novo, `tests/api_helpers.py`, cria o usuário no banco e
gera o access token com `security.create_access_token`, sem passar pelo login.

Valor: um erro no cadastro do barbeiro, na escala padrão (que o agendamento usa para calcular os
horários livres) ou nas permissões passa a quebrar a CI.

## Critérios de aceitação

Testes em `tests/test_barbers_integracao.py`, com o PostgreSQL de `TEST_DATABASE_URL`:

- [ ] **Listagem pública:** devolve só os barbeiros com o perfil ativo e a conta ativa, com nome,
      avatar, bio e Instagram, e sem a comissão. Sem barbeiros, devolve uma lista vazia.
- [ ] **Detalhes públicos:** devolvem os mesmos dados de um barbeiro. Respondem 404
      `Barbeiro não encontrado.` para um id desconhecido e 404 `Barbeiro não está ativo.` quando
      o perfil ou a conta estão desativados. Um id que não é UUID responde 422.
- [ ] **Escala pública:** devolve os 7 dias, de domingo (0) a sábado (6). Um barbeiro desconhecido
      responde 404 `Escala não encontrada.`.
- [ ] **Cadastro pelo admin:** responde 201 e cria o perfil com comissão de 50% por padrão, ou com
      a comissão, a bio e o Instagram enviados. Um cliente passa a ter o perfil `barber`, e um admin
      continua `admin`. É criada a escala padrão: domingo de folga, sem almoço; de segunda a sábado,
      das 9h às 18h, com almoço das 12h às 13h. O barbeiro novo aparece na listagem pública.
- [ ] **Erros do cadastro:** usuário desconhecido responde 400 `Usuário não encontrado.`. Usuário
      que já é barbeiro responde 400 `Usuário já possui perfil de barbeiro.`, e a escala dele não é
      duplicada. Comissão fora de 0 a 100, bio com mais de 500 caracteres e Instagram que não é URL
      respondem 422.
- [ ] **Alteração da escala pelo admin:** muda o dia pedido e grava a mudança, inclusive a folga.
      Fim antes do início, fim do almoço antes do início do almoço e dia da semana fora de 0 a 6
      respondem 422. Um dia de outro barbeiro ou desconhecido responde 404
      `Dia de escala não encontrado.`.
- [ ] **Bio pelo barbeiro:** o próprio barbeiro muda a bio e o Instagram. O campo que não é enviado
      continua como estava, e uma `commission_rate` enviada junto é ignorada. A mudança aparece nos
      detalhes públicos. Um usuário com perfil `barber` mas sem o cadastro de barbeiro recebe 404
      `Perfil de barbeiro não encontrado.`.
- [ ] **Permissões:** sem token, as rotas do admin e a da bio respondem 403. Com token de cliente
      ou de barbeiro, o cadastro e a alteração da escala respondem 403, e com token de cliente a
      bio também responde 403.
- [ ] **Os testes testam:** se o corpo de qualquer método de `BarberService` for trocado por um
      `raise`, algum teste novo falha.
- [ ] `tests/test_barbers.py` (gerado) é apagado, e `barbers` sai da lista `MODULES` de
      `tests/generate_tests.py`.

## Fora do escopo

- Mudar o comportamento do módulo. As diferenças entre o código e a spec da AP1 ficam numa issue
  própria: não existe o `PUT /api/barbers/{id}`, então o admin não consegue mudar a comissão nem
  desativar o barbeiro; a alteração da escala não confere se o almoço cai dentro do expediente e
  aceita trocar o dia da semana de um registro; e a resposta de `PUT /me/bio` mostra a comissão
  ao próprio barbeiro.
- Usar o `tests/api_helpers.py` nos testes do `auth` (PR #36), o que fica para depois do merge.
