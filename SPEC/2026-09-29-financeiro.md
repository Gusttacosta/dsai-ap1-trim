# Módulo Financeiro e Cobranças (2026-09-29)

## O quê e por quê

O coração financeiro da barbearia. Este módulo atua como o Ponto de Venda (PDV/Caixa) e o Livro Razão das receitas. 
Ele junta os agendamentos realizados, os produtos vendidos no balcão e as assinaturas ativas para gerar os registros de `Transaction` (Transação Financeira).
Ele também é responsável por calcular o valor da comissão devida ao barbeiro a cada atendimento concluído.

### Decisões técnicas
- Todo dinheiro que entra gera uma `Transaction`.
- Uma `Transaction` pode estar ligada a um `Appointment` (pagamento de serviço), a uma venda avulsa de `Product`, ou a uma mensalidade de `UserSubscription`.
- Quando um agendamento é marcado como `COMPLETED`, o sistema deve criar automaticamente as transações de pagamento (ou abater se for cliente Trim Club VIP) e registrar o saldo de comissão do barbeiro em uma tabela `Commission`.

---

## Entidades

### Transaction (Transação / Receita)
| Campo | Tipo | Restrições |
|-------|------|------------|
| id | UUID | PK, auto-gerado |
| type | enum | `APPOINTMENT`, `PRODUCT_SALE`, `SUBSCRIPTION` |
| reference_id | UUID | FK genérica (aponta para o ID do agendamento, do produto movimentado ou da assinatura) |
| amount | decimal | not null (valor pago pelo cliente) |
| payment_method| enum | `CASH`, `CREDIT_CARD`, `DEBIT_CARD`, `PIX`, `TRIM_CLUB_CREDIT` |
| user_id | UUID | FK (users.id), nullable (o cliente que pagou, se houver cadastro) |
| created_at | datetime | auto-gerado |

### BarberCommission (Comissão do Barbeiro)
| Campo | Tipo | Restrições |
|-------|------|------------|
| id | UUID | PK, auto-gerado |
| barber_id | UUID | FK (barbers.id), not null |
| transaction_id| UUID | FK (transactions.id), not null (a venda que gerou a comissão) |
| amount | decimal | not null (valor a ser repassado ao barbeiro) |
| is_paid | boolean | default false (se o dono da barbearia já repassou esse dinheiro ao barbeiro) |
| created_at | datetime | auto-gerado |
| paid_at | datetime | nullable (data em que o acerto de contas foi feito) |

---

## Endpoints da API

### Autenticados (Admin/Caixa)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/finance/checkout/appointment/{id}` | Realiza a cobrança de um agendamento, muda status pra COMPLETED e gera a Transaction e Commission. |
| POST | `/api/finance/checkout/product` | Venda avulsa no balcão (gera Transaction e baixa o estoque no módulo de Produtos). |
| GET | `/api/finance/transactions` | Extrato de caixa (lista de todas as transações, com filtros de data). |
| GET | `/api/finance/commissions` | Relatório de comissões pendentes (agrupado por barbeiro). |
| PUT | `/api/finance/commissions/pay` | Admin marca as comissões de um barbeiro como `is_paid = True` (acerto de contas semanal/mensal). |

### Autenticados (Barbeiro)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/finance/commissions/me` | Barbeiro vê o saldo que ele tem a receber (`is_paid = False`) e o histórico de recebimentos. |

---

## Regras de negócio

1. **Cálculo da Comissão:** A comissão é gerada apenas quando o `payment_method` não for `TRIM_CLUB_CREDIT` (ou se houver uma regra acordada). Por padrão, a fórmula é: `Comissão = Valor do Serviço * (Barber.commission_rate / 100)`.
2. **Trim Club (Assinantes):** Se o cliente possui uma assinatura ativa e for pagar o agendamento no caixa, o `payment_method` deve ser enviado como `TRIM_CLUB_CREDIT`, o `amount` lançado na transaction é R$ 0.00, e a comissão do barbeiro deve ser tratada conforme a política do dono (Nesta versão: comissão zero, o dono paga um bônus fixo por fora, ou comissão com base no valor normal). *Decisão:* Para simplificar na AP1, o Trim Club zera a transação e zera a comissão no BD, ficando o acerto fora do sistema.
3. **Imutabilidade:** Transações financeiras não possuem endpoint de `DELETE` ou `PUT`. Se houver erro, deve-se gerar uma transação reversa (estorno), mas não implementaremos estorno nesta fase do projeto para poupar complexidade.
4. **Pagamento Múltiplo:** Nesta fase 1, um checkout recebe apenas 1 método de pagamento (não dá pra pagar metade em dinheiro e metade em PIX).

---

## Critérios de aceitação

- [ ] Checkout de agendamento muda o status para `COMPLETED` e cria a `Transaction`.
- [ ] O checkout do agendamento calcula e insere a `BarberCommission` usando a taxa de comissão definida no perfil do barbeiro.
- [ ] Checkout de produto integra com o `ProductService` para subtrair estoque e cria a `Transaction`.
- [ ] Admin consegue ver o total a pagar para cada barbeiro.
- [ ] Admin consegue realizar o "Acerto" marcando as comissões como pagas.
- [ ] Barbeiro consegue visualizar quanto tem a receber hoje.

---

## Fora do escopo

- Emissão de Nota Fiscal Eletrônica.
- Divisão de pagamentos (Split) na maquininha.
- Estornos de transações.
