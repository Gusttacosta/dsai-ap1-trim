# Módulo de Agendamentos (Appointments) (2026-09-29)

## O quê e por quê

Este módulo é o "motor" da barbearia. Ele orquestra o encontro entre um **Cliente**, um **Barbeiro** e um ou mais **Serviços** em um momento específico no tempo.
Ele precisa garantir que não ocorram "choques" (overbooking) e respeitar o horário de trabalho (WorkSchedule) do barbeiro.

### Decisões técnicas
- O Agendamento (Appointment) terá um status (`PENDING`, `CONFIRMED`, `COMPLETED`, `CANCELLED`, `NO_SHOW`).
- Prevenção de conflito de horário: Antes de salvar no banco, o sistema fará uma verificação ativa se o slot de tempo do barbeiro está livre para a duração solicitada.
- Histórico de preço: Como os preços dos serviços podem mudar, o Agendamento copiará o `price` e `duration` daquele momento para uma tabela filha de itens do agendamento, garantindo consistência financeira.

---

## Entidades

### Appointment (Agendamento base)
| Campo | Tipo | Restrições |
|-------|------|------------|
| id | UUID | PK, auto-gerado |
| client_id | UUID | FK (users.id), not null |
| barber_id | UUID | FK (barbers.id), not null |
| start_datetime | datetime | not null (com fuso horário) |
| end_datetime | datetime | not null (calculado somando a duração dos serviços) |
| status | enum | `PENDING`, `CONFIRMED`, `COMPLETED`, `CANCELLED`, `NO_SHOW` (default: `CONFIRMED`) |
| total_price | decimal | calculado a partir dos serviços |
| notes | text | nullable (observações do cliente ou do barbeiro) |
| created_at | datetime | auto-gerado |
| updated_at | datetime | auto-atualizado |

### AppointmentItem (Serviços do Agendamento)
Necessário pois um agendamento pode ter múltiplos serviços (Corte + Barba).
| Campo | Tipo | Restrições |
|-------|------|------------|
| id | UUID | PK, auto-gerado |
| appointment_id | UUID | FK (appointments.id), ondelete="CASCADE" |
| service_id | UUID | FK (services.id), nullable (pode ficar null se o serviço for apagado no futuro, mantendo a FK com SET NULL ou usando apenas cópia de dados) -> Para preservar, usaremos cópia: `service_name` e `locked_price` |
| service_name | string | Cópia do nome do serviço no momento do agendamento |
| locked_price | decimal | Cópia do preço do serviço no momento do agendamento |
| duration_minutes | int | Cópia da duração |

---

## Endpoints da API

### Autenticados (Clientes)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/appointments/me` | Lista os agendamentos futuros e passados do cliente logado |
| POST | `/api/appointments` | Cria um novo agendamento |
| PUT | `/api/appointments/{id}/cancel` | Cliente cancela o próprio agendamento (somente se futuro) |

### Autenticados (Barbeiros)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/appointments/barber/me` | Lista os agendamentos do barbeiro (hoje, futuros, etc) |
| PUT | `/api/appointments/{id}/status` | Barbeiro altera o status (ex: marca como `COMPLETED` ou `NO_SHOW`) |

### Autenticados (Admin)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/appointments` | Visão geral de todos os agendamentos (com filtros de data e barbeiro) |
| PUT | `/api/appointments/{id}` | Admin pode forçar alteração de data/hora/status de qualquer um |

### Públicos (Busca de Disponibilidade)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/appointments/availability` | Retorna os horários livres (slots) de um barbeiro para uma data e duração específicas |

---

## Regras de negócio

1. **Validação de Slot:** O `start_datetime` e `end_datetime` não podem colidir com um agendamento existente com status `CONFIRMED` ou `PENDING` para o mesmo barbeiro.
2. **Expediente:** O horário do agendamento deve estar contido estritamente no `WorkSchedule` do barbeiro para aquele dia da semana, não sobrepondo o horário de almoço (`break_start`/`break_end`).
3. **Cálculo automático:** `end_datetime` e `total_price` do `Appointment` são a soma dos `duration_minutes` e `locked_price` dos `AppointmentItem`.
4. **Habilitação:** Ao criar, validar se o barbeiro escolhido está habilitado (`BarberServiceAssociation`) a fazer os serviços solicitados.
5. **Cancelamento do Cliente:** Cliente só pode cancelar (status `CANCELLED`) um agendamento com X horas de antecedência (nesta versão inicial: qualquer horário no futuro).

---

## Critérios de aceitação

- [ ] A API de disponibilidade (`/availability`) retorna uma lista de horários (ex: ["09:00", "09:30"]) válidos, descontando almoço e agendamentos confirmados.
- [ ] Criação de agendamento rejeita se o barbeiro não atende aquele serviço.
- [ ] Criação de agendamento rejeita se houver conflito de horário (overbooking).
- [ ] O preço e nome dos serviços ficam "congelados" na tabela `AppointmentItem` para segurança financeira caso o serviço mude no futuro.
- [ ] Cliente consegue listar seus agendamentos passados e futuros de forma separada ou ordenada.
- [ ] Barbeiro consegue visualizar a própria agenda do dia.
- [ ] Barbeiro consegue concluir (`COMPLETED`) um agendamento.

---

## Fora do escopo

- Pagamento no ato do agendamento (Integração com Stripe/MercadoPago). Será mockado ou tratado no módulo de Finance depois.
- Lembretes automáticos via WhatsApp/Email.
- Aprovação manual de agendamento pelo barbeiro (o sistema auto-confirma baseado na disponibilidade livre).
