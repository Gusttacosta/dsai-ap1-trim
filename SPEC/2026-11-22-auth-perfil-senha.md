# Perfil do usuário e troca de senha (2026-11-22)

> Complementa: SPEC/2026-09-29-autenticacao.md (rotas `PUT /api/auth/me` e
> `PUT /api/auth/me/password`, regra 2 e o critério "alteração de senha exige confirmação da senha
> atual") e SPEC/2026-11-22-auth-refresh-logout.md (sessões no servidor)
> Issue: #35

## O quê e por quê

A spec da AP1 prevê duas rotas que não existem (#35):

- `PUT /api/auth/me`, para a pessoa atualizar o próprio nome, telefone e foto;
- `PUT /api/auth/me/password`, para ela trocar a senha informando a atual.

Os schemas `UserUpdateRequest` e `PasswordChangeRequest` existem, mas nenhuma rota os usa. Hoje, quem
errou o nome no cadastro não tem como corrigir. Quem quer trocar a senha precisa pedir a
redefinição por e-mail, que ainda nem é enviado (#30). No frontend também não existe nenhuma tela
de conta.

Há ainda duas falhas de validação ligadas a esses campos:

- **O telefone não é validado.** A spec da AP1 pede "formato brasileiro", mas o cadastro aceita
  qualquer texto. Um telefone com mais de 20 caracteres estoura a coluna (`String(20)`) e o
  cadastro responde 500.
- **O nome não tem limite de tamanho.** Um nome com mais de 255 caracteres também dá 500.

Solução:

1. Criar as duas rotas.
2. Validar o telefone e o tamanho do nome nos schemas, no cadastro e no perfil.
3. Criar a página "Minha conta" no frontend, para o cliente e para o painel do admin e do barbeiro.

Valor: a pessoa corrige os próprios dados e troca a senha sem depender de e-mail, e quem desconfia
que a senha vazou encerra as outras sessões ao trocá-la.

## Regras

**Perfil (`PUT /api/auth/me`, autenticado):**

- A atualização é parcial: só os campos enviados mudam. Um corpo vazio (`{}`) responde 200 sem
  alterar nada.
- Só são aceitos `full_name`, `phone` e `avatar_url`. Qualquer outro campo, como `email`, `role` ou
  `is_active`, responde 422. A pessoa não pode se promover nem trocar o e-mail por essa rota.
- **`full_name`:** os espaços das pontas saem, e o nome precisa ter entre 2 e 255 caracteres.
  `null` responde 422, porque o nome é obrigatório.
- **`phone`:** `null` ou texto vazio apaga o telefone. Fora isso, o telefone tem que ser
  brasileiro, com DDD:
  - aceita dígitos, espaços, parênteses, hífen e o prefixo opcional `+55`;
  - sem o `+55`, sobram 10 dígitos (fixo) ou 11 dígitos (celular);
  - o DDD não começa com 0;
  - o celular começa com 9 depois do DDD.

  O telefone é gravado no formato `(91) 99999-0000` ou `(91) 3333-0000`, não importa como foi
  digitado. O cadastro passa a usar a mesma regra.
- **`avatar_url`:** `null` ou texto vazio apaga a foto. Fora isso, a URL precisa ser `http` ou
  `https`, ter um host e ter no máximo 2.048 caracteres.
- A resposta é o usuário atualizado, no formato do `GET /me`, e o `updated_at` avança.

**Troca de senha (`PUT /api/auth/me/password`, autenticado):**

- **Senha atual errada:** responde 400 com "Senha atual incorreta.". O código é 400, e não 401,
  porque um 401 faria o frontend tentar o refresh e repetir o pedido.
- **Senha nova igual à atual:** responde 400.
- A senha nova segue a regra 2 da AP1: no mínimo 8 caracteres, com pelo menos uma letra e um
  número. Fora disso, responde 422.
- Com sucesso, o hash bcrypt é trocado, e todas as outras sessões do usuário são revogadas. A
  sessão do cookie de quem fez a troca, se houver, continua valendo. Os tokens de redefinição de
  senha ainda não usados são invalidados.
- O login com a senha antiga passa a responder 401, e o login com a nova funciona.

**Refatoração localizada:** as três cópias da validação de senha forte em `schemas.py` (cadastro,
troca e redefinição) passam a chamar uma função só, junto com as validações novas de telefone e
nome. As mensagens de erro continuam as mesmas, e os testes atuais do cadastro e da redefinição
cobrem essa troca.

## Critérios de aceitação

Backend, com testes de integração em `tests/test_auth_perfil.py`:

- [ ] `PUT /me` altera só os campos enviados, devolve o usuário atualizado e grava no banco. O
      `{}` não muda nada.
- [ ] O nome é gravado sem os espaços das pontas. Nome com menos de 2 ou mais de 255 caracteres, ou
      `null`, responde 422.
- [ ] Os telefones válidos são normalizados (com e sem máscara, com `+55`, fixo e celular). `null`
      e texto vazio apagam o telefone. DDD com 0, quantidade errada de dígitos, letras e celular de
      11 dígitos sem o 9 respondem 422.
- [ ] O cadastro normaliza e valida o telefone com a mesma regra, e nome acima de 255 caracteres
      responde 422 em vez de 500.
- [ ] A URL da foto aceita `http` e `https`. Outros esquemas, URL sem host e URL acima de 2.048
      caracteres respondem 422. `null` e texto vazio apagam a foto.
- [ ] Campos fora da lista (`email`, `role`, `is_active`) respondem 422, e nada muda.
- [ ] Sem token, as duas rotas respondem 403, e com token inválido respondem 401, como o `GET /me`.
- [ ] A troca de senha com a senha atual certa responde 200. Depois dela, o login com a senha antiga
      falha e com a nova funciona.
- [ ] Senha atual errada e senha nova igual à atual respondem 400, e senha nova fraca responde 422.
      Nos três casos, a senha não muda.
- [ ] A troca revoga as outras sessões e mantém a do cookie de quem trocou. Sem cookie, revoga
      todas.
- [ ] A troca invalida os tokens de redefinição de senha pendentes.

Frontend:

- [ ] Página "Minha conta" em `/conta`, para o cliente, e em `/admin/conta`, no painel. Ela tem um
      formulário de perfil (nome, telefone e URL da foto) e um de troca de senha (atual, nova e
      confirmação).
- [ ] A página valida os campos antes de enviar, com as mesmas regras do backend, e mostra os erros
      do backend (400 e a lista do 422) em português.
- [ ] Depois de salvar, a página mostra os dados como o backend devolveu, com o telefone
      normalizado. A troca de senha limpa os campos e confirma que as outras sessões foram
      encerradas.
- [ ] A barra do cliente e o menu do painel ganham o link "Minha conta".
- [ ] Testes no Vitest cobrem as funções de validação e os dois formulários, com o React Testing
      Library e o jsdom.

## Fora do escopo

- Troca de e-mail, que exigiria verificar o endereço novo.
- Upload de foto: o campo continua sendo uma URL.
- Revogar os access tokens já emitidos na troca de senha. Eles são stateless e vencem sozinhos (em
  30 minutos para o cliente e em 12 horas para a equipe).
- Rate limiting das tentativas de senha atual, que vai junto com o rate limiting do login, em outro
  grupo da #35.
- Validar ou normalizar os telefones já gravados no banco.
