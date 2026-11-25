# Migrações do Alembic de verdade, e plano do Trim Club com quantidade ilimitada (2026-11-25)

> Complementa: SPEC/2026-11-16-deploy-render.md, SPEC/2026-11-16-seed-seguro.md e
> SPEC/2026-09-29-assinaturas.md
> Issues: #6 e #16

## O quê e por quê

**#6:** `alembic/versions/` estava vazia, então o `alembic upgrade head` não fazia nada. As tabelas
nasciam do `Base.metadata.create_all` no startup, que só cria tabelas novas: uma coluna nova, ou
uma restrição como o `CHECK (balance >= 0)` da #73, nunca chegava ao banco de produção. Também
não havia como saber em que versão do esquema um banco estava.

**#16:** o plano Executivo é "cortes ilimitados", mas `included_cuts` era `NOT NULL`, e o seed
usava 30 como aproximação. A mudança de modelo recomendada na issue (opção A: `NULL` =
ilimitado) exige justamente uma migração. Por isso as duas issues vão juntas.

**Achado ao mexer na tela, corrigido aqui:** a página `/trim-club` lia `plan.price` e
`plan.billing_cycle`, campos que a API não tem, e mostrava "R$ NaN/ano". Um plano sem descrição
quebrava a tela no `.split`.

## Decisões

- **Revisões:**
  - `0001`: o esquema inicial, as 26 tabelas, gerado pelo autogenerate a partir de
    `Base.metadata`;
  - `0002`: leva aos bancos antigos o `CHECK` da carteira, só onde falta, com `NOT VALID` para
    não falhar por algum saldo antigo;
  - `0003`: `included_cuts` e `included_shaves` aceitam `NULL`, e o Executivo de 30 cortes vira
    `NULL`.
- **`scripts/migrate.py`** roda antes do `uvicorn` (no `Procfile` e no `startCommand` do
  `render.yaml`):
  - banco vazio: `upgrade head`;
  - banco com as tabelas do `create_all` e sem `alembic_version` (a produção): `stamp 0001` e
    depois `upgrade head`;
  - banco versionado: `upgrade head`.
- **O `create_all` do startup fica só em desenvolvimento.** Em produção, só as migrações mexem no
  esquema.
- **Ilimitado:**
  - `null` = ilimitado, `0` = não incluso, `n` = n por mês;
  - no `PUT`, `null` nesses campos passa a ser aceito (ilimitado), e omitir o campo não muda nada;
  - "barba a cada 15 dias" continua como 2 por mês: uma regra de intervalo pediria a tabela de
    benefícios da opção C, e nada no sistema consome a cota hoje.

## Critérios de aceitação

1. [ ] Num banco vazio, as migrações criam exatamente as tabelas dos modelos, e o autogenerate não
   acha diferença entre os modelos e o banco migrado. Esse teste falha quando alguém muda um
   modelo sem criar uma migração.
2. [ ] Num banco "de produção" (tabelas do `create_all`, sem `alembic_version`, sem o `CHECK`, com
   dados e um Executivo de 30 cortes), o `migrate` faz `stamp` e `upgrade`:
   - os dados continuam;
   - o `CHECK` aparece;
   - o Executivo vira `NULL`;
   - a revisão é a `head`.
3. [ ] Rodar o `migrate` de novo não muda nada, e o `downgrade base` remove as tabelas e os enums.
4. [ ] Há uma cabeça só no histórico de revisões.
5. [ ] **Planos:**
   - criar com `included_cuts: null` grava e devolve `null`;
   - omitir o campo grava 0;
   - o `PUT` alterna entre limitado e ilimitado;
   - um valor negativo continua respondendo 422.
6. [ ] **Tela `/trim-club`:**
   - mostra o preço mensal (`monthly_price`, "R$ 150,00/mês");
   - mostra "Cortes: Ilimitados" ou "Cortes: 2 por mês", e omite o que é 0;
   - não quebra com um plano sem descrição.
7. [ ] O README explica o `scripts/migrate.py` e como criar uma migração nova.

## Testes

- `tests/test_migracoes.py`: schema novo no PostgreSQL de `TEST_DATABASE_URL`, com psycopg2;
- `tests/test_plano_ilimitado.py`;
- `src/frontend/src/pages/TrimClub.test.tsx`.

## Implantação

O primeiro deploy depois do merge roda `python scripts/migrate.py` contra o banco de produção. Ele
cria a tabela `alembic_version`, registra a `0001`, acrescenta o `CHECK` (0002) e torna as colunas
do plano anuláveis (0003). Se o serviço do Render não acompanhar o `render.yaml` (Blueprint sem
sincronizar), o *Start Command* precisa ser trocado no painel para o mesmo comando.
