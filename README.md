# Trim ✂️ — Gestão Completa para Barbearias

> **AP1 — Desenvolvimento de Software Apoiado por IA (2026.4 — UFPA)**

> **URL Pública:** [https://trim.app](https://trim.app) *(a definir — será atualizada antes da entrega)*

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
- **Hospedagem / Deploy:** Vercel (frontend) + Render / Railway (backend + banco)

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
npm run dev
```

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
github.com/AlDanial/cloc v 1.98  T=1.46 s (54.8 files/s, 4431.8 lines/s)
-------------------------------------------------------------------------------
Language                     files          blank        comment           code
-------------------------------------------------------------------------------
Python                          74           1156            759           4104
CSS                              1             38              0            258
TypeScript                       2              5              0             64
INI                              1             10              0             32
Mako                             1              8              0             18
HTML                             1              0              0             13
-------------------------------------------------------------------------------
SUM:                            80           1217            759           4489
-------------------------------------------------------------------------------
```

---

## 📁 Estrutura do Repositório

Consulte o arquivo [AGENTS.md](file:///c:/Users/Gusta/Desktop/REPO/dsai-ap1-trim/AGENTS.md) para detalhes completos sobre o fluxo de desenvolvimento SDD, convenções de commits com trailers e registro de prompts.
