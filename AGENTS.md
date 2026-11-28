# AGENTS.md — Diretrizes e Base Operacional do Projeto (AP2)

Este arquivo define as regras, o fluxo de trabalho e as convenções para a **Atividade Prática 2 (AP2)** da disciplina **Desenvolvimento de Software Apoiado por IA (2026.4 — UFPA)**, ministrada pelo **Prof. Gustavo Pinto**.

Todas as sessões de desenvolvimento, conduzidas por agentes de IA ou por humanos, **devem** seguir estas diretrizes.

> **Princípio da AP2:** a avaliação é extraída do repositório por script.
> *"O que não está no repositório não aconteceu."*

---

## 1. Contexto

- **Projeto herdado:** Trim, sistema de gestão de barbearia, desenvolvido na AP1 em `Gusttacosta/dsai-ap1-trim`.
- **Fork da AP2:** `henriquelm-io/dsai-ap2-trim`.
- **Dupla (FDE):** `Severino-Sobrinho` e `henriquelm-io`. A dupla é dona do negócio e da técnica.
- **Cliente:** o autor original da AP1. **O cliente não escreve código**: commits dos autores originais no fork não contam.
- **Linha de base:** o último commit herdado da AP1 é `95c79b5` (a confirmar com o professor, já que houve commits depois do prazo da AP1). Toda métrica de "código novo" é medida a partir dele.
- **Missão:** estudar o projeto, entender o que foi construído, investigar se foi usado, definir o que falta e implementar.

---

## 2. Restrições (violá-las anula a AP2)

1. **Sem reescrita.** Trocar linguagem ou framework, abrir um repositório novo ou apagar módulos para refazê-los **anula a AP2**.
2. **Refatoração localizada**, sempre justificada em uma issue e coberta por teste.
3. **100 mil linhas novas**, medidas como a diferença entre o fork e a linha de base (`cloc --diff`). O que já existia não conta.
4. **Fora da contagem:** código duplicado, código gerado em massa, código morto e arquivos gerados (lockfiles, `build/`, `dist/`, `vendor/`, minificados). **Proibido inflar a contagem.**
5. **Histórico sem reescrita:** proibido `push --force`, `rebase` de commits já enviados e `squash` destrutivo na `main`.
6. **Gate:** sem **URL pública no ar** e **CI verde**, a AP2 não é avaliada. Critério abaixo do mínimo vale zero.

---

## 3. Métricas de avaliação (50 pts)

| Critério | Métrica | Mínimo | Pts |
| :--- | :--- | :--- | ---: |
| Tamanho | linhas novas no `cloc`, descontado o que a AP1 já tinha | 100 mil | 8 |
| Duplicação | código duplicado (`jscpd`) | até 5% | 3 |
| Specs | spec datada em `SPEC/` por funcionalidade nova, commitada **antes** do 1º commit de código que a cita | 100% | 5 |
| Commits com agente | commits com trailers `Agent:` e `Spec:` | 80% | 3 |
| Frequência | dias distintos com commit; mediana do tamanho do commit | 2 dias/semana; mediana < 400 linhas | 3 |
| Sessões | sessão em `prompts/sessoes/` para cada dia com commit de agente | 100% dos dias | 3 |
| Autoria | parcela de commits de cada membro da dupla | 30% cada | 2 |
| Testes | cobertura de linhas do código novo (diff coverage) | 70% | 5 |
| Testes que testam | testes novos falham quando a mudança é revertida | amostra de 5, todos falham | 4 |
| CI | pipeline verde no último commit da `main`; builds verdes no projeto | verde; 80% | 3 |
| Revisão | merges na `main` feitos por PR aprovado pela dupla | 100% | 3 |
| Segurança | segredos no histórico (`gitleaks`) e alertas críticos de dependências | zero | 3 |
| Produção | URL pública responde e serve a versão do último commit da `main` | no ar no dia | 3 |
| Custo | tokens ou custo registrado em cada sessão | 100% | 2 |

---

## 4. Fluxo de trabalho

1. **Investigar com evidência.** Todo problema ou necessidade vira uma **issue** com passos de reprodução, evidência (saída, arquivo:linha, print) e proposta. O backlog é a lista de issues.
2. **Spec antes do código.** Funcionalidade nova ou mudança de comportamento exige uma spec em `SPEC/`, commitada antes de qualquer código que a cite (ver §6).
3. **Uma branch por issue ou spec**, criada a partir da `main` atualizada:
   - `feat/<assunto>`, `fix/<assunto>`, `test/<assunto>`, `docs/<assunto>`, `chore/<assunto>`.
