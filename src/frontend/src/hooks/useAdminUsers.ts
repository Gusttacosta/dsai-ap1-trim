import { useCallback } from 'react';
import api from '../api';
import { useApiResource } from './useApiResource';

// Usuários no painel do admin: a página da listagem (GET /auth/users) e as ações sobre um
// usuário (SPEC/2026-11-25-admin-usuarios.md). As ações devolvem o que o backend gravou e
// lançam o erro da API, para quem chamou mostrar a mensagem.

export type UserRole = 'admin' | 'barber' | 'client';

export type AdminUser = {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  role: UserRole;
  is_active: boolean;
  email_verified: boolean;
  must_change_password: boolean;
};

export type UserPage = {
  users: AdminUser[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
};

/** Busca no nome ou e-mail, filtro de perfil ('' = todos) e página, a partir de 1. */
export type UserFilters = { q: string; role: UserRole | ''; page: number };

export const PER_PAGE = 20;
const EMPTY: UserPage = { users: [], total: 0, page: 1, per_page: PER_PAGE, total_pages: 0 };
const LOAD_ERROR = 'Não foi possível carregar os usuários.';

export function useAdminUsers({ q, role, page }: UserFilters) {
  const load = useCallback(async () => {
    const params: Record<string, string | number> = { page, per_page: PER_PAGE };
    if (q.trim()) params.q = q.trim();
    if (role) params.role = role;
    return (await api.get<UserPage>('/auth/users', { params })).data;
  }, [q, role, page]);

  const { data, setData, status, loadError, reload } = useApiResource(load, EMPTY, LOAD_ERROR);

  /** Troca o usuário da página pelo que o backend devolveu. */
  const store = useCallback((saved: AdminUser) => {
    setData((current) => ({ ...current, users: current.users.map((u) => (u.id === saved.id ? saved : u)) }));
    return saved;
  }, []);

  const changeRole = useCallback(
    async (id: string, newRole: UserRole) =>
      store((await api.put<AdminUser>(`/auth/users/${id}/role`, { role: newRole })).data),
    [store],
  );

  const setActive = useCallback(
    async (id: string, isActive: boolean) =>
      store((await api.put<AdminUser>(`/auth/users/${id}/status`, { is_active: isActive })).data),
    [store],
  );

  /**
   * Gera a senha temporária e a devolve para ser mostrada uma vez: ela não fica guardada aqui.
   * O usuário passa a aparecer com a troca de senha pendente.
   */
  const generateTemporaryPassword = useCallback(async (id: string) => {
    const response = await api.post<{ temporary_password: string }>(`/auth/users/${id}/temporary-password`);
    setData((current) => ({
      ...current,
      users: current.users.map((u) => (u.id === id ? { ...u, must_change_password: true } : u)),
    }));
    return response.data.temporary_password;
  }, []);

  return { ...data, status, loadError, reload, changeRole, setActive, generateTemporaryPassword };
}
