# AGENTS.md — Diretrizes e Base Operacional do Projeto

Este arquivo define os padrões de arquitetura, fluxo de trabalho, convenções de versionamento e regras obrigatórias para o desenvolvimento da **Atividade Prática 1 (AP1)** da disciplina **Desenvolvimento de Software Apoiado por IA (2026.4 — UFPA)**, ministrada pelo **Prof. Gustavo Pinto**.

Todas as sessões de desenvolvimento (conduzidas por agentes de IA ou humanos) **devem** seguir estritamente as diretrizes aqui documentadas.

---

## 1. Visão Geral e Metas

- **Objetivo:** Construção de uma aplicação completa, funcional e **não trivial** (ex.: delivery/pedidos, carona/mobilidade, avaliação de locais, etc.).
- **Metodologia:** **SDD (Spec-Driven Development)** com fluxo *Spec -> Plan -> Tasks*.
- **Valor:** 30 pontos (única atividade prática do semestre).
- **Data limite de commits:** **01/10/2026 às 18:00h** (commits posteriores serão desconsiderados).
- **Apresentação:** **01/10/2026** (ao vivo, sem slides, navegando na URL pública e no repositório).

---

## 2. Requisitos Obrigatórios de Entrega

1. **Aplicação Publicada:**
   - Deve abrir com apenas 1 clique a partir de uma **URL pública** informada no `README.md`.
   - Deve estar estável e funcional no momento da apresentação.
2. **Meta de 100 Mil Linhas de Código:**
   - Medição oficial realizada pelo utilitário `cloc`.
   - Excluem-se dependências, builds, arquivos de lock, documentações e bases de dados.
3. **SDD Rígido (Spec-First):**
   - Cada parte ou módulo do sistema deve possuir uma especificação datada na pasta `SPEC/`.
   - **Regra de ouro:** A spec deve ser **commitada no Git ANTES** do código que a implementa.
4. **Registro Integral de Sessões e Prompts:**
   - Todo e qualquer prompt utilizado precisa ser registrado na íntegra em `prompts/sessoes/`.
   - Projeto no ar sem o histórico dos prompts **não será avaliado**.
5. **Autoria e Colaboração:**
   - Repositório novo e público no GitHub (ex.: `dsai-ap1-<nome-da-app>`).
   - Ambos os membros da dupla devem assinar commits com suas respectivas contas do GitHub para comprovar a divisão de sessões.
   - Todo código deve entrar via terminal (`git commit` e `git push`); **proibido** upload manual via interface web do GitHub.
   - Histórico do Git não pode ser reescrito: **proibido** `git rebase` de commits já enviados, `git squash` destrutivo ou `push --force`.

---

## 3. Estrutura de Pastas do Repositório

```text
.
├── AGENTS.md      # Este arquivo: constituição e regras do projeto
├── README.md      # URL pública, dupla, stack, como rodar, ferramentas/modelos e saída do cloc
├── SPEC/          # Uma spec por parte/módulo do sistema (datadas)
│   ├── 2026-09-29-visao-geral.md
│   └── ...
├── src/           # Código-fonte da aplicação (organização interna livre)
├── tests/         # Testes automatizados (unitários, integração, e2e)
└── prompts/
    └── sessoes/   # Exportações brutas das conversas e interações com IA
```

*Arquivos complementares opcionais:*
- `PLAN.md` / `TASKS.md` (detalhamento de planos e tarefas)
- Registro de custos de API / tokens consumidos

---

## 4. Arquitetura e Modularidade (Proibido "Obeliscos")

O projeto adota uma política de **tolerância zero** para arquivos gigantes (obeliscos/arquivos monolíticos) e código espaguete. A manutenção e escalabilidade são prioridades.

### Backend (Python/FastAPI)
- **Estrutura Modular:** Cada módulo (auth, barbers, services, etc.) deve ser um pacote isolado dentro de `src/backend/modules/`.
- **Separação de Responsabilidades (Clean Architecture style):**
  - `models.py`: Apenas definição das tabelas do banco.
  - `schemas.py`: Apenas validação de dados (Pydantic).
  - `service.py`: Regras de negócio (nunca no router).
  - `router.py`: Apenas a definição da rota e injeção de dependências, delegando a execução para o service.

### Frontend (React/Vite)
- **Componentização:** Componentes grandes devem ser quebrados em subcomponentes menores, reutilizáveis e com responsabilidade única.
- **Hooks Customizados:** Lógica complexa ou de fetch de dados deve ser extraída do componente para *custom hooks* (ex.: `useAuth`, `useAppointments`).
- **Páginas vs. Componentes:** Telas/Páginas ficam em `src/pages/` (ou rota) e componentes reutilizáveis em `src/components/`.

---

## 5. Padrão da Pasta `SPEC/` (Spec-Driven Development)

### Nomenclatura dos arquivos
- Formato: `AAAA-MM-DD-<parte-do-sistema>.md`
- Exemplos:
  - `SPEC/2026-09-29-visao-geral.md`
  - `SPEC/2026-09-29-autenticacao.md`
  - `SPEC/2026-09-30-catalogo-produtos.md`
  - `SPEC/2026-09-30-carrinho.md`
  - `SPEC/2026-10-01-checkout.md` (se substituir uma parte anterior, declarar no topo)

### Template de Cada Spec
Toda especificação deve conter seções objetivas e verificáveis:

