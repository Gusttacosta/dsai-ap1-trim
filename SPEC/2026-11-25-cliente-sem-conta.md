# Cliente sem conta: um único usuário "Visitante" para a fila e o agendamento, e a fila sem erros 500 (2026-11-25)

> Complementa: SPEC/2026-09-29-agendamentos.md, SPEC/2026-11-24-testes-integracao-walkin.md (PR #70)
> e SPEC/2026-11-24-testes-integracao-appointments.md
> Issues: #21 e #69

## O quê e por quê

O agendamento exige um `client_id` (`NOT NULL`). Hoje há dois caminhos para quem não tem conta, e
os dois estão quebrados:
- **#21:** `POST /api/appointments/guest` cria um usuário `guest_<hex>@trim.local` a cada
  agendamento. A mesma pessoa vira vários "clientes", que não conseguem entrar no sistema e se
  acumulam na tabela `users`. Eles inflam as contagens e recebem os avisos gerais.
- **#69:** puxar para a cadeira alguém da fila sem cadastro (`user_id` nulo) estoura o
  `NOT NULL` e responde 500. É o caso mais comum da fila.

**Decisão (as perguntas ao cliente não tiveram resposta):** existe **um único usuário
"Visitante"** (`visitante@trim.local`), criado na primeira vez que for preciso:
- `is_active=False` e uma senha que não é um hash bcrypt, então ninguém entra com ele;
- os dois caminhos usam esse usuário;
- o nome da pessoa fica nas observações do agendamento (`Visitante: <nome>` no site, e
  `Fila de espera: <nome>` na fila). O painel do dono já mostra as observações.

Assim não é preciso mudar o esquema do banco (`client_id` nulo exigiria uma migração no banco de
produção). O dashboard passa a contar os visitantes como um cliente só.

## Critérios de aceitação

### Visitante (#21)
- [ ] Dois agendamentos de visitante usam o **mesmo** `client_id`, o do Visitante. Cada um
  guarda o próprio nome em `notes`.
- [ ] O Visitante é `role=client`, `is_active=False`, e nenhuma senha entra com ele.
- [ ] Um agendamento recusado (conflito, serviço inválido, horário passado, barbeiro desativado)
  não deixa usuário para trás.
- [ ] Os testes que fixavam o `guest_<hex>` passam a conferir o Visitante.

### Fila de espera (#69)
1. [ ] **Sem conta:** o `/assign` de quem não tem `user_id` cria o agendamento no Visitante,
   com `notes = "Fila de espera: <nome>"`, e responde 200. Quem tem conta continua com o próprio
   `client_id`.
2. [ ] **Nome:** `customer_name` é aparado e exige pelo menos 1 caractere (422). A fila da TV
   (`/live`) não cai com um registro antigo só com espaços: mostra `?***`.
3. [ ] **IDs no `POST`:** respondem **404**, sem gravar nada:
   - `requested_service_id` desconhecido ou inativo;
   - `requested_barber_id` desconhecido ou inativo;
   - `user_id` desconhecido.

   No `/assign`, um `barber_id` desconhecido ou desativado também responde 404.
4. [ ] **Agendamento completo:**
   - fim = início + a duração do serviço, para bloquear a agenda;
   - um `AppointmentItem` com o nome, o preço e a duração do serviço;
   - o barbeiro só puxa o cliente para a **própria** cadeira (403), e o admin pode escolher
     qualquer cadeira;
   - um usuário `barber` sem perfil recebe 403.

   O barbeiro pedido na fila (`requested_barber_id`) continua informativo: quem está livre pode
   atender. É o comportamento que os testes do PR #70 fixam.
5. [ ] **Dia da fila no fuso da barbearia:** as posições e o `/live` usam o início e o fim do dia
   em `settings.shop_timezone`, convertidos para UTC. Às 22:00 em Brasília, a fila do dia
   continua a mesma.

## Fora do escopo

O registro desconhecido no `/assign` e no `/cancel` continua respondendo 400, como os testes do
PR #70 fixam.

## Testes

- `tests/test_cliente_sem_conta.py`, com o "agora" da fila fixado (`walkin.service.utc_now`).
- Ajustes nos testes de visitante de `tests/test_appointments_integracao.py`,
  `tests/test_nome_do_visitante.py` e `tests/test_barbeiros_admin.py`.
