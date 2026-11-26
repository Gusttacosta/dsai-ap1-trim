// @vitest-environment jsdom
import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { httpError, networkError } from '../testUtils/httpError';
import { useRowAction } from './useRowAction';

// Ação de uma linha dos painéis (SPEC/2026-11-25-admin-usuarios.md).

describe('useRowAction', () => {
  it('ocupa a linha enquanto a ação roda e mostra a mensagem no fim', async () => {
    const { result } = renderHook(() => useRowAction());
    let finish: (value: string) => void = () => {};
    let returned: Promise<string | undefined> = Promise.resolve(undefined);

    act(() => {
      returned = result.current.run('l1', () => new Promise<string>((resolve) => (finish = resolve)), 'Feito.');
    });
    expect(result.current.busyId).toBe('l1');

    await act(async () => {
      finish('resultado');
      expect(await returned).toBe('resultado');
    });
    expect(result.current.busyId).toBeNull();
    expect(result.current.message).toBe('Feito.');
    expect(result.current.actionError).toBe('');
  });

  it.each([
    ['a mensagem do backend', httpError(400, 'Recusado.'), 'Recusado.'],
    ['a mensagem padrão', httpError(500), 'Não foi possível concluir a ação.'],
    ['sem conexão', networkError(), /Sem conexão/],
  ])('erro mostra %s, libera a linha e devolve undefined', async (_, error, expected) => {
    const { result } = renderHook(() => useRowAction());

    let returned: unknown = 'não rodou';
    await act(async () => {
      returned = await result.current.run('l1', () => Promise.reject(error), 'Feito.');
    });

    expect(returned).toBeUndefined();
    expect(result.current.actionError).toMatch(expected);
    expect(result.current.message).toBe('');
    expect(result.current.busyId).toBeNull();
  });

  it('uma ação nova e o clear apagam o resultado anterior', async () => {
    const { result } = renderHook(() => useRowAction());
    await act(() => result.current.run('l1', () => Promise.reject(httpError(400, 'Recusado.')), 'x'));

    await act(() => result.current.run('l2', () => Promise.resolve(1), 'Feito.'));
    expect(result.current.actionError).toBe('');

    act(() => result.current.clear());
    expect(result.current.message).toBe('');
  });
});
