# Barbeiros: alteração pelo admin, escala validada e serviços nos detalhes (2026-11-23)

> Complementa: SPEC/2026-09-29-barbeiros.md (rotas do admin, regra 4 e o critério do almoço) e
> SPEC/2026-09-29-servicos.md (critério "Ao pedir os detalhes de um barbeiro, a API deve listar seus
> serviços habilitados")
> Issues: #37 e o item 5 da #39

## O quê e por quê

Os testes de integração do módulo (#3) acharam estas diferenças em relação à spec da AP1 (#37):

1. **O admin não altera um barbeiro.** Falta o `PUT /api/barbers/{id}`. Mudar a comissão ou desativar
   um barbeiro só é possível direto no banco. O schema `BarberUpdateAdminRequest` existe, mas nenhuma
   rota o usa.
2. **O admin não vê os barbeiros desativados**, nem a comissão de cada um: a única listagem é a
   pública.
3. **A escala aceita almoço fora do expediente** (expediente das 9h às 12h com almoço das 14h às
   15h) e `break_start` sem `break_end`.
4. **A escala aceita trocar o dia de um registro.** Mandar `day_of_week = 3` para o registro da terça
   deixa duas quartas e nenhuma terça.
5. **A alteração de um dia exige o payload completo**, e não existe o `PUT /api/barbers/{id}/schedule`
   da semana inteira.
6. **A comissão vaza para o barbeiro:** a resposta de `PUT /me/bio` traz a `commission_rate`, que a
   regra 4 reserva ao admin.
7. **A bio e o Instagram não podem ser apagados**, porque `PUT /me/bio` ignora `null`.
8. **Os detalhes do barbeiro não trazem os serviços** (item 5 da #39). Eles só existem em
   `GET /api/services/barber/{id}`.

E um problema que os testes desta spec encontraram:

9. **Barbeiro desativado continua recebendo agendamentos.** A criação de agendamento e a
   disponibilidade não conferem se o barbeiro está ativo. Ele some da vitrine, mas um `POST` direto,
   ou uma aba aberta antes da desativação, ainda agenda com ele.

Valor: o dono gerencia a equipe pela API, que será usada na tela de barbeiros do painel, sem mexer
no banco. As escalas gravadas passam a fazer sentido, e o cliente não agenda com quem saiu.

## Regras

### Alteração pelo admin: `PUT /api/barbers/{id}`

Só para admin (403 para os outros e sem token). Alteração parcial: só os campos enviados mudam.

| Campo | Regra | `null` |
|---|---|---|
| `bio` | Até 500 caracteres. | Apaga a bio. |
| `instagram_url` | URL http(s). | Apaga o Instagram. |
| `commission_rate` | De 0 a 100. | 422 |
| `is_active` | `false` desativa e `true` reativa. | 422 |

- Campo desconhecido responde 422 (`extra=forbid`), para um erro de digitação não passar em branco.
- Barbeiro desconhecido responde 404.
- A resposta é a do admin (abaixo).

**Desativação com agendamentos futuros (decisão no lugar do cliente):** a #37 perguntava se
desativar um barbeiro deve cancelar ou avisar os agendamentos futuros dele. **Decisão: recusar.**
Se o barbeiro tem agendamentos `pending` ou `confirmed` que ainda não começaram, a desativação
responde 400 com a quantidade:

`O barbeiro tem 3 agendamento(s) futuro(s). Cancele ou remaneje antes de desativá-lo.`

Cancelar sozinho deixaria clientes sem aviso, e o sistema ainda não manda notificações. Recusar
obriga o dono a olhar a agenda antes. A reativação não tem essa conferência.

### Listagem do admin: `GET /api/barbers/admin`

Só para admin. Lista todos os barbeiros, ativos e desativados, em ordem alfabética do nome. A
resposta do admin tem os campos públicos mais `email`, `commission_rate`, `is_active` (perfil de
barbeiro) e `user_is_active` (conta).

### Escala

As mesmas regras valem para um dia e para a semana:

- `end_time` depois de `start_time`.
- Almoço completo ou nenhum: `break_start` e `break_end` vêm juntos, ou os dois `null`.
- Almoço dentro do expediente: `start_time <= break_start < break_end <= end_time`.
- Mensagens (422):
  - `O horário de término deve ser após o início.`
  - `Informe o início e o fim do almoço, ou nenhum dos dois.`
  - `O fim do almoço deve ser após o início do almoço.`
  - `O almoço deve ficar dentro do expediente.`

**Um dia: `PUT /api/barbers/{id}/schedule/{schedule_id}`** passa a aceitar alteração parcial. As
regras são conferidas com o resultado (o que foi enviado sobre o que estava gravado). O
`day_of_week` pode ser enviado, mas tem que ser o do registro: outro dia responde 422 com
`Não é possível trocar o dia de um registro da escala.`

**Semana: `PUT /api/barbers/{id}/schedule`** recebe a lista dos 7 dias, cada um completo e com
`day_of_week` de 0 a 6 sem repetição. Faltar ou repetir um dia responde 422 com
`Envie os 7 dias da semana (0 a 6), um de cada.` Ou tudo é gravado, ou nada. A resposta é a semana
gravada, de domingo a sábado.

As duas rotas são só do admin.

### Barbeiro: `PUT /api/barbers/me/bio`

- `null` em `bio` ou `instagram_url` apaga o campo. Campo não enviado continua como estava.
- A resposta não tem `commission_rate`: são os campos públicos mais o `is_active`.

### Detalhes: `GET /api/barbers/{id}`

Passa a trazer `services`: os serviços ativos vinculados ao barbeiro, em ordem alfabética, com
`id`, `name`, `price` e `duration_minutes`. O resto continua igual, inclusive o 404 para o barbeiro
inativo.

### Agendamento com barbeiro desativado

- `POST /api/appointments` e `POST /api/appointments/guest` com barbeiro desativado (perfil ou
  conta) respondem 400 com `Barbeiro indisponível para agendamento.`, sem gravar nada.
- `GET /api/appointments/availability` para esse barbeiro responde 404 com a mesma mensagem.
- Os agendamentos que já existem não mudam.

## Critérios de aceitação

Testes em `tests/test_barbeiros_admin.py` e, para a escala, em `tests/test_barbeiros_escala.py`
(pela API, com o banco de teste), que falham com o código de antes desta spec:

- [ ] O admin altera a comissão (limites 0 e 100 aceitos; -1, 100,01 e `null` recusados), a bio e o
      Instagram, inclusive apagando os dois com `null`. Campo não enviado não muda, e campo
      desconhecido responde 422.
- [ ] O admin desativa e reativa. O desativado some da vitrine e dos detalhes públicos, e volta
      quando reativado.
- [ ] A desativação com agendamento futuro `pending` ou `confirmed` responde 400 com a quantidade,
      sem desativar. Agendamentos passados, cancelados ou concluídos não impedem.
- [ ] Cliente, barbeiro e chamada sem token recebem 403 no `PUT /{id}`, na listagem do admin e nas
      duas rotas de escala. Barbeiro desconhecido responde 404.
- [ ] `GET /api/barbers/admin` traz ativos e desativados, em ordem alfabética, com a comissão e as
      duas situações.
- [ ] A escala recusa almoço fora do expediente, almoço incompleto e troca de dia, tanto num dia
      quanto na semana, sem gravar nada. O almoço encostado no início ou no fim do expediente é
      aceito.
- [ ] A alteração parcial de um dia muda só o que foi enviado, e as regras valem para o resultado.
- [ ] A semana inteira grava os 7 dias. Faltar, repetir ou ter um dia inválido não grava nenhum.
- [ ] A resposta de `PUT /me/bio` não tem `commission_rate`. `null` apaga a bio e o Instagram.
- [ ] `GET /api/barbers/{id}` traz os serviços ativos vinculados, em ordem alfabética, sem os
      desativados e sem os de outros barbeiros.
- [ ] Agendar (cliente e visitante) com barbeiro desativado responde 400, sem gravar. A
      disponibilidade dele responde 404.

## Fora do escopo

- A tela de barbeiros do painel, com o vínculo de serviços que ficou fora da tela de serviços
  (SPEC/2026-11-23-painel-servicos.md). Ela terá spec e PR próprios, sobre estas rotas.
- Desativar a conta (`User.is_active`) do barbeiro: é assunto do admin de usuários (#35).
- Notificar os clientes ou remanejar agendamentos.
- Feriados e folgas avulsas (já fora do escopo da spec da AP1).
