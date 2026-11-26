import { useCallback } from 'react';
import api from '../api';
import { useApiResource } from './useApiResource';

// Lista de nomes do painel (categorias de despesa e tags da galeria): carrega de `path`, cria
// com POST, renomeia com PUT `path/{id}` e apaga com DELETE, mantendo a ordem alfabética do
// backend (SPEC/2026-11-26-painel-despesas.md e SPEC/2026-11-26-painel-galeria.md). As ações
// devolvem o que o backend gravou e lançam o erro da API, para quem chamou mostrar a mensagem.

export type NamedItem = { id: string; name: string };

export const byName = (a: NamedItem, b: NamedItem) => a.name.localeCompare(b.name, 'pt-BR', { sensitivity: 'base' });

/** Põe `saved` na lista, no lugar do item de mesmo id ou como novo, e ordena. */
export function upsert<T extends { id: string }>(list: T[], saved: T, order: (a: T, b: T) => number): T[] {
  return [...list.filter((item) => item.id !== saved.id), saved].sort(order);
}

export function useNameList<T extends NamedItem>(path: string, loadErrorText: string) {
  const load = useCallback(async () => (await api.get<T[]>(path)).data, [path]);
  const { data: items, setData, status, loadError, reload } = useApiResource(load, [] as T[], loadErrorText);

  const store = useCallback((saved: T) => {
    setData((current) => upsert(current, saved, byName));
    return saved;
  }, []);

  const create = useCallback(async (name: string) => store((await api.post<T>(path, { name })).data), [path, store]);

  const rename = useCallback(
    async (id: string, name: string) => store((await api.put<T>(`${path}/${id}`, { name })).data),
    [path, store],
  );

  const remove = useCallback(
    async (id: string) => {
      await api.delete(`${path}/${id}`);
      setData((current) => current.filter((item) => item.id !== id));
    },
    [path],
  );

  return { items, status, loadError, reload, create, rename, remove };
}

export type NameListResource<T extends NamedItem> = ReturnType<typeof useNameList<T>>;
