# Agendamento de visitante: nome e sobrenome validados no backend (2026-11-23)

> Complementa: SPEC/2026-09-29-agendamentos.md (agendamento sem cadastro)
> Issue: #22

## O quê e por quê

Quem agenda sem conta informa só o nome, na primeira etapa de `/agendar`. Hoje:

- o frontend só exige 3 caracteres (`Booking.tsx`, `guestName.trim().length < 3`), e "sev" foi aceito
  no teste manual de 08/11;
- o backend não valida nada (`GuestAppointmentCreateRequest.guest_name: str`). Um `POST` direto em
  `/api/appointments/guest` aceita nome vazio, só com espaços, com números ou com milhares de
  caracteres. Acima de 255 caracteres, a coluna `users.full_name` recusa o valor e a rota responde
  500;
- o botão "Próximo" fica desabilitado sem dizer por quê.

O nome vai para `users.full_name` e para as notas do agendamento, que é o que o barbeiro vê.

Valor: o barbeiro sabe quem vem, e o visitante entende o que falta preencher.

## Regras

O backend é a fonte da regra. O frontend repete a mesma regra para dar retorno imediato.

1. **Limpeza:** os espaços das pontas são removidos, e espaços repetidos no meio viram um só.
   O nome gravado (no usuário e nas notas) é o nome limpo.
2. **Nome e sobrenome:** pelo menos duas palavras, cada uma com pelo menos 2 caracteres
   ("Ana Sá", "João da Silva", "Li Wu").
3. **Caracteres:** só letras (com acento), espaço, apóstrofo, hífen e ponto ("D'Ávila",
   "Maria-José", "Jr."). Cada palavra precisa ter pelo menos uma letra.
4. **Tamanho:** no máximo 255 caracteres depois da limpeza, o tamanho de `users.full_name`.

| Situação | Mensagem (422 no backend e na tela) |
|---|---|
| Vazio, só espaços ou uma palavra só | `Informe nome e sobrenome` |
| Uma palavra com 1 caractere ("Ana S") | `Informe nome e sobrenome` |
| Número ou símbolo fora da lista ("Ana 123", "Ana @Silva") | `Nome deve ter só letras, espaços, apóstrofo, hífen e ponto` |
| Mais de 255 caracteres | `Nome deve ter no máximo 255 caracteres` |

**Na tela:** a mensagem aparece embaixo do campo depois que o visitante digita algo (não antes),
e o botão "Próximo" continua desabilitado enquanto o nome não serve. O payload leva o nome já
limpo.

## Decisões no lugar do cliente

A #22 perguntava se o visitante deve informar nome e sobrenome e se o telefone deve ser
obrigatório.

- **Nome e sobrenome: sim.** O objetivo da issue é o barbeiro saber quem vem, e um primeiro nome
  ou um apelido ("sev", "Visitante") não diz isso.
- **Telefone: continua fora.** Ele está ligado à #21 (o usuário `guest_<hex>@trim.local` criado a
  cada agendamento), que vai decidir como o visitante é identificado e contatado.

## Critérios de aceitação

Testes em `tests/test_nome_do_visitante.py` (pela API, com o banco de teste) e no Vitest, que
falham com o código de antes desta spec:

- [ ] `POST /api/appointments/guest` com nome vazio, só espaços, uma palavra, palavra de 1
      caractere, número, símbolo ou mais de 255 caracteres responde 422 com a mensagem da tabela,
      e nenhum usuário nem agendamento é criado.
- [ ] Os nomes válidos dos exemplos das regras são aceitos (201). Com 255 caracteres exatos,
      também.
- [ ] O nome gravado no usuário e nas notas ("Visitante: ...") é o nome limpo:
      `"  ana   de  souza "` vira `"ana de souza"`.
- [ ] No frontend, a mesma regra (`utils/guestName.ts`) recusa e aceita os mesmos casos.
- [ ] Na etapa do nome, a mensagem só aparece depois que algo é digitado. Com o nome inválido,
      "Próximo" fica desabilitado. Com o nome válido, ele habilita e, ao confirmar, o
      `POST /appointments/guest` leva o nome limpo.

## Fora do escopo

- Telefone do visitante (ver acima, #21).
- As notas digitadas pelo visitante: a tela não tem esse campo, e a rota troca as notas por
  "Visitante: <nome>". Fica como está.
- O nome do cadastro e do perfil (`clean_full_name`, SPEC/2026-11-22-auth-perfil-senha.md), que
  continua aceitando um nome só: quem tem conta já é identificado pelo e-mail.
