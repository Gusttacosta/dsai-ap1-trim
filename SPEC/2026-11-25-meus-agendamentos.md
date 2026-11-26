# Meus agendamentos: o cliente vê e cancela os próprios agendamentos (2026-11-25)

> Complementa: SPEC/2026-09-29-agendamentos.md e SPEC/2026-11-18-cancelamento-agendamento.md
> Issue: #97

## O quê e por quê

O backend já lista os agendamentos do cliente (`GET /api/appointments/me`) e deixa cancelar
(`PUT /api/appointments/{id}/cancel`), mas nenhuma tela usa essas rotas. Depois de agendar, o
cliente não consegue conferir o horário nem desistir dele sem ligar para a barbearia.

A página "Minha conta" (`/conta`) ganha a seção **"Meus agendamentos"**, só para o cliente.

## Regras

- **Próximos:** agendamentos com início no futuro, do mais próximo para o mais distante.
  **Anteriores:** os outros, do mais recente para o mais antigo. Um agendamento cancelado no
  futuro continua em "Próximos", com o status "Cancelado".
- Cada agendamento mostra o **status** em português (Pendente, Confirmado, Concluído, Cancelado,
  Não compareceu), os **serviços**, o **barbeiro** e a **data e hora no fuso da barbearia**
  (`America/Sao_Paulo`), qualquer que seja o fuso do navegador.
- O nome do barbeiro vem de `GET /api/barbers`. Barbeiro que saiu da vitrine aparece como
  "Barbeiro". Se a lista de barbeiros falhar, os agendamentos aparecem do mesmo jeito.
- **"Cancelar"** segue a regra do backend (`AppointmentService.cancel_by_client`): status
  `pending` ou `confirmed` e início ainda no futuro. Nos outros, o botão não aparece.
- Cancelar pede **confirmação na própria linha** ("Cancelar este agendamento?" com "Confirmar" e
  "Voltar"), o mesmo padrão de "Desativar" no painel de serviços. O padrão vira um componente
  genérico (`ConfirmButton`), usado nas duas telas.
- Depois de cancelar, o agendamento passa a aparecer como o backend o devolveu ("Cancelado"),
  sem recarregar a lista.

## Critérios de aceitação

- [ ] `/conta` do cliente mostra "Meus agendamentos" com as listas "Próximos" e "Anteriores",
      na ordem acima, e um texto quando uma delas está vazia.
- [ ] Cada agendamento mostra status, serviços, barbeiro e data/hora no fuso da barbearia.
- [ ] "Cancelar" só em agendamento pendente ou confirmado que ainda não começou.
- [ ] "Voltar" não chama a API; "Confirmar" chama `PUT /appointments/{id}/cancel` e o
      agendamento passa a "Cancelado", sem o botão.
- [ ] Erro ao cancelar (400, 404 ou sem conexão) mostra a mensagem do backend e mantém a lista.
- [ ] Erro ao carregar mostra uma mensagem na seção, e o resto da página continua funcionando.
- [ ] Barbeiro e admin não veem a seção.
- [ ] Testes vitest da regra de cancelamento, da formatação no fuso, do hook e dos componentes.

## Fora do escopo

- Remarcar um agendamento.
- Mudanças no backend: as duas rotas já existem e são cobertas por
  `tests/test_cancelamento_agendamento.py` e `tests/test_appointments_integracao.py`.
- Paginação da lista.