4. **Commits pequenos** (mediana < 400 linhas), cada um com testes quando alterar código (ver §7).
5. **Pull Request para a `main`**, que referencia a issue (`Closes #N`) e a spec. Precisa de **aprovação do outro membro da dupla**. **Ninguém faz push direto na `main`.**
6. **CI verde** é pré-requisito do merge. PR com CI vermelha não entra.
7. **Registrar a sessão** com o agente em `prompts/sessoes/` no mesmo dia, com o custo (ver §8).
8. Todo código entra via `git commit`/`git push` pelo terminal. É proibido upload pela interface web do GitHub.

---

## 5. Estrutura de pastas

```text
.
├── AGENTS.md          # Este arquivo
├── README.md          # URL pública, dupla, stack, como rodar, saída do cloc
├── .github/workflows/ # CI (GitHub Actions)
├── SPEC/              # Specs datadas (AP1: 2026-09-29-*; AP2: datas a partir de 2026-11)
├── src/
│   ├── backend/       # FastAPI (Python 3.12)
│   └── frontend/      # React + Vite (TypeScript)
├── tests/             # Testes automatizados
└── prompts/
    └── sessoes/       # Sessões com agentes, notas e CUSTOS.md/NOTAS.md (gerados)
```

`scripts/custos.py` gera `prompts/sessoes/CUSTOS.md` e `prompts/sessoes/NOTAS.md` (ver §8).

### Arquitetura (mantida da AP1; proibido "obeliscos")

**Backend (Python/FastAPI):** cada módulo é um pacote em `src/backend/modules/`, com:
- `models.py`: só tabelas;
- `schemas.py`: só validação (Pydantic);
- `service.py`: regras de negócio (nunca no router);
- `router.py`: só a rota e a injeção de dependências, delegando ao service.

**Frontend (React/Vite):** componentes pequenos e com responsabilidade única, lógica de dados em *custom hooks*, páginas em `src/pages/` e componentes reutilizáveis em `src/components/`.

---

## 6. Specs (`SPEC/`)

- Nome: `AAAA-MM-DD-<parte-do-sistema>.md`, com a data em que a spec foi escrita.
- **Mudança de rumo:** crie um arquivo novo com a nova data e declare no topo qual spec anterior ele substitui ou revisa. Não reescreva specs antigas.
- **Specs da AP1 são somente leitura:** os arquivos `SPEC/2026-09-29-*` nunca são editados, renomeados ou apagados. Qualquer mudança no que eles descrevem vira uma spec nova da AP2, com `> Substitui/complementa: SPEC/<arquivo>.md` no topo.
- **Pequenos ajustes:** valem só para specs da AP2. Edite a spec existente em um commit próprio, antes do código.

### Template

```markdown
# [Nome da Funcionalidade/Módulo] (AAAA-MM-DD)

> Substitui/complementa: SPEC/<arquivo>.md (se houver)
> Issue: #N

## O quê e por quê
Problema, solução e valor para o usuário.

## Critérios de aceitação
- [ ] Critério verificável 1
- [ ] Critério verificável 2
- [ ] Tratamento de erros e limites

## Fora do escopo
- O que deliberadamente NÃO será feito.

## Rollback
- Código: `git revert -m 1 <sha-do-merge>` numa branch, por PR (nunca `push --force`).
- Migração (se houver): `alembic downgrade <revisão-anterior>`, junto com o revert do PR.
- Deploy: redeploy do commit anterior no Render (Rollback no deploy anterior do serviço).
```

---

## 7. Commits e trailers

### Formato

```text
<escopo>: <descrição sucinta no imperativo>

<corpo opcional: o que mudou e por quê; Refs #N>

Agent: <ferramenta/modelo>
Spec: SPEC/<arquivo-da-spec>.md
```

### Trailer `Agent:`
- Gerado por agente: `Agent: claude-code/claude-opus-5-5`
- Gerado por agente e ajustado à mão: `Agent: claude-code/claude-opus-5-5 + manual`
- 100% manual: `Agent: none`

### Trailer `Spec:`
- Sempre que existir uma spec relacionada, aponte para ela, **inclusive em `fix:`**. Correções de bug apontam para a spec da funcionalidade corrigida (por exemplo, `SPEC/2026-09-29-agendamentos.md`).
- Mudanças de processo, CI ou documentação apontam para `SPEC/2026-11-10-processo-ap2.md`.
- `Spec: none` só em último caso. A meta é que ≥ 80% dos commits tenham os dois trailers com valor real.

### Autoria
- Cada membro faz commits com a **própria conta** (`git config user.name/user.email` local do repositório). Meta: ≥ 30% dos commits para cada um.

### Testes junto com o código
- Toda mudança de código vem com testes que **falham se a mudança for revertida**. Antes do PR, confira: reverta a mudança localmente, rode o teste e veja ele falhar.
- Meta de cobertura do diff: ≥ 70% das linhas novas.

---

## 8. Sessões e custo (`prompts/sessoes/`)

