# Módulo de Fidelidade e Gamificação (Loyalty) (2026-09-29)

## O quê e por quê

Para aumentar a taxa de retorno dos clientes (frequência), introduzimos um programa de fidelidade. 
Sempre que um cliente paga por um agendamento ou compra um produto, ele ganha uma quantidade de "Pontos" na sua carteira. 
Com esses pontos acumulados, ele pode acessar um catálogo de recompensas (ex: "100 pts = Corte Grátis" ou "50 pts = Pomada Modeladora") e resgatá-las.

### Decisões técnicas
- O saldo de pontos será mantido diretamente no cadastro do usuário ou em uma tabela de Wallet. Para a AP1, vamos gerenciar uma tabela `LoyaltyWallet` atrelada ao `User`.
- A geração de pontos deve ser injetada/acoplada no processo de Checkout (módulo de Finanças). No entanto, criaremos os endpoints aqui para manipular os pontos isoladamente se necessário.
- Teremos um catálogo de `Reward` (Recompensas).
- O ato de trocar os pontos por um prêmio cria um registro em `RewardRedemption`.

---

## Entidades

### LoyaltyWallet (Carteira de Pontos)
| Campo | Tipo | Restrições |
|-------|------|------------|
| id | UUID | PK, auto-gerado |
| user_id | UUID | FK (users.id), unique, not null |
| balance | integer | not null, default 0 (Pontos atuais) |
| lifetime_points| integer | not null, default 0 (Total de pontos que a pessoa já acumulou na vida) |
| updated_at | datetime | auto-atualizado |

### Reward (Prêmio do Catálogo)
| Campo | Tipo | Restrições |
|-------|------|------------|
| id | UUID | PK, auto-gerado |
| name | string | not null (ex: "Corte na Faixa") |
| description | string | nullable |
| points_cost | integer | not null, maior que 0 |
| is_active | boolean | default true |
| created_at | datetime | auto-gerado |

### RewardRedemption (Resgate)
| Campo | Tipo | Restrições |
|-------|------|------------|
| id | UUID | PK, auto-gerado |
| wallet_id | UUID | FK (loyalty_wallets.id), not null |
| reward_id | UUID | FK (rewards.id), not null |
| points_spent | integer | not null (tirado de points_cost no momento do resgate) |
| redeemed_at | datetime | auto-gerado |

---

## Endpoints da API

### Autenticados (Cliente)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/loyalty/me` | Retorna a `LoyaltyWallet` do cliente logado, criando-a automaticamente se não existir. |
| GET | `/api/loyalty/rewards` | Lista o catálogo de prêmios ativos (`is_active = True`). |
| POST | `/api/loyalty/redeem/{reward_id}` | Tenta trocar pontos pelo prêmio. Se houver saldo, deduz o saldo e gera o `RewardRedemption`. |

### Autenticados (Admin)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/loyalty/rewards` | Cria um novo prêmio no catálogo. |
| PUT | `/api/loyalty/rewards/{id}` | Edita os pontos ou dados de um prêmio. |
| POST | `/api/loyalty/wallet/{user_id}/add` | (Ação manual/sistema) Adiciona X pontos na carteira do cliente. |
| GET | `/api/loyalty/redemptions` | Vê um log de quem resgatou o quê recentemente. |

---

## Regras de negócio

1. **Auto-criação da Carteira:** Como nem todo cliente tem uma carteira ao nascer (usuário antigo), qualquer requisição que busque ou adicione pontos a um `user_id` deve instanciar a carteira zerada se ela não existir.
2. **Ganho de Pontos (Integração):** Para a nossa spec, deixaremos a função `add_points` exposta para o módulo financeiro chamar. A regra "1 real = 1 ponto" é o default sugerido.
3. **Imutabilidade do Custo:** A `RewardRedemption` deve copiar o `points_cost` do prêmio. Assim, se o prêmio aumentar de preço no futuro, o histórico de resgate anterior manterá o registro dos pontos exatos que o cliente gastou na época.
4. **Saldo Suficiente:** A lógica de resgate deve travar a transação e estourar um erro se `wallet.balance < reward.points_cost`.

---

## Critérios de aceitação

- [ ] Admin pode gerenciar o catálogo de prêmios (Rewards).
- [ ] O cliente pode consultar seu saldo, que é inicializado em 0 automaticamente se for a primeira vez.
- [ ] O cliente consegue realizar um resgate se tiver saldo. O saldo é diminuído imediatamente.
- [ ] O sistema impede resgate caso o cliente não possua pontos suficientes.

---

## Fora do escopo

- Emissão de voucher ou QR code automático. O "resgate" na API serve apenas para registrar a troca. O acerto do desconto será feito "no boca-a-boca" no caixa (o barbeiro abate o preço do serviço porque viu que o cliente resgatou).
- Validade ou expiração de pontos (Os pontos nunca expiram nesta versão).
