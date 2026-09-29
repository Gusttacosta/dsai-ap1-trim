# Autenticação e Controle de Acesso (2026-09-29)

## O quê e por quê

O módulo de autenticação é a base de todo o sistema Trim. Ele controla quem pode acessar o quê, garantindo que:
- Donos de barbearia (admins) tenham acesso total à gestão.
- Barbeiros vejam apenas sua própria agenda e desempenho.
- Clientes acessem apenas agendamento, assinaturas e seu próprio histórico.

Sem autenticação, nenhum outro módulo pode funcionar de forma segura.

### Decisões técnicas
- **JWT (JSON Web Tokens)** para autenticação stateless — o backend não precisa manter sessão.
- **bcrypt** para hash de senhas — padrão da indústria, resistente a ataques de força bruta.
- **Perfis (roles)** armazenados no payload do JWT — verificação de permissão sem consulta extra ao banco.
- **Refresh token** via cookie httpOnly — segurança contra XSS.

---

## Entidades

### User
| Campo | Tipo | Restrições |
|-------|------|------------|
| id | UUID | PK, auto-gerado |
| email | string | unique, not null, validação de formato |
| hashed_password | string | not null |
| full_name | string | not null, min 2 chars |
| phone | string | nullable, formato brasileiro |
| role | enum | `admin`, `barber`, `client` — not null, default `client` |
| avatar_url | string | nullable |
| is_active | boolean | default true |
| email_verified | boolean | default false |
| created_at | datetime | auto-gerado |
| updated_at | datetime | auto-atualizado |

---

## Endpoints da API

### Públicos (sem autenticação)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/auth/register` | Cadastro de novo usuário (default role: `client`) |
| POST | `/api/auth/login` | Login com email/senha, retorna access + refresh token |
| POST | `/api/auth/refresh` | Renova o access token usando o refresh token |

### Públicos (sem autenticação) — cont.
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/auth/verify-email` | Confirma o e-mail com token recebido |
| POST | `/api/auth/verify-email/resend` | Reenvia o token de verificação |
| POST | `/api/auth/forgot-password` | Solicita reset de senha (envia token por e-mail) |
| POST | `/api/auth/reset-password` | Redefine a senha usando o token de reset |

### Autenticados
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/auth/me` | Retorna os dados do usuário logado |
| PUT | `/api/auth/me` | Atualiza dados do perfil (nome, telefone, avatar) |
| PUT | `/api/auth/me/password` | Altera a senha (exige senha atual) |
| POST | `/api/auth/logout` | Invalida o refresh token |

### Admin only
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/auth/users` | Lista todos os usuários (com filtros e paginação) |
| GET | `/api/auth/users/{id}` | Detalhes de um usuário |
| PUT | `/api/auth/users/{id}/role` | Altera o role de um usuário (promover a barbeiro, etc.) |
| PUT | `/api/auth/users/{id}/status` | Ativa/desativa um usuário |

---

## Regras de negócio

1. **Email único:** Não permite cadastro com email já existente.
2. **Senha forte:** Mínimo 8 caracteres, pelo menos 1 letra e 1 número.
3. **Access token (por perfil):**
   - **Cliente:** 30 minutos (uso pontual — agendar e sair).
   - **Barbeiro:** 12 horas (jornada de trabalho — fica logado o dia todo).
   - **Admin:** 12 horas (gestão contínua ao longo do dia).
   - Payload contém `user_id`, `email` e `role`.
4. **Refresh token (por perfil):**
   - **Cliente:** 7 dias.
   - **Barbeiro / Admin:** 30 dias.
   - Armazenado como cookie httpOnly.
5. **Proteção de rotas:** Middleware que valida o JWT e injeta o usuário no request.
6. **Role hierarchy:** Admin pode tudo. Barbeiro acessa rotas de barbeiro + cliente. Cliente acessa apenas rotas de cliente.
7. **Primeiro usuário:** O primeiro usuário cadastrado no sistema recebe automaticamente o role `admin`.
8. **Soft delete:** Desativar usuário (`is_active = false`) impede login, mas mantém o histórico.
9. **Rate limiting de login:** Máximo de 5 tentativas de login por IP/email em 15 minutos. Após exceder, bloqueia por 15 minutos com resposta 429.
10. **Verificação de e-mail:** Ao se cadastrar, o usuário recebe um token de verificação (simulado em dev: impresso no console). Enquanto o e-mail não for verificado, o campo `email_verified` fica `false`. O usuário pode usar o sistema normalmente, mas recebe um aviso visual no frontend.
11. **Reset de senha:** O usuário solicita reset informando o e-mail. Um token de uso único (expira em 1 hora) é gerado. Em dev, o token é impresso no console. Em produção, seria enviado por e-mail.

---

## Critérios de aceitação

- [ ] Cadastro cria usuário com senha hasheada e retorna tokens
- [ ] Login com credenciais válidas retorna access token + refresh token
- [ ] Login com credenciais inválidas retorna 401 com mensagem genérica
- [ ] Access token expirado retorna 401 e pode ser renovado via refresh
- [ ] Rotas protegidas rejeitam requests sem token válido
- [ ] Admin consegue listar, filtrar e alterar role de usuários
- [ ] Usuário desativado não consegue fazer login
- [ ] Primeiro usuário cadastrado recebe role admin automaticamente
- [ ] Endpoint `/me` retorna os dados do usuário logado sem expor a senha
- [ ] Alteração de senha exige confirmação da senha atual
- [ ] Rate limiting bloqueia após 5 tentativas de login em 15 minutos (429)
- [ ] Cadastro dispara token de verificação de e-mail (impresso no console em dev)
- [ ] Endpoint de verificação de e-mail aceita token válido e marca `email_verified = true`
- [ ] Fluxo de reset de senha gera token de uso único com expiração de 1 hora
- [ ] Reset de senha com token válido altera a senha e invalida o token

---

## Fora do escopo

- Login social (Google, Facebook, GitHub)
- Autenticação de dois fatores (2FA)
- Envio real de e-mails em produção (em dev, tokens são impressos no console)
