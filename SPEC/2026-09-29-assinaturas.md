# Módulo de Assinaturas (Trim Club) (2026-09-29)

## O quê e por quê

Este módulo introduz o conceito de "Clube de Vantagens" (Trim Club) para os clientes. 
Em vez de pagar avulso a cada ida, o cliente pode assinar um plano mensal que lhe dá direito a uma certa quantidade de serviços gratuitos ou descontos em produtos. 
Isso garante previsibilidade de caixa para a barbearia e fidelização do cliente.

### Decisões técnicas
- O sistema de assinaturas terá **Planos (SubscriptionPlan)** e **Assinaturas de Clientes (UserSubscription)**.
- Um plano define um preço mensal e a quantidade de serviços que ele cobre.
- Nesta versão do sistema, o uso do serviço da assinatura não será descontado automaticamente em um "banco de créditos". A assinatura servirá como uma "flag" no perfil do cliente (`is_vip` ou `active_subscription`). O barbeiro, ao cobrar o Agendamento no final do serviço, aplicará o desconto manualmente ou o sistema marcará o agendamento com valor R$ 0.00 ao notar que o cliente possui assinatura.

---

## Entidades

### SubscriptionPlan (Os planos que a barbearia vende)
| Campo | Tipo | Restrições |
|-------|------|------------|
| id | UUID | PK, auto-gerado |
| name | string | unique, not null (ex: "Trim Club Ouro") |
| description | text | nullable |
| monthly_price | decimal | not null, maior que 0 |
| included_cuts | integer | not null, default 0 (quantos cortes inclui) |
| included_shaves | integer | not null, default 0 (quantas barbas inclui) |
| discount_percentage | decimal | not null, default 0.0 (desconto na compra de produtos) |
| is_active | boolean | default true (Planos desativados não podem ser vendidos, mas quem já tem continua) |
| created_at | datetime | auto-gerado |
| updated_at | datetime | auto-atualizado |

### UserSubscription (Assinatura atual de um cliente)
| Campo | Tipo | Restrições |
|-------|------|------------|
| id | UUID | PK, auto-gerado |
| user_id | UUID | FK (users.id), unique, not null (um usuário só pode ter 1 plano ativo) |
| plan_id | UUID | FK (subscription_plans.id), not null |
| start_date | date | not null (quando iniciou) |
| end_date | date | not null (data de expiração do ciclo atual) |
| status | enum | `ACTIVE`, `CANCELED`, `PAST_DUE` (inadimplente) |
| created_at | datetime | auto-gerado |
| updated_at | datetime | auto-atualizado |

---

## Endpoints da API

### Públicos (Clientes Não-logados e Logados)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/subscriptions/plans` | Lista os planos ativos disponíveis para compra. |

### Autenticados (Clientes)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/subscriptions/me` | Retorna o status da assinatura atual do cliente logado. |
| POST | `/api/subscriptions/me/subscribe` | Cliente contrata um plano (cria `UserSubscription`). |
| PUT | `/api/subscriptions/me/cancel` | Cliente cancela a renovação (status vira `CANCELED`, mas ele usufrui até o `end_date`). |

### Autenticados (Admin)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/subscriptions/plans` | Cria um novo plano. |
| PUT | `/api/subscriptions/plans/{id}` | Edita nome ou preço de um plano. |
| DELETE| `/api/subscriptions/plans/{id}` | Desativa um plano (ninguém mais pode assinar). |
| GET | `/api/subscriptions/users` | Lista todos os assinantes do clube. |

---

## Regras de negócio

1. **Assinatura Única:** Um cliente (`user_id`) só pode ter no máximo uma `UserSubscription` ativa ou inadimplente. Para mudar de plano (upgrade/downgrade), a API deve cancelar a antiga e iniciar a nova.
2. **Uso até o fim:** Quando o cliente cancela, o `status` pode ir para `CANCELED`, mas os benefícios do plano continuam válidos até o `end_date` do mês já pago.
3. **Planos Legados:** Se o Admin desativar (`is_active = False`) o "Trim Club Ouro", os clientes que possuem uma `UserSubscription` apontando para esse `plan_id` continuam com ele funcionando normalmente. O sistema apenas esconde o plano do endpoint de compra.
4. **Ciclo de Cobrança Mockado:** Como não integraremos Stripe agora, o `end_date` da assinatura deve ser automaticamente cravado para 30 dias após o `start_date` no momento da assinatura.

---

## Critérios de aceitação

- [ ] Admin pode criar e editar Planos.
- [ ] Endpoint de listagem de planos só exibe os ativos.
- [ ] Cliente consegue assinar um plano (se não tiver outro ativo).
- [ ] O sistema automaticamente calcula o `end_date` para +30 dias a partir do momento da assinatura.
- [ ] Endpoint `/me` de assinatura retorna adequadamente se o cliente é VIP e quando expira.
- [ ] Cliente pode cancelar assinatura.

---

## Fora do escopo

- Integração com gateway de pagamento real (Stripe/MercadoPago). Vamos apenas assumir que a chamada à API é bem sucedida.
- Job agendado (Cron) para verificar faturas vencidas e setar `PAST_DUE`. Faremos isso sob demanda ou mockaremos essa verificação no futuro.
- Abater do "banco de cortes" da assinatura toda vez que ocorrer um agendamento. Nesta versão, o barbeiro apenas confere o VIP e isenta o valor na hora do atendimento se o cliente for assinante.
