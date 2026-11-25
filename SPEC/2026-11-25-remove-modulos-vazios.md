# Remove os módulos vazios clients, landing e queue (2026-11-25)

> Issue: #9

## O quê e por quê

`src/backend/modules/clients`, `landing` e `queue` têm só um `__init__.py` com uma docstring.
Nenhum código os importa, e eles não têm rota.
- **queue:** a fila de walk-in fica no módulo `walkin`, exposto em `/api/queue`. Um pacote
  `queue` vazio leva quem lê a procurar a fila no lugar errado. Além disso, o nome coincide com o
  módulo `queue` da biblioteca padrão.
- **clients:** os clientes são os `User` com `role=client`, no módulo `auth`. Não existe CRM
  separado, e nenhuma spec da AP1 nem da AP2 o descreve.
- **landing:** a landing page é uma página do frontend (`src/frontend/src/pages/Landing.tsx`)
  e usa as rotas públicas dos outros módulos.

A pergunta da #9 ao cliente era se havia um plano para eles. Nenhuma spec, issue ou tela depende
desses módulos, então a decisão é removê-los. Se um CRM ou uma landing com conteúdo editável
vierem a ser pedidos, eles entram com uma spec própria.

## Critérios de aceitação

- [ ] Os três pacotes saem do repositório.
- [ ] Um teste confere que **todo pacote em `src/backend/modules` tem um `router.py` registrado no
  `main.py`**. Assim, um módulo vazio ou esquecido volta a quebrar a CI. Esse teste falha com os
  três pacotes de volta.
- [ ] A suíte e a aplicação continuam subindo (nenhum import quebra).