```markdown
# [Nome da Funcionalidade/Módulo] (AAAA-MM-DD)

## O quê e por quê
Descrição clara do problema, da solução técnica e do valor para o usuário final.

## Critérios de aceitação
- [ ] Critério 1 verificável objetivamente
- [ ] Critério 2 verificável objetivamente
- [ ] Critério 3 de tratamento de erros ou limites

## Fora do escopo
- O que deliberadamente NÃO será implementado nesta etapa/módulo.
```

### Regras de Ciclo de Vida da Spec
- **Pequenos ajustes:** Edite a spec existente e realize um commit com trailer `Spec: ...`.
- **Mudança de rumo:** Crie um novo arquivo com nova data, indicando qual spec anterior está sendo substituída ou revisada.
- **Antes do código:** Sempre realize o commit da spec antes de iniciar a implementação do código correspondente.

---

## 5. Padrão de Commits e Git Trailers

Os commits devem ser atômicos, frequentes e pequenos (no mínimo um commit para cada parte/funcionalidade do sistema).

### Formato Obrigatório da Mensagem:
```text
<escopo>: <descrição sucinta no imperativo>

Agent: <ferramenta/modelo>
Spec: SPEC/<arquivo-da-spec>.md
```

### Variações do Trailer `Agent:`
- Código gerado integralmente por agente:  
  `Agent: antigravity/gemini-2.5-pro` (ou `claude-code/claude-sonnet-5-5`, etc.)
- Código gerado por agente e ajustado manualmente:  
  `Agent: antigravity/gemini-2.5-pro + manual`
- Código escrito 100% à mão (sem auxílio de agente):  
  `Agent: none`

### Exemplo de Commit Válido:
```text
carrinho: bloqueia adicao de itens sem estoque disponivel

Agent: antigravity/gemini-2.5-pro
Spec: SPEC/2026-09-30-carrinho.md
```

---

## 6. Registro de Prompts e Sessões (`prompts/sessoes/`)

Nenhuma interação pode ser perdida ou omitida.

### O que deve ser registrado:
- Todos os prompts do início ao fim do projeto;
- Prompts curtos de continuidade ou correção (ex.: *"continue"*, *"arrume o erro x"*);
- Prompts de brainstorming ou rascunho de specs realizados em navegadores ou ferramentas auxiliares;
- Prompts que geraram erros ou código descartado;
- Os textos devem ser mantidos **exatamente como foram digitados**, preservando erros de digitação e termos originais (nunca editar a posteriori).

### Nomenclatura dos arquivos de sessão:
`prompts/sessoes/AAAA-MM-DD-HHMM-<ferramenta>.<ext>`
*(Exemplo: `2026-09-29-2030-antigravity.md` ou `2026-09-30-1415-claudecode.jsonl`)*

### Segurança e Segredos (CRÍTICO):
- **Varredura obrigatória antes de cada commit:** Verificar se os logs contêm senhas, chaves de API (`AIza...`, `sk-...`), tokens de acesso ou conteúdos de arquivos `.env`.
- Caso alguma credencial vaze em um log, ela deve ser **imediatamente revogada e recriada**, e não apenas apagada do histórico.
- Sessões com arquivos brutos superiores a **50 MB** devem ser compactadas via `gzip` (`.gz`).

---

## 7. Verificação de Volume de Código (`cloc`)

O projeto deve atingir no mínimo **100.000 linhas de código** em arquivos de produção e testes.

### Comando Oficial de Verificação:
```bash
cloc . --vcs=git \
  --exclude-dir=node_modules,vendor,dist,build,prompts \
  --exclude-lang=Markdown,JSON,YAML,CSV,Text,SVG \
  --not-match-f='(lock|\.min\.)'
```

- A saída tabular gerada pelo comando deve ser colada no `README.md`.
- No `README.md`, detalhar a proporção de linhas de código de aplicação vs. linhas de código de testes.

---

## 8. Roteiro da Apresentação (01/10)

A apresentação da dupla não terá slides. A avaliação será conduzida em 4 etapas objetivas:

1. **Demonstração ao Vivo:** Abrir a URL pública e executar o fluxo principal de ponta a ponta.
2. **A Spec em 1 Minuto:** Explicar sucintamente o objetivo do sistema e os limites do escopo.
3. **Os 3 Prompts:**
   - O prompt que **melhor funcionou**;
   - O prompt que **pior funcionou** (ou causou regressão);
   - O prompt que **mudou os rumos** do projeto;
   - *(Explicar a causa e o aprendizado de cada um).*
4. **Métricas Finais:** Total de linhas (`cloc`), quantidade de specs, total de prompts/sessões e horas estimadas.

---

## 10. Checklist de Conformidade Pré-Commit e Entrega

- [ ] URL pública ativa e adicionada com destaque no topo do `README.md`.
- [ ] Especificações com formato `AAAA-MM-DD-<parte>.md` na pasta `SPEC/`.
- [ ] Ordem cronológica comprovada no Git: commits de spec precedem commits de código.
- [ ] Logs brutos de todas as interações salvos em `prompts/sessoes/`.
- [ ] Código refatorado e modularizado: nenhum "obelisco" ou arquivo excessivamente longo. Regras de negócio separadas dos controllers/routers.
- [ ] Ausência total de segredos (chaves de API / senhas) no repositório.
- [ ] Todos os commits possuem os metadados `Agent:` e `Spec:`.
- [ ] Ambos os membros da dupla possuem commits autorados com suas respectivas contas.
- [ ] Saída do `cloc` inserida no `README.md` demonstrando no mínimo 100.000 linhas.
- [ ] Último commit realizado até 01/10 às 18:00h.
