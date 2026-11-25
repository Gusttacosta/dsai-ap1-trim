# Frontend: checagem de tipos no build e dependências sem alerta high (2026-11-24)

> Issues: #7, #8

## O quê e por quê

**Tipos (#7).** O script `build` do `src/frontend/package.json` é só `vite build`. O Vite remove
os tipos sem checá-los, então um erro de TypeScript nunca quebra o build nem a CI.
`npx tsc --noEmit` hoje acusa **10 erros**. A issue contava 11, e o PR #52 já corrigiu um.

- 9 × `TS6133: 'React' is declared but its value is never read`, porque o `tsconfig` usa
  `"jsx": "react-jsx"` e o import do `React` não é mais necessário: `AdminFinance`,
  `AdminNotifications`, `AdminStore`, `Booking`, `Dashboard`, `Fidelidade`, `Gallery`,
  `Landing` e `TrimClub`;
- 1 × `TS6133: 'setExpenses' is declared but its value is never read` em `AdminFinance.tsx`.
  A tela não tem rota de listagem de despesas, e a lista fica sempre vazia.

**Dependências (#8).** `npm audit` acusa **6 vulnerabilidades: 5 high e 1 moderate**. Todas são
transitivas, e o `npm audit fix` sem `--force` corrige todas, sem mudar o `package.json`.

| Pacote | Antes | Depois | Severidade | Vem de |
|---|---|---|---|---|
| vite | 8.3.1 | 8.3.8 | high | devDependency direta, vitest, plugin-react |
| follow-redirects | 1.16.0 | 1.16.3 | high | axios |
| compression | 1.8.1 | 1.8.2 | high | serve |
| serve | 14.2.6 | 14.2.8 | high (por compression) | dependência direta |
| source-map-js | 1.2.1 | 1.2.4 | high | postcss (vite) |
| fast-uri | 3.1.8 | 3.1.9 | moderate | ajv (serve) |

A CI só falha em alerta **crítico** (`npm audit --audit-level=critical`, #41). Por isso esses
alertas high passaram.

Valor: o deploy no Render (`serve`) e o `axios` do navegador deixam de usar versões com
advisories conhecidos, e um erro de tipo novo passa a ser pego no PR.

## Regras

1. Os 10 erros são corrigidos sem mudar o comportamento das telas:
   - o import `React` sem uso sai, e os hooks continuam importados;
   - em `AdminFinance`, `const [expenses] = useState<any[]>([])`. O setter volta quando existir
     a rota de despesas. O `any` fica, porque tipar a tela está fora desta spec.
2. Um script `typecheck` (`tsc --noEmit`) entra no `package.json`, e o `build` passa a ser
   `tsc --noEmit && vite build`.
3. A CI ganha o passo **Tipos (tsc)** (`npm run typecheck`) no job do frontend, antes dos
   testes. O passo "Build sem VITE_API_URL falha" continua valendo: com os tipos checados antes,
   ele só pode falhar por falta da variável.
4. `npm audit fix` (sem `--force`): só o `package-lock.json` muda.
5. O passo do npm audit na CI sobe de `--audit-level=critical` para `--audit-level=high`, como a
   #8 propõe. O pip-audit continua só em crítico, porque o backend ainda tem alertas high
   (python-multipart e starlette) que ficam para outra issue.

## Fora do escopo

- Tipar os `any` das páginas antigas e ligar regras mais estritas no `tsconfig`.
- Os alertas high do pip-audit.
- Atualizar versões major (o `npm audit fix --force` não é usado).

## Critérios de aceitação

- [ ] `npm run typecheck` termina sem erros.
- [ ] Reintroduzir um import sem uso (por exemplo, `import React` em `Gallery.tsx`) faz
      `npm run typecheck` e `npm run build` falharem.
- [ ] `npm audit --audit-level=high` termina com 0 vulnerabilidades.
- [ ] Voltar o `package-lock.json` da `main` faz `npm audit --audit-level=high` falhar.
- [ ] `npm test` (Vitest) e `npm run build` com `VITE_API_URL` continuam verdes, e o build sem
      `VITE_API_URL` continua falhando.
- [ ] CI verde.
