# Seed seguro (`/api/dev/seed` e `/api/dev/update_dates`) (2026-11-16)

> Complementa: SPEC/2026-09-29-visao-geral.md e SPEC/2026-09-29-assinaturas.md
> Issues: #5, #10

## O quê e por quê

As rotas `POST /api/dev/seed` e `POST /api/dev/update_dates` (`src/backend/modules/dev_router.py`)
estão registradas em todos os ambientes, inclusive produção, e são protegidas por um segredo
escrito no código de um repositório público. As senhas dos usuários de demonstração também estão
no código (#5).

Além disso, o seed quebra no meio ao criar os planos do Trim Club, porque usa campos que não
existem mais em `SubscriptionPlan` (`price`, `billing_cycle`). Mesmo assim responde HTTP 200, com o
traceback do servidor no corpo, e deixa o banco populado pela metade (#10).

Solução:

- As duas rotas só existem quando a variável de ambiente `SEED_SECRET` está definida e não vazia.
  Sem ela, respondem 404, como se não existissem.
- O segredo é enviado no cabeçalho `X-Seed-Secret` (cabeçalho não aparece em log de acesso, ao
  contrário da query string) e comparado com `secrets.compare_digest` contra `SEED_SECRET`.
  Nenhum segredo fica no código.
- A senha do admin de demonstração vem de `SEED_ADMIN_PASSWORD`. Sem ela, o seed não cria o admin
  (nem o perfil de barbeiro dele nem as transações associadas a ele) e segue com o resto.
- Os demais usuários de demonstração (barbeiro e cliente) são criados com uma senha aleatória
  descartada na hora: existem como dados, mas ninguém consegue entrar com eles.
- O seed roda numa transação só: ou grava tudo, ou não grava nada.
- Em caso de erro, a resposta é HTTP 500 com uma mensagem genérica. O detalhe e o traceback vão
  para o log do servidor.
- Os planos do Trim Club passam a usar os campos atuais do modelo, com `included_cuts` e
  `included_shaves` coerentes com a descrição de cada plano:

  | Plano | `monthly_price` | `included_cuts` | `included_shaves` |
  | :--- | ---: | ---: | ---: |
  | Básico (2 cortes no mês) | 80,00 | 2 | 0 |
  | Executivo (cortes ilimitados, barba a cada 15 dias) | 150,00 | 30 | 2 |
  | Barba & Cabelo (2 cortes e 2 barbas no mês) | 120,00 | 2 | 2 |

  O modelo não tem um valor especial para "ilimitado" (o schema exige inteiro ≥ 0), então o plano
  Executivo usa 30 cortes, um por dia do mês.

Valor: o banco de produção deixa de poder ser populado ou alterado por qualquer pessoa que leia o
repositório, e um banco novo passa a ser populado por completo, com o Trim Club funcionando.

## Critérios de aceitação

- [ ] Sem `SEED_SECRET` (ou com ela vazia), `POST /api/dev/seed` e `POST /api/dev/update_dates`
      respondem 404.
- [ ] Com `SEED_SECRET` definida, sem o cabeçalho `X-Seed-Secret` ou com valor diferente, as duas
      rotas respondem 403 e não tocam no banco.
- [ ] A comparação do segredo usa `secrets.compare_digest`. Não há segredo nem senha de
      demonstração escritos no código.
- [ ] Com `SEED_ADMIN_PASSWORD` definida, o seed cria o admin com essa senha. Sem ela, o admin não
      é criado e o restante do seed é gravado normalmente.
- [ ] Em um banco novo, o seed com o segredo certo responde 200 e grava os três planos do Trim Club
      com `monthly_price`, `included_cuts` e `included_shaves` da tabela acima.
- [ ] Rodar o seed de novo não duplica dados.
- [ ] Se qualquer etapa do seed falhar, nada é gravado no banco.
- [ ] Em caso de erro, as duas rotas respondem 500 com `{"detail": "<mensagem genérica>"}`, sem
      traceback nem mensagem da exceção no corpo; o erro é registrado no log com o traceback.
- [ ] `.env.example` lista `SEED_SECRET` e `SEED_ADMIN_PASSWORD` vazias.
- [ ] Testes automatizados cobrem: 404 sem `SEED_SECRET`, 403 com segredo errado, resposta de erro
      sem traceback e seed completo num banco PostgreSQL novo. A CI sobe um PostgreSQL para esses testes.

## Fora do escopo

- Trocar as senhas dos usuários de demonstração já criados em ambientes publicados. Isso é uma
  ação operacional, feita fora do código; o seed não altera usuários que já existem.
- Criar migrações do Alembic (#6).
- Mudar o conteúdo do seed além dos planos do Trim Club e das senhas.
- Mover o seed para um comando de linha de comando ou separar `dev_router.py` em pacote.
