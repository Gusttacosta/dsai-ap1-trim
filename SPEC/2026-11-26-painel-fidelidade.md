# Fidelidade no painel: prêmios, carteiras com ajuste de pontos e resgates (2026-11-26)

> Complementa: SPEC/2026-11-25-fidelidade-correcoes.md (#73: as rotas do admin, que ganham o
> motivo do ajuste) e SPEC/2026-11-25-fidelidade-pontos.md (#13)
> Issue: #110

## O quê e por quê

O backend da fidelidade está pronto (#13, #73), mas o painel não tem aba para ele. O admin cria e
altera prêmios chamando a API à mão, não vê as carteiras nem o histórico de resgates. E o ajuste
manual de pontos não diz **por quê**: a notificação do crédito diz só "+N pts da barbearia", e o
débito tira pontos do cliente sem avisar.

| Ação | Rota | Quem |
|---|---|---|
| Prêmios (lista) | `GET /api/loyalty/rewards` (só os ativos, do mais barato ao mais caro) | admin, nesta tela |
| Criar prêmio | `POST /api/loyalty/rewards` | admin |
| Editar e desativar prêmio | `PUT /api/loyalty/rewards/{id}` | admin |
| Carteiras | `GET /api/loyalty/wallets` (do maior saldo ao menor) | admin |
| Adicionar pontos | `POST /api/loyalty/wallet/{user_id}/add?points=N&reason=...` | admin |
| Retirar pontos | `POST /api/loyalty/wallet/{user_id}/remove?points=N&reason=...` | admin |
| Resgates | `GET /api/loyalty/redemptions` (o mais novo primeiro) | admin |

Valor: o dono monta o catálogo, corrige um lançamento errado com o motivo registrado, e o cliente
sabe por que o saldo mudou.

## Backend: o motivo do ajuste

- `reason` passa a ser **obrigatório** no `/add` e no `/remove`, na query, como o `points`:
  aparado, de 3 a 200 caracteres. Sem ele, ou fora do tamanho, a rota responde **422**, e nada
  muda (nem carteira, nem notificação).
- O motivo vai na notificação `loyalty_update` do cliente:
  - `/add`: "Você ganhou pontos", `+50 pts da barbearia: Aniversário. Saldo: 170 pts.`;
  - `/remove`, que antes não notificava: "Pontos retirados",
    `-50 pts: Lançamento em dobro. Saldo: 70 pts.`.
- A notificação entra no mesmo commit do ajuste; o débito recusado (saldo insuficiente) não
  notifica.
- O resto das regras da #73 continua: pontos ≤ 0 respondem 400, usuário desconhecido 404, e as
  rotas são só do admin (403).

## Regras da tela (`/admin/fidelidade`)

### Menu e acesso

- O item "Fidelidade" e a rota aparecem só para o **admin**, como Trim Club. O barbeiro e o
  cliente não veem o item nem a tela, e nada chama `/loyalty/wallets`.

### Prêmios

- Tabela com nome (e descrição), custo (`120 pts`) e ações, na ordem do backend (custo
  crescente). Vazio: "Nenhum prêmio cadastrado.".
- "+ Novo prêmio" e "Editar" abrem o formulário (`AdminForm`):
  - nome, de 1 a 150 caracteres sem contar os espaços das pontas:
    `Nome do prêmio deve ter entre 1 e 150 caracteres`;
  - descrição (opcional), aparada, até 500 caracteres; vazia vai como `null`:
    `Descrição deve ter até 500 caracteres`;
  - custo, inteiro de 1 a 1.000.000 pontos: `Custo deve ser um número inteiro de 1 a 1.000.000 pontos`.
- Tudo é conferido antes da API. A edição manda só os campos que mudaram ("Nada mudou." quando
  nenhum mudou). O erro da API (nome repetido, 400, ou a lista do 422) aparece no formulário.
- "Desativar" pede confirmação na linha ("Desativar o prêmio? Ele sai do catálogo, e os resgates
  feitos continuam no histórico."), manda `PUT {is_active: false}` e tira o prêmio da lista. A
  falha mostra a mensagem da API e o prêmio continua.

### Carteiras

- Tabela com cliente (nome e e-mail), saldo (`120 pts`), total acumulado e ações, na ordem do
  backend. Vazio: "Nenhuma carteira ainda.".
- "Ajustar pontos" abre o formulário do ajuste (`AdminForm`) para aquele cliente:
  - operação: "Adicionar" ou "Retirar";
  - pontos, inteiro de 1 a 1.000.000: `Pontos devem ser um número inteiro de 1 a 1.000.000`;
  - motivo, de 3 a 200 caracteres sem contar os espaços das pontas:
    `O motivo deve ter entre 3 e 200 caracteres`.
- Com os campos válidos, o formulário **pede confirmação** antes da API, com a pergunta
  "Adicionar 50 pts a Ana Lima? O saldo passa de 120 para 170 pts. Motivo: Aniversário." (ou
  "Retirar ..."), e os botões "Confirmar" e "Voltar". "Voltar", ou mudar um campo, volta ao
  formulário sem chamar a API.
- "Confirmar" chama a rota com `points` e `reason` (aparado), põe na linha o saldo que o backend
  devolveu (reordenando do maior ao menor) e mostra "Pontos adicionados." ou "Pontos retirados.".
  O erro da API (saldo insuficiente, 400) aparece no formulário, e o saldo da linha continua.
- Carregando, erro com a mensagem da API e "Tentar de novo".

### Resgates

- Tabela com a data e a hora no fuso da barbearia (`qui., 26/11/2026 às 14:30`, como em Meus
  agendamentos), o cliente (nome da lista de carteiras, ou
  "Cliente não encontrado"), o prêmio e os pontos gastos, na ordem do backend. Vazio:
  "Nenhum resgate ainda.". Só de leitura.

### Reaproveitamento (jscpd ≤ 5%)

- Carga e ações: `useApiResource`, `useRowAction` e o `upsert` da lista de nomes; tela:
  `LoadState`, `ActionFeedback`, `ConfirmButton`, `AdminForm`, `FormField` e
  `AdminShared.module.css`.
- A confirmação do ajuste é do `AdminForm` (uma pergunta opcional antes de salvar), para outros
  formulários usarem; sem a pergunta, ele continua salvando direto.
- O número inteiro de pontos (custo e ajuste) usa a mesma validação.
- A linha de prêmio e a de plano do Trim Club são iguais (nome com descrição, valores, "Editar" e
  a ação confirmada): viram um componente de linha de catálogo usado pelas duas.

## Critérios de aceitação

Backend (pytest, com o PostgreSQL de `TEST_DATABASE_URL`):

- [ ] `/add` e `/remove` sem `reason`, com `reason` de 2 caracteres (depois de aparar) ou de 201
      respondem 422, sem mudar a carteira nem criar notificação.
- [ ] O `/add` com motivo notifica `+N pts da barbearia: <motivo>. Saldo: X pts.`; o `/remove`
      notifica "Pontos retirados" com o motivo; o débito recusado não notifica.

Frontend (vitest, com a API simulada), que falham se a tela for desfeita:

- [ ] O admin vê "Fidelidade" no menu e a tela em `/admin/fidelidade`; o barbeiro e o cliente
      não, e nenhum dos dois chama `/loyalty/wallets`.
- [ ] Criar manda nome, descrição e custo no formato da API e põe o prêmio na lista, na ordem de
      custo; editar manda só o que mudou e atualiza a linha.
- [ ] Nome vazio ou longo, descrição longa e custo zero, fracionário ou acima do limite são
      recusados na tela, sem chamada. O 400 e o 422 da API aparecem no formulário.
- [ ] Desativar pede confirmação, manda `is_active: false` e tira o prêmio; a falha mostra a
      mensagem da API e o prêmio continua.
- [ ] O ajuste sem motivo ou com pontos inválidos é recusado sem chamada; o válido mostra a
      pergunta, e só "Confirmar" chama `/add` ou `/remove` com `points` e `reason`; o saldo novo
      aparece na linha. "Voltar" não chama a API. O 400 do saldo insuficiente aparece e o saldo
      continua.
- [ ] O histórico mostra a data, o nome do cliente, o prêmio e os pontos; a falha na carga mostra
      a mensagem e "Tentar de novo".

## Fora do escopo

- Guardar os ajustes numa tabela própria e mostrar o histórico deles: o motivo fica na
  notificação do cliente.
- Listar e reativar prêmios desativados: o `GET /rewards` só devolve os ativos.
- Ajustar os pontos de quem ainda não tem carteira: a lista só tem as carteiras que existem (a
  carteira nasce no primeiro acesso a `/fidelidade` ou no primeiro pagamento).
- O limite de 1.000.000 pontos é só da tela: o backend não tem teto (a coluna é `Integer`).
- Filtros, busca e paginação das carteiras e dos resgates.
