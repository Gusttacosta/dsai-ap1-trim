# Fidelidade de verdade: pagamentos geram pontos e a tela usa a API (2026-11-25)

> Complementa: SPEC/2026-09-29-fidelidade.md, SPEC/2026-11-25-fidelidade-correcoes.md (#73) e
> SPEC/2026-11-25-notificacoes.md (#75)
> Issue: #13 (e a parte `loyalty_update` da #75)

## O quê e por quê

A tela `/fidelidade` parecia funcionar, mas era fachada:
- os prêmios eram fixos no código (`MOCK_REWARDS`);
- o saldo era `useState(120)`;
- o "resgate" só subtraía de uma variável local, e o saldo voltava ao recarregar.

No backend, nenhum fluxo gerava pontos: o `add_points` só era chamado pelo admin, à mão.

## Decisão: a regra de pontuação

A pergunta ao cliente (n.º 2 de "Primeiras impressões", #15) ficou sem resposta. A regra adotada é
**1 ponto por real pago**, sem os centavos (R$ 45,90 vale 45 pontos):

| Pagamento | Pontos |
|---|---|
| atendimento concluído pelo barbeiro (cobrança automática da #26) | sim |
| atendimento cobrado no caixa | sim, uma vez só |
| atendimento pago com crédito do Trim Club (0,00) | não: o sócio já tem o benefício do clube |
| produto vendido no caixa com o cliente informado | sim |
| produto vendido sem cliente | não |
| conta desativada, inclusive o usuário Visitante da #21 | não |

- Os pontos entram no **mesmo commit** da cobrança: se ela falha, os pontos não entram.
- A carteira é lida com `FOR UPDATE`, como no resgate (#73).
- Cada crédito, o crédito manual do admin e cada resgate geram uma notificação `loyalty_update`
  (#75).

## Critérios de aceitação

- [ ] Concluir um atendimento de R$ 45,90 dá 45 pontos ao cliente (`balance` e
  `lifetime_points`) e uma notificação `Você ganhou pontos`.
- [ ] Cobrar no caixa pontua uma vez, e uma segunda tentativa de cobrança não pontua de novo.
- [ ] O crédito do Trim Club, a venda sem cliente e o cliente desativado não criam carteira nem
  pontos.
- [ ] Os pontos somam numa carteira que já existe.
- [ ] Os pontos ganhos podem ser resgatados no catálogo, e o resgate gera `Resgate confirmado`.
- [ ] **Tela `/fidelidade`:**
  - mostra o saldo de `GET /api/loyalty/me` e os prêmios de `GET /api/loyalty/rewards`;
  - o resgate chama `POST /api/loyalty/redeem/{id}`, mostra a confirmação e recarrega o saldo;
  - um erro do servidor (por exemplo, saldo insuficiente) aparece na tela;
  - sem login, mostra o catálogo, explica a regra e pede para entrar.

## Testes

- `tests/test_fidelidade_pontos.py`: os pagamentos pela API, mais a regra `points_for` sem banco;
- `src/frontend/src/pages/Fidelidade.test.tsx`, no vitest.
