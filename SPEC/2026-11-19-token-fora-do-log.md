# Tokens de redefinição de senha e de verificação de e-mail fora do log em produção (2026-11-19)

> Complementa: SPEC/2026-11-19-backend-windows-unicode.md (o e-mail falso passou a ir pelo
> `logging`) e SPEC/2026-11-16-deploy-render.md (`APP_ENV=production` no Render)
> Issue: #30

## O quê e por quê

O backend não envia e-mail. Em `src/backend/modules/auth/service.py`, o "e-mail falso"
(`[MOCK EMAIL]`) escreve no log, em qualquer ambiente:

- `create_user`: o e-mail do usuário e o token de verificação;
- `create_password_reset_token`: o e-mail do usuário e o link `/reset-password?token=<token>`.

Em produção, o log do serviço `trim-api` fica guardado no Render. `POST /api/auth/forgot-password`
é público e aceita qualquer e-mail. Então qualquer pessoa pode pedir a redefinição para o e-mail de
outra, como o admin, e quem lê o log usa o token em `POST /api/auth/reset-password` para trocar a
senha dessa conta. O token vale 1 hora (#30).

Solução:

- **Em desenvolvimento** (`settings.is_development`, ou seja, `APP_ENV=development`, o padrão), nada
  muda: o log mostra o e-mail e o token, porque é assim que o desenvolvedor testa o cadastro e a
  recuperação de senha sem servidor de e-mail.
- **Em qualquer outro ambiente** (`production`, `staging` etc.), o log registra só que o e-mail
  seria enviado, para qual usuário (pelo `id`) e que o envio não está configurado. Fica de fora o
  token, o link e o endereço de e-mail. As mensagens continuam só em ASCII, como na #2:
  - cadastro: `[MOCK EMAIL] Verificacao de email gerada para o usuario <id>; envio de email nao
    configurado (token omitido fora de development).`
  - redefinição: `[MOCK EMAIL] Redefinicao de senha gerada para o usuario <id>; envio de email nao
    configurado (token omitido fora de development).`
- **O resto não muda:** os tokens continuam sendo gravados no banco com a mesma validade,
  `forgot-password` continua respondendo a mesma mensagem para e-mails cadastrados e não
  cadastrados, e `create_password_reset_token` continua devolvendo o token a quem chama (a rota
  não o devolve).
- **Fora do escopo:** o envio de e-mail de verdade e as telas de "esqueci a senha" e de verificação.
  Isso depende de uma resposta do cliente, registrada na #30. Enquanto isso, a recuperação de senha
  não funciona em produção, como já acontecia: o usuário nunca recebia o token.

Valor: o log de produção deixa de ser um jeito de tomar a conta de qualquer usuário, e o fluxo de
desenvolvimento continua igual.

## Critérios de aceitação

Testes em `tests/test_token_fora_do_log.py`, com o PostgreSQL da CI. `settings.app_env` é fixado
em cada teste:

- [ ] Com `production` e com `staging`, `POST /api/auth/register` responde 201, e nenhuma mensagem
      do log contém o token de verificação gravado no banco nem o e-mail do usuário; a mensagem
      tem o `id` do usuário.
- [ ] Com `production` e com `staging`, `POST /api/auth/forgot-password` de um e-mail cadastrado
      responde 200, e nenhuma mensagem do log contém o token de redefinição gravado no banco nem o
      e-mail; a mensagem tem o `id` do usuário.
- [ ] O token gravado em produção continua válido: `POST /api/auth/reset-password` com ele
      responde 200.
- [ ] Com `development`, o cadastro e a redefinição registram o e-mail e o token, com as mesmas
      mensagens de antes.
- [ ] Com `auth/service.py` revertido, os testes de `production` e `staging` falham.
