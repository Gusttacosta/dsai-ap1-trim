# Passagem do projeto: Trim (AP2 → dupla da AP1)

> Spec: [`SPEC/2026-11-26-passagem.md`](../SPEC/2026-11-26-passagem.md) · Issue: #114
> Estado descrito: `origin/main` em `fecf54d` (merge do #113), 26/11/2026.
> Linha de base da AP1: `95c79b5`.

Este documento é para quem vai manter o Trim depois da AP2. As regras de trabalho (issue, spec
antes do código, trailers, sessões) continuam em [`AGENTS.md`](../AGENTS.md). As métricas
(`cloc`, `jscpd`, commits e PRs) estão no [`README.md`](../README.md#-métricas-da-ap2).

## a) O que mudou

Os 65 PRs mergeados desde `95c79b5` (`gh pr list --state merged`), por tema. Cada PR aparece
uma vez, no tema principal dele.

### Segurança

| PR | O quê |
| :--- | :--- |
| #17 | Rota de seed protegida por `SEED_SECRET` (cabeçalho `X-Seed-Secret`), sem segredo nem senhas no código, e seed que não quebra no meio (#5, #10) |
| #25 | O cliente só cancela o próprio agendamento, ativo e futuro (#24) |
| #29 | `/status` só altera o próprio agendamento, com transições válidas e cobrança única (#26) |
| #31 | Token de redefinição e de verificação fora do log em produção (#30) |
| #43 | Troca do `python-jose` pelo PyJWT (alerta crítico GHSA-3qf3-8w2g-rqmx, #42) |
| #78 | Galeria: permissões, erros 500, envio pelo admin, tags e moderação (#71) |
| #90 | Dependências do backend sem alertas high, e `pip-audit` falhando em high (#77) |

### CI e testes

| PR | O quê |
| :--- | :--- |
| #34 | `gitleaks` na CI, com allowlist restrita aos falsos positivos conhecidos (#33) |
| #44 | CI confere trailers, dependências, duplicação e cobertura do código novo (#41) |
| #56 | `tsc` no build do frontend e `npm audit` sem alerta high (#7, #8) |
| #36, #38, #40 | Testes de integração de `auth`, `barbers` e `services` no lugar dos gerados (#3) |
| #58, #60, #62, #63 | Testes de integração de `appointments`, `finance`, `products` e `subscriptions` (#3) |
| #66, #68, #70, #72 | Testes de integração de `expenses`, `dashboard`, `walkin` e `gallery` (#3) |
| #74, #76 | Testes de integração de `loyalty` e `notifications` (#3) |
| #95 | Remove o gerador de testes, que não gerava mais nada (#3) |

### Backend

| PR | O quê |
| :--- | :--- |
| #20 | Agendamento no fuso da barbearia (`SHOP_TIMEZONE`), sem horários passados (#12) |
| #45 | Refresh do access token e logout que revoga a sessão (#35) |
| #46 | Perfil do usuário (`PUT /me`) e troca de senha (`PUT /me/password`) (#35) |
| #47 | Serviços: validação dos campos, reativação e vínculo só com ativos (#39) |
| #48 | Agendamento só dentro do expediente e fora do almoço (#23) |
| #52 | Nome e sobrenome do visitante validados no backend e na tela (#22) |
| #53 | Barbeiros: o admin altera e desativa, escala validada (#37, #39) |
| #79 | Disponibilidade recusa duração fora de 1 a 1440 minutos (#57) |
| #81 | Remove os módulos vazios `clients`, `landing` e `queue` (#9) |
| #82 | Despesas: validações e categorias editáveis (#65) |
| #83 | Usuário Visitante único e fila de espera sem erros 500 (#21, #69) |
| #84 | Fidelidade: erros 500, nomes de prêmio, resgate travado e operações do admin (#73) |
| #85 | Produtos: validações, sinal da movimentação, produto desativado e reativação (#61) |
| #86 | Financeiro: venda atômica, regras do caixa, Trim Club, comissões pendentes e extrato por data (#59) |
| #87 | Notificações de agendamento, aviso geral com público e telas ligadas à API (#75) |
| #88 | Trim Club: ciclo da assinatura, mensalidade no caixa e planos validados (#64) |
| #89 | Relatórios: fuso da barbearia, faturamento do dia, ocupação e ranking dos ativos (#67) |
| #91 | Reenvio da verificação, administração de usuários, limite de login e token de redefinição único (#35) |
| #93 | Pagamentos geram pontos de fidelidade, e a tela usa a API (#13) |
| #94 | Migrações do Alembic com stamp da produção, e plano ilimitado (#6, #16) |

### Painel admin

| PR | O quê |
| :--- | :--- |
| #51 | Serviços: criar, editar, desativar e reativar (#49) |
| #100 | Usuários e senha temporária (#99) |
| #103 | Barbeiros: perfil, serviços, ativação e escala (#102) |
| #105 | Despesas com categorias (#104) |
| #107 | Galeria: envio de fotos, moderação no painel e filtro por tag na página pública (#106) |
| #109 | Trim Club: planos e assinantes no painel, assinatura na conta do cliente (#108) |
| #111 | Fidelidade: prêmios, carteiras com ajuste de pontos e resgates (#110) |
| #113 | Loja & Estoque: estoque dos produtos com histórico e movimentação (#112) |

### Conta do cliente

| PR | O quê |
| :--- | :--- |
| #50 | O formulário de perfil não apaga o que foi digitado ao abrir |
| #98 | Meus agendamentos, com cancelamento (#97) |

A assinatura do Trim Club na conta do cliente veio no #109 (painel admin, acima).

### Deploy e ambiente

| PR | O quê |
| :--- | :--- |
| #19 | Deploy no Render: `trim-db`, `trim-api` e `trim-web`, pelo [`render.yaml`](../render.yaml) (#4) |
| #28 | O backend sobe no console do Windows, com logging sem emojis (#2) |
| #80 | Vite com porta fixa e `strictPort` no dev e no preview (#11) |

### Processo e documentação

| PR | O quê |
| :--- | :--- |
| #1 | Organização da AP2: spec de processo, `AGENTS.md`, CI e sessões |
| #18 | Specs da AP1 (`SPEC/2026-09-29-*`) passam a ser somente leitura |
| #27, #32 | README da AP2 (blocos AP2 e AP1 por seção, #14) e como rodar no Windows (#2) |
| #55 | `CUSTOS.md` e `NOTAS.md` gerados por `scripts/custos.py` (#54) |
| #92 | Regrava `CUSTOS.md` e `NOTAS.md` depois dos merges do #60 e do #62 |
| #96, #101 | Registro das sessões de 25/11 |

## b) Rodar, testar e fazer deploy

### Rodar local

O passo a passo completo, para Linux e para Windows, está no
[`README.md`](../README.md#-como-rodar-o-projeto-localmente). Em resumo:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # preencha DATABASE_URL, SECRET_KEY e CORS_ORIGINS
python scripts/migrate.py          # aplica as migrações do Alembic
uvicorn src.backend.main:app --port 8001

cd src/frontend && npm ci
VITE_API_URL=http://localhost:8001/api npm run dev
```

Os dados de demonstração vêm de `POST /api/dev/seed`, que só existe com `SEED_SECRET` definida
(ver [`SPEC/2026-11-16-seed-seguro.md`](../SPEC/2026-11-16-seed-seguro.md)).

### Testar

```bash
# Backend: sem TEST_DATABASE_URL, os testes de banco são pulados
TEST_DATABASE_URL=postgresql+asyncpg://<usuário>:<senha>@localhost:5432/trim_test pytest -q

# Frontend
cd src/frontend && npm run typecheck && npm test && VITE_API_URL=http://x/api npm run build

# O mesmo que a CI confere sobre as sessões
python3 scripts/custos.py --check
```

A CI ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) roda em todo push e PR para a
`main`: backend (PostgreSQL 16, `pytest` com cobertura e `diff-cover` de 70% sobre o código
novo), frontend (typecheck, testes e build), `gitleaks`, trailers `Agent:`/`Spec:`,
`pip-audit`/`npm audit` e o relatório do `jscpd`.

### Deploy (Render)

O deploy é automático: cada merge na `main` dispara o deploy do `trim-api` e do `trim-web`
(Blueprint [`render.yaml`](../render.yaml)). O `trim-api` roda `python scripts/migrate.py` antes
do `uvicorn`, então as migrações novas entram junto com o deploy. Variáveis e URLs reais estão no
[`README.md`](../README.md#-deploy).

Para conferir que a versão no ar é a do último commit da `main`:

```bash
curl https://trim-api-ujwo.onrender.com/health
# {"status":"healthy","app":"Trim","version":"0.1.0","commit":"<sha>"}
git fetch origin && git rev-parse origin/main   # deve ser o mesmo <sha>
```

O `trim-web` lê a `VITE_API_URL` no build: depois de mudá-la no painel, faça um novo deploy dele.

## c) Rollback

### Reverter um PR

Nunca reescreva a `main` (`push --force` e `rebase` são proibidos pelo `AGENTS.md`). Reverta o
merge com um commit novo, numa branch e por PR, como qualquer mudança:

```bash
git switch main && git pull
git log --merges --oneline | grep '#<número do PR>'    # acha o commit de merge
git switch -c fix/revert-pr-<número>
git revert -m 1 <sha-do-merge>                         # -m 1: mantém o lado da main
git push -u origin fix/revert-pr-<número>              # e abra o PR, com a CI verde
```

Se o PR trouxe uma migração, volte o banco antes (abaixo): o código revertido não conhece mais a
coluna ou a tabela nova.

### Voltar uma migração

As migrações estão em `alembic/versions/` (`0001` → `0002` → `0003` → `0004`), todas com
`downgrade`. O `alembic/env.py` usa a `DATABASE_URL` do `.env` (ou do ambiente).

```bash
alembic current            # revisão atual do banco
alembic downgrade -1       # volta uma revisão
alembic downgrade 0003     # ou volta até uma revisão específica
```

Atenção: o `trim-api` roda `python scripts/migrate.py` (`upgrade head`) a cada início. Se o
arquivo da migração continuar na `main`, o próximo deploy ou reinício aplica a migração de novo.
Por isso, em produção, o downgrade vai junto com o revert do PR que trouxe a migração. Um
downgrade que remove uma coluna apaga os dados dela: faça um dump do banco antes
(`pg_dump "$DATABASE_URL" > backup.sql`, com a URL externa do `trim-db` no painel do Render).

### Voltar o deploy no Render

1. No painel do Render, abra o serviço (`trim-api` ou `trim-web`) → **Events** (ou **Deploys**).
2. No deploy anterior que estava bom, use **Rollback** e confirme.
3. Confira o commit no `/health` (só o `trim-api` mostra o commit).
4. Confira se o deploy automático continua ligado depois do rollback, e faça o revert do PR na
   `main` (acima): o próximo push na `main` publica de novo o que estiver nela.

O rollback do deploy não mexe no banco. Se a versão nova aplicou uma migração, a versão antiga
roda sobre o esquema novo até o downgrade.

## d) Custo

O custo de cada sessão com agente está em
[`prompts/sessoes/CUSTOS.md`](../prompts/sessoes/CUSTOS.md), e as observações de cada sessão em
[`prompts/sessoes/NOTAS.md`](../prompts/sessoes/NOTAS.md). Os dois são gerados por
`python scripts/custos.py` (não edite à mão).

Total registrado em 26/11/2026, nas 42 sessões do `CUSTOS.md`: **344.645.516 tokens**
(input 3.890; output 1.677.228; escrita de cache 3.148.328; leitura de cache 339.816.070).

## e) Problemas conhecidos e não corrigidos

- **`/admin` abre para qualquer conta logada.** A rota do painel no frontend só exige login. As
  abas novas conferem o perfil e o backend protege as rotas (um cliente recebe 403), mas a casca
  do painel aparece para qualquer conta.
- **Plano do Trim Club excluído não pode ser reativado pela tela.** O painel não tem como trazer
  de volta um plano excluído.
- **Pontos de fidelidade acima de 2^31 respondem 500.** A coluna de pontos é `Integer` no
  PostgreSQL; um valor acima de 2.147.483.647 estoura no banco e a API devolve 500 em vez de 422.
- **Um teste do Vitest é intermitente:** falhou 1 vez em 4 rodadas, no PR #113. Rodar de novo
  passa; a causa não foi investigada.
- **O commit `f0a494e` não compila sozinho.** As aspas da mensagem de nome repetido em
  `src/frontend/src/hooks/useAdminExpenses.test.ts` quebravam o arquivo. Foi corrigido no
  `68bf736`, no mesmo PR (#105). Num `git bisect`, pule o `f0a494e` (`git bisect skip`).

## f) Decisões

### Remoção dos `tests/test_*.py` gerados da AP1

A AP1 entregou 13 arquivos `tests/test_<módulo>.py` escritos por `tests/generate_tests.py`:
1.000 funções por módulo, cerca de 28 mil linhas por arquivo. Cada função copiava um dicionário
fixo e conferia o próprio dicionário (`assert payload is not None`,
`assert payload['scenario_id'] == i`). Nenhuma importava `src`, então apagar o corpo de qualquer
serviço do backend não quebrava nenhum teste. Esses arquivos também respondiam por quase toda a
duplicação medida pelo `jscpd`: 287.976 das 288.427 linhas duplicadas (#3,
[`SPEC/2026-11-21-testes-integracao-auth.md`](../SPEC/2026-11-21-testes-integracao-auth.md)).

O que os substituiu: um módulo por PR (#36, #38, #40, #58, #60, #62, #63, #66, #68, #70, #72,
#74, #76), testes de integração pela API (`httpx.AsyncClient` com a aplicação) sobre o
PostgreSQL de teste, no arquivo `tests/test_<módulo>_integracao.py`. Cada PR apagava o arquivo
gerado do módulo e o tirava da lista do gerador, para nenhum módulo ficar sem testes no meio do
caminho. Com a lista vazia, o #95 removeu o gerador e acrescentou um teste que falha se um
arquivo no padrão gerado ou o gerador voltarem
([`SPEC/2026-11-25-fim-dos-testes-gerados.md`](../SPEC/2026-11-25-fim-dos-testes-gerados.md)).
Por isso o `cloc` mostra 195.278 linhas de Python removidas e a duplicação caiu para 2,25%.

### "Recuperar senha" descartado, trocado pela senha temporária do admin

A redefinição por e-mail (`forgot-password` / `reset-password`) existe no backend, mas o envio é
simulado: a mensagem só vai para o log (`[MOCK EMAIL]`, sem o token desde o #31). Não há
provedor de e-mail configurado, então um "Esqueci a senha" na tela não chegaria a ninguém. Em vez
dele, o #100 ([`SPEC/2026-11-25-admin-usuarios.md`](../SPEC/2026-11-25-admin-usuarios.md)) criou
`POST /api/auth/users/{id}/temporary-password`: o admin gera uma senha temporária de 12
caracteres, mostrada uma vez só, que encerra as sessões do usuário e obriga a troca da senha no
próximo login (imposta pelo servidor, campo `must_change_password`, migração `0004`). Quando
houver um provedor de e-mail, a tela de "Esqueci a senha" pode usar as rotas que já existem.

## g) Segurança

- A falha encontrada no projeto herdado (#5: a rota de seed exposta em produção, protegida por um
  segredo escrito no código público, com as senhas de demonstração também no código) foi
  informada ao professor, e houve tentativa de contato com a dupla da AP1. No fork, ela foi
  corrigida no #17.
- **Recomendação:** gere um `SEED_SECRET` novo
  (`python -c "import secrets; print(secrets.token_urlsafe(32))"`) em qualquer ambiente que ainda
  use o antigo, porque ele foi exposto no histórico público. Defina a variável só durante o seed e
  apague-a depois (com ela vazia, as rotas `/api/dev/*` respondem 404). Troque também as senhas
  das contas de demonstração criadas com as senhas antigas.
- **O banco gratuito do Render expira em 30 dias.** Antes disso, mude de plano ou faça um dump
  (`pg_dump`). Depois de recriar o `trim-db`, o `trim-api` cria o esquema pelas migrações no
  início, e o seed precisa ser rodado de novo.

## h) Próximos passos

O backend destas duas áreas já está pronto e testado; falta a tela.

- **Comissões** (painel do admin e conta do barbeiro):
  - `GET /api/finance/commissions`: resumo das comissões pendentes por barbeiro;
  - `GET /api/finance/commissions/{barber_id}`: comissões de um barbeiro;
  - `GET /api/finance/commissions/me`: comissões do barbeiro logado;
  - `PUT /api/finance/commissions/pay`: marca comissões como pagas.
- **Fila walk-in** (recepção e TV):
  - `POST /api/queue`: entra na fila;
  - `GET /api/queue/live`: fila ao vivo (hoje só o `Dashboard.tsx` lê);
  - `PUT /api/queue/{id}/assign`: puxa para a cadeira;
  - `PUT /api/queue/{id}/cancel`: tira da fila.
- **Histórico dos ajustes de pontos:** o ajuste manual do admin
  (`POST /api/loyalty/wallet/{id}/add` e `/remove`) exige um motivo, mas o motivo só vai na
  notificação do cliente. Uma tabela própria (quem ajustou, quando, quanto e por quê) permite
  auditar as carteiras.
