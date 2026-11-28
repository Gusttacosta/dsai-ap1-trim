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
- **ORM / Migrações:** SQLAlchemy 2 assíncrono (`asyncpg`; `psycopg2` para a URL síncrona) e Alembic, com as migrações em `alembic/versions/` (`0001` a `0004`) aplicadas por `scripts/migrate.py` (#6, PR #94)
- **Banco de Dados:** PostgreSQL (16 na CI; o Render fornece o de produção)
- **Validação e configuração:** Pydantic 2 + pydantic-settings (variáveis do `.env`)
- **Autenticação:** JWT com PyJWT (no lugar do python-jose desde o PR #43) + passlib/bcrypt, com refresh token e logout que revoga a sessão
- **Fuso horário:** `zoneinfo` + `tzdata`, com o fuso da barbearia em `SHOP_TIMEZONE` ([`SPEC/2026-11-18-agendamento-fuso-horario.md`](SPEC/2026-11-18-agendamento-fuso-horario.md))
- **Testes do backend:** pytest + pytest-asyncio + httpx; os testes de banco usam um PostgreSQL em `TEST_DATABASE_URL`
- **Qualidade:** Ruff
- **CI:** GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)), em todo push e PR para a `main`, com seis jobs:
  - `backend`: Python 3.12 e PostgreSQL 16 de serviço. Faz o import da aplicação, roda `scripts/custos.py --check` e o `pytest` com cobertura, e o `diff-cover` exige pelo menos 70% de cobertura do código novo;
  - `frontend`: Node 22. Confere que não há URL do Railway em `src/` e roda `npm ci`, `tsc` e `npm test`. O build sem `VITE_API_URL` precisa falhar, e com ela precisa passar;
  - `gitleaks`: procura segredos no histórico inteiro, com as exceções restritas de [`.gitleaks.toml`](.gitleaks.toml);
  - `trailers`: todo commit do PR precisa ter `Agent:` e `Spec:`;
  - `dependencias`: `npm audit` e `pip-audit`, que falham em alertas high e críticos;
  - `duplicacao`: `jscpd` 5.4.3 em `src/`.
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

Os modelos são os que aparecem na coluna "Modelos" de [`prompts/sessoes/CUSTOS.md`](prompts/sessoes/CUSTOS.md), que registra os tokens de cada sessão. O `claude-haiku-5-5` foi usado por um subagente da sessão de 10/11, cujo arquivo não está no repositório, e por isso só aparece na nota dessa sessão em [`prompts/sessoes/NOTAS.md`](prompts/sessoes/NOTAS.md). As transcrições ficam em [`prompts/sessoes/`](prompts/sessoes/).

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

