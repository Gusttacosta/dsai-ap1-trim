# Testes de integração do módulo de autenticação, no lugar dos testes gerados (2026-11-21)

> Complementa: SPEC/2026-09-29-autenticacao.md (descreve o comportamento que os testes conferem)
> Issue: #3

## O quê e por quê

Os 13 arquivos `tests/test_<módulo>.py` herdados da AP1 são escritos por `tests/generate_tests.py`.
São 1.000 funções por módulo, cerca de 28 mil linhas por arquivo. Cada função copia um dict fixo e
confere o próprio dict (`assert payload is not None`, `assert payload['scenario_id'] == i`).
Nenhuma delas importa `src`, então apagar o corpo de qualquer função de
`src/backend/modules/*/service.py` não quebra nenhum teste (#3). Esses arquivos também respondem por
quase toda a duplicação medida pelo `jscpd`: 287.976 das 288.427 linhas duplicadas, ou 76,2% do
total.

Plano da #3, **um módulo por PR**:

1. Escrever os testes de integração reais do módulo, pela API (`httpx.AsyncClient` com a aplicação)
   e com o PostgreSQL de teste, usando as fixtures `sessionmaker` e `client` de
   `tests/agenda_fixtures.py`.
2. No mesmo PR, apagar o `tests/test_<módulo>.py` gerado e tirar o módulo da lista `MODULES` de
   `tests/generate_tests.py`, para que ele não volte se alguém rodar o gerador. Quando a lista
   ficar vazia, o gerador também sai.

Assim, nenhum módulo fica sem testes no meio do caminho, e a duplicação cai a cada PR. Este
primeiro PR cobre o `auth`, porque os outros módulos vão usar o cadastro, o login e o token dele.

Os testes descrevem o comportamento **atual** das 7 rotas de `/api/auth` (`register`, `login`,
`logout`, `me`, `verify-email`, `forgot-password` e `reset-password`) e das dependências
`get_current_user`, `get_current_admin` e `get_current_barber_or_admin`. O código da aplicação não
muda.

Valor: um erro no cadastro, no login, no token ou na redefinição de senha passa a quebrar a CI, e o
número de testes do `pytest` passa a medir alguma coisa.

## Critérios de aceitação

Testes em `tests/test_auth_integracao.py`, com o PostgreSQL de `TEST_DATABASE_URL` (o mesmo da CI):

- [ ] **Cadastro:** responde 201 com `access_token`, `token_type = bearer` e o usuário sem a senha,
      e grava o cookie `refresh_token` como `HttpOnly`. A senha fica no banco só como hash bcrypt.
      O primeiro usuário vira `admin` e os seguintes viram `client`. O nome é gravado sem espaços nas
      pontas. É criado um token de verificação que vence em 24 horas, e `email_verified` fica falso.
- [ ] **Validação do cadastro:** e-mail repetido responde 400 (`Email já cadastrado.`). Senha com
      menos de 8 caracteres, sem letra ou sem número, nome com menos de 2 caracteres e e-mail
      inválido respondem 422, e nenhum usuário é gravado.
- [ ] **Tokens:** o access token traz `user_id`, `email` e `role` e vence em 30 minutos para
      cliente e em 12 horas para barbeiro e admin (`expires_in` = 1800 ou 43200). O refresh token
      traz `type = refresh` e vence em 7 dias para cliente e em 30 dias para barbeiro e admin.
- [ ] **Login:** com as credenciais certas, responde 200 com os tokens. Senha errada e e-mail
      desconhecido respondem 401 com a mesma mensagem (`E-mail ou senha incorretos`) e o cabeçalho
      `WWW-Authenticate: Bearer`. Usuário desativado também recebe 401.
- [ ] **`/me` e rotas protegidas:** com um access token válido, `/me` devolve o usuário sem a
      senha. Sem token, a resposta é 403 (o `HTTPBearer` do FastAPI 0.115). Respondem 401: token
      malformado, assinado com outra chave, vencido, refresh token usado como access, payload sem
      `user_id`, `user_id` que não é UUID e usuário que não existe mais. Usuário desativado recebe
      403.
- [ ] **Perfis:** `get_current_admin` aceita só admin. `get_current_barber_or_admin` aceita admin e
      barbeiro. Os dois respondem 403 para os outros perfis.
- [ ] **Logout:** responde 200 e apaga o cookie `refresh_token`.
- [ ] **Verificação de e-mail:** o token do cadastro marca `email_verified` e fica usado. O mesmo
      token de novo, um token vencido ou um token desconhecido respondem 400.
- [ ] **Redefinição de senha:** `forgot-password` responde 200 com a mesma mensagem para e-mail
      cadastrado e desconhecido. Só no cadastrado cria um token, que vence em 1 hora.
      `reset-password` com o token troca a senha: a nova entra e a antiga não. Token reutilizado,
      vencido ou desconhecido responde 400. Nova senha fraca responde 422.
- [ ] **Os testes testam:** se o corpo de qualquer método de `AuthService` for trocado por um
      `raise`, algum teste novo falha.
- [ ] `tests/test_auth.py` (gerado) é apagado, e `auth` sai da lista `MODULES` de
      `tests/generate_tests.py`.

## Fora do escopo

- Mudar o comportamento do `auth`. As diferenças entre o código e a spec da AP1 ficam numa issue
  própria: `/refresh`, reenvio da verificação, `PUT /me`, troca de senha, rotas de admin para
  usuários e rate limiting de login não existem.
- Os testes dos outros 12 módulos, que vêm em PRs próprios, seguindo o mesmo plano.
