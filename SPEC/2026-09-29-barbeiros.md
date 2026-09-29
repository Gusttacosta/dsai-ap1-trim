# Módulo de Barbeiros / Time (2026-09-29)

## O quê e por quê

Este módulo gerencia o time da barbearia. É necessário para que os clientes saibam com quem estão agendando e para que o sistema saiba quais serviços um profissional específico oferece, além de quando ele está disponível (escala/horário de trabalho).

### Decisões técnicas
- O `Barber` será uma extensão lógica do `User`. Em termos de banco de dados, o `Barber` terá uma relação 1:1 com a tabela `users`. O `User` guarda o e-mail, senha e nome, enquanto o `Barber` guarda dados específicos da profissão (bio, especialidades, comissão, etc.).
- A escala de trabalho (`WorkSchedule`) será flexível por dia da semana, permitindo folgas e horários de almoço.

---

## Entidades

### Barber
| Campo | Tipo | Restrições |
|-------|------|------------|
| id | UUID | PK |
| user_id | UUID | FK (users.id), unique, not null |
| bio | text | nullable, até 500 chars |
| instagram_url | string | nullable |
| commission_rate | decimal | default 50.0 (porcentagem de comissão) |
| is_active | boolean | default true (pode ser inativado sem perder o user) |
| created_at | datetime | auto-gerado |
| updated_at | datetime | auto-atualizado |

### BarberSpecialty (Muitos para Muitos entre Barber e Service)
*A ser detalhado quando criarmos o módulo de Serviços, mas essencialmente relaciona quais serviços o barbeiro faz.*

### WorkSchedule (Escala de Trabalho)
| Campo | Tipo | Restrições |
|-------|------|------------|
| id | UUID | PK |
| barber_id | UUID | FK (barbers.id), not null |
| day_of_week | int | 0 = Domingo, 1 = Segunda... 6 = Sábado |
| start_time | time | not null (ex: 09:00) |
| end_time | time | not null (ex: 18:00) |
| break_start | time | nullable (início do almoço) |
| break_end | time | nullable (fim do almoço) |
| is_working | boolean | default true (se false, é a folga do barbeiro) |

---

## Endpoints da API

### Públicos (sem autenticação)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/barbers` | Lista os barbeiros ativos (para a vitrine do cliente) |
| GET | `/api/barbers/{id}` | Detalhes do barbeiro e sua bio |
| GET | `/api/barbers/{id}/schedule` | Retorna a escala de trabalho do barbeiro na semana |

### Autenticados (Admin)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/barbers` | Cadastra um novo barbeiro (cria/linka user e cria profile) |
| PUT | `/api/barbers/{id}` | Atualiza bio, comissão, etc. |
| PUT | `/api/barbers/{id}/schedule` | Atualiza a escala de trabalho do barbeiro (dias e horários) |

### Autenticados (Barbeiro - Self)
| Método | Rota | Descrição |
|--------|------|-----------|
| PUT | `/api/barbers/me/bio` | Barbeiro pode atualizar sua própria bio e redes sociais |

---

## Regras de negócio

1. **Relação com User:** Só é possível criar um registro de `Barber` se existir um `User` válido e o role do usuário for (ou for atualizado para) `BARBER`.
2. **Escala Padrão:** Ao criar um barbeiro, ele deve receber uma escala de trabalho padrão (ex: Segunda a Sábado, 09:00 as 18:00, com 1 hora de almoço, folga no Domingo).
3. **Listagem Pública:** A listagem `/api/barbers` só deve retornar barbeiros onde `Barber.is_active = True` e a conta `User` relacionada também esteja ativa.
4. **Comissão:** O valor da comissão (`commission_rate`) só pode ser visto e alterado por administradores.

---

## Critérios de aceitação

- [ ] Admin consegue promover um User existente para Barbeiro (criando o profile `Barber`).
- [ ] Criação de Barbeiro gera automaticamente os 7 registros de `WorkSchedule` (domingo a sábado) preenchidos com os valores padrão.
- [ ] Listagem pública retorna apenas barbeiros ativos.
- [ ] Endpoint de detalhes do barbeiro exibe os dados combinados (`User.full_name`, `User.avatar_url`, e `Barber.bio`).
- [ ] Admin consegue alterar a comissão e horário de trabalho de qualquer barbeiro.
- [ ] Barbeiro consegue alterar sua própria bio e instagram, mas não sua comissão.
- [ ] O request de alteração de horário valida se `start_time` é anterior ao `end_time` e se o `break` está dentro do horário de expediente.

---

## Fora do escopo

- Gestão de feriados ou dias atípicos de folga (isso ficará no módulo de Agenda/Appointments).
- Atribuição de especialidades/serviços (depende do módulo de Serviços que será feito depois).
