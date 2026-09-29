# Módulo Central de Notificações In-App (2026-09-29)

## O quê e por quê

A retenção e engajamento dos usuários dependem muito da comunicação proativa. 
O Módulo de Notificações centraliza os avisos de sistema, como lembretes de agendamento ("Seu corte é amanhã às 14h"), avisos de fidelidade ("Você ganhou 10 pontos!"), ou ações administrativas ("Seu plano Trim Club foi renovado").

### Decisões técnicas
- Será um sistema *In-App* (dentro do próprio aplicativo). Não envolveremos integrações com SendGrid (e-mail) ou Twilio (SMS/WhatsApp) nesta fase para não aumentar a complexidade técnica fora do escopo central.
- Uma notificação pertence a um `User` (seja ele cliente, barbeiro ou admin) e possui os campos clássicos de `title`, `message`, `type` e `is_read`.
- A API proverá a infraestrutura. A geração efetiva das notificações poderá ser chamada programaticamente por outros *Services* (ex: O LoyaltyService chama o NotificationService após creditar pontos).

---

## Entidades

### Notification
| Campo | Tipo | Restrições |
|-------|------|------------|
| id | UUID | PK, auto-gerado |
| user_id | UUID | FK (users.id), not null (Quem recebe a notificação) |
| title | string | not null (ex: "Agendamento Confirmado") |
| message | text | not null (ex: "Te esperamos amanhã às 14h com o barbeiro João.") |
| type | enum | `APPOINTMENT_REMINDER`, `LOYALTY_UPDATE`, `SUBSCRIPTION_NOTICE`, `SYSTEM_ALERT` |
| is_read | boolean | default false |
| created_at | datetime | auto-gerado (Data do disparo) |

---

## Endpoints da API

### Autenticados (Qualquer Usuário Logado)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/notifications` | Lista as notificações do usuário logado (ordenadas pelas mais recentes). |
| GET | `/api/notifications/unread-count` | Retorna apenas a contagem de mensagens não lidas (ideal para o badge vermelho do frontend). |
| PUT | `/api/notifications/{id}/read` | Marca uma notificação específica como lida (`is_read = True`). |
| PUT | `/api/notifications/read-all` | Marca todas as notificações não lidas do usuário como lidas. |

### Autenticados (Admin)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/notifications/broadcast` | (Admin) Dispara uma notificação do tipo `SYSTEM_ALERT` para todos os usuários cadastrados. |

---

## Regras de negócio

1. **Privacidade:** Cada usuário enxerga e manipula estritamente as suas próprias notificações. Um cliente não pode alterar a notificação de outro cliente.
2. **Desempenho no Frontend:** O endpoint de `unread-count` deve ser extremamente leve, pois o frontend poderá consultá-lo periodicamente (polling) ou renderizá-lo em todas as páginas para atualizar o "sininho".
3. **Broadcast:** O admin tem a capacidade de enviar comunicados gerais (ex: "Barbearia fechada neste feriado") que clona a notificação para cada `User` no banco.

---

## Critérios de aceitação

- [ ] Os usuários logados podem visualizar seu histórico de notificações e a contagem de não lidas.
- [ ] O usuário consegue marcar notificações individuais ou todas de uma vez como lidas.
- [ ] O Admin consegue usar a rota de Broadcast e o sistema distribui a mensagem corretamente para os clientes.

---

## Fora do escopo

- Envio de SMS, WhatsApp ou Push Notifications Nativas (Apple/Android). Tudo será resolvido dentro da interface web.
- Cron Job automático para "Lembrete 24h antes" rodando no backend. Por enquanto, se quisermos testar, simulamos chamando a função de envio pelo Swagger/Admin.
