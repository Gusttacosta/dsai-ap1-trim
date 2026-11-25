# Fim dos testes gerados: o gerador sai do repositório (2026-11-25)

> Complementa: SPEC/2026-11-21-testes-integracao-auth.md (o plano da #3, um módulo por PR)
> Issue: #3

## O quê e por quê

O plano da #3 trocou, um módulo por PR, os 13 arquivos `tests/test_<módulo>.py` gerados pela AP1
por testes de integração pela API. Cada PR também tirava o módulo da lista `MODULES` de
`tests/generate_tests.py`. O passo final do plano era: "Quando a lista ficar vazia, o gerador
também sai."

Com o #74 (loyalty) e o #76 (notifications), a lista ficou vazia. O `generate_tests.py` não gera
mais nada e só escrevia de volta os arquivos de 1.000 funções que conferiam um dicionário fixo.

## Critérios de aceitação

- [ ] `tests/generate_tests.py` sai do repositório.
- [ ] Nenhum `tests/test_<módulo>.py` gerado sobra: cada um dos 13 módulos tem o seu
  `tests/test_<módulo>_integracao.py` (ou equivalente) pela API.
- [ ] Nenhum arquivo do projeto, fora as specs e as sessões antigas, referencia o gerador.
- [ ] Um teste confere que não há arquivo de teste com o padrão gerado (1.000 funções
  `test_<módulo>_<n>`) e que o gerador não voltou. Com o gerador de volta, ele falha.
