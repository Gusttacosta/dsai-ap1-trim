# gitleaks sem falsos positivos e verificação de segredos na CI (2026-11-21)

> Complementa: SPEC/2026-11-10-processo-ap2.md (critério de segurança: zero segredos no histórico)
> Issue: #33

## O quê e por quê

O critério de segurança da AP2 mede os segredos no histórico com o `gitleaks` e pede zero. Hoje,
`gitleaks git .` (v8.30.1, regras padrão) aponta 503 achados na `main` (cc0fc3e), todos da regra
`generic-api-key` e todos falsos positivos (#33):

- **500 nas transcrições `prompts/sessoes/*.jsonl`.** Cada registro traz o campo `"betas"`, a
  lista de recursos beta da API usados pelo agente. A regra genérica lê o item
  `"oauth-2025-04-20"` como nome de chave e o item seguinte, `"interleaved-thinking-2025-05-14"`,
  como o valor secreto.
- **3 senhas de teste:** `senhaForte123` em `tests/test_token_fora_do_log.py` e em
  `tests/test_backend_windows_unicode.py`, e `outraSenha456` em `tests/test_token_fora_do_log.py`.
  Essas senhas só existem no banco descartável dos testes.

Com 503 achados de ruído, um segredo de verdade passaria despercebido. Além disso, nada impede hoje
que um segredo entre no histórico, porque a CI não roda o `gitleaks`.

Solução:

- **`.gitleaks.toml` na raiz**, que estende as regras padrão (`[extend] useDefault = true`) e
  acrescenta duas exceções restritas à regra `generic-api-key`. Cada exceção exige as duas condições
  ao mesmo tempo (`condition = "AND"`):
  1. o arquivo está em `prompts/sessoes/` e termina em `.jsonl`, **e** o valor capturado é um nome
     de recurso beta com data (letras minúsculas, dígitos e hífens, terminando em `-AAAA-MM-DD`,
     como `interleaved-thinking-2025-05-14`);
  2. o arquivo está em `tests/`, **e** o valor capturado é exatamente `senhaForte123` ou
     `outraSenha456`.

  Fica de fora qualquer outro valor nessas pastas, e qualquer valor em outras pastas. As outras
  regras padrão (chaves da AWS, do GitHub, da Anthropic, chaves privadas etc.) não ganham exceção.
- **Job `Segredos (gitleaks)` na CI**, em todo push e PR para a `main`. Ele faz o checkout do
  histórico inteiro (`fetch-depth: 0`), baixa o binário do `gitleaks` 8.30.1 das releases oficiais,
  confere o SHA-256 com o arquivo de checksums da mesma release e roda
  `gitleaks git . --redact --config .gitleaks.toml`. Qualquer achado falha o build, sem expor o
  valor no log.

Valor: o critério de segurança fica em zero, e um segredo de verdade passa a quebrar a CI.

## Critérios de aceitação

- [ ] `gitleaks git . --config .gitleaks.toml` no histórico do branch termina com `no leaks found`
      e código de saída 0.
- [ ] Sem o `.gitleaks.toml`, `gitleaks git .` volta a apontar os 503 achados.
- [ ] A configuração continua apontando um segredo de verdade: em um repositório de teste com o
      mesmo `.gitleaks.toml`, uma chave no formato da AWS em `prompts/sessoes/x.jsonl`, uma
      `api_key = "<valor aleatório>"` em `tests/` e outra fora de `tests/` são todas apontadas
      (código de saída 1).
- [ ] O job `Segredos (gitleaks)` passa no PR e falha se o checksum do binário não conferir.

## Fora do escopo

- Reescrever o histórico, que as regras da AP2 proíbem e que não é necessário, porque nenhum achado
  é segredo.
- Os alertas de dependências (`npm audit`, #8), que ficam para outro PR.
