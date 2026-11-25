# Vite com porta fixa: um processo órfão na 5173 gera erro, e não uma troca silenciosa de porta (2026-11-25)

> Complementa: SPEC/2026-11-16-deploy-render.md (VITE_API_URL obrigatória no build, #4)
> Issue: #11

## O quê e por quê

No Windows, um `npm run dev` encerrado sem Ctrl+C deixa um `node ...vite.js` escutando a 5173.
Sem `--strictPort`, o Vite novo sobe em outra porta sem avisar. O navegador em `localhost:5173`
continua no Vite antigo, que pode apontar para outro backend, inclusive o de produção. Hoje, a
única proteção é lembrar de passar `--port 5173 --strictPort`, como o README pede.

A configuração passa a fixar a porta no `vite.config.ts`. A proteção deixa de depender de quem
roda o comando.

## Critérios de aceitação

- [ ] `server: { port: 5173, strictPort: true }` no `vite.config.ts`: com a porta ocupada, o
  `npm run dev` falha com "porta em uso".
- [ ] `preview: { port: 4173, strictPort: true }`, pelo mesmo motivo, no `npm run preview`.
- [ ] O README deixa de exigir `--port 5173 --strictPort` e mantém o contorno (`netstat`) para
  encerrar o processo órfão.
- [ ] Teste do vitest (`src/frontend/vite.config.test.ts`) que resolve a configuração e falha sem
  a porta fixa.
