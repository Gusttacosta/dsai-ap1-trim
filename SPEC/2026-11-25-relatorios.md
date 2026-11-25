# Relatórios no fuso da barbearia, com faturamento do dia, ocupação e ranking dos ativos (2026-11-25)

> Complementa: SPEC/2026-09-29-dashboard.md, SPEC/2026-11-18-agendamento-fuso-horario.md e
> SPEC/2026-11-24-testes-integracao-dashboard.md (PR #68)
> Issue: #67

## O quê e por quê

Os testes de integração dos relatórios (PR #68) acharam seis problemas:
1. o faturamento do dia é calculado e some da resposta, porque o schema não tem o campo;
2. as datas usam `func.date()` no fuso da sessão do banco (UTC) e o `date.today()` do servidor.
   Um atendimento às 22:00 de Brasília conta no dia seguinte, e uma cobrança às 21:30 do último
   dia do mês cai no mês seguinte;
3. o ranking inclui barbeiros desativados;
4. falta a ocupação da agenda que a spec da AP1 promete;
5. um período invertido devolve zeros sem aviso;
6. o ranking faz 3 consultas por barbeiro (N+1).

Valor: é a tela que o dono usa para decidir. Números do dia errado, um faturamento que não
aparece e barbeiros que já saíram no ranking levam a decisões erradas.

## Critérios de aceitação

1. [ ] `GET /api/reports/daily-overview` traz `total_revenue`: a soma das transações do dia.
2. [ ] **Fuso da barbearia:**
   - todos os filtros por dia e por período usam o início e o fim do dia em
     `settings.shop_timezone`, convertidos para UTC;
   - o padrão (hoje e o mês corrente) é o dia da barbearia;
   - 22:00 de 10/11 em Brasília conta no dia 10, e 21:30 de 30/11 conta em novembro;
   - as despesas continuam filtradas pelo `payment_date`, que já é um dia local.
3. [ ] O ranking só tem barbeiros com o perfil e a conta ativos. Empates no faturamento são
   ordenados pelo nome.
4. [ ] **Ocupação** na visão do dia:
   - `booked_minutes`: a duração dos agendamentos `pending`, `confirmed` e `completed` do dia;
   - `available_minutes`: o expediente dos barbeiros ativos que trabalham naquele dia da semana,
     sem o almoço;
   - `occupancy_rate`: agendado ÷ disponível × 100, com 2 casas. Sem expediente, vale 0.
5. [ ] `start_date` depois de `end_date` responde **422** `A data inicial não pode ser depois da
   data final.` em `/financial-summary`, `/barber-ranking` e `/me`.
6. [ ] O ranking usa consultas agrupadas: um número fixo de consultas, qualquer que seja o tamanho
   da equipe.

Os testes do PR #68 gravam os dados ao meio-dia UTC (09:00 em Brasília) e continuam valendo.
Dois deles ganham um commit no #68 para valer com e sem esta correção:
- a comparação da visão vazia passa a olhar só os campos que já existiam;
- o "hoje" padrão passa a aceitar o dia do servidor ou o da barbearia.

## Testes

`tests/test_relatorios_correcoes.py`, pela API, com o PostgreSQL de `TEST_DATABASE_URL`.
