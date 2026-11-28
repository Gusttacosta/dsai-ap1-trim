# Dependências do backend sem alertas high, e pip-audit falhando a partir de high (2026-11-25)

> Complementa: SPEC/2026-11-24-frontend-tipos-e-dependencias.md (o mesmo limite no npm audit, #8)
> Issue: #77

## O quê e por quê

O job "Dependências" da CI passa porque o pip-audit só falha em alertas `critical`. Com isso,
o `requirements.txt` da `main` tem 15 alertas, 6 deles high:
- 3 no python-multipart 0.0.20;
- 3 no starlette 0.46.2, que vem do fastapi 0.115.12;
- medium no pytest 8.4.1 e no python-dotenv 1.1.0.

Hoje o backend não usa upload, formulários nem arquivos estáticos, então a maior parte desses
alertas não é alcançável. Mesmo assim, as dependências precisam ficar em dia antes de alguém
usar esses recursos, e a CI precisa avisar quando um alerta high voltar.

## Decisões

| Pacote | De | Para | Motivo |
|---|---|---|---|
| fastapi | 0.115.12 | 0.165.0 | aceita o starlette corrigido |
| starlette | (via fastapi) 0.46.2 | 1.10.0, fixado | os 7 alertas, high e outros, do starlette |
| python-multipart | 0.0.20 | 0.0.34 | os 6 alertas |
| python-dotenv | 1.1.0 | 1.2.4 | GHSA-mf9w-mj56-hr94 |
| pytest | 8.4.1 | 9.2.0 | GHSA-6w46-j5rx-g56g |
| pytest-asyncio | 0.26.0 | 1.5.0 | o 0.26 não aceita o pytest 9 |

Os testes usam `@pytest.mark.asyncio` e `pytest_asyncio.fixture`, sem o fixture `event_loop`
nem o `asyncio_mode`. Por isso o pytest-asyncio 1.x não pede mudança nos testes.

## Critérios de aceitação

- [ ] O `pip-audit -r requirements.txt` da CI não tem alerta high nem critical.
- [ ] O job passa a **falhar a partir de high**, como o `npm audit` desde o #8. Esse é o teste
  da mudança: com as versões antigas, o job falha.
- [ ] A suíte inteira passa com as versões novas, na CI (PostgreSQL) e localmente. Localmente,
  sem `TEST_DATABASE_URL`, passaram 8.050 testes, e 595 foram pulados.
