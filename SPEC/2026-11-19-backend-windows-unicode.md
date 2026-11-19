# Backend sobe no Windows: mensagens pelo logging, sem emojis (2026-11-19)

> Complementa: SPEC/2026-09-29-visao-geral.md (somente leitura)
> Issue: #2

## O quê e por quê

No Windows, a saída do processo usa a codificação local (cp1252) sempre que não é um console
nativo: Git Bash, terminal de IDE, saída redirecionada para arquivo. Nesses casos o backend não
sobe:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680' in position 0: character maps to <undefined>
ERROR:    Application startup failed. Exiting.
```

A causa são os `print` com emoji. Há três lugares:

1. `src/backend/main.py`, `lifespan`: 🚀, 🛠️, ✅ e 👋 na inicialização e no encerramento. O
   `UnicodeEncodeError` sai do startup e o uvicorn encerra o processo.
2. `src/backend/modules/auth/service.py`, `create_user`: o "e-mail" falso com o token de
   verificação (📧). O `print` roda antes do `commit`, e `UnicodeEncodeError` é um `ValueError`,
   que a rota trata como erro de cadastro. Por isso `POST /api/auth/register` responde 400 com
   `"'charmap' codec can't encode character..."` e o usuário não é criado.
3. `src/backend/modules/auth/service.py`, `create_password_reset_token`: o link de redefinição de
   senha (🔑). O `print` roda depois do `commit`, então `POST /api/auth/forgot-password` responde
   500, mas o token já foi gravado.

Hoje o contorno é `PYTHONUTF8=1` antes de subir o servidor, e isso não está documentado.

Solução:

- **Os `print` viram `logging`**, cada módulo com `logger = logging.getLogger(__name__)`:
  - `lifespan` registra a inicialização (nome do app, ambiente, debug), a criação das tabelas, o
    banco pronto e o encerramento;
  - `create_user` e `create_password_reset_token` registram o e-mail falso com o mesmo conteúdo
    de antes: destinatário, token ou link.
- **As mensagens são só ASCII**: sem emoji e sem acento. Assim cabem em qualquer codificação de
  console.
- **O logging não derruba a aplicação.** Se um dado variável da mensagem, como um e-mail com
  acento, não couber na codificação da saída, o `logging` avisa no stderr e a requisição segue.
  Com o `print`, o erro chegava até a rota.
- **As mensagens continuam aparecendo no terminal.** O uvicorn só configura os loggers dele, e
  sem configuração um `logger.info` não aparece. `src/backend/main.py` passa a configurar o logger
  `src.backend`: nível INFO e um handler no stderr no formato do uvicorn (`INFO:     mensagem`),
  adicionado uma vez só. O logger raiz não muda, então as bibliotecas não passam a escrever mais.
- **Fora do escopo:** o e-mail falso continua mostrando o token no log, como já acontecia com o
  `print`. Enviar e-mail de verdade, ou esconder o token em produção, fica para outra issue.

Valor: o backend sobe no Windows em qualquer terminal, sem variáveis extras, e o cadastro e a
recuperação de senha param de falhar nesses ambientes.

## Critérios de aceitação

Testes em `tests/test_backend_windows_unicode.py`. Eles trocam `sys.stdout` e `sys.stderr` por
fluxos cp1252 com `errors="strict"`, como o console do Windows:

- [ ] O `lifespan` inicia e encerra sem exceção, sem banco: o `engine` é trocado por um falso, que
      registra a chamada a `create_all`.
- [ ] O `lifespan` registra a inicialização, o banco pronto e o encerramento no logger
      `src.backend.main`, e todas as mensagens são ASCII.
- [ ] Com o PostgreSQL da CI, `POST /api/auth/register` responde 201 e o usuário fica no banco; o
      token de verificação aparece no log em ASCII.
- [ ] Com o PostgreSQL da CI, `POST /api/auth/forgot-password` de um e-mail cadastrado responde
      200; o link de redefinição aparece no log em ASCII.
- [ ] O logger `src.backend` tem nível INFO e um único handler no stderr, mesmo que a configuração
      rode duas vezes.
- [ ] Com `main.py` e `auth/service.py` revertidos, os testes do `lifespan`, do cadastro e da
      recuperação de senha falham.

Verificação manual: no Git Bash do Windows, sem `PYTHONUTF8`,
`python -m uvicorn src.backend.main:app` sobe e mostra as mensagens de inicialização.
