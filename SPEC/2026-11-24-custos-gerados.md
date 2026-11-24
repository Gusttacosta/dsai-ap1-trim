# Custo das sessões gerado por script (2026-11-24)

> Complementa: SPEC/2026-11-10-processo-ap2.md
> Issue: #54

## O quê e por quê

Cada sessão registrada acrescenta uma linha à tabela de `prompts/sessoes/CUSTOS.md`, muda a linha
**Total** e acrescenta uma nota no fim do arquivo. Dois PRs com sessão abertos ao mesmo tempo
alteram sempre as mesmas linhas, e o segundo a entrar conflita. Desde 19/11, seis merges tiveram
alterações dos dois lados no `CUSTOS.md` (o último foi o `e1e77db`, no PR #53), e seis notas
explicam que a linha de outro PR "também está aqui, para o total ficar certo depois dos dois
merges". Os números também são somados à mão com `jq` a cada sessão, e nada confere se a tabela
bate com os `.jsonl` do repositório.

Solução: o `CUSTOS.md` e um novo `NOTAS.md` passam a ser gerados por `scripts/custos.py`, a partir
dos arquivos de cada sessão. Um PR com sessão só acrescenta arquivos novos (o `.jsonl`, os
`.jsonl` dos subagentes e, se houver algo a explicar, a nota). Depois de um merge da `main`, basta
rodar o script de novo, e o `--check` na CI garante que os gerados não ficaram para trás.

### Arquivos de entrada (`prompts/sessoes/`)

- `<sessão>-claudecode.jsonl`: transcrição da sessão principal. `<sessão>` é `AAAA-MM-DD-HHMM`.
- `<sessão>-claudecode-subagente-<n>.jsonl`: transcrição de um subagente da mesma sessão, com o
  mesmo mascaramento da principal. `<n>` é um número a partir de 1.
- `<sessão>.notas.md`: nota opcional da sessão (exportação, mascaramento, cortes por `timestamp`,
  o que ficou de fora da contagem), em Markdown livre.

### Regra de soma

Para cada sessão, o script lê o `.jsonl` principal e os dos subagentes e, em cada um:

1. considera só as entradas com `type == "assistant"`;
2. descarta as de `message.model == "<synthetic>"` (mensagens geradas pelo próprio Claude Code,
   sem chamada ao modelo);
3. conta cada `message.id` uma vez (as respostas em streaming repetem o mesmo `id` com o mesmo
   `usage`), ficando com a primeira ocorrência, como o `unique_by(.message.id)` do `jq`;
4. soma `input_tokens`, `output_tokens`, `cache_creation_input_tokens` e
   `cache_read_input_tokens` do `message.usage` (campo ausente conta como 0).

Os totais dos subagentes entram na linha da sessão principal. Um arquivo de subagente sem o
`.jsonl` principal correspondente é um erro.

### Colunas do `CUSTOS.md`

| Coluna | Origem |
| :--- | :--- |
| Sessão | nome do `.jsonl` principal, em código |
| Início | `DD/MM HH:MM`, tirado do nome do arquivo (o horário de início já está nele, AGENTS.md §8) |
| Fim | maior `timestamp` entre a principal e os subagentes, em America/Sao_Paulo, `HH:MM`; se cair em outro dia, `HH:MM (DD/MM)` |
| Modelos | modelos contados, sem `<synthetic>`, em ordem alfabética e separados por vírgula |
| Input, Output, Cache (escrita), Cache (leitura) | somas da regra acima |
| Total | soma das quatro colunas |

As sessões ficam em ordem de nome. A última linha é o **Total** de cada coluna numérica, em
negrito. Os números usam vírgula como separador de milhar, como a tabela de hoje. O arquivo tem
só um título, uma frase dizendo que é gerado e como, a tabela e o Total.

### `NOTAS.md`

Junta os `<sessão>.notas.md` em ordem de sessão. Cada nota vem sob um título com o link para o
`.jsonl` da sessão (`### [<sessão>-claudecode.jsonl](<sessão>-claudecode.jsonl)`), com o texto da
nota sem alteração. Uma nota sem `.jsonl` correspondente é um erro.

### Linha de comando

- `python scripts/custos.py`: regrava os dois arquivos.
- `python scripts/custos.py --check`: não grava nada; sai com código 1 e diz qual arquivo está
  desatualizado se algum dos dois for diferente do que seria gerado; sai com 0 se ambos estiverem
  em dia.
- `--dir <pasta>`: pasta das sessões (padrão: `prompts/sessoes`), para os testes.

Só a biblioteca padrão do Python 3.12, sem dependência nova.

### Migração

- As notas que hoje estão no fim do `CUSTOS.md` vão para os `<sessão>.notas.md`, sem mudar o texto.
  Uma nota que fala de várias sessões fica na primeira delas.
- Antes de trocar a tabela, a gerada é comparada com a atual, sessão por sessão, e as diferenças
  são apresentadas com a causa provável. Nenhum número muda sem decisão da dupla.
- Nenhum `.jsonl` já registrado é alterado.

## Critérios de aceitação

- [ ] `python scripts/custos.py` gera o `CUSTOS.md` com as colunas acima e a linha Total, e o
      `NOTAS.md` com cada nota sob o link do `.jsonl` da sessão.
- [ ] Tokens de um `<sessão>-claudecode-subagente-<n>.jsonl` entram na linha da sessão principal,
      e o modelo do subagente aparece na coluna Modelos.
- [ ] Mensagens `<synthetic>` não entram na soma nem na coluna Modelos.
- [ ] Um `message.id` repetido é contado uma vez.
- [ ] Uma sessão que passa da meia-noite mostra o dia no Fim.
- [ ] Subagente ou nota sem o `.jsonl` principal correspondente fazem o script falhar com uma
      mensagem que diz o arquivo.
- [ ] `--check` sai com 1 se o `CUSTOS.md` ou o `NOTAS.md` estiverem desatualizados (inclusive
      ausentes) e com 0 se estiverem em dia.
- [ ] Testes em `tests/` falham se a regra de soma for desfeita (sem o `unique_by`, com o
      `<synthetic>`, sem os subagentes).
- [ ] A CI roda `python scripts/custos.py --check`.
- [ ] O AGENTS.md §8 descreve o fluxo novo: exportar o `.jsonl` da sessão e os dos subagentes
      (com o mesmo mascaramento), criar a nota se houver algo a explicar e rodar
      `python scripts/custos.py` antes do commit.

## Fora do escopo

- Alterar o conteúdo de qualquer `.jsonl` já registrado.
- Custo em US$ (a tabela continua em tokens).
- Sessões de outras ferramentas além do Claude Code (o padrão `*-claudecode.jsonl` continua sendo o
  único lido; uma ferramenta nova pede uma spec nova).