- **Toda sessão com agente** que resultar em commit deve ser registrada no mesmo dia, na íntegra (exportação bruta), incluindo prompts curtos ("continue"), prompts descartados e prompts que causaram erro.
- Nome: `prompts/sessoes/AAAA-MM-DD-HHMM-<ferramenta>.<ext>` (horário de início, America/Sao_Paulo). Exemplo: `2026-11-10-1933-claudecode.jsonl`.
- **Custo:** cada sessão aparece como uma linha em `prompts/sessoes/CUSTOS.md`, com tokens de entrada, saída e cache. O `CUSTOS.md` e o `NOTAS.md` são **gerados** por `scripts/custos.py`: não edite os dois à mão.
- Arquivos acima de 50 MB devem ser compactados com `gzip`.

### Registrar uma sessão (fluxo)

1. **Exporte a sessão principal** como `prompts/sessoes/<sessão>-claudecode.jsonl`, onde `<sessão>` é `AAAA-MM-DD-HHMM` (início da sessão).
2. **Exporte cada subagente** da sessão como `prompts/sessoes/<sessão>-claudecode-subagente-<n>.jsonl` (`<n>` a partir de 1), com **o mesmo mascaramento** da sessão principal. Os tokens deles entram na linha da sessão principal.
3. **Crie a nota** `prompts/sessoes/<sessão>.notas.md` se houver algo a explicar: como foi exportada, o que foi mascarado, corte por `timestamp`, o que ficou de fora da contagem. Uma nota que vale para várias sessões fica na primeira delas, e as outras ganham uma nota de uma linha: `Ver a nota em <arquivo>`.
4. **Rode `python scripts/custos.py` antes do commit** e commite o `CUSTOS.md` e o `NOTAS.md` regravados junto com a sessão.

A soma usa as respostas do agente (`type: assistant`), uma vez por `message.id`, sem o modelo `<synthetic>` (SPEC/2026-11-24-custos-gerados.md). Um PR com sessão só acrescenta arquivos novos. Se a `main` ganhar outra sessão enquanto o PR está aberto, faça o merge da `main` e rode o script de novo: num conflito no `CUSTOS.md` ou no `NOTAS.md`, fique com qualquer um dos lados e regrave. A CI roda `python scripts/custos.py --check` e falha se os dois arquivos estiverem desatualizados.

### Segurança (CRÍTICO)
- **Varredura antes de cada commit** de sessão: senhas, chaves (`AIza...`, `sk-...`, `gh*_...`), tokens JWT, conteúdo de `.env`, e-mails pessoais.
- O único tipo de edição permitido em uma sessão exportada é **mascarar segredos** (por exemplo, `[jwt-removido]`). Registre isso na nota da sessão (`<sessão>.notas.md`). Nenhuma outra edição é permitida.
- Credencial vazada deve ser **revogada e recriada**, não apenas removida.

---

## 9. Integração contínua

- `.github/workflows/ci.yml` roda em todo `push` e `pull_request` para a `main`:
  - **backend:** Python 3.12, `pip install -r requirements.txt`, import de `src.backend.main` e `pytest`;
  - **frontend:** Node LTS, `npm ci` e `npm run build` em `src/frontend`;
  - **gitleaks:** histórico inteiro, com as exceções de `.gitleaks.toml` (só falsos positivos conhecidos, exigindo caminho e valor). Um falso positivo novo vira uma exceção restrita nesse arquivo, nunca um caminho liberado inteiro.
- Próximas etapas previstas (cada uma em PR próprio): banco PostgreSQL de teste na CI, cobertura do diff, `jscpd`, `npm audit`.

---

## 10. Medição de volume (`cloc`)

Linhas novas em relação à linha de base (§1):

```bash
cloc --git --diff 95c79b5 HEAD \
  --exclude-dir=node_modules,vendor,dist,build,prompts \
  --exclude-lang=Markdown,JSON,YAML,CSV,Text,SVG \
  --not-match-f='(lock|\.min\.)'
```

Cole a saída no `README.md` e separe linhas de aplicação de linhas de teste.

---

## 11. Checklist antes de abrir um PR

- [ ] Issue criada, com evidência, e referenciada no PR.
- [ ] Spec commitada antes do código (quando for funcionalidade ou mudança de comportamento).
- [ ] Commits pequenos, com `Agent:` e `Spec:`.
- [ ] Testes novos passam e **falham com a mudança revertida**.
- [ ] CI verde.
- [ ] Sessão do dia em `prompts/sessoes/`, varrida em busca de segredos (subagentes inclusive), e `python scripts/custos.py` rodado (`CUSTOS.md` e `NOTAS.md` em dia).
- [ ] Nenhum segredo no diff (`.env`, chaves, tokens).
- [ ] Nenhum código duplicado, gerado em massa ou morto adicionado para inflar linhas.
- [ ] Revisão e aprovação do outro membro da dupla.
