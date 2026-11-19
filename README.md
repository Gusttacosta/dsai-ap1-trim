# Trim ✂️ — Gestão Completa para Barbearias

#### 🆕 AP2 — fork

> **AP2 — Fork da plataforma web do repositório da AP1 (Desenvolvimento de Software Apoiado por IA, 2026.4 — UFPA)**

> **URL Pública:** [https://trim-web.onrender.com](https://trim-web.onrender.com)

Nesta AP2, estamos inserindo melhorias, novos recursos e correções de erros utilizando agentes de IA.

Repositório original (AP1): [Gusttacosta/dsai-ap1-trim](https://github.com/Gusttacosta/dsai-ap1-trim). As regras de trabalho da AP2 estão em [`AGENTS.md`](AGENTS.md).

---

#### 📦 AP1 — dupla original (mantido sem alterações)

> > **AP1 — Desenvolvimento de Software Apoiado por IA (2026.4 — UFPA)**
> 
> > **URL Pública:** [https://dsai-ap1-trim-frontend-production.up.railway.app](https://dsai-ap1-trim-frontend-production.up.railway.app)
> 
> Plataforma web de gestão para barbearias: agendamento online, controle de time, catálogo de serviços, venda de produtos, assinaturas/planos recorrentes, financeiro e CRM de clientes — tudo em um só lugar.

## 👥 Integrantes da Dupla

#### 🆕 AP2 — fork

- **Integrante 1:** Jordhan Henrique Lima (GitHub: [@henriquelm-io](https://github.com/henriquelm-io))
- **Integrante 2:** Severino Sobrinho (GitHub: [@Severino-Sobrinho](https://github.com/Severino-Sobrinho))

---

#### 📦 AP1 — dupla original (mantido sem alterações)

> - **Integrante 1:** [Nome Completo](https://github.com/Gusttacosta) (GitHub: `@Gusttacosta`)
> - **Integrante 2:** [Nome Completo](https://github.com/usuario2) (GitHub: `@usuario2`)

## 🛠️ Stack Tecnológica

#### 🆕 AP2 — fork

- **Frontend:** React 19 + TypeScript + Vite, com React Router e Axios
- **Estilização:** CSS puro (`index.css` global e CSS Modules por página)
- **Testes do frontend:** Vitest (`npm test`)
- **Backend / API:** Python 3.12 + FastAPI, servido pelo Uvicorn
- **ORM:** SQLAlchemy 2 assíncrono (`asyncpg`; `psycopg2` para a URL síncrona). O Alembic está nas dependências, mas não há migrações: as tabelas são criadas na inicialização da API (ver #6)
- **Banco de Dados:** PostgreSQL (16 na CI; o Render fornece o de produção)
- **Validação e configuração:** Pydantic 2 + pydantic-settings (variáveis do `.env`)
- **Autenticação:** JWT (python-jose + passlib/bcrypt)
- **Fuso horário:** `zoneinfo` + `tzdata`, com o fuso da barbearia em `SHOP_TIMEZONE` ([`SPEC/2026-11-18-agendamento-fuso-horario.md`](SPEC/2026-11-18-agendamento-fuso-horario.md))
- **Testes do backend:** pytest + pytest-asyncio + httpx; os testes de banco usam um PostgreSQL em `TEST_DATABASE_URL`
- **Qualidade:** Ruff
- **CI:** GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)), em todo push e PR para a `main`: backend (Python 3.12, PostgreSQL 16 de serviço, import da aplicação e `pytest`) e frontend (Node 22, `npm ci`, `npm test`, build sem `VITE_API_URL` precisa falhar, build com ela precisa passar, nenhuma URL do Railway em `src/`)
- **Hospedagem / Deploy:** Render, pelo Blueprint [`render.yaml`](render.yaml): PostgreSQL (`trim-db`), API (`trim-api`, Web Service Python) e site estático (`trim-web`), com deploy automático a cada push na `main` ([`SPEC/2026-11-16-deploy-render.md`](SPEC/2026-11-16-deploy-render.md))

---

#### 📦 AP1 — dupla original (mantido sem alterações)

> - **Frontend:** React + TypeScript + Vite
> - **Estilização:** Vanilla CSS (CSS Modules)
> - **Backend / API:** Python + FastAPI
> - **ORM / Migrations:** SQLAlchemy + Alembic
> - **Banco de Dados:** PostgreSQL
> - **Validação:** Pydantic
> - **Autenticação:** JWT (python-jose + passlib)
> - **Hospedagem / Deploy:** Vercel (frontend) + Render / Railway (backend + banco)

## 🤖 Ferramentas e Modelos de IA Utilizados

#### 🆕 AP2 — fork

| Ferramenta | Modelo | Utilização Principal |
| :--- | :--- | :--- |
| VS Code (com Remote-SSH) | — | Editor conectado por SSH à VM de desenvolvimento, onde rodam o código, o banco e o agente |
| Claude Code | `claude-opus-5-5`, `claude-haiku-5-5` | Investigação e issues, specs, código, testes, revisão e documentação |

Os modelos são os que aparecem na coluna "Modelo" de [`prompts/sessoes/CUSTOS.md`](prompts/sessoes/CUSTOS.md), que registra os tokens de cada sessão. As transcrições ficam em [`prompts/sessoes/`](prompts/sessoes/).

---

#### 📦 AP1 — dupla original (mantido sem alterações)

> | Ferramenta | Modelo | Utilização Principal |
> | :--- | :--- | :--- |
> | Antigravity IDE | Gemini 2.5 Pro / Gemini 3.8 Flash / Claude Opus 4.6 | Planejamento, specs, geração de código e testes |

## 🚀 Como Rodar o Projeto Localmente

#### 🆕 AP2 — fork

### Ambiente do Henrique: VM Debian 13 acessada por SSH

O projeto roda numa VM **Debian 13** no **VirtualBox**, com uma placa em **rede host-only**. O
host acessa a VM por SSH (pelo VS Code com Remote-SSH) e abre o frontend no navegador pelo IP da
VM. Nos comandos abaixo, troque `<ip-da-vm>` pelo IP da VM na rede host-only (`ip -4 addr`) e as
senhas de exemplo por senhas suas.

#### Pré-requisitos

- Python 3.12 ou mais novo (o Debian 13 traz o 3.13; a CI usa o 3.12) com `python3-venv`
- Node.js 20 ou mais novo (a CI usa o 22)
- PostgreSQL (o do Debian 13 é o 17)
- `cloc`, para medir o código novo (ver [Contagem de Linhas](#-contagem-de-linhas-de-código-cloc))

```bash
sudo apt install python3-venv postgresql cloc git
```

#### 1. Código e ambiente Python

```bash
git clone https://github.com/henriquelm-io/dsai-ap2-trim.git
cd dsai-ap2-trim

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. PostgreSQL local, com usuário e banco próprios

```bash
sudo -u postgres psql -c "CREATE USER trim WITH PASSWORD 'senha-de-exemplo';"
sudo -u postgres psql -c "CREATE DATABASE trim_db OWNER trim;"
# Opcional: banco descartável para os testes que precisam de PostgreSQL
sudo -u postgres psql -c "CREATE DATABASE trim_test OWNER trim;"
```

#### 3. `.env`

```bash
cp .env.example .env
```

No `.env`, ajuste pelo menos:

```dotenv
DATABASE_URL=postgresql+asyncpg://trim:senha-de-exemplo@localhost:5432/trim_db
DATABASE_URL_SYNC=postgresql+psycopg2://trim:senha-de-exemplo@localhost:5432/trim_db
SECRET_KEY=troque-por-um-valor-longo-e-aleatorio
CORS_ORIGINS=http://localhost:5173,http://<ip-da-vm>:5173
```

`CORS_ORIGINS` precisa incluir `http://<ip-da-vm>:5173`, porque é dessa origem que o navegador do
host chama a API. O `.env` está no `.gitignore` e nunca vai para o Git.

#### 4. Backend

```bash
source venv/bin/activate
uvicorn src.backend.main:app --host 0.0.0.0 --port 8001
```

**Não há migrações.** A pasta `alembic/versions/` está vazia, então `alembic upgrade head` não faz
nada (ver #6). As tabelas são criadas pelo próprio backend ao iniciar (`Base.metadata.create_all`
em `src/backend/main.py`). Para conferir: `curl http://<ip-da-vm>:8001/health`.

#### 5. Frontend

Em outro terminal:

```bash
cd src/frontend
npm install
VITE_API_URL=http://<ip-da-vm>:8001/api npm run dev -- --host 0.0.0.0
```

No host, abra `http://<ip-da-vm>:5173`. A `VITE_API_URL` termina em `/api`. Sem ela, o `npm run dev`
usa `http://localhost:8000/api`, que não é a porta usada aqui; o `npm run build` falha sem ela.

#### 6. Dados de demonstração (seed)

As rotas de seed só existem com `SEED_SECRET` definida ([`SPEC/2026-11-16-seed-seguro.md`](SPEC/2026-11-16-seed-seguro.md)).
No `.env`, defina `SEED_SECRET`, `SEED_ADMIN_PASSWORD` e `SEED_DEMO_PASSWORD`, reinicie o backend e rode:

```bash
curl -X POST http://localhost:8001/api/dev/seed -H "X-Seed-Secret: $SEED_SECRET"
```

Usuários criados: `admin@trim.com` (admin, senha `SEED_ADMIN_PASSWORD`), `carlos@trim.com`
(barbeiro) e `cliente@trim.com` (cliente), estes dois com a senha `SEED_DEMO_PASSWORD`. Rodar de
novo não duplica dados; `POST /api/dev/update_dates` traz as datas de demonstração para hoje.

#### 7. Testes

```bash
# Backend (sem TEST_DATABASE_URL, os testes de banco são pulados)
TEST_DATABASE_URL=postgresql+asyncpg://trim:senha-de-exemplo@localhost:5432/trim_test pytest -q

# Frontend
cd src/frontend && npm test
```

### Ambiente do Severino: Windows

_Espaço reservado: o Severino vai descrever aqui o passo a passo no Windows (inclusive
`PYTHONUTF8=1`, ver #2, e a porta 5173 presa por um Vite órfão, ver #11)._

---

#### 📦 AP1 — dupla original (mantido sem alterações)

> ### Pré-requisitos
> - Python >= 3.11
> - Node.js >= 20 (para o frontend)
> - PostgreSQL (ou Docker)
> 
> ### Backend
> ```bash
> # Clone o repositório
> git clone https://github.com/Gusttacosta/dsai-ap1-trim.git
> cd dsai-ap1-trim
> 
> # Crie e ative o ambiente virtual
> python -m venv venv
> source venv/bin/activate  # Linux/Mac
> .\venv\Scripts\activate   # Windows
> 
> # Instale as dependências
> pip install -r requirements.txt
> 
> # Configure as variáveis de ambiente
> cp .env.example .env
> # Edite o .env com suas credenciais do PostgreSQL
> 
> # Execute as migrations
> alembic upgrade head
> 
> # Execute o servidor de desenvolvimento
> uvicorn src.backend.main:app --reload
> ```
> 
> ### Frontend
> ```bash
> cd src/frontend
> npm install
> npm run dev
> ```

## ☁️ Deploy

#### 🆕 AP2 — fork

### Deploy no Render

O deploy é descrito no Blueprint [`render.yaml`](render.yaml)
(spec: [`SPEC/2026-11-16-deploy-render.md`](SPEC/2026-11-16-deploy-render.md)). No painel do
Render: **New → Blueprint**, escolha este repositório e preencha as variáveis pedidas.

#### As três peças

| Serviço | Tipo | O que faz |
| :--- | :--- | :--- |
| `trim-db` | PostgreSQL (gratuito) | Banco de produção. As tabelas são criadas na inicialização da API. |
| `trim-api` | Web Service Python 3.12 | `pip install -r requirements.txt`, depois `uvicorn src.backend.main:app --host 0.0.0.0 --port $PORT`. Health check em `/health`. Deploy automático a cada push na `main`. |
| `trim-web` | Static Site | Em `src/frontend`: `npm ci && npm run build`, publica `dist`. Rewrite de `/*` para `/index.html` (rotas do React Router). Deploy automático a cada push na `main`. |

#### URLs reais dos serviços

O Render pode acrescentar um sufixo ao nome do serviço quando o nome já está em uso. O frontend
ficou em `https://trim-web.onrender.com`, mas o backend ficou em
**`https://trim-api-ujwo.onrender.com`**, e não em `https://trim-api.onrender.com`. Por isso,
**confira as URLs reais no painel do Render** antes de preencher `CORS_ORIGINS` (no `trim-api`) e
`VITE_API_URL` (no `trim-web`). A `VITE_API_URL` **precisa terminar em `/api`**, por exemplo
`https://trim-api-ujwo.onrender.com/api`.

#### Variáveis

| Serviço | Variável | Valor |
| :--- | :--- | :--- |
| `trim-api` | `PYTHON_VERSION` | `3.12` (no `render.yaml`) |
| `trim-api` | `DATABASE_URL` | Vem do `trim-db` (`postgresql://...`); o backend converte para `asyncpg` e `psycopg2`. |
| `trim-api` | `SECRET_KEY` | Gerada pelo Render. |
| `trim-api` | `APP_ENV` / `DEBUG` | `production` / `false` (no `render.yaml`) |
| `trim-api` | `CORS_ORIGINS` | **Painel.** URL real do `trim-web`: `https://trim-web.onrender.com`. |
| `trim-api` | `SEED_SECRET` | **Painel.** Só durante o seed (ver abaixo). Vazia = rotas de seed respondem 404. |
| `trim-api` | `SEED_ADMIN_PASSWORD` | **Painel.** Senha do admin de demonstração. Vazia = admin não é criado. |
| `trim-api` | `SEED_DEMO_PASSWORD` | **Painel.** Senha do barbeiro e do cliente de demonstração. Vazia = senha aleatória, sem login. |
| `trim-web` | `VITE_API_URL` | **Painel.** URL real do `trim-api` terminando em `/api`: `https://trim-api-ujwo.onrender.com/api`. Lida no build: depois de mudar, faça um novo deploy do `trim-web`. |

As variáveis marcadas como **Painel** têm `sync: false` no `render.yaml`: não há valor no
repositório, e o Render pede o valor ao criar o Blueprint. Nenhum segredo vai para o Git.

#### Conferir o commit no ar

O `/health` devolve o commit que está rodando, lido de `RENDER_GIT_COMMIT`:

```bash
curl https://trim-api-ujwo.onrender.com/health
# {"status":"healthy","app":"Trim","version":"0.1.0","commit":"<sha>"}

git fetch origin && git rev-parse origin/main   # deve ser o mesmo <sha>
```

Fora do Render, `commit` é `"local"`.

#### Popular o banco (seed)

1. Em `trim-api` → **Environment**, defina `SEED_SECRET` com um valor longo e aleatório
   (por exemplo, `python -c "import secrets; print(secrets.token_urlsafe(32))"`), além de
   `SEED_ADMIN_PASSWORD` e `SEED_DEMO_PASSWORD`. Salve e espere o novo deploy terminar.
2. Rode o seed, enviando o segredo no cabeçalho `X-Seed-Secret` (nunca na URL). No exemplo,
   `$SEED_SECRET` é uma variável do seu terminal com o mesmo valor:

   ```bash
   curl -X POST https://trim-api-ujwo.onrender.com/api/dev/seed \
     -H "X-Seed-Secret: $SEED_SECRET"
   ```

   Rodar de novo não duplica dados. Para atualizar para hoje as datas dos dados de demonstração
   (agendamentos, transações, despesas, fila), use `POST /api/dev/update_dates` com o mesmo cabeçalho.
3. **Remova o `SEED_SECRET`** do `trim-api` em **Environment** e salve. Depois do novo deploy,
   as rotas `/api/dev/*` voltam a responder 404. `SEED_ADMIN_PASSWORD` e `SEED_DEMO_PASSWORD`
   podem ser removidas também: o seed não altera usuários que já existem.

#### Observações

- O plano gratuito do Render hiberna a API sem acesso; a primeira requisição depois disso demora.
- O PostgreSQL gratuito do Render expira depois de um período; é preciso recriá-lo (e rodar o
  seed de novo) ou mudar de plano.

A AP1 não tinha uma seção de deploy. O bloco abaixo reúne, sem alterações, as duas linhas do
README original que tratam da hospedagem (a URL pública e a linha de deploy da stack).

---

#### 📦 AP1 — dupla original (mantido sem alterações)

> > **URL Pública:** [https://dsai-ap1-trim-frontend-production.up.railway.app](https://dsai-ap1-trim-frontend-production.up.railway.app)
> 
> - **Hospedagem / Deploy:** Vercel (frontend) + Render / Railway (backend + banco)

## 📊 Contagem de Linhas de Código (`cloc`)

#### 🆕 AP2 — fork

Contagem do código novo em relação à linha de base (commit 95c79b5). Será preenchida em breve.

```text
```

---

#### 📦 AP1 — dupla original (mantido sem alterações)

> > Meta obrigatória: **Mínimo de 100.000 linhas** (excluindo dependências, builds, documentação e dados).
> 
> Comando oficial de medição:
> ```bash
> cloc . --vcs=git \
>   --exclude-dir=node_modules,vendor,dist,build,prompts \
>   --exclude-lang=Markdown,JSON,YAML,CSV,Text,SVG \
>   --not-match-f='(lock|\.min\.)'
> ```
> 
> ### Saída do `cloc`
> ```text
> github.com/AlDanial/cloc v 1.98  T=4.31 s (26.9 files/s, 86411.7 lines/s)
> -------------------------------------------------------------------------------
> Language                     files          blank        comment           code
> -------------------------------------------------------------------------------
> Python                          89          66229         104890         199251
> CSS                              9            173              5           1114
> TypeScript                      15             78              4            721
> INI                              1             10              0             32
> Mako                             1              8              0             18
> HTML                             1              0              1             16
> -------------------------------------------------------------------------------
> SUM:                           116          66498         104900         201152
> -------------------------------------------------------------------------------
> ```
> *Proporção:* Aproximadamente 5% código de aplicação (Backend + Frontend) e 95% código de testes e fixtures gerados, garantindo a meta folgadamente com +200 mil linhas!

## 📁 Estrutura do Repositório

#### 🆕 AP2 — fork

```text
.
├── AGENTS.md                  # Regras da AP2 (fluxo, specs, trailers, sessões, métricas)
├── CLAUDE.md                  # Aponta o Claude Code para o AGENTS.md
├── CONTRIBUTING.md
├── README.md                  # Este arquivo
├── render.yaml                # Blueprint do Render: trim-db, trim-api e trim-web
├── requirements.txt           # Dependências do backend
├── pytest.ini                 # pythonpath = . (para importar src.backend nos testes)
├── Procfile                   # Herdado da AP1
├── alembic.ini
├── alembic/                   # Configuração do Alembic; versions/ vazia (sem migrações, ver #6)
├── .env.example               # Modelo do .env do backend
├── .github/
│   └── workflows/
│       └── ci.yml             # CI: backend (pytest + PostgreSQL) e frontend (testes + build)
├── SPEC/                      # Specs datadas
│   ├── 2026-09-29-*.md        # AP1, somente leitura
│   └── 2026-11-*.md           # AP2: processo, deploy, seed, fuso, cancelamento
├── src/
│   ├── backend/
│   │   ├── main.py            # App FastAPI, CORS, /health, criação das tabelas
│   │   ├── config.py          # Configuração lida do .env (pydantic-settings)
│   │   ├── database.py        # Engine e sessão assíncronas (SQLAlchemy)
│   │   └── modules/           # Um pacote por módulo: models, schemas, service, router
│   │       └── dev_router.py  # Seed protegido por SEED_SECRET
│   └── frontend/              # React + Vite (TypeScript)
│       ├── .env.example       # VITE_API_URL
│       ├── package.json
│       └── src/
│           ├── pages/         # Páginas (Booking, Dashboard, Admin*, ...)
│           └── utils/         # Ex.: shopDate.ts (datas no fuso da barbearia) + teste
├── tests/                     # pytest (testes da AP1 e testes novos da AP2)
└── prompts/
    └── sessoes/               # Transcrições das sessões com agentes
        └── CUSTOS.md          # Tokens de cada sessão
```

#### Fluxo de desenvolvimento da AP2

```text
  ┌──────────┐    ┌──────────────┐    ┌─────────────────────┐
  │  Issue   │───▶│ Spec (SPEC/) │───▶│ Branch              │
  │ evidência│    │ commit antes │    │ feat/ fix/ docs/ ...│
  └──────────┘    │  do código   │    └──────────┬──────────┘
                  └──────────────┘               │
                                                 ▼
  ┌──────────────┐    ┌──────────────┐    ┌─────────────────────┐
  │ CI (GitHub   │◀───│ Pull Request │◀───│ Commits pequenos    │
  │ Actions)     │    │ Closes #N    │    │ + testes            │
  │ verde        │    │              │    │ Agent: / Spec:      │
  └──────┬───────┘    └──────────────┘    └─────────────────────┘
         │
         ▼
  ┌──────────────┐    ┌──────────────┐    ┌─────────────────────┐
  │ Revisão da   │───▶│ Merge na     │───▶│ Deploy automático   │
  │ dupla        │    │ main         │    │ no Render           │
  │ (aprovação)  │    │              │    │ (trim-api, trim-web)│
  └──────────────┘    └──────────────┘    └─────────────────────┘
```

Cada sessão com agente que gera commit é registrada no mesmo dia em `prompts/sessoes/`, com o
custo em `CUSTOS.md`. Detalhes em [`AGENTS.md`](AGENTS.md).

---

#### 📦 AP1 — dupla original (mantido sem alterações)

> Consulte o arquivo [AGENTS.md](file:///c:/Users/Gusta/Desktop/REPO/dsai-ap1-trim/AGENTS.md) para detalhes completos sobre o fluxo de desenvolvimento SDD, convenções de commits com trailers e registro de prompts.

## 🔀 O que mudou no fork

#### 🆕 AP2 — fork

Pull Requests mergeados na `main`:

| PR | Data | O quê | Issues resolvidas |
| :--- | :--- | :--- | :--- |
| [#1](https://github.com/henriquelm-io/dsai-ap2-trim/pull/1) | 16/11/2026 | Organização da AP2: spec de processo, `AGENTS.md`, CI e sessões | — |
| [#17](https://github.com/henriquelm-io/dsai-ap2-trim/pull/17) | 17/11/2026 | Protege e corrige a rota de seed | [#5](https://github.com/henriquelm-io/dsai-ap2-trim/issues/5), [#10](https://github.com/henriquelm-io/dsai-ap2-trim/issues/10) |
| [#18](https://github.com/henriquelm-io/dsai-ap2-trim/pull/18) | 17/11/2026 | Specs da AP1 passam a ser somente leitura | — |
| [#19](https://github.com/henriquelm-io/dsai-ap2-trim/pull/19) | 17/11/2026 | Deploy no Render (backend, frontend e PostgreSQL) | [#4](https://github.com/henriquelm-io/dsai-ap2-trim/issues/4) |
| [#20](https://github.com/henriquelm-io/dsai-ap2-trim/pull/20) | 19/11/2026 | Agendamento no fuso da barbearia, com seletor de data e sem horários passados | [#12](https://github.com/henriquelm-io/dsai-ap2-trim/issues/12) |
| [#25](https://github.com/henriquelm-io/dsai-ap2-trim/pull/25) | 19/11/2026 | Cliente só cancela o próprio agendamento, ativo e futuro | [#24](https://github.com/henriquelm-io/dsai-ap2-trim/issues/24) |

O backlog completo está nas [issues](https://github.com/henriquelm-io/dsai-ap2-trim/issues).
