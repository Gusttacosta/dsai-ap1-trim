# Deploy no Render (2026-11-16)

> Substitui/complementa: SPEC/2026-09-29-visao-geral.md (seção de deploy)
> Issue: #4

## O quê e por quê

A visão geral da AP1 previa o deploy em Vercel (frontend) e Render/Railway (backend e banco), e o
que ficou no ar foi o Railway da AP1, que não é da dupla da AP2. A AP2 só é avaliada com uma URL
pública no ar servindo o último commit da `main`, então o fork precisa de um deploy próprio,
descrito no repositório e reproduzível.

Além disso, o frontend usa como padrão a URL do backend de produção da AP1 no Railway
(`src/frontend/src/api.ts:3`). Rodar `npm run dev` sem configuração conversa com produção, e um
build sem `VITE_API_URL` publica um frontend apontando para um backend que não é nosso (#4). O
`CORS_ORIGINS` padrão do backend também libera o frontend do Railway.

Solução:

- Todo o deploy passa a ser no **Render**, descrito num Blueprint (`render.yaml` na raiz) com três
  peças:
  - **`trim-db`**: PostgreSQL no plano gratuito.
  - **`trim-api`**: Web Service Python 3.12. Build `pip install -r requirements.txt`, start
    `uvicorn src.backend.main:app --host 0.0.0.0 --port $PORT`, health check em `/health` e deploy
    automático a partir da `main`. Variáveis: `DATABASE_URL` vinda do `trim-db`, `SECRET_KEY`
    gerada pelo Render, `APP_ENV=production`, `DEBUG=false`, e `CORS_ORIGINS`, `SEED_SECRET`,
    `SEED_ADMIN_PASSWORD` e `SEED_DEMO_PASSWORD` preenchidas no painel (`sync: false`), sem valor
    padrão no arquivo.
  - **`trim-web`**: Static Site com `rootDir` `src/frontend`, build `npm ci && npm run build`,
    publicando `dist`, com `VITE_API_URL` preenchida no painel (`sync: false`) e rewrite de `/*`
    para `/index.html` (rotas do React Router).
- O backend aceita a `DATABASE_URL` no formato do Render (`postgresql://...`) e deriva dela as URLs
  do `asyncpg` (aplicação) e do `psycopg2` (Alembic).
- O frontend não tem mais URL de backend fixa no código:
  - em `npm run dev`, sem `VITE_API_URL`, usa `http://localhost:8000/api`;
  - em `npm run build`, sem `VITE_API_URL`, o build falha com uma mensagem que diz qual variável
    definir;
  - `src/frontend/.env.example` documenta `VITE_API_URL`.
- O `CORS_ORIGINS` padrão do backend passa a ter só origens locais. Em produção, a origem do
  `trim-web` é configurada no painel.
- `GET /health` passa a devolver também `commit`, lido de `RENDER_GIT_COMMIT` (variável que o
  Render define em cada deploy), ou `"local"` quando ela não existe. Assim dá para conferir qual
  commit está no ar.
- O README ganha uma seção de deploy: as três peças, as variáveis, como conferir o commit no ar e
  como popular o banco com o seed (`SEED_SECRET` no cabeçalho `X-Seed-Secret`) e remover o
  `SEED_SECRET` depois.

Valor: o projeto tem uma URL pública própria, o deploy é reproduzível a partir do repositório, dá
para provar que produção serve o último commit da `main`, e ninguém altera dados de produção sem
querer rodando o frontend local.

## Critérios de aceitação

- [ ] `render.yaml` descreve `trim-db`, `trim-api` e `trim-web` como acima, sem nenhum segredo nem
      URL de produção escritos no arquivo.
- [ ] Com `DATABASE_URL=postgresql://...` (ou `postgres://...`), `database_url_async` usa
      `postgresql+asyncpg://` e `database_url_sync` usa `postgresql+psycopg2://`.
- [ ] `GET /health` responde 200 com `status`, `app`, `version` e `commit`; `commit` é o valor de
      `RENDER_GIT_COMMIT`, ou `"local"` sem ela.
- [ ] O `CORS_ORIGINS` padrão não contém nenhuma URL do Railway.
- [ ] Nenhum arquivo em `src/` contém URL `*.up.railway.app`, e a CI falha se uma voltar.
- [ ] `npm run build` sem `VITE_API_URL` falha com mensagem clara; com ela, o build passa e o
      bundle usa essa URL. A CI verifica os dois casos.
- [ ] `npm run dev` sem `VITE_API_URL` usa `http://localhost:8000/api`.
- [ ] `src/frontend/.env.example` existe com `VITE_API_URL=http://localhost:8000/api`.
- [ ] O README documenta o deploy no Render, as variáveis, a conferência do commit no ar e o seed.

## Fora do escopo

- Criar os serviços no painel do Render e preencher as variáveis (ação operacional da dupla).
- Desligar ou apagar o deploy da AP1 no Railway.
- Trocar o `create_all` da inicialização por migrações do Alembic no deploy (#6).
- Plano pago, domínio próprio, backups do banco. O PostgreSQL gratuito do Render expira após um
  período e precisa ser recriado ou migrado de plano.
- Atualizar a URL pública no topo do README antes de o deploy estar no ar.
