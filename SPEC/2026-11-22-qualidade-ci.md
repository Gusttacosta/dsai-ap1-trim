# Métricas de qualidade da AP2 na CI (2026-11-22)

> Complementa: SPEC/2026-11-10-processo-ap2.md
> Issue: #41

## O quê e por quê

A CI (`.github/workflows/ci.yml`) roda os testes do backend e do frontend, o build e o `gitleaks`.
Quatro métricas da AP2 (AGENTS.md §3) ficam de fora dela, e só descobriríamos que estão abaixo
do mínimo na avaliação. Medição local na `main` 05e1697 (#41):

| Métrica | Mínimo | Hoje |
| :--- | :--- | :--- |
| Commits com `Agent:` e `Spec:` desde `95c79b5` | 80% | 74,6% (47 de 63). Os 16 que faltam têm uma linha em branco entre os trailers e o `Co-Authored-By:`, então o git não os lê como trailers |
| Alertas críticos de dependências | zero | `npm audit`: 0 críticos (5 altos). `pip-audit`: 1 crítico (`python-jose`, resolvido no #42/#43) |
| Duplicação (`jscpd`) em `src/` | até 5% | 3,57% com o `jscpd` 5.4.3 (Python: 4,48%) |
| Cobertura do código novo | 70% | 64% de 190 linhas desde `95c79b5`, com PostgreSQL |

Solução: cada métrica vira um job ou passo com nome próprio na CI, sem mexer no `gitleaks`.

1. **Job `Trailers (Agent e Spec)`**, só em `pull_request`, com `fetch-depth: 0`. Ele lista os
   commits do PR que não são merges (`git rev-list --no-merges base..head`) e lê os trailers com
   `git log --format='%(trailers:key=Agent,valueonly)'` (e o mesmo para `Spec`). Falha se algum
   commit não tiver um dos dois, com uma linha `::error::` por commit, mostrando o hash e o assunto.
   Vale o que o git reconhece como trailer: a regra é a mesma que a avaliação usa.
2. **Job `Dependências (npm audit e pip-audit)`**, falhando só em vulnerabilidade crítica:
   - `npm audit --audit-level=critical` em `src/frontend`, que usa o `package-lock.json`;
   - `pip-audit -r requirements.txt` (versão fixada) com saída JSON. O `pip-audit` não informa
     severidade. Para cada alerta, o job consulta a severidade na base de advisories do GitHub
     (`gh api /advisories/<GHSA>`, com o `GITHUB_TOKEN` da própria CI). Ele lista todos os
     alertas no log, com pacote, versão, id e severidade, e falha se algum for `critical`. Um
     alerta sem GHSA, ou cuja consulta falhe, vira um aviso (`::warning::`), não uma falha. Se o
     próprio `pip-audit` não gerar o JSON, o job falha.
3. **Job `Duplicação (jscpd)`**, só como relatório: `jscpd` 5.4.3 sobre `src/`, ignorando
   `node_modules`, `dist`, `__pycache__` e `package-lock.json`. A tabela por formato e os clones vão
   para o log, e o relatório em Markdown vai para o resumo do job. O job não falha por duplicação.
4. **Cobertura no job do backend**: o passo de testes passa a rodar
   `pytest --cov=src/backend --cov-report=xml`, e um passo separado, `Cobertura do código novo
   (diff-cover)`, roda `diff-cover coverage.xml --compare-branch=origin/main --fail-under=70`. O
   checkout do backend passa a usar `fetch-depth: 0`, para que exista `origin/main`. No push para
   a `main`, o diff contra `origin/main` é vazio, e o `diff-cover` passa. `pytest-cov` e
   `diff-cover` são instalados só na CI, com versão fixada, e ficam fora do `requirements.txt`,
   que é o mesmo da produção.

O limite de 70% vale para o diff de cada PR. O código novo acumulado desde `95c79b5` está em 64%,
mas esse histórico não trava os PRs futuros: só o que cada PR acrescenta é medido.

Valor: a dupla vê cada métrica a cada PR, e trailers ausentes, dependência crítica ou código
novo sem teste quebram a CI antes do merge, não na avaliação.

## Critérios de aceitação

- [ ] Em um PR, um commit (fora os merges) sem `Agent:` ou sem `Spec:` reconhecido pelo git faz o
      job de trailers falhar, apontando o commit. Com todos os commits corretos, ele passa. Em
      `push`, o job não roda.
- [ ] Um alerta crítico no `npm audit` ou no `pip-audit` faz o job de dependências falhar. Alertas
      altos, moderados e baixos aparecem no log sem falhar.
- [ ] O job do `jscpd` mostra a porcentagem e os clones de `src/` no log e no resumo, e passa
      mesmo com duplicação.
- [ ] O job do backend gera `coverage.xml`, mostra a cobertura por arquivo no log e roda o
      `diff-cover` contra `origin/main`, falhando abaixo de 70% nas linhas novas.
- [ ] Os jobs `Backend`, `Frontend` e `Segredos (gitleaks)` continuam passando, e o `gitleaks` não
      muda.

## Fora do escopo

- Corrigir os trailers dos 16 commits de 16/11, porque reescrever o histórico da `main` é
  proibido (AGENTS.md §2).
- Corrigir os alertas altos do `npm audit` (#8) e do `pip-audit` (`starlette`, `python-multipart`).
- Reduzir a duplicação ou fazer o `jscpd` falhar a CI.
- Cobertura do frontend.
