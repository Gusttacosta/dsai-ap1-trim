# Serviços: validação dos campos, reativação e vínculo só com ativos (2026-11-22)

> Complementa: SPEC/2026-09-29-servicos.md (regra 1, soft delete, e o CRUD do admin)
> Issue: #39 (itens 1 a 4; o item 5 fica para a #37, no módulo `barbers`)

## O quê e por quê

Os testes de integração do catálogo (#3) acharam estes problemas (#39):

1. **`null` explícito dá 500.** `PUT /api/services/{id}` com `{"name": null}`, `{"price": null}`
   ou `{"duration_minutes": null}` passa na validação e grava `None` numa coluna `NOT NULL`.
2. **Valores fora da coluna dão 500.** O preço acima de 99.999.999,99 estoura o `Numeric(10, 2)`,
   e a duração acima de 2.147.483.647 estoura o `Integer`. Os dois respondem 500, na criação e na
   alteração.
3. **Nome vazio é aceito**, e o nome não é limpo dos espaços. Também é possível ter "Corte" e
   "corte" como serviços diferentes.
4. **Não há como reativar.** O `DELETE` só desativa, e nenhuma rota faz o serviço voltar. Como o
   nome continua único, também não é possível criar outro serviço com o mesmo nome. Para piorar, o
   admin não tem como ver os serviços desativados: a listagem é a pública, que só traz os ativos.
5. **Vínculo com inativo é aceito.** Dá para vincular um serviço desativado ou um barbeiro
   desativado. Nenhum dos dois aparece para o cliente, então o vínculo não serve para nada.

Valor: o admin recebe um erro claro (422 ou 400) no lugar de um 500, consegue trazer de volta um
serviço que tirou do catálogo e não cria vínculos que ninguém vê.

## Regras

**Campos (criação e alteração):**

| Campo | Regra | `null` na alteração |
|---|---|---|
| `name` | Sem espaços nas pontas, de 2 a 100 caracteres. | 422 |
| `description` | Livre. | Apaga a descrição, como hoje. |
| `price` | De 0 a 99.999.999,99, arredondado para 2 casas, como hoje. | 422 |
| `duration_minutes` | Inteiro de 1 a 720 minutos (12 horas, um dia inteiro de trabalho). | 422 |
| `is_active` | Só na alteração. `true` reativa o serviço e `false` o desativa, como o `DELETE`. | 422 |

- **Nome único, sem diferenciar maiúsculas:** "Corte" e "corte" são o mesmo serviço, nos ativos e
  nos desativados. Trocar só a caixa do próprio nome ("corte" para "Corte") é permitido.
- **Nome de um serviço desativado:** a criação com esse nome continua respondendo 400. A mensagem
  passa a dizer que o serviço está desativado e que basta reativá-lo:
  `Já existe um serviço desativado com o nome 'Corte'. Reative-o em vez de criar outro.`

**Listagem do admin:** `GET /api/services/admin` (só admin) lista todos os serviços, ativos e
desativados, em ordem alfabética e com o `is_active`. A listagem pública continua igual.

**Vínculo com barbeiro** (`POST /api/services/{id}/barbers/{barber_id}`):

- Serviço desativado responde 400 com `Serviço desativado não pode receber barbeiros.`.
- Barbeiro desativado (perfil `Barber` ou conta `User` inativos) responde 400 com
  `Barbeiro desativado não pode ser vinculado.`.
- Serviço ou barbeiro inexistentes e vínculo repetido continuam respondendo 400 com a mensagem
  atual.
- O desvínculo continua liberado para qualquer situação.

## Critérios de aceitação

Testes em `tests/test_services_validacao.py`, que falham com o código de antes desta spec:

- [ ] `null` em `name`, `price`, `duration_minutes` e `is_active` na alteração responde 422, e o
      serviço não muda. `description: null` continua apagando a descrição.
- [ ] Preço acima de 99.999.999,99 e duração acima de 720 respondem 422 na criação e na alteração,
      e nada é gravado. 99.999.999,99 e 720 são aceitos.
- [ ] Nome vazio, só com espaços ou com 1 caractere responde 422. O nome é gravado sem os espaços
      das pontas.
- [ ] Criar "corte" com "Corte" já cadastrado responde 400, e o mesmo vale para renomear outro
      serviço para "CORTE". Mudar só a caixa do próprio nome é aceito.
- [ ] Criar com o nome de um serviço desativado responde 400 com a mensagem de reativação.
- [ ] `PUT` com `is_active: true` reativa o serviço, que volta para a listagem pública, para os
      detalhes e para os serviços do barbeiro, com os vínculos antigos. `is_active: false`
      desativa.
- [ ] `GET /api/services/admin` traz os ativos e os desativados, em ordem alfabética. Sem token,
      cliente e barbeiro recebem 403.
- [ ] Vincular serviço desativado, barbeiro desativado ou barbeiro com a conta desativada responde
      400 com a mensagem própria, sem criar o vínculo.

## Fora do escopo

- Os serviços habilitados no `GET /api/barbers/{id}` (item 5 da #39). Esse ponto vai para a #37,
  que já mexe no módulo `barbers`.
- Desfazer vínculos quando um serviço ou um barbeiro é desativado. Os vínculos são mantidos para
  que a reativação os traga de volta.
- A tela de serviços do painel, cujos botões "Novo Serviço", "Editar" e "Excluir" ainda não fazem
  nada. Ela terá uma issue própria.
