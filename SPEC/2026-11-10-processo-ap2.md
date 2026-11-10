# Processo de desenvolvimento da AP2 (2026-11-10)

> Spec de processo e infraestrutura. Não altera funcionalidades do Trim.
> Complementa (não substitui) as specs de 2026-09-29.

## O quê e por quê

O Trim foi herdado da AP1 (`Gusttacosta/dsai-ap1-trim`) e passa a ser evoluído pela dupla
`Severino-Sobrinho` + `henriquelm-io` no fork `henriquelm-io/dsai-ap2-trim`, seguindo as regras
da aula 09 (Prof. Gustavo Pinto, 22/10/2026).

A avaliação da AP2 é extraída do repositório por script. Por isso o próprio repositório precisa:

1. documentar as regras da AP2 para humanos e agentes (`AGENTS.md`);
2. ter uma pipeline de CI que rode a cada push e a cada PR, condição obrigatória para a AP2 ser avaliada;
3. guardar as sessões com agentes e o custo (tokens) de cada uma em `prompts/sessoes/`.

## Critérios de aceitação

- [ ] `AGENTS.md` descreve as regras da AP2: sem reescrita, refatoração localizada com issue e teste,
      linhas novas medidas por `cloc --diff`, `jscpd` ≤ 5%, spec antes do código, trailers `Agent:`/`Spec:`,
      sessão + custo por dia de commit com agente, PR aprovado pela dupla, CI verde, `gitleaks`, URL pública.
- [ ] `AGENTS.md` não contém mais prazos nem roteiro de apresentação da AP1, e a numeração das seções é contínua.
- [ ] `.github/workflows/ci.yml` roda em `push` e `pull_request` para `main`, com:
  - [ ] backend: instala `requirements.txt` em Python 3.12, importa `src.backend.main` e roda `pytest`;
  - [ ] frontend: `npm ci` e `npm run build` em `src/frontend`.
- [ ] A pipeline passa no estado atual do código (sem mudar funcionalidades).
- [ ] `prompts/sessoes/` contém as sessões com agente já realizadas e um `CUSTOS.md` com os tokens de cada sessão,
      sem segredos (JWT, tokens, e-mail pessoal mascarados).

## Fora do escopo

- Corrigir os problemas levantados na linha de base (issues P01–P13): cada um terá a sua própria branch, spec ou issue e testes.
- Substituir os testes gerados (P02) por testes reais.
- `gitleaks`, `jscpd`, cobertura do diff e `npm audit` na CI: entram em PRs seguintes, depois que houver testes reais e uma decisão sobre o histórico herdado.
- Deploy da versão da AP2 (URL pública própria).
- Proteção da branch `main` e ativação de issues no GitHub (configuração do repositório feita pelo admin).
