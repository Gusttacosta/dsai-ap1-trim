# Visão Geral — Trim (2026-09-29)

## O quê e por quê

**Trim** é uma plataforma completa de gestão para barbearias. O objetivo é oferecer ao dono de barbearia (e sua equipe) uma ferramenta única para controlar todas as operações do dia a dia — desde o agendamento online até o financeiro — eliminando planilhas, cadernos e WhatsApp como ferramentas de gestão.

O cliente final (quem corta o cabelo) também interage com o sistema: agenda horários, assina planos recorrentes e acompanha seu histórico.

### Problema
Barbearias pequenas e médias gerenciam agendamentos por WhatsApp, controlam caixa em caderno e não têm visibilidade sobre faturamento, recorrência de clientes ou desempenho dos barbeiros. Isso gera faltas, conflitos de horário, perda de receita e zero fidelização estruturada.

### Solução
Uma aplicação web responsiva (funciona bem no celular e no desktop) com dois perfis de acesso:

- **Painel Administrativo (Dono/Barbeiro):** Gestão completa do negócio.
- **Área do Cliente:** Agendamento, assinaturas, histórico e perfil.

---

## Módulos do Sistema

### 1. Autenticação e Controle de Acesso
- Cadastro e login (email/senha)
- Perfis: **admin** (dono da barbearia), **barbeiro** (membro do time) e **cliente**
- Recuperação de senha
- Proteção de rotas por perfil

### 2. Gestão do Time (Barbeiros)
- CRUD de barbeiros vinculados à barbearia
- Definição de horário de trabalho e disponibilidade por dia da semana
- Associação de serviços que cada barbeiro realiza
- Foto de perfil e bio (exibida na tela de agendamento)
- Dashboard individual de desempenho (atendimentos, faturamento)

### 3. Catálogo de Serviços
- CRUD de serviços (nome, descrição, duração estimada, preço)
- Categorias de serviço (corte, barba, combo, tratamento)
- Serviços ativos/inativos (sem excluir do histórico)
- Associação com barbeiros que executam cada serviço

### 4. Agendamento
- Calendário visual com slots disponíveis por barbeiro
- Cliente escolhe: serviço → barbeiro → data/hora
- Validação automática de conflitos de horário
- Status do agendamento: **agendado**, **confirmado**, **em andamento**, **concluído**, **cancelado**, **falta (no-show)**
- Notificações de lembrete (in-app)
- Reagendamento e cancelamento com regras de antecedência
- Visão de agenda diária/semanal para o barbeiro e para o admin

### 5. Gestão de Clientes (CRM)
- Cadastro automático no primeiro agendamento
- Histórico completo de atendimentos por cliente
- Informações de contato, preferências e observações
- Indicadores: frequência de visitas, ticket médio, tempo desde última visita
- Segmentação (cliente novo, recorrente, inativo)

### 6. Produtos (Venda no Balcão)
- CRUD de produtos (pomada, shampoo, óleo para barba, etc.)
- Controle de estoque (quantidade disponível)
- Registro de vendas avulsas (fora do contexto de um agendamento)
- Histórico de vendas por produto

### 7. Assinaturas e Planos
- Criação de planos recorrentes (ex.: "2 cortes por mês", "corte + barba semanal")
- Definição de preço mensal, serviços inclusos e limite de uso
- Adesão e cancelamento pelo cliente
- Controle de créditos restantes no período
- Renovação automática mensal

### 8. Financeiro e Cobranças
- Registro de receitas (agendamentos concluídos, vendas de produtos, assinaturas)
- Fluxo de caixa diário/semanal/mensal
- Relatório de faturamento por barbeiro
- Relatório de faturamento por serviço
- Histórico de pagamentos (forma de pagamento: dinheiro, pix, cartão)
- Comissões por barbeiro (percentual configurável por serviço)

### 9. Dashboard e Relatórios
- Visão geral do dia: agendamentos, faturamento, ocupação
- Métricas semanais/mensais: receita total, ticket médio, taxa de no-show, novos clientes
- Ranking de barbeiros (por atendimentos e faturamento)
- Gráficos de tendência
- Exportação de relatórios em PDF e CSV

### 10. Fila de Espera (Walk-in)
- Registro de clientes que chegam sem agendamento prévio
- Fila ordenada por ordem de chegada, com estimativa de tempo de espera
- Atribuição automática ou manual ao próximo barbeiro disponível
- Painel de TV / tela de espera com posição na fila e tempo estimado
- Integração com o calendário: se o barbeiro não tem slot, entra na fila

