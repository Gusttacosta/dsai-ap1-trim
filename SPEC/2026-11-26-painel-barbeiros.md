# Painel do admin: barbeiros, serviços e escala (2026-11-26)

> Complementa: SPEC/2026-11-23-barbeiros-admin-escala.md (as rotas que esta tela usa) e
> SPEC/2026-11-23-painel-servicos.md (o vínculo de serviços que ficou para a tela de barbeiros)
> Issue: #102

## O quê e por quê

O backend já lista, cria, altera, desativa e reativa barbeiros, e grava a escala da semana com o
almoço (#37). Nenhuma tela usa essas rotas: o dono chama a API à mão. O vínculo de serviços, que a
tela de serviços deixou de fora, também não tem tela.

Esta spec entrega a aba **"Barbeiros"** no painel do admin (`/admin/barbeiros`), só no frontend,
sobre as rotas que já existem:

| Ação | Rota |
|---|---|
| Lista | `GET /api/barbers/admin` |
| Criar o perfil de um usuário | `POST /api/barbers` |
| Editar bio, Instagram e comissão; desativar e reativar | `PUT /api/barbers/{id}` |
| Serviços do barbeiro | `GET /api/services/barber/{id}`, `POST` e `DELETE /api/services/{id}/barbers/{barber_id}` |
| Catálogo para escolher | `GET /api/services/admin` (só os ativos aparecem) |
| Escala | `GET` e `PUT /api/barbers/{id}/schedule` |
| Busca do usuário | `GET /api/auth/users` (a mesma busca da aba Usuários) |

Valor: o dono monta e mantém a equipe pelo painel, sem mexer no banco.

## Regras da tela

### Menu e acesso

- O item "Barbeiros" e a rota aparecem só para o admin, como as outras abas de gestão.

### Lista

- Todos os barbeiros, na ordem do backend (alfabética do nome), com nome, e-mail, comissão
  (`50,00%`) e a situação: "Ativo" ou "Desativado" (perfil). Se a conta do usuário estiver
  desativada, a linha avisa "Conta desativada".
- Carregando, erro com a mensagem da API e "Tentar de novo", e "Nenhum barbeiro cadastrado."
- Ações de cada linha: "Editar", "Escala" e "Desativar" (pede confirmação na linha) ou
  "Reativar" (não pede).
- A recusa da desativação por agendamentos futuros (400 do backend) aparece no topo da tela, e
  o barbeiro continua ativo na lista.

### Novo barbeiro

1. Busca do usuário por nome ou e-mail, com o mesmo componente e a mesma paginação da aba
   Usuários (sem o filtro de perfil).
2. Usuário que já tem perfil de barbeiro aparece como "Já é barbeiro", sem o botão "Escolher".
3. Depois de escolher, o formulário pede comissão (obrigatória, padrão `50`), bio, Instagram e
   os serviços. O usuário escolhido aparece no topo do formulário, com "Trocar".
4. Ao salvar: `POST /api/barbers`, depois um `POST` de vínculo por serviço marcado, e a lista é
   carregada de novo (o backend promove o cliente a barbeiro e cria a escala padrão).

### Editar

- O mesmo formulário, com os dados do barbeiro e os serviços dele já marcados.
- Só os campos alterados vão no `PUT /api/barbers/{id}`. Apagar a bio ou o Instagram manda
  `null`. Sem mudança nenhuma (nem de serviços), o formulário diz "Nada mudou." sem chamar a API.
- Serviços marcados viram `POST` de vínculo; desmarcados, `DELETE`.

### Validação do formulário (antes da API, com as regras do backend)

- Comissão: número de 0 a 100, com até 2 casas, vírgula ou ponto.
  `Comissão deve ser um valor entre 0 e 100, com até 2 casas decimais`
- Bio: até 500 caracteres. `A bio deve ter até 500 caracteres`
- Instagram: vazio, ou um endereço começando com `http://` ou `https://`.
  `Informe o endereço completo do Instagram, começando com https://`
- O erro da API (por exemplo, vínculo recusado para barbeiro desativado) aparece no formulário.

### Escala

- "Escala" abre o editor da semana, de domingo a sábado, com: "Trabalha", início, fim, início e
  fim do almoço (campos de hora). Sem "Trabalha", os horários do dia ficam desabilitados, mas
  são enviados como estão.
- Salvar manda os 7 dias de uma vez (`PUT /api/barbers/{id}/schedule`) e mostra a semana gravada.
- Antes da API, cada dia é conferido com as mesmas regras e mensagens do backend, e o erro diz o
  dia (`Terça: O almoço deve ficar dentro do expediente.`):
  - `O horário de término deve ser após o início.`
  - `Informe o início e o fim do almoço, ou nenhum dos dois.`
  - `O fim do almoço deve ser após o início do almoço.`
  - `O almoço deve ficar dentro do expediente.`
- Erro da carga ou da gravação mostra a mensagem da API.

### Reaproveitamento (jscpd ≤ 5%)

- Carga e ações: `useApiResource` e `useRowAction`; tela: `LoadState`, `ActionFeedback`,
  `ConfirmButton`, `Pagination` e `UserFilters` (o filtro de perfil passa a ser opcional).
- O selo "Ativo"/"Desativado", repetido nas linhas de serviços e de usuários, vira o componente
  `StatusBadge`, usado também na linha de barbeiro.
- A moldura do formulário do painel (título, erro, "Nada mudou.", "Salvando...", "Cancelar") vira
  o componente `AdminForm`, usado pelo formulário de serviço e pelo de barbeiro.

## Critérios de aceitação

Testes vitest (com a API simulada) que falham se a tela for desfeita:

- [ ] O admin vê "Barbeiros" no menu e a tela em `/admin/barbeiros`; o barbeiro não vê nenhum
      dos dois.
- [ ] A lista usa `GET /api/barbers/admin` e mostra comissão, situação e a conta desativada. A
      falha da carga mostra a mensagem da API e "Tentar de novo" carrega de novo.
- [ ] Novo barbeiro: a busca chama `/auth/users` com o texto; quem já é barbeiro não pode ser
      escolhido; salvar manda `user_id` e a comissão, vincula os serviços marcados e recarrega a
      lista. Erro da API aparece no formulário.
- [ ] Editar manda só o que mudou, `null` para bio e Instagram apagados, e vincula e desvincula os
      serviços pela diferença. Sem mudança, "Nada mudou." sem chamada.
- [ ] Comissão, bio e Instagram inválidos são recusados na tela, sem chamada.
- [ ] Desativar pede confirmação e manda `is_active: false`; a recusa do backend aparece e o
      barbeiro continua ativo. Reativar manda `is_active: true`.
- [ ] A escala carrega os 7 dias, grava a semana inteira e recusa, na tela e sem chamada, almoço
      incompleto, almoço fora do expediente e término antes do início, com o nome do dia.
- [ ] O formulário de serviço continua passando nos testes dele depois de usar o `AdminForm`.

## Fora do escopo

- Backend: nenhuma rota nova ou alterada.
- Foto (avatar) do barbeiro, folgas e feriados.
- Ver ou remanejar os agendamentos futuros que impedem a desativação.
- Desativar a conta do usuário (fica na aba Usuários).
