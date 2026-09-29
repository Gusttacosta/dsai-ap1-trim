# Guia de Contribuição

Este documento descreve as convenções de **branches**, **commits** e **pull requests** adotadas neste repositório.

---

## 1. Nomenclatura de Branches

Cada branch deve ser única e descartável. Usamos a data do dia para garantir que nunca haja repetição ao mexer no mesmo módulo.

**Padrão:** `tipo/AAAAMMDD-descricao-curta`

| Tipo        | Quando usar                                                |
| ----------- | ---------------------------------------------------------- |
| `feat/`     | Novas funcionalidades                                      |
| `fix/`      | Correção de erros                                          |
| `refactor/` | Melhoria de código (sem mudar a lógica de negócio)         |
| `chore/`    | Tarefas repetitivas (ex.: atualizar bibliotecas, limpeza)  |
| `docs/`     | Apenas documentação                                        |

### Exemplos

- `feat/20240325-login-google`
- `fix/20240326-erro-calculo-frete`
- `feat/20240327-ajuste-perfil-usuario` (mesmo módulo, dia diferente)

> **Regra de ouro:** Fez o merge? Delete a branch. A branch é um rascunho — o que vale é o código na `main`.

---

## 2. Mensagens de Commit

Seguimos o padrão **Conventional Commits** e exigimos Git Trailers de rastreabilidade.

**Padrão:**
```text
<tipo>: <descrição curta em letra minúscula e no imperativo>

Agent: <ferramenta/modelo ou none>
Spec: SPEC/<arquivo-da-spec>.md
```

| Tipo        | Significado                                  |
| ----------- | -------------------------------------------- |
| `feat`      | Adição de algo novo                          |
| `fix`       | Conserto de algo quebrado                    |
| `docs`      | Mudança em documentação                      |
| `style`     | Estética e formatação (sem mudar lógica)     |
| `refactor`  | Melhoria de performance ou organização       |
| `chore`     | Manutenção, build, dependências              |
| `test`      | Adição/ajuste de testes                      |

### Exemplos de Commit Válido:

```text
feat: adiciona campo de telefone no cadastro

Agent: antigravity/gemini-3.1-pro
Spec: SPEC/2026-09-29-autenticacao.md
```

```text
fix: corrige erro ao salvar endereco sem numero

Agent: none
Spec: SPEC/2026-09-29-checkout.md
```

---

## 3. Modelo de Pull Request

O PR é onde explicamos o **"porquê"** da mudança para quem for revisar.

**Título:** `tipo: Descrição da entrega`
Exemplo: `feat: Implementação do Login Social`

### Template do corpo do PR

```markdown
## 📝 Descrição
O que foi feito nesta tarefa? (contexto rápido).

## 🛠️ Alterações Principais
- Criado o componente X.
- Ajustada a rota Y no backend.
- Adicionados testes unitários para a função Z.

## 🧪 Como Testar?
1. Faça o checkout para a branch `feat/AAAAMMDD-descricao`.
2. Execute `npm install` (ou equivalente).
3. Reproduza o cenário X e verifique o resultado Y.

## 🖼️ Evidências (opcional)
[Cole aqui um print ou link de vídeo para alterações visuais]
```

---

## 4. Promoção de `homologacao` para `main`

Após um conjunto de PRs ser mergeado em `homologacao` e validado, promovemos essas mudanças para `main` através de um **PR de consolidação**.

**Padrão:**

- **Base:** `main`
- **Head:** `homologacao`
- **Título:** `chore: Promocao homolog para main (PRs #X, #Y, #Z)`
  - Liste os números dos PRs consolidados desde o último merge em `main`.

### Template do corpo do PR de consolidação

```markdown
## 📝 Descrição
Promoção do conteúdo validado em `homologacao` para `main`.

## 📦 PRs incluídos
- #X — <título do PR>
- #Y — <título do PR>
- #Z — <título do PR>

## ✅ Validação em homologação
- [ ] Todos os PRs listados foram testados no ambiente de homologação
- [ ] Não há regressões conhecidas
```

### Fluxo

1. Garanta que `homologacao` está atualizada com todos os PRs desejados.
2. No GitHub, abra um PR de `homologacao` → `main`.
3. Use o título e template acima. Puxe os números dos PRs comparando `main..homologacao` (ex.: `git log --merges main..homologacao --oneline`).
4. Após aprovado, faça **merge commit** (não squash) para preservar o histórico dos merges individuais.
5. **Não delete** a branch `homologacao` — ela é permanente.

> **Automação:** você pode acionar o workflow `/promover-main` para o Cascade levantar os PRs pendentes e montar título/corpo automaticamente.

---

## ✅ Resumo das Boas Práticas

- **Sempre** puxe a `main` atualizada antes de criar sua branch.
- **Commits curtos:** melhor 5 commits explicando passos do que 1 commit gigante com 20 arquivos.
- **Data é chave:** o formato `AAAAMMDD` impede que seu nome de branch colida com o de um colega ou com uma tarefa antiga sua.
- **Nunca** trabalhe direto na `main`.
- **Delete** a branch após o merge.