### 11. Galeria e Portfólio
- Upload de fotos de cortes realizados (antes/depois)
- Associação da foto ao barbeiro, ao serviço e (opcionalmente) ao cliente
- Galeria pública visível na landing page e na tela de escolha de barbeiro
- Tags/categorias visuais (degradê, navalhado, afro, barba, etc.)
- Moderação pelo admin (aprovar/rejeitar fotos)

### 12. Programa de Fidelidade e Gamificação
- Sistema de pontos por atendimento concluído (configurável pelo admin)
- Regras de acúmulo: pontos por valor gasto, por frequência ou por serviço específico
- Catálogo de recompensas (ex.: "10º corte grátis", "desconto de 20% na pomada")
- Resgate de recompensas pelo cliente com débito automático de pontos
- Badges e conquistas (ex.: "Cliente Fiel", "5 cortes seguidos", "Primeiro Combo")
- Ranking de clientes mais fiéis (visível para o admin)

### 13. Landing Page Pública da Barbearia
- Página institucional gerada automaticamente com os dados da barbearia
- Seções: sobre, equipe (com fotos e bio), serviços com preços, galeria de cortes, localização (mapa)
- Link direto para o fluxo de agendamento online
- Personalizável: nome, logo, cores do tema, redes sociais, horário de funcionamento
- SEO-friendly e responsiva

### 14. Controle de Despesas
- CRUD de despesas (aluguel, água, luz, produtos de consumo, manutenção)
- Categorias de despesa configuráveis
- Despesas fixas (recorrentes) e variáveis (avulsas)
- Relatório de lucro líquido: receitas (módulo 8) − despesas
- Gráficos comparativos de receita vs. despesa ao longo do tempo

### 15. Central de Notificações In-App
- Notificações em tempo real dentro da aplicação (sino/badge no header)
- Tipos: lembrete de agendamento, confirmação, cancelamento, assinatura prestes a vencer, novo cliente, meta de fidelidade atingida
- Marcação como lida/não lida
- Histórico de notificações
- Configuração de preferências de notificação por tipo (ativar/desativar)

---

## Público-alvo

| Perfil | Descrição | Ações principais |
| :--- | :--- | :--- |
| **Admin (Dono)** | Proprietário da barbearia | Configurar tudo, ver relatórios, gerenciar time e financeiro |
| **Barbeiro** | Membro do time | Ver sua agenda, registrar atendimentos, ver seu desempenho |
| **Cliente** | Pessoa que agenda e usa os serviços | Agendar, assinar planos, ver histórico |

---

## Stack Técnica (Proposta)

- **Frontend:** React + TypeScript + Vite
- **Estilização:** Vanilla CSS (CSS Modules)
- **Backend:** Python + FastAPI
- **ORM / Migrations:** SQLAlchemy + Alembic
- **Banco de Dados:** PostgreSQL
- **Autenticação:** JWT (JSON Web Tokens) via python-jose + passlib
- **Validação:** Pydantic
- **Deploy:** Vercel (frontend) + Render/Railway (backend + banco)

---

## Critérios de aceitação (da visão geral)

- [ ] A aplicação é acessível via URL pública com 1 clique
- [ ] Existem 3 perfis de acesso distintos (admin, barbeiro, cliente) com rotas protegidas
- [ ] Todos os 15 módulos descritos possuem pelo menos o fluxo principal implementado
- [ ] O sistema é responsivo (funciona em tela de celular e desktop)
- [ ] O fluxo completo funciona: cliente agenda → barbeiro atende → admin vê o faturamento
- [ ] A fila de espera (walk-in) funciona em paralelo com o agendamento
- [ ] O programa de fidelidade acumula pontos e permite resgate de recompensas
- [ ] A landing page pública exibe dados reais da barbearia e linka para o agendamento
- [ ] O financeiro inclui receitas e despesas com cálculo de lucro líquido
- [ ] A aplicação possui pelo menos 100.000 linhas de código medidas pelo `cloc`

---

## Fora do escopo

- Integração real com gateways de pagamento (Stripe, PagSeguro, etc.) — o financeiro é registrado manualmente
- Notificações por SMS ou e-mail externo (apenas in-app)
- Múltiplas unidades/filiais da barbearia (apenas uma unidade por instância)
- App mobile nativo (é uma aplicação web responsiva)
- Chat em tempo real entre cliente e barbearia
- Marketplace de barbearias (o sistema atende uma única barbearia por instância)
