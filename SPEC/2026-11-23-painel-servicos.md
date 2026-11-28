# Painel: tela de serviços com criar, editar, desativar e reativar (2026-11-23)

> Complementa: SPEC/2026-09-29-servicos.md (CRUD básico restrito a administradores) e
> SPEC/2026-11-22-servicos-validacao-reativacao.md (validações, `is_active` e `GET /api/services/admin`)
> Issue: #49

## O quê e por quê

A tela **Serviços** do painel (`/admin/servicos`, `src/frontend/src/pages/AdminServices.tsx`) só
lista os serviços ativos, pela listagem pública. Os botões "+ Novo Serviço", "Editar" e "Excluir"
não têm ação. Hoje o dono só consegue mexer no catálogo pela API (`curl` ou `/docs`), e os serviços
desativados nem aparecem.

O backend já tem tudo de que a tela precisa (#47): `GET /api/services/admin`, `POST`, `PUT` com
`is_active` e `DELETE`. Esta spec liga a tela a essas rotas.

Valor: o dono da barbearia cuida do catálogo sozinho, pelo painel, e consegue trazer de volta um
serviço que tirou do ar.

## Regras

**Listagem**

- Vem de `GET /api/services/admin`: ativos e desativados, na ordem do backend (alfabética).
- Colunas: serviço (com a descrição embaixo, quando houver), duração, preço em reais
  (`R$ 35,00`), situação ("Ativo" ou "Desativado") e ações.
- Um filtro "Mostrar desativados" vem marcado. Desmarcado, a tabela mostra só os ativos.
- Sem serviços, a tela mostra "Nenhum serviço cadastrado.". Na carga, "Carregando serviços...".
  Se a carga falhar, mostra a mensagem do erro e um botão "Tentar de novo".

**Formulário (criar e editar)**

- "+ Novo Serviço" abre o formulário vazio, com o título "Novo serviço". "Editar" abre o
  formulário com os dados do serviço, com o título "Editar serviço". Só um formulário fica aberto
  por vez.
- Campos: nome, descrição (opcional), preço em reais e duração em minutos.
- Validação antes de enviar, com as regras do backend:

| Campo | Regra | Mensagem |
|---|---|---|
| Nome | Sem espaços nas pontas, de 2 a 100 caracteres. | `Nome deve ter entre 2 e 100 caracteres` |
| Preço | Número de 0 a 99.999.999,99, com no máximo 2 casas. Aceita vírgula ou ponto como separador decimal. | `Preço deve ser um valor entre 0 e 99.999.999,99, com até 2 casas decimais` |
| Duração | Inteiro de 1 a 720. | `Duração deve ser um número inteiro de 1 a 720 minutos` |

- A criação envia os quatro campos, com a descrição vazia como `null`. A edição envia só o que
  mudou. Sem mudança, não chama o backend e mostra "Nada mudou.".
- Os erros 400 e 422 do backend aparecem no formulário em português (`apiErrorMessage`), e o
  formulário continua aberto com o que foi digitado. Isso inclui o nome repetido e o nome de um
  serviço desativado, cuja mensagem pede a reativação.
- Ao salvar, o formulário fecha, a lista passa a mostrar o serviço como o backend devolveu, e a
  tela mostra "Serviço criado." ou "Serviço atualizado.".
- "Cancelar" fecha o formulário sem enviar nada.

**Desativar e reativar**

- "Desativar" (o antigo "Excluir": o backend só faz o *soft delete*) pede confirmação na própria
  linha: "Desativar este serviço?" com "Confirmar" e "Voltar". Só "Confirmar" chama o
  `DELETE /api/services/{id}`. Depois, o serviço aparece como "Desativado" e a tela mostra
  "Serviço desativado.".
- Os desativados têm "Reativar" no lugar de "Desativar". Ele chama
  `PUT /api/services/{id}` com `{"is_active": true}`, sem confirmação. Depois, a tela mostra
  "Serviço reativado.".
- Enquanto uma ação está em andamento, os botões da linha ficam desabilitados, para não enviar
  duas vezes.
- Se a ação falhar, a mensagem do erro aparece no topo da tela, e o serviço fica como estava.

**Organização do código**

- `src/utils/serviceValidation.ts`: validação e conversão dos campos (preço em texto para o
  formato da API), sem React.
- `src/hooks/useAdminServices.ts`: carga e ações (criar, editar, desativar, reativar) sobre a API,
  mantendo a lista local em ordem alfabética.
- `src/components/services/ServiceForm.tsx` e `ServiceRow.tsx`: o formulário e a linha da tabela.
- `src/pages/AdminServices.tsx`: junta as peças.

## Critérios de aceitação

Testes no Vitest com o Testing Library, que falham com a tela de antes desta spec:

- [ ] A tela chama `GET /services/admin`, e não a listagem pública, e mostra ativos e
      desativados com a situação de cada um. O filtro esconde os desativados.
- [ ] "+ Novo Serviço" abre o formulário. Salvar envia `POST /services` com os campos no formato
      da API (preço "35,5" vira `"35.50"`, descrição vazia vira `null`), e o serviço entra na
      lista em ordem alfabética.
- [ ] Cada regra da tabela do formulário recusa o valor com a mensagem dela, sem chamar a API.
      Os limites (2 e 100 caracteres, 0 e 99.999.999,99, 1 e 720) são aceitos.
- [ ] "Editar" abre o formulário com os dados do serviço. Salvar envia `PUT /services/{id}` só
      com os campos alterados. Sem mudança, nada é enviado.
- [ ] O erro 400 do backend (nome repetido) aparece no formulário, que continua aberto com os
      valores digitados.
- [ ] "Desativar" só chama o `DELETE` depois de "Confirmar". "Voltar" não chama nada. Depois do
      `DELETE`, a linha mostra "Desativado" e o botão "Reativar".
- [ ] "Reativar" envia `PUT /services/{id}` com `{"is_active": true}`, e a linha volta a "Ativo".
- [ ] A falha numa ação mostra a mensagem do erro e mantém o serviço como estava. A falha na carga
      mostra o erro e "Tentar de novo", que carrega de novo.

## Decisões no lugar do cliente

A #49 perguntava se a tela de serviços deve também vincular e desvincular barbeiros. **Decisão:
não nesta tela.** O vínculo fica para a tela de barbeiros, que é refeita na #37 (admin de
barbeiros). Aqui, o formulário cuida só dos dados do serviço. Se o cliente pedir, a seção de
barbeiros entra como uma issue própria, sem mexer nesta spec.

## Fora do escopo

- Vincular e desvincular barbeiros (ver acima).
- Ordenar ou buscar na tabela, e paginação: o catálogo de uma barbearia tem poucas dezenas de
  serviços.
- Imagem do serviço: o modelo não tem esse campo.
