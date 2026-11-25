# Notificações de verdade: avisos de agendamento, aviso geral com público e telas ligadas à API (2026-11-25)

> Complementa: SPEC/2026-09-29-notificacoes.md e SPEC/2026-11-24-testes-integracao-notifications.md (PR #76)
> Issue: #75

## O quê e por quê

Os testes de integração das notificações (PR #76) mostraram quatro problemas:
1. **Nada gera notificação.** Fora o aviso geral, `create_notification` não é chamado por nenhum
   módulo, e o frontend não usa `/api/notifications`. A tela "Disparo de Notificações" do admin só
   mostra um `alert()`.
2. **O aviso geral vai para todo mundo,** inclusive contas desativadas e visitantes fantasmas, e
   não dá para escolher o público.
3. **Título e mensagem vazios** são aceitos.
4. **A lista não tem paginação,** e não há como apagar uma notificação.

## Decisões

Sem resposta do cliente, a barbearia passa a avisar sobre o que já acontece no sistema:

| Quando | Quem recebe | Título |
|---|---|---|
| cliente agenda (logado ou visitante) | cliente e barbeiro | `Agendamento recebido` / `Novo agendamento` |
| barbearia confirma, cancela ou conclui | cliente | `Agendamento confirmado` / `Agendamento cancelado` / `Atendimento concluído` |
| cliente cancela | barbeiro | `Agendamento cancelado` |

- O tipo é `appointment_reminder`, e a mensagem traz o dia e a hora no fuso da barbearia
  (`02/12 às 10:00`). As notificações entram no mesmo commit da mudança, então um agendamento
  recusado não avisa ninguém.
- Contas desativadas não recebem nada, nem o usuário Visitante (#21).
- **Os outros tipos ficam nos PRs dos módulos deles, para não conflitar:**
  - `subscription_notice` (assinou ou cancelou o Trim Club) no PR da #64;
  - `loyalty_update` (ganhou ou resgatou pontos) no PR da #13.
- Um lembrete na véspera exigiria uma tarefa agendada, que o projeto não tem. Ele fica fora.

## Critérios de aceitação

1. [ ] **Avisos de agendamento:** criados como na tabela acima, sem duplicar e sem avisar contas
   desativadas.
2. [ ] **Aviso geral:**
   - `POST /api/notifications/broadcast` vai só para contas **ativas**;
   - aceita `audience`: `all` (padrão), `clients`, `barbers` ou `admins`. Outro valor responde 422;
   - a resposta continua `Mensagem enviada para N usuários.`
3. [ ] `title` e `message` são aparados e exigem pelo menos 1 caractere (422). A mensagem tem no
   máximo 2.000 caracteres.
4. [ ] **Lista e exclusão:**
   - `GET /api/notifications` aceita `limit` (de 1 a 200, padrão 50), `offset` (≥ 0) e
     `unread_only`;
   - `DELETE /api/notifications/{id}` apaga uma notificação do próprio usuário (204). A de outra
     pessoa, ou um id desconhecido, responde 404 `Notificação não encontrada.`
5. [ ] **Frontend:**
   - "Minha conta" (`/conta` e `/admin/conta`) mostra as notificações e o número de não lidas,
     com as ações de marcar como lida, marcar todas e apagar;
   - a tela do admin envia o aviso de verdade: escolhe o público, título e mensagem, e mostra
     quantos receberam ou o erro do servidor.

## Testes

- `tests/test_notificacoes_correcoes.py`, pela API, com o "agora" fixado;
- `src/frontend/src/components/account/NotificationsList.test.tsx` e
  `src/frontend/src/pages/AdminNotifications.test.tsx`, no vitest.
