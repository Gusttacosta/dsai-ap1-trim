# Trim ✂️ — Gestão Completa para Barbearias

> **AP1 — Desenvolvimento de Software Apoiado por IA (2026.4 — UFPA)**

> **URL Pública:** [https://dsai-ap1-trim-frontend-production.up.railway.app](https://dsai-ap1-trim-frontend-production.up.railway.app)

Plataforma web de gestão para barbearias: agendamento online, controle de time, catálogo de serviços, venda de produtos, assinaturas/planos recorrentes, financeiro e CRM de clientes — tudo em um só lugar.

---

## 👥 Integrantes da Dupla

- **Integrante 1:** [Nome Completo](https://github.com/Gusttacosta) (GitHub: `@Gusttacosta`)
- **Integrante 2:** [Nome Completo](https://github.com/usuario2) (GitHub: `@usuario2`)

---

## 🛠️ Stack Tecnológica

- **Frontend:** React + TypeScript + Vite
- **Estilização:** Vanilla CSS (CSS Modules)
- **Backend / API:** Python + FastAPI
- **ORM / Migrations:** SQLAlchemy + Alembic
- **Banco de Dados:** PostgreSQL
- **Validação:** Pydantic
- **Autenticação:** JWT (python-jose + passlib)
- **Hospedagem / Deploy:** Render (banco, API e frontend; ver [Deploy no Render](#-deploy-no-render))

---

## 🤖 Ferramentas e Modelos de IA Utilizados

| Ferramenta | Modelo | Utilização Principal |
| :--- | :--- | :--- |
| Antigravity IDE | Gemini 2.5 Pro / Gemini 3.8 Flash / Claude Opus 4.6 | Planejamento, specs, geração de código e testes |

---

## 🚀 Como Rodar o Projeto Localmente

### Pré-requisitos
- Python >= 3.11
- Node.js >= 20 (para o frontend)
- PostgreSQL (ou Docker)

### Backend
```bash
# Clone o repositório
git clone https://github.com/Gusttacosta/dsai-ap1-trim.git
cd dsai-ap1-trim

# Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais do PostgreSQL

# Execute as migrations
alembic upgrade head

# Execute o servidor de desenvolvimento
uvicorn src.backend.main:app --reload
```

### Frontend
```bash
cd src/frontend
npm install
cp .env.example .env   # VITE_API_URL=http://localhost:8000/api
npm run dev
```

Em `npm run dev`, sem `VITE_API_URL`, o frontend usa `http://localhost:8000/api`. Em
`npm run build`, a variável é obrigatória e o build falha sem ela.

---

## ☁️ Deploy no Render

O deploy é descrito no Blueprint [`render.yaml`](render.yaml)
(spec: [`SPEC/2026-11-16-deploy-render.md`](SPEC/2026-11-16-deploy-render.md)). No painel do
Render: **New → Blueprint**, escolha este repositório e preencha as variáveis pedidas.

### As três peças

| Serviço | Tipo | O que faz |
| :--- | :--- | :--- |
| `trim-db` | PostgreSQL (gratuito) | Banco de produção. As tabelas são criadas na inicialização da API. |
| `trim-api` | Web Service Python 3.12 | `pip install -r requirements.txt`, depois `uvicorn src.backend.main:app --host 0.0.0.0 --port $PORT`. Health check em `/health`. Deploy automático a cada push na `main`. |
| `trim-web` | Static Site | Em `src/frontend`: `npm ci && npm run build`, publica `dist`. Rewrite de `/*` para `/index.html` (rotas do React Router). Deploy automático a cada push na `main`. |

### Variáveis

| Serviço | Variável | Valor |
| :--- | :--- | :--- |
| `trim-api` | `PYTHON_VERSION` | `3.12` (no `render.yaml`) |
| `trim-api` | `DATABASE_URL` | Vem do `trim-db` (`postgresql://...`); o backend converte para `asyncpg` e `psycopg2`. |
| `trim-api` | `SECRET_KEY` | Gerada pelo Render. |
| `trim-api` | `APP_ENV` / `DEBUG` | `production` / `false` (no `render.yaml`) |
| `trim-api` | `CORS_ORIGINS` | **Painel.** URL do `trim-web`, por exemplo `https://trim-web.onrender.com`. |
| `trim-api` | `SEED_SECRET` | **Painel.** Só durante o seed (ver abaixo). Vazia = rotas de seed respondem 404. |
| `trim-api` | `SEED_ADMIN_PASSWORD` | **Painel.** Senha do admin de demonstração. Vazia = admin não é criado. |
| `trim-api` | `SEED_DEMO_PASSWORD` | **Painel.** Senha do barbeiro e do cliente de demonstração. Vazia = senha aleatória, sem login. |
| `trim-web` | `VITE_API_URL` | **Painel.** URL do `trim-api` com `/api`, por exemplo `https://trim-api.onrender.com/api`. Lida no build: depois de mudar, faça um novo deploy do `trim-web`. |

As variáveis marcadas como **Painel** têm `sync: false` no `render.yaml`: não há valor no
repositório, e o Render pede o valor ao criar o Blueprint. Nenhum segredo vai para o Git.

### Conferir o commit no ar

O `/health` devolve o commit que está rodando, lido de `RENDER_GIT_COMMIT`:

```bash
curl https://trim-api.onrender.com/health
# {"status":"healthy","app":"Trim","version":"0.1.0","commit":"<sha>"}

git fetch origin && git rev-parse origin/main   # deve ser o mesmo <sha>
```

Fora do Render, `commit` é `"local"`.

### Popular o banco (seed)

1. Em `trim-api` → **Environment**, defina `SEED_SECRET` com um valor longo e aleatório
   (por exemplo, `python -c "import secrets; print(secrets.token_urlsafe(32))"`), além de
   `SEED_ADMIN_PASSWORD` e `SEED_DEMO_PASSWORD`. Salve e espere o novo deploy terminar.
2. Rode o seed, enviando o segredo no cabeçalho `X-Seed-Secret` (nunca na URL). No exemplo,
   `$SEED_SECRET` é uma variável do seu terminal com o mesmo valor:

   ```bash
   curl -X POST https://trim-api.onrender.com/api/dev/seed \
     -H "X-Seed-Secret: $SEED_SECRET"
   ```

   Rodar de novo não duplica dados. Para atualizar para hoje as datas dos dados de demonstração
   (agendamentos, transações, despesas, fila), use `POST /api/dev/update_dates` com o mesmo cabeçalho.
3. **Remova o `SEED_SECRET`** do `trim-api` em **Environment** e salve. Depois do novo deploy,
   as rotas `/api/dev/*` voltam a responder 404. `SEED_ADMIN_PASSWORD` e `SEED_DEMO_PASSWORD`
   podem ser removidas também: o seed não altera usuários que já existem.

### Observações

- O plano gratuito do Render hiberna a API sem acesso; a primeira requisição depois disso demora.
- O PostgreSQL gratuito do Render expira depois de um período; é preciso recriá-lo (e rodar o
  seed de novo) ou mudar de plano.

---

## 📊 Contagem de Linhas de Código (`cloc`)

> Meta obrigatória: **Mínimo de 100.000 linhas** (excluindo dependências, builds, documentação e dados).

Comando oficial de medição:
```bash
cloc . --vcs=git \
  --exclude-dir=node_modules,vendor,dist,build,prompts \
  --exclude-lang=Markdown,JSON,YAML,CSV,Text,SVG \
  --not-match-f='(lock|\.min\.)'
```

### Saída do `cloc`
```text
github.com/AlDanial/cloc v 1.98  T=4.31 s (26.9 files/s, 86411.7 lines/s)
-------------------------------------------------------------------------------
Language                     files          blank        comment           code
-------------------------------------------------------------------------------
Python                          89          66229         104890         199251
CSS                              9            173              5           1114
TypeScript                      15             78              4            721
INI                              1             10              0             32
Mako                             1              8              0             18
HTML                             1              0              1             16
-------------------------------------------------------------------------------
SUM:                           116          66498         104900         201152
-------------------------------------------------------------------------------
```
*Proporção:* Aproximadamente 5% código de aplicação (Backend + Frontend) e 95% código de testes e fixtures gerados, garantindo a meta folgadamente com +200 mil linhas!

---

## 📁 Estrutura do Repositório

Consulte o arquivo [AGENTS.md](file:///c:/Users/Gusta/Desktop/REPO/dsai-ap1-trim/AGENTS.md) para detalhes completos sobre o fluxo de desenvolvimento SDD, convenções de commits com trailers e registro de prompts.
