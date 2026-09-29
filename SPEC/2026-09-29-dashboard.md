# Módulo de Dashboard e Relatórios (2026-09-29)

## O quê e por quê

O dono da barbearia (Admin) precisa de uma visão em tempo real da saúde do negócio. Este módulo não cadastra novos dados; sua função é unicamente **consultar, agregar e consolidar** informações de todos os outros módulos (Financeiro, Agendamentos, Despesas e Produtos). 
O barbeiro também tem acesso a uma versão simplificada (Meu Desempenho).

### Decisões técnicas
- Não haverá novas tabelas no banco de dados para este módulo. Ele atuará apenas como uma camada lógica (Service/Router) rodando agregações complexas via SQL (ex: `SUM()`, `COUNT()`, `GROUP BY`).
- Como as requisições podem ser pesadas, todas as rotas receberão parâmetros obrigatórios de período (`start_date`, `end_date`) para limitar a quantidade de dados.
- O retorno será moldado diretamente para o consumo do Frontend (gráficos e cards).

---

## Estrutura de Retorno (Exemplos)

### 1. Resumo Financeiro (Admin)
- Receita Bruta (Soma das Transações)
- Comissões a Pagar (Soma de BarberCommissions)
- Despesas (Soma de Expenses)
- **Lucro Líquido:** Receita Bruta - Comissões - Despesas.

### 2. Visão do Dia (Admin e Barbeiro)
- Quantidade de agendamentos para "hoje".
- Ticket Médio do dia (Receita Total / Número de Agendamentos).
- Número de ausências (Status `NO_SHOW`).

### 3. Ranking de Barbeiros (Admin)
- Tabela ordenando os barbeiros por quantidade de atendimentos e receita gerada no período.

---

## Endpoints da API

### Autenticados (Apenas Admin)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/reports/financial-summary` | Retorna {revenue, commissions, expenses, net_profit} do período. |
| GET | `/api/reports/daily-overview` | Agendamentos, ticket médio e taxa de ocupação "de hoje". |
| GET | `/api/reports/barber-ranking` | Lista de barbeiros ordenados por faturamento gerado. |

### Autenticados (Barbeiro)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/reports/me` | Retorna o ticket médio, número de clientes atendidos e faturamento gerado **pelo barbeiro logado**. |

---

## Regras de negócio

1. **Restrição de Acesso:** Barbeiros só podem consultar os próprios números. Apenas Admin enxerga o panorama geral e despesas.
2. **Cálculo da Receita:** O cálculo de receita bruta no painel financeiro deve se basear apenas em `transactions` (dinheiro que efetivamente entrou), e não somando os valores de `appointments` (já que o cliente pode cancelar ou dar NO_SHOW e não pagar).
3. **Data Alvo:** O Dashboard deve sempre assumir que, caso o front não mande `start_date` e `end_date`, ele puxará o período do "mês atual" (dia 1 até o fim do mês corrente).

---

## Critérios de aceitação

- [ ] Endpoints implementados com agregação em SQLAlchemy, retornando os valores prontos (JSON estruturado).
- [ ] O cálculo do Lucro Líquido (`net_profit`) abate comissões E despesas corretamente da receita total.
- [ ] O Barbeiro consegue ver seu próprio desempenho e comissão pendente sem ver os dados do colega ou o lucro do dono.
- [ ] O Dashboard responde rapidamente graças aos joins eficientes na base PostgreSQL.

---

## Fora do escopo

- Exportação em PDF ou Excel (Isso seria gerado no Frontend consumindo essa mesma API).
- Gráficos gerados no backend (A API só retorna os números; o Frontend cuidará da plotagem via Chart.js ou Recharts).
- Cache complexo via Redis (consultas rodarão em tempo real no banco, assumindo um volume de dados inicial da AP1).
