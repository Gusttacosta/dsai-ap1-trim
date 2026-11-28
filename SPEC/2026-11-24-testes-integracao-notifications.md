# Testes de integração das notificações, no lugar dos testes gerados (2026-11-24)

> Complementa: SPEC/2026-11-21-testes-integracao-auth.md (plano da #3, um módulo por PR) e
> SPEC/2026-09-29-notificacoes.md (descreve o comportamento que os testes conferem)
> Issue: #3

## O quê e por quê

Último módulo do plano da #3. O `tests/test_notifications.py` herdado da AP1 tem 1.000 funções
geradas que conferem um dict fixo e não importam a aplicação. Ele é trocado por testes de
integração pela API (`/api/notifications`), com o PostgreSQL de teste e as fixtures de
`tests/agenda_fixtures.py` e `tests/api_helpers.py`.

As 5 rotas do módulo são:
- **usuário logado:** listar as próprias notificações, contar as não lidas, marcar uma como lida e
  marcar todas;
- **admin:** enviar um aviso geral (`broadcast`) para todos os usuários.

O `NotificationService.create_notification` (uma notificação para um usuário) não tem rota e
nenhum outro módulo o chama. Ele é testado direto pelo serviço, com o mesmo banco de teste. O
código da aplicação não muda.

Com este PR, o `tests/generate_tests.py` fica sem nenhum módulo na lista `MODULES`: os 13 arquivos
gerados da AP1 terão sido trocados por testes reais.

Valor: o contador de não lidas é a "bolinha vermelha" do app. Um usuário que lê a notificação de
outro, ou um aviso geral que não chega a todos, passa a quebrar a CI.

## Critérios de aceitação

Testes em `tests/test_notifications_integracao.py`, com o PostgreSQL de `TEST_DATABASE_URL`:

- [ ] **Listar:**
  - devolve só as notificações do usuário do token, da mais recente para a mais antiga, com
    título, mensagem, tipo, `is_read` e data;
  - sem notificações, devolve uma lista vazia.
- [ ] **Não lidas:** `/unread-count` conta só as não lidas do usuário do token; sem notificações, 0.
- [ ] **Marcar uma como lida:**
  - responde 200 com a notificação lida, e o contador cai;
  - marcar de novo continua lida;
  - a notificação de outro usuário, ou desconhecida, responde 404 `Notificação não encontrada.`, e
    nada muda.
- [ ] **Marcar todas:**
  - marca só as não lidas do usuário do token e responde `<n> notificações marcadas como lidas.`
    com a quantidade que mudou;
  - as de outros usuários continuam como estavam;
  - sem nada para marcar, responde com 0.
- [ ] **Aviso geral (admin):**
  - cria uma notificação `system_alert`, não lida, com o título e a mensagem, para cada usuário
    cadastrado (clientes, barbeiros e admins), e responde 201 `Mensagem enviada para <n>
    usuários.`;
  - título com mais de 150 caracteres, ou título ou mensagem faltando, responde 422, e nada é
    criado.
- [ ] **Notificação para um usuário (serviço):** `create_notification` grava a notificação não lida
      para o usuário e o tipo pedidos, e ela aparece na lista e no contador dele.
- [ ] **Permissões:**
  - sem token, as 5 rotas respondem 403;
  - com token de cliente ou de barbeiro, o aviso geral responde 403, e nada é criado.
- [ ] **Os testes testam:** se o corpo de qualquer método de `NotificationService` for trocado por
      um `raise`, algum teste novo falha.
- [ ] `tests/test_notifications.py` (gerado) é apagado, e `notifications` sai da lista `MODULES` de
      `tests/generate_tests.py`.

## Fora do escopo

Mudar o comportamento do módulo. As diferenças encontradas vão para uma issue própria e não são
fixadas pelos testes:
- nada gera notificações além do aviso geral: lembrete de agendamento, pontos de fidelidade e
  avisos de assinatura (os outros tipos do enum) nunca são criados, e o frontend não usa o módulo;
- o aviso geral vai também para contas desativadas e para os usuários fantasmas dos visitantes
  (`guest_<hex>@trim.local`, #21), e não há como mandar só para um grupo (por exemplo, só para os
  clientes);
- título e mensagem vazios são aceitos;
- não há como apagar uma notificação, e a lista não tem paginação.
