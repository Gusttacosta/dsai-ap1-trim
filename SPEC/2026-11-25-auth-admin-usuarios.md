# Auth: reenvio da verificação, administração de usuários, limite de login e redefinição de senha com token único (2026-11-25)

> Complementa: SPEC/2026-09-29-autenticacao.md, SPEC/2026-11-22-auth-refresh-logout.md e
> SPEC/2026-11-22-auth-perfil-senha.md
> Issue: #35

## O quê e por quê

A #35 listou 8 rotas da spec da AP1 que faltavam em `/api/auth`, além do rate limiting do login.
Os PRs de 22/11 já entregaram parte:
- o `POST /refresh`;
- o logout que revoga a família do refresh;
- o `PUT /me` e o `PUT /me/password`.

Este PR fecha o que falta:
1. `POST /verify-email/resend`. O token de verificação vence em 24 horas, e hoje não há como
   pedir outro;
2. a administração de usuários: `GET /users`, `GET /users/{id}`, `PUT /users/{id}/role` e
   `PUT /users/{id}/status`. Hoje não há como promover um cliente a barbeiro nem desativar uma
   conta sem mexer no banco;
3. o rate limiting do login: 5 tentativas por IP e e-mail em 15 minutos, e depois 429;
4. um pedido novo de redefinição de senha passa a invalidar o anterior. Hoje os dois links
   trocam a senha.

## Decisões

- **Limite em memória,** por processo. O deploy roda um processo só (`Procfile`). Contam só as
  falhas, o e-mail não diferencia maiúsculas, e um login certo zera a contagem. A resposta 429
  traz o `Retry-After`.
- **O admin não se rebaixa nem se desativa** (400). Assim o sistema não fica sem administrador.
- **Desativar encerra as sessões:** os refresh tokens da conta são revogados, e o login passa a
  responder 401, como já era para conta desativada.
- **Promover a barbeiro só muda o papel.** O perfil de barbeiro (comissão e escala) continua
  sendo criado pela tela de barbeiros, e a galeria e a fila já tratam o barbeiro sem perfil (#71
  e #69).

## Critérios de aceitação

1. [ ] **Reenvio da verificação:** `POST /verify-email/resend` com o e-mail de uma conta ativa e
   não verificada cria um token novo de 24 horas e marca os anteriores como usados.
   - A resposta é sempre 200 e igual, também para e-mail desconhecido, já verificado ou conta
     desativada, e nesses casos nenhum token é criado;
   - um e-mail inválido responde 422.
2. [ ] **Administração de usuários** (só o admin; os outros recebem 403):
   - `GET /users` filtra por `role`, `is_active` e `q` (nome ou e-mail, sem diferenciar
     maiúsculas), pagina com `page` ≥ 1 e `per_page` de 1 a 100, e responde
     `{users, total, page, per_page, total_pages}` sem a senha;
   - `GET /users/{id}` detalha um usuário;
   - `PUT /users/{id}/role` muda o papel. Um papel inválido responde 422;
   - `PUT /users/{id}/status` ativa ou desativa a conta;
   - um id desconhecido responde 404 `Usuário não encontrado.`
3. [ ] **Limite de login:** a sexta tentativa depois de 5 falhas do mesmo IP e e-mail responde
   **429** `Muitas tentativas de login. Tente de novo em alguns minutos.`, mesmo com a senha certa.
   Outro e-mail ou outro IP não é afetado. A janela é de 15 minutos.
4. [ ] **Redefinição de senha:** um novo `forgot-password` invalida os links anteriores não usados.
   Só o mais recente troca a senha. O teste que fixava o comportamento antigo foi atualizado.

## Testes

- `tests/test_auth_admin_usuarios.py`, pela API, com o PostgreSQL de `TEST_DATABASE_URL`;
- `tests/test_login_rate_limit.py`, a janela do limitador com um relógio falso, sem banco;
- o `tests/conftest.py` zera o limitador antes e depois de cada teste.
