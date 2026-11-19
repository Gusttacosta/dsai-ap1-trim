# Agendamento no fuso da barbearia, com data escolhida e sem horários passados (2026-11-18)

> Complementa: SPEC/2026-09-29-agendamentos.md (somente leitura; esta spec substitui o que ela diz
> sobre fuso e disponibilidade)
> Issue: #12

## O quê e por quê

O agendamento grava o dia e a hora errados e aceita horários que já passaram (#12). No teste
manual de 08/11/2026, por volta das 22h de Brasília, o cliente escolheu "16:30" e a tela mostrou
"Hoje às 16:30". O banco gravou `2026-11-09 16:30 UTC`, ou seja, segunda 09/11 às 13:30 em
Brasília: nem o dia nem a hora escolhidos. As causas:

1. O frontend calcula "hoje" com `new Date().toISOString().split('T')[0]`
   (`src/frontend/src/pages/Booking.tsx`, na busca de disponibilidade e na criação), que é a data em
   UTC. Depois das 21h de Brasília, isso já é o dia seguinte.
2. O backend (`src/backend/modules/appointments/service.py`, `get_availability`) monta os slots a
   partir do `WorkSchedule` como se o expediente estivesse em UTC ("Simulando TZ UTC"). O horário
   "16:30" do expediente vira 16:30 UTC, que são 13:30 em Brasília.
3. `create_appointment` trata `start_datetime` sem fuso como UTC. O frontend manda
   `"AAAA-MM-DDTHH:MM:00"`, sem fuso, e o horário local escolhido é gravado como UTC.
4. A busca do dia (`start_of_day`/`end_of_day`) também usa a meia-noite UTC, então um agendamento
   às 21:30 de Brasília (00:30 UTC do dia seguinte) cai no dia errado e não bloqueia o slot.
5. Nem a disponibilidade nem a criação rejeitam horários no passado.
6. A tela não tem seletor de data e escreve "Hoje" fixo, no resumo e no alerta de confirmação.

Solução:

- **Fuso da barbearia na configuração.** `Settings` ganha `shop_timezone: str = "America/Sao_Paulo"`
  (variável `SHOP_TIMEZONE`), carregado com `zoneinfo.ZoneInfo`. O `WorkSchedule` continua
  guardando horas locais (`09:00`, `18:00`), e a interpretação delas passa a ser explícita: são
  horas no fuso da barbearia.
- **Banco sempre em UTC.** `start_datetime` e `end_datetime` continuam `timestamptz` e são gravados
  em UTC, convertidos do fuso da barbearia.
- **Disponibilidade no fuso local.** `get_availability(barber_id, target_date, duration)`:
  - `target_date` é uma data no fuso da barbearia;
  - os slots são montados em horário local e convertidos para UTC só na comparação com os
    agendamentos e o almoço;
  - os agendamentos do dia são buscados entre a meia-noite local de `target_date` e a do dia
    seguinte, convertidas para UTC;
  - a resposta continua sendo uma lista de `"HH:MM"` em horário local, então o contrato da API não
    muda.
- **Sem horários no passado.** A disponibilidade não devolve slots com início `<= agora +
  antecedência mínima`. Uma data anterior a hoje (no fuso da barbearia) devolve lista vazia, e uma
  data além do limite de dias à frente também.
- **Criação.** Em `create_appointment`:
  - um `start_datetime` **sem fuso** é interpretado no fuso da barbearia (é o que o frontend
    manda);
  - um `start_datetime` **com fuso** é convertido para UTC;
  - o dia da semana do expediente passa a ser o da data local, e não o da data UTC;
  - um início `<= agora + antecedência mínima` é rejeitado com 400 e a mensagem "Não é possível
    agendar em um horário que já passou.";
  - uma data além do limite de dias à frente também é rejeitada com 400.
  - Fica o 400 porque é assim que o módulo já responde aos outros erros de regra (conflito, dia sem
    expediente), via `ValueError`. A #12 sugeria 422, mas usar dois códigos para o mesmo tipo de
    erro deixaria o comportamento do módulo inconsistente.
- **"Agora" injetável.** O serviço recebe um relógio (`now: Callable[[], datetime]`, padrão
  `datetime.now(timezone.utc)`). Assim, os testes fixam "agora" em 08/11/2026 às 22h de Brasília
  sem depender da hora em que a CI roda e sem uma biblioteca nova.
- **Limites configuráveis**, até a resposta do cliente (#15):
  `booking_min_lead_minutes: int = 0` (só proíbe o passado) e `booking_max_days_ahead: int = 30`.
- **Frontend (`Booking.tsx`).**
  - "Hoje" é calculado no fuso da barbearia, com `Intl.DateTimeFormat('en-CA', { timeZone:
    'America/Sao_Paulo' })`, numa função pura em `src/frontend/src/utils/shopDate.ts`.
  - O passo do horário ganha um seletor de data: de hoje até 30 dias à frente, com hoje como padrão.
    A disponibilidade é buscada para a data escolhida.
  - O resumo e o alerta mostram a data por extenso, por exemplo "segunda-feira, 09/11/2026 às
    16:30", e não "Hoje".
  - `start_datetime` é enviado como `"<data escolhida>T<hora>:00"`, sem fuso, e o backend o
    interpreta no fuso da barbearia.
  - A lista fixa `ALL_TIMES` deixa de valer como horário disponível: a tela mostra só o que a API
    devolver.
- **Windows.** `zoneinfo` não traz a base de fusos no Windows. `tzdata` entra em
  `requirements.txt` para o backend funcionar no Windows (ver #2) e no Render igual.

Valor: o cliente agenda no dia e na hora que escolheu, vê a data antes de confirmar e não consegue
marcar um horário que já passou. O barbeiro deixa de receber agendamentos fantasmas em horários
deslocados em 3 horas.

## Critérios de aceitação

Backend, com testes em `tests/test_agendamento_fuso.py`. Os testes usam o relógio injetado e o
PostgreSQL da CI, como em `tests/test_dev_seed.py`:

- [ ] Com expediente das 09:00 às 18:00 e "agora" = 08/11/2026 14:10 em Brasília
      (17:10 UTC), a disponibilidade de 08/11 começa em `"14:30"`, e não em `"09:00"`.
- [ ] Com "agora" = 08/11/2026 22:00 em Brasília (09/11 01:00 UTC), a disponibilidade de 08/11 é
      vazia, e a de 09/11 começa em `"09:00"`.
- [ ] A disponibilidade de uma data anterior a hoje, ou além de `booking_max_days_ahead`, é vazia.
- [ ] Criar um agendamento com `start_datetime = "2026-11-09T16:30:00"` (sem fuso) grava
      `2026-11-09 19:30:00+00` no banco, e a resposta, convertida para Brasília, é 09/11 às 16:30.
- [ ] Criar com `start_datetime = "2026-11-09T16:30:00-03:00"` grava o mesmo instante.
- [ ] Um agendamento às 21:30 de Brasília (00:30 UTC do dia seguinte) bloqueia o slot de 21:30 na
      disponibilidade do próprio dia, e não na do dia seguinte. Para isso, o teste cria um
      expediente que vai até 22:00.
- [ ] O dia da semana usado para achar o `WorkSchedule` é o da data local. Um agendamento às 21:30
      de um sábado procura o expediente de sábado, e não o de domingo.
- [ ] Criar um agendamento com início `<= agora` responde 400, pela rota autenticada e pela de
      visitante. Nada é gravado no banco, nem o usuário visitante.
- [ ] Criar além de `booking_max_days_ahead` responde 400.
- [ ] `SHOP_TIMEZONE` muda o fuso: com `UTC`, `"16:30"` é gravado como `16:30 UTC`.
- [ ] Os testes falham se a correção for revertida. Isso é conferido revertendo
      `service.py` localmente antes do PR e registrado na sessão.

Frontend:

- [ ] `shopDate.ts` devolve `"2026-11-08"` para o instante `2026-11-09T01:00:00Z` (22h de
      Brasília). O teste fica em `src/frontend/src/utils/shopDate.test.ts`, com `vitest` como nova
      dependência de desenvolvimento e o script `npm test` rodando na CI.
- [ ] A tela tem seletor de data, mostra a data por extenso no resumo e no alerta e não escreve
      "Hoje" fixo.
- [ ] `npm run build` continua passando.

## Fora do escopo

Cada item abaixo vira uma issue própria:

- Usuários `guest_<hex>@trim.local` acumulados a cada agendamento de visitante
  (`appointments/router.py`).
- Nomes de visitante com 3 letras aceitos.
- A criação não confere se o horário cabe no expediente nem se cai no almoço, só se o barbeiro
  trabalha no dia. A regra 2 da spec da AP1 não é cumprida: um `POST` direto às 03:00 é aceito.
- O cancelamento pelo cliente também não confere se o agendamento é futuro.
- Antecedência mínima e limite de dias definitivos: dependem da resposta do cliente (#15). Esta
  spec só deixa os dois configuráveis.
- Migrações do Alembic (#6): nenhuma coluna muda nesta spec.
