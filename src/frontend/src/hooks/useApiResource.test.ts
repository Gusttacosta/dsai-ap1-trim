// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { httpError } from '../testUtils/httpError';
import { useApiResource } from './useApiResource';

// Carga genérica usada pelo painel de serviços e por Meus agendamentos
// (SPEC/2026-11-23-painel-servicos.md e SPEC/2026-11-25-meus-agendamentos.md).

const FALLBACK = 'Não foi possível carregar.';

describe('useApiResource', () => {
  it('começa carregando, com o valor inicial, e depois mostra o que carregou', async () => {
    const load = vi.fn().mockResolvedValue(['a']);
    const { result } = renderHook(() => useApiResource(load, [] as string[], FALLBACK));

    expect(result.current.status).toBe('loading');
    expect(result.current.data).toEqual([]);
    await waitFor(() => expect(result.current.status).toBe('ready'));
    expect(result.current.data).toEqual(['a']);
    expect(load).toHaveBeenCalledTimes(1);
  });

  it('erro: mostra a mensagem do backend, ou a padrão', async () => {
    const load = vi.fn().mockRejectedValueOnce(httpError(403, 'Acesso negado.')).mockRejectedValueOnce(httpError(500));
    const { result } = renderHook(() => useApiResource(load, 0, FALLBACK));

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.loadError).toBe('Acesso negado.');

    act(() => result.current.reload());
    await waitFor(() => expect(result.current.loadError).toBe(FALLBACK));
  });

  it('"Tentar de novo" carrega outra vez, e setData troca o valor sem carregar', async () => {
    const load = vi.fn().mockRejectedValueOnce(httpError(500)).mockResolvedValue(1);
    const { result } = renderHook(() => useApiResource(load, 0, FALLBACK));
    await waitFor(() => expect(result.current.status).toBe('error'));

    act(() => result.current.reload());
    await waitFor(() => expect(result.current.status).toBe('ready'));
    expect(result.current.data).toBe(1);

    act(() => result.current.setData(2));
    expect(result.current.data).toBe(2);
    expect(load).toHaveBeenCalledTimes(2);
  });
});
