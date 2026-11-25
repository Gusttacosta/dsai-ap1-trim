import { describe, expect, it } from 'vitest';
import type { UserConfig } from 'vite';
import config from './vite.config';

// Porta fixa do Vite (#11, SPEC/2026-11-25-vite-porta-fixa.md).
type ConfigFn = (env: { command: 'serve' | 'build'; mode: string }) => UserConfig;
const resolve = config as unknown as ConfigFn;

describe('vite.config', () => {
  it('npm run dev usa a 5173 e falha se ela estiver ocupada, sem trocar de porta', () => {
    const { server } = resolve({ command: 'serve', mode: 'development' });
    expect(server?.port).toBe(5173);
    expect(server?.strictPort).toBe(true);
  });

  it('npm run preview também não troca de porta em silêncio', () => {
    const { preview } = resolve({ command: 'serve', mode: 'production' });
    expect(preview?.port).toBe(4173);
    expect(preview?.strictPort).toBe(true);
  });
});
