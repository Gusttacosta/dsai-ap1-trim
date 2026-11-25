# Disponibilidade só aceita duração entre 1 minuto e 24 horas (2026-11-25)

> Complementa: SPEC/2026-09-29-agendamentos.md e SPEC/2026-11-24-testes-integracao-appointments.md
> Issue: #57

## O quê e por quê

`GET /api/appointments/availability` recebe `duration_minutes` como um `int` sem limite. Com `0`, a
lista inclui o horário de fechamento (18:00), e com `-30` aparecem ainda mais horários. Nenhum
serviço dura zero minutos, e uma duração negativa não tem sentido: a tela recebe horários que
o próprio agendamento depois recusaria ou gravaria com um fim antes do início.

O limite superior de 24 horas (1.440 minutos) evita que um valor absurdo percorra o laço à toa.
Um atendimento maior que o expediente já volta como uma lista vazia.

## Critérios de aceitação

- [ ] `duration_minutes` igual a `0`, negativo ou maior que `1440` responde **422**.
- [ ] Os valores de borda funcionam: `1` e `1440` respondem 200.
- [ ] Sem regressão: num expediente das 09:00 às 18:00, `30` continua devolvendo 09:00 a 17:30,
  `540` devolve só 09:00, e `541` devolve uma lista vazia.
- [ ] Os testes falham com o código anterior.

## Testes

`tests/test_disponibilidade_duracao.py`, com `create_shop` de `tests/agenda_fixtures.py`.
