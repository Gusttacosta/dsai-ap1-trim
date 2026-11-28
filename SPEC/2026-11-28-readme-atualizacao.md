# Atualização do README (2026-11-28)

> Complementa: SPEC/2026-11-26-passagem.md
> Issue: #117

## O quê e por quê

O `README.md` da `main` (`44a381f`) não acompanhou os PRs de 24/11 a 27/11. Ele diz que não há
migrações, descreve a CI e o deploy de antes do Alembic e lista só os PRs até o #25. As métricas
são de `fecf54d`. Além disso, o bloco da AP1 de "Como rodar", marcado como "mantido sem
alterações", foi editado.

A atualização é só de documentação, sem código:

1. **Correções:**
   - migrações do Alembic no Stack, na seção do Windows e no Deploy;
   - os 6 jobs da CI;
   - PyJWT no lugar do python-jose;
   - o número atual de testes do backend;
   - o bloco AP1 de "Como rodar" volta ao texto de `95c79b5` (`alembic upgrade head`).
2. **"O que mudou no fork":**
   - uma tabela resumida por tema, com todos os PRs mergeados desde `95c79b5` e as issues
     resolvidas;
   - um parágrafo com as funcionalidades novas da AP2;
   - um link para `docs/PASSAGEM.md`, que tem os detalhes.
3. **Métricas da AP2**, medidas de novo sobre a `main` atual:
   - `cloc`, `jscpd`, commits e PRs;
   - e também: commits por membro, trailers, mediana do tamanho dos commits, gitleaks, diff-cover
     na CI e issues abertas.
4. **Estrutura do repositório:** `docs/`, `scripts/migrate.py`, `alembic/versions/`, `.coveragerc`
   e `.gitleaks.toml`. O comentário do `main.py` também é corrigido.
5. **Variáveis do `.env`:** uma tabela com as variáveis do `.env.example`, incluindo `SHOP_TIMEZONE`,
   `BOOKING_MIN_LEAD_MINUTES`, `BOOKING_MAX_DAYS_AHEAD` e `ACCESS_TOKEN_EXPIRE_MINUTES`.

## Critérios de aceitação

- [ ] Nenhuma frase do README diz que não há migrações ou que as tabelas são criadas na
  inicialização em produção.
- [ ] Todo PR mergeado até a data da medição aparece uma vez na tabela por tema.
- [ ] Os números das métricas saem dos comandos citados ao lado deles, sobre o commit citado.
- [ ] Os blocos "📦 AP1" ficam iguais ao README de `95c79b5`.
- [ ] A seção "Contagem de Linhas" de 19/11 continua como registro.
- [ ] A CI fica verde.

## Fora do escopo

- Mudar código, testes, CI ou `docs/PASSAGEM.md`.
- Corrigir o link `file:///` do bloco da AP1, que está assim no original.

## Rollback

`git revert -m 1 <merge>` do PR. Não há migração nem efeito no deploy além do README.