**Migrações (#6).** O esquema vem das migrações do Alembic em `alembic/versions/`. Rode
`python scripts/migrate.py` antes de subir o backend. Num banco vazio, ele cria tudo. Num banco
antigo, criado pelo `create_all`, ele registra a revisão inicial (`stamp 0001`) e aplica só o que vem
depois. Em desenvolvimento (`APP_ENV=development`), o backend ainda cria as tabelas que faltarem ao
iniciar. Em produção, só as migrações mexem no esquema. Para conferir:
`curl http://<ip-da-vm>:8001/health`.

Uma mudança num modelo precisa de uma migração nova:
`alembic revision --autogenerate -m "o que mudou"`. Depois, revise o arquivo gerado.
O teste `tests/test_migracoes.py` falha se os modelos e as migrações divergirem.

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

O projeto roda direto no **Windows 10** (Home, versão 10.0.19045), com backend, frontend e
PostgreSQL na mesma máquina, acessados por `localhost`. Os comandos abaixo são para o
**PowerShell 5.1**, o padrão do Windows 10. No Git Bash valem os comandos da seção do Henrique,
trocando `source venv/bin/activate` por `source venv/Scripts/activate`. Troque as senhas de
exemplo por senhas suas.

#### Pré-requisitos

Versões usadas neste ambiente:

| Ferramenta | Versão | Observação |
| :--- | :--- | :--- |
| Python | 3.12.10 | a CI usa o 3.12 |
| Node.js / npm | 26.13 / 11.20 | qualquer Node 20 ou mais novo serve; a CI usa o 22 |
| PostgreSQL | 17 (instalador oficial) | roda como o serviço `postgresql-x64-17`, que inicia com o Windows |
| Git | 2.56 (Git for Windows) | traz o Git Bash |

O instalador do PostgreSQL não põe o `psql` no `PATH`. Nos comandos abaixo, ele é chamado pelo
caminho completo. Para conferir se o serviço está no ar: `Get-Service postgresql-x64-17`.

O `cloc` não está instalado neste ambiente. A contagem de linhas está na seção
[Contagem de Linhas](#-contagem-de-linhas-de-código-cloc).

#### 1. Código e ambiente Python

```powershell
git clone https://github.com/henriquelm-io/dsai-ap2-trim.git
cd dsai-ap2-trim

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Se o PowerShell recusar o `Activate.ps1` por causa da política de execução, libere scripts locais
só para o seu usuário com `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Outra opção é não
ativar o venv e chamar o Python dele direto: `.\venv\Scripts\python.exe -m pip ...`,
`.\venv\Scripts\python.exe -m uvicorn ...` e `.\venv\Scripts\python.exe -m pytest ...`.

#### 2. PostgreSQL local, com usuário e banco próprios

Os comandos pedem a senha do usuário `postgres`, definida na instalação:

```powershell
$psql = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
& $psql -U postgres -c "CREATE USER trim WITH PASSWORD 'senha-de-exemplo';"
& $psql -U postgres -c "CREATE DATABASE trim_db OWNER trim;"
# Opcional: banco descartável para os testes que precisam de PostgreSQL
& $psql -U postgres -c "CREATE DATABASE trim_test OWNER trim;"
```

#### 3. `.env`

```powershell
Copy-Item .env.example .env
```

No `.env`, ajuste pelo menos:

```dotenv
DATABASE_URL=postgresql+asyncpg://trim:senha-de-exemplo@localhost:5432/trim_db
DATABASE_URL_SYNC=postgresql+psycopg2://trim:senha-de-exemplo@localhost:5432/trim_db
SECRET_KEY=troque-por-um-valor-longo-e-aleatorio
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Como tudo roda na mesma máquina, o CORS só precisa liberar o `localhost:5173` do Vite. O `.env`
está no `.gitignore` e nunca vai para o Git.

#### 4. Backend

```powershell
.\venv\Scripts\Activate.ps1
python -m uvicorn src.backend.main:app --port 8000
```

O backend sobe sem nenhuma variável extra desde a correção da #2 (PR #28). Num commit anterior a
ela, a inicialização falha com `UnicodeEncodeError` (os `print` com emoji não cabem no cp1252 do
console). Nesse caso, rode `$env:PYTHONUTF8=1` antes do `uvicorn`.

Como na seção do Henrique, rode `python scripts/migrate.py` antes do `uvicorn`, para aplicar as
migrações do Alembic (ver #6). Para conferir, use `curl.exe http://localhost:8000/health`. No PowerShell 5.1,
`curl` sem `.exe` é um apelido do `Invoke-WebRequest` e não aceita as mesmas opções.

#### 5. Frontend

Em outro terminal:

```powershell
cd src\frontend
npm install
$env:VITE_API_URL="http://localhost:8000/api"; npm run dev
```

Abra `http://localhost:5173`. No `npm run dev`, sem `VITE_API_URL`, o padrão já é
`http://localhost:8000/api`. Definir a variável deixa claro para qual backend o frontend aponta.
O `npm run build` falha sem ela.

**A porta é fixa (ver #11).** O `vite.config.ts` usa `port: 5173` e `strictPort: true`, então não é
preciso passar `--port` nem `--strictPort`. O motivo: no Windows, se o `npm run dev` for encerrado sem Ctrl+C no
próprio terminal (pelo Gerenciador de Tarefas ou fechando a ferramenta que o iniciou), o processo
`node ...vite.js` continua escutando a porta 5173. Sem a porta fixa, o Vite novo subiria em outra
porta sem avisar, e o navegador em `localhost:5173` continua falando com o Vite antigo, que pode
estar apontando para outro backend. Com ela, aparece o erro de porta em uso. Para
achar e encerrar o processo órfão:

```powershell
netstat -ano | findstr :5173
# Confira se o PID da última coluna é mesmo o Vite antes de encerrá-lo
Get-CimInstance Win32_Process -Filter "ProcessId=<pid>" | Select-Object CommandLine
Stop-Process -Id <pid>
```

Para conferir para qual backend o Vite no ar aponta, abra `http://localhost:5173/src/api.ts`: o
`VITE_API_URL` servido precisa ser `http://localhost:8000/api`.

#### 6. Dados de demonstração (seed)

O mesmo da seção do Henrique: defina `SEED_SECRET`, `SEED_ADMIN_PASSWORD` e `SEED_DEMO_PASSWORD` no
`.env`, reinicie o backend e rode, com o valor de `SEED_SECRET` no cabeçalho:

```powershell
curl.exe -X POST http://localhost:8000/api/dev/seed -H "X-Seed-Secret: <valor-de-SEED_SECRET>"
```

#### 7. Testes

```powershell
# Backend (sem TEST_DATABASE_URL, os testes de banco são pulados)
$env:TEST_DATABASE_URL="postgresql+asyncpg://trim:senha-de-exemplo@localhost:5432/trim_test"
python -m pytest -q

# Frontend
cd src\frontend; npm test
```

A suíte do backend tem 1.226 testes (`pytest --collect-only -q`, em 28/11/2026). Os cerca de 13 mil
testes gerados da AP1 foram trocados por testes de integração por módulo (#3).

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
| `trim-db` | PostgreSQL (gratuito) | Banco de produção. O esquema vem das migrações do Alembic, aplicadas a cada deploy da API. |
| `trim-api` | Web Service Python 3.12 | `pip install -r requirements.txt`, depois `python scripts/migrate.py && uvicorn src.backend.main:app --host 0.0.0.0 --port $PORT`. O `migrate.py` aplica as migrações pendentes; num banco antigo, criado pelo `create_all`, ele faz antes o `stamp 0001`. Health check em `/health`. Deploy automático a cada push na `main`. |
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

## 📈 Métricas da AP2

Medidas em 28/11/2026 sobre a `origin/main` em `44a381f` (merge do #116), contra a linha de base
da AP1, `95c79b5`. A documentação para quem vai manter o projeto está em
[`docs/PASSAGEM.md`](docs/PASSAGEM.md).

### Linhas novas (`cloc`)

Comando, rodado na raiz do repositório:

```bash
cloc --git --diff 95c79b5 origin/main \
  --exclude-dir=node_modules,dist,build,vendor,prompts \
  --not-match-f='(lock|\.min\.|CUSTOS\.md|NOTAS\.md)'
```

No Windows, o `--git` do `cloc` falha, por causa do `tar` do Git Bash e da falta de `unzip`. Nesse
caso, exporte as duas árvores com `git archive 95c79b5 | tar -x -C ap1` e
`git archive origin/main | tar -x -C main`, e rode `cloc --diff ap1 main` com os mesmos filtros.
A medição abaixo foi feita assim, com o `cloc` 2.12.

`prompts/` só contém `prompts/sessoes/`, e o único lockfile versionado é
`src/frontend/package-lock.json`.

| Linguagem | Arquivos adicionados | Linhas de código adicionadas | Linhas de código modificadas |
| :--- | ---: | ---: | ---: |
| TypeScript | 165 | 11.786 | 183 |
| Python | 59 | 11.258 | 354 |
| Markdown | 61 | 4.473 | 131 |
| CSS | 2 | 353 | 0 |
| YAML | 2 | 259 | 0 |
| TOML | 1 | 24 | 0 |
| JSON | 0 | 6 | 3 |
| Text | 0 | 4 | 6 |
| INI | 1 | 2 | 0 |
| **Total** | **291** | **28.165** | **677** |

O Markdown é quase todo specs (`SPEC/`) e documentação. Sem Markdown, JSON, YAML e Text (as
linguagens que o comando de [`AGENTS.md`](AGENTS.md) §10 exclui), as linhas de código adicionadas
são 23.423. As 195.278 linhas de Python removidas são, na maior parte, os 13
`tests/test_<módulo>.py` gerados pela AP1 (ver [`docs/PASSAGEM.md`](docs/PASSAGEM.md#decisões)).

<details>
<summary>Saída completa do <code>cloc</code></summary>

```text
github.com/AlDanial/cloc v 2.12  T=6.18 s (70.4 files/s, 66609.7 lines/s)
-------------------------------------------------------------------------------
Language                     files          blank        comment           code
-------------------------------------------------------------------------------
Python
 same                           25            144            699           3958
 modified                       48              0             76            354
 added                          59           4215            957          11258
 removed                        17          65071         104143         195278
TypeScript
 same                            3              6              5            828
 modified                       15              0              0            183
 added                         165           2341            699          11786
 removed                         0              1              4             55
Markdown
 same                           15            346              0           1133
 modified                        2              0              0            131
 added                          61           1024              0           4473
 removed                         0              0              0             54
CSS
 same                            7            146              4           1126
 modified                        2              0              1              0
 added                           2             59              7            353
 removed                         0              0              0              0
YAML
 same                            0              0              0              0
 modified                        0              0              0              0
 added                           2             34             27            259
 removed                         0              0              0              0
JSON
 same                            1              2              0             46
 modified                        1              0              0              3
 added                           0              0              0              6
 removed                         0              0              0              0
INI
 same                            1             10              0             32
 modified                        0              0              0              0
 added                           1              0              0              2
 removed                         0              0              0              0
Text
 same                            0              0              0             23
 modified                        1              0              0              6
 added                           0              0              0              4
 removed                         0              0              0              0
SVG
 same                            4              0              0             27
 modified                        0              0              0              0
 added                           0              0              0              0
 removed                         0              0              0              0
TOML
 same                            0              0              0              0
 modified                        0              0              0              0
 added                           1              5              9             24
 removed                         0              0              0              0
Mako
 same                            1              8              0             18
 modified                        0              0              0              0
 added                           0              0              0              0
 removed                         0              0              0              0
HTML
 same                            1              0              1             16
 modified                        0              0              0              0
 added                           0              0              0              0
 removed                         0              0              0              0
-------------------------------------------------------------------------------
SUM:
 same                           58            662            709           7207
 modified                       69              0             77            677
 added                         291           7678           1699          28165
 removed                        17          65072         104147         195387
-------------------------------------------------------------------------------
```

</details>

### Duplicação (`jscpd`)

Mesmo comando e mesma versão do job `duplicacao` da CI
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)):

```bash
npx --yes jscpd@5.4.3 src \
  --ignore "**/node_modules/**,**/dist/**,**/__pycache__/**,**/package-lock.json" \
  --reporters console,markdown --output jscpd-report --exit-code 0
```

Resultado: **2,25% de linhas duplicadas** (596 de 26.544 linhas, 60 clones em 257 arquivos;
2,24% dos tokens). Por formato: Python 3,43%, TSX 1,79%, TypeScript 1,67%, CSS 0,93%.

### Commits e PRs

Desde `95c79b5` até `44a381f`:

- **401 commits** (`git rev-list --count 95c79b5..origin/main`): 313 sem contar merges e 88 merges.
- **67 PRs mergeados** (`gh pr list --state merged`), do #1 ao #116.

### Demais critérios do [`AGENTS.md`](AGENTS.md) §3

| Critério | Medição em `44a381f` | Mínimo |
| :--- | :--- | :--- |
| Trailers `Agent:` e `Spec:` | 313 de 313 commits sem merge (100%) | 80% |
| Autoria (commits sem merge, `git shortlog -sn --no-merges 95c79b5..origin/main`) | Severino 201 (64,2%), Henrique 112 (35,8%) | 30% cada |
| Frequência | Commits em 10 dias, de 10/11 a 26/11. Mediana de 123 linhas por commit (adicionadas + removidas no `git show --numstat`) | 2 dias/semana; mediana < 400 |
| Cobertura do código novo | O job `backend` da CI falha abaixo de 70% (`diff-cover`) | 70% |
| Segredos | `gitleaks git .`: nenhum achado nos 402 commits do histórico | zero |
| CI | Verde no último commit da `main` | verde |
| Produção | `https://trim-api-ujwo.onrender.com/health` devolve o commit `44a381f`, o mesmo da `main`; `https://trim-web.onrender.com` responde 200 | no ar |
| Issues abertas | Nenhuma, além da #117, que esta atualização do README fecha | — |

---

## 📊 Contagem de Linhas de Código (`cloc`)

#### 🆕 AP2 — fork

Medição de 19/11/2026, mantida como registro. A medição atual está em
[Métricas da AP2](#-métricas-da-ap2).

Comando executado em 19/11/2026, comparando a linha de base da AP1 (95c79b5) com o estado atual do fork. Código novo: 734 linhas adicionadas e 94 modificadas.

```github.com/AlDanial/cloc v 2.04  T=0.18 s (96.9 files/s, 11681.6 lines/s)
-------------------------------------------------------------------------------
Language                     files          blank        comment           code
-------------------------------------------------------------------------------
Python
 same                            0              0             94            566
 modified                        6              0             13             67
 added                           5            275             67            635
 removed                         0              0              2             17
TypeScript
 same                            0              0              1            163
 modified                        3              0              0             27
 added                           2             14              8             97
 removed                         0              0              0              1
INI
 same                            0              0              0              0
 modified                        0              0              0              0
 added                           1              0              0              2
 removed                         0              0              0              0
-------------------------------------------------------------------------------
SUM:
 same                            0              0             95            729
 modified                        9              0             13             94
 added                           8            289             75            734
 removed                         0              0              2             18
-------------------------------------------------------------------------------
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
├── alembic/                   # Migrações do Alembic (scripts/migrate.py as aplica, ver #6)
├── .env.example               # Modelo do .env do backend
├── .github/
│   └── workflows/
│       └── ci.yml             # CI: backend (pytest + PostgreSQL) e frontend (testes + build)
├── SPEC/                      # Specs datadas
│   ├── 2026-09-29-*.md        # AP1, somente leitura
│   └── 2026-11-*.md           # AP2: processo, deploy, seed, fuso, cancelamento
├── scripts/
│   └── custos.py              # Gera prompts/sessoes/CUSTOS.md e NOTAS.md (--check na CI)
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
        ├── CUSTOS.md          # Tokens de cada sessão (gerado por scripts/custos.py)
        └── NOTAS.md           # Notas das sessões (gerado por scripts/custos.py)
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
custo em `CUSTOS.md`, gerado por `python scripts/custos.py`. Detalhes em [`AGENTS.md`](AGENTS.md).

---

#### 📦 AP1 — dupla original (mantido sem alterações)

> Consulte o arquivo [AGENTS.md](file:///c:/Users/Gusta/Desktop/REPO/dsai-ap1-trim/AGENTS.md) para detalhes completos sobre o fluxo de desenvolvimento SDD, convenções de commits com trailers e registro de prompts.

## 🔀 O que mudou no fork

#### 🆕 AP2 — fork

Os 67 PRs mergeados na `main` desde a linha de base da AP1 (`95c79b5`) até `44a381f` (27/11/2026),
resumidos por tema. Cada PR aparece uma vez, no tema principal dele. A lista PR a PR, com o que
cada um faz, está em [`docs/PASSAGEM.md`](docs/PASSAGEM.md#a-o-que-mudou).

| Tema | PRs | O que mudou | Issues resolvidas |
| :--- | :--- | :--- | :--- |
| Segurança | #17, #25, #29, #31, #43, #78, #90 | A rota de seed fica protegida por `SEED_SECRET`. O cliente só cancela ou altera o próprio agendamento. Os tokens saem do log em produção. O python-jose foi trocado pelo PyJWT. A galeria ganhou permissões, e as dependências do backend não têm alerta high | #5, #10, #24, #26, #30, #42, #71, #77 |
| Agendamento | #20, #48, #52, #79, #83 | Os horários seguem o fuso da barbearia, sem horário passado, dentro do expediente e fora do almoço. O visitante é validado, a duração fica entre 1 e 1440 minutos, e há um usuário Visitante único | #12, #23, #22, #57, #21, #69 |
| Autenticação e usuários | #45, #46, #91 | Refresh token e logout que revoga a sessão. Perfil (`PUT /me`) e troca de senha. Reenvio da verificação, administração de usuários, limite de login e token de redefinição único | #35 |
| Regras de negócio do backend | #47, #53, #81, #82, #84, #85, #86, #87, #88, #89, #93 | Validações e correção de erros 500 em serviços, barbeiros, despesas, fidelidade, produtos, financeiro, notificações, Trim Club e relatórios. Os pagamentos passam a gerar pontos de fidelidade. Os módulos vazios foram removidos | #37, #39, #9, #65, #73, #61, #59, #75, #64, #67, #13 |
| Banco de dados | #94 | Migrações do Alembic (`scripts/migrate.py`), com stamp do banco de produção, e plano ilimitado no Trim Club | #6, #16 |
| Painel do admin | #51, #100, #103, #105, #107, #109, #111, #113 | Abas de serviços, usuários (com senha temporária), barbeiros, despesas, galeria, Trim Club, fidelidade e estoque, todas ligadas à API | #49, #99, #102, #104, #106, #108, #110, #112 |
| Conta do cliente | #50, #98 | Meus agendamentos, com cancelamento. O formulário de perfil não apaga mais o que foi digitado | #97 |
| CI e testes | #34, #36, #38, #40, #44, #56, #58, #60, #62, #63, #66, #68, #70, #72, #74, #76, #95 | A CI ganhou `gitleaks`, trailers, `npm audit`, `pip-audit`, `jscpd`, `tsc` e `diff-cover`. Os testes gerados da AP1 foram trocados por testes de integração, módulo por módulo, e o gerador foi removido | #33, #41, #7, #8, #3 |
| Deploy e ambiente | #19, #28, #80 | Deploy no Render pelo `render.yaml`. O backend sobe no console do Windows, e o Vite usa porta fixa | #4, #2, #11 |
| Processo e documentação | #1, #18, #27, #32, #55, #92, #96, #101, #115, #116 | `AGENTS.md`, specs da AP1 somente leitura, README da AP2 e `CUSTOS.md`/`NOTAS.md` gerados por script. Também os registros das sessões e a passagem do projeto ao cliente ([`docs/PASSAGEM.md`](docs/PASSAGEM.md)) | #14, #54, #114 |

### Funcionalidades novas da AP2

- **Cliente:**
  - Meus agendamentos, com cancelamento (só de agendamento próprio, ativo e futuro);
  - assinatura do Trim Club na conta;
  - pontos de fidelidade a cada pagamento.
- **Painel do admin:** antes, as telas não estavam ligadas à API. Agora há abas ligadas a ela para:
  - usuários, com senha temporária e troca obrigatória no primeiro login;
  - barbeiros, com perfil, serviços, ativação e escala;
  - serviços;
  - despesas, com categorias;
  - galeria, com moderação e filtro por tag na página pública;
  - Trim Club, com planos e assinantes;
  - fidelidade, com prêmios, carteiras e resgates;
  - estoque, com histórico e movimentação.
- **Conta:** refresh token, logout que revoga a sessão, perfil, troca de senha, reenvio da
  verificação e limite de tentativas de login.
- **Infraestrutura:**
  - migrações do Alembic;
  - deploy no Render com o commit em `/health`;
  - CI com seis jobs;
  - custo das sessões gerado por `scripts/custos.py`.

O backlog completo está nas [issues](https://github.com/henriquelm-io/dsai-ap2-trim/issues).
