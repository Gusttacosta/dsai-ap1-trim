# Renovação do access token e logout que invalida a sessão (2026-11-22)

> Complementa: SPEC/2026-09-29-autenticacao.md (rota `POST /api/auth/refresh`, regra 4 e o logout
> que "invalida o refresh token")
> Issue: #35

## O quê e por quê

O cadastro e o login gravam o cookie `refresh_token`, mas nenhuma rota usa esse cookie. O access
token do cliente vence em 30 minutos e o do barbeiro e do admin em 12 horas. Depois disso, a pessoa
precisa digitar a senha de novo. O `POST /api/auth/refresh` da spec da AP1 não existe (#35).

O logout só apaga o cookie. Como o servidor não guarda os refresh tokens, uma cópia roubada do
cookie continua valendo até vencer, que leva 7 ou 30 dias.

Há ainda dois defeitos no cookie de hoje:

- **Não tem `Max-Age`.** Ele vira um cookie de sessão do navegador e some quando o navegador fecha,
  em vez de durar os 7 ou 30 dias da regra 4.
- **Usa `SameSite=Lax`.** Em produção, o frontend (`trim-web.onrender.com`) e a API
  (`trim-api-ujwo.onrender.com`) ficam em sites diferentes, porque o `onrender.com` está na Public
  Suffix List. O navegador não manda um cookie `Lax` num `fetch` entre sites, então o refresh nunca
  receberia o cookie.

Solução:

1. O servidor passa a guardar cada refresh token emitido na tabela nova `refresh_tokens`, e o JWT
   do refresh ganha a claim `jti` com o id da linha.
2. Cria-se o `POST /api/auth/refresh`. Ele lê o cookie, troca o refresh token por um novo
   (**rotação**) e devolve um access token novo.
3. O logout revoga a sessão do cookie no servidor.
4. A redefinição de senha (`reset-password`) revoga todas as sessões do usuário.
5. O frontend renova o access token sozinho quando recebe um 401, e o botão "Sair" chama o logout
   da API.

Valor: o cliente não é deslogado a cada 30 minutos, e quem sai ou troca a senha encerra de fato as
sessões abertas.

## Regras

- **Sessão (família):** o login e o cadastro abrem uma sessão nova, identificada por `family_id`.
  Cada refresh revoga o token usado e emite outro na mesma família, com validade nova (7 dias para
  cliente, 30 dias para barbeiro e admin, contados a partir do refresh).
- **Reuso:** apresentar um refresh token já trocado indica que ele pode ter sido copiado. Nesse
  caso, a família inteira é revogada e a resposta é 401.
  - **Exceção de corrida:** se o token foi trocado há até 10 segundos (duas abas renovando juntas),
    a resposta é 401 sem revogar a família. A outra aba já recebeu o cookie novo, e a família
    continua valendo.
- **Dados atuais:** o novo access token usa o `email` e o `role` lidos do banco no momento do
  refresh, não os do token antigo. Assim, uma promoção a barbeiro vale no próximo refresh.
- **Usuário inativo ou apagado:** o refresh responde 401.
- **Tokens antigos:** um refresh token emitido antes desta mudança, sem `jti`, responde 401. A
  pessoa entra de novo uma vez.
- **Origem:** o refresh e o logout respondem 403 quando o cabeçalho `Origin` vem e não está em
  `CORS_ORIGINS`. O cookie `SameSite=None` é enviado em pedidos de outros sites, e essa conferência
  impede que outro site encerre ou gire a sessão de alguém. Pedidos sem `Origin`, como os de
  `curl` e dos testes, seguem normalmente.
- **Cookie:** `HttpOnly`, `Secure`, `Path=/api/auth`, `Max-Age` igual à validade do refresh token
  e `SameSite` vindo da configuração nova `REFRESH_COOKIE_SAMESITE`. O padrão é `lax`, para o
  desenvolvimento local, em que frontend e API são o mesmo site. O `render.yaml` define `none`. O
  logout apaga o cookie com os mesmos atributos, porque um `Path` diferente não apagaria o cookie.

## Critérios de aceitação

Backend, com testes de integração em `tests/test_auth_refresh.py`:

- [ ] Cadastro e login gravam uma linha em `refresh_tokens` e devolvem o cookie com `Max-Age`
      (604800 para cliente e 2592000 para barbeiro e admin), `Path=/api/auth`, `HttpOnly`,
      `Secure` e o `SameSite` da configuração. O JWT do refresh traz `jti` igual ao id da linha.
- [ ] `POST /api/auth/refresh` com um cookie válido responde 200 com o mesmo formato do login
      (`access_token`, `token_type`, `expires_in` e `user`) e um cookie novo. O token usado fica
      revogado, e o novo pertence à mesma família.
- [ ] O access token novo usa o `role` atual do banco: um cliente promovido a barbeiro recebe
      `expires_in = 43200`.
- [ ] Sem cookie, com cookie malformado, assinado com outra chave, vencido, com um access token no
      lugar do refresh, sem `jti` ou com um `jti` que não existe, a resposta é 401.
- [ ] Reusar um token já trocado, depois da janela de 10 segundos, responde 401 e revoga todos os
      tokens da família, inclusive o mais novo. Dentro da janela, responde 401 e a família continua
      valendo.
- [ ] Usuário desativado ou apagado recebe 401 no refresh.
- [ ] `Origin` fora de `CORS_ORIGINS` recebe 403 no refresh e no logout. `Origin` permitido e
      pedido sem `Origin` passam.
- [ ] O logout com um cookie válido revoga a família dele, e o refresh seguinte com esse cookie
      responde 401. Outras sessões do mesmo usuário continuam valendo. O logout sem cookie ou com
      cookie inválido responde 200. Nos dois casos, o cookie é apagado com `Path=/api/auth`.
- [ ] `reset-password` com sucesso revoga todas as sessões do usuário.

Frontend:

- [ ] O `api` (axios) manda o cookie (`withCredentials`). Quando uma resposta vem com 401, ele
      chama o `/auth/refresh` uma vez, guarda o token novo e repete o pedido. Vários 401 ao mesmo
      tempo compartilham um único refresh.
- [ ] Os 401 do próprio `/auth/login` e do `/auth/refresh` não disparam um refresh. Se o refresh
      falha, o token local é apagado e o pedido original falha como antes.
- [ ] Os botões "Sair" da barra e do painel chamam `POST /auth/logout` antes de apagar o token
      local.
- [ ] Testes do Vitest cobrem a renovação, o refresh compartilhado, a falha do refresh e a
      exclusão das rotas de login e refresh.

## Fora do escopo

- Lista de sessões abertas e "sair de todos os dispositivos" na interface.
- Limpeza periódica das linhas vencidas de `refresh_tokens`.
- Migração do Alembic para a tabela nova. O projeto ainda cria as tabelas com `create_all` (#6).
- As outras rotas da #35 (reenvio da verificação, perfil, troca de senha, administração de usuários
  e rate limiting). Cada grupo terá spec e PR próprios.
- Os navegadores que bloqueiam cookies de terceiros (Safari, por exemplo) não mandam o cookie entre
  `onrender.com` diferentes, mesmo com `SameSite=None`. Nesses navegadores, a pessoa entra de novo
  quando o access token vence, como hoje. Resolver isso exige servir a API e o frontend no mesmo
  site (domínio próprio ou proxy), o que é uma decisão de deploy fora desta spec.
