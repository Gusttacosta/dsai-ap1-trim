# Painel do admin: usuários e senha temporária (2026-11-25)

> Complementa: SPEC/2026-11-25-auth-admin-usuarios.md e SPEC/2026-11-22-auth-perfil-senha.md
> Issue: #99

## O quê e por quê

O backend já lista usuários, muda o perfil e ativa ou desativa contas (#35), mas nenhuma tela usa
essas rotas: o admin precisa chamar a API à mão ou mexer no banco. E quem esquece a senha não
tem saída, porque a redefinição por e-mail depende de um envio que ainda não existe.

Este PR entrega:
1. a aba **"Usuários"** no painel do admin (`/admin/usuarios`);
2. a rota **`POST /api/auth/users/{id}/temporary-password`**, que gera uma senha temporária;
3. a **troca obrigatória** da senha temporária no primeiro login com ela.

## Decisões

- **Geração:** 12 caracteres de letras e dígitos, com `secrets.choice`, com pelo menos uma letra e
  um dígito (passa na regra de senha forte). Só o hash vai para o banco.
- **Uma vez só:** a senha aparece só na resposta da rota, com `Cache-Control: no-store`. Nenhum
  `logger` recebe a senha. Gerar de novo cria outra e invalida a anterior.
- **Efeitos de gerar:** as sessões do usuário são encerradas (os refresh tokens são revogados) e
  os links de redefinição pendentes deixam de valer, como na troca de senha.
- **Campo novo `users.must_change_password`** (booleano, padrão `false`, migração `0004` com
  downgrade). Aparece no `UserResponse`.
- **Troca obrigatória no servidor, não só na tela:** com o campo ligado, o `get_current_user`
  responde **403** `Troque a senha temporária para continuar.` em todas as rotas, menos
  `GET /api/auth/me` e `PUT /api/auth/me/password`. O login, o refresh e o logout continuam
  funcionando. A troca de senha (`PUT /me/password`) e a redefinição por token desligam o campo.
- **Limites da rota:** só o admin (403 para os outros); id desconhecido 404; o próprio admin 400
  (`Você não pode gerar uma senha temporária para a sua própria conta.`), porque ele tem a troca
  de senha da própria conta; conta desativada 400 (`Ative a conta antes de gerar uma senha
  temporária.`), porque ela não conseguiria entrar.
- **Frontend reaproveitado:**
  - `ConfirmButton` para desativar e para gerar a senha;
  - `PasswordForm` na tela de troca obrigatória;
  - `useApiResource` para a carga da lista;
  - `AdminShared.module.css` e o CSS de `components/account`.
  O painel de serviços e o de usuários repetiriam a "ação de uma linha" (linha ocupada, mensagem
  e erro) e o bloco "carregando / erro / tentar de novo": os dois viram o hook `useRowAction` e
  o componente `LoadState`, usados nas duas telas.

## Critérios de aceitação

### Backend
1. [ ] `POST /users/{id}/temporary-password` (admin) responde 200 com `temporary_password` e
   `Cache-Control: no-store`. A senha tem 12 caracteres, letras e dígitos, e entra no login.
   A senha antiga deixa de entrar.
2. [ ] Depois de gerar, o refresh antigo do usuário responde 401 e `must_change_password` é `true`.
3. [ ] Cliente e barbeiro recebem 403; sem token, 403; id desconhecido, 404; o próprio admin, 400;
   conta desativada, 400.
4. [ ] A senha gerada não aparece em nenhum registro de log (`caplog`, em qualquer nível).
5. [ ] Com a troca pendente: `GET /me` responde 200, outra rota protegida responde 403 com a
   mensagem acima; `PUT /me/password` com a senha temporária como atual troca a senha, desliga o
   campo, e a rota protegida volta a responder 200.
6. [ ] A redefinição por token também desliga o campo.
7. [ ] A migração `0004` cria a coluna (as linhas existentes ficam `false`) e o downgrade a remove;
   modelos e banco migrado não divergem.

### Frontend
8. [ ] O item "Usuários" aparece no menu só para o admin, e a rota `/admin/usuarios` só existe para
   ele.
9. [ ] A tabela mostra nome, e-mail, perfil e situação, com busca por nome ou e-mail, filtro por
   perfil e paginação ("Anterior" e "Próxima", com "Página X de Y").
10. [ ] Trocar o perfil no seletor chama `PUT /users/{id}/role`; "Desativar" pede confirmação e
    chama `PUT /users/{id}/status`; "Ativar" chama sem confirmação. A linha passa a mostrar o que o
    backend devolveu. Erros da API aparecem na tela e a lista continua.
11. [ ] "Gerar senha temporária" pede confirmação e mostra a senha num quadro com "Copiar"
    (área de transferência) e "Fechar". Fechar tira a senha da tela; ela não fica guardada no hook.
12. [ ] O admin não vê as ações na própria linha (o backend recusaria).
13. [ ] No login do cliente e no profissional, `must_change_password` leva a `/trocar-senha`. Ao
    trocar, o cliente vai para `/` e o admin ou barbeiro para `/admin`. O painel, ao carregar um
    usuário com a troca pendente, também manda para `/trocar-senha`.
14. [ ] Testes vitest do hook, dos componentes, da página e do redirecionamento do login.

## Fora do escopo

- Envio de e-mail.
- Criar ou apagar usuários pelo painel.
- Perfil de barbeiro (comissão e escala): continua na tela de barbeiros.
- Expirar a senha temporária por tempo.
