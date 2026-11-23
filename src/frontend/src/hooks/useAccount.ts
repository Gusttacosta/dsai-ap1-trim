import { isAxiosError } from 'axios';
import { useCallback, useEffect, useState } from 'react';
import api from '../api';
import { apiErrorMessage } from '../utils/apiError';

// Dados da conta do usuário logado e as duas ações da página "Minha conta"
// (SPEC/2026-11-22-auth-perfil-senha.md).

export type AccountUser = {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  avatar_url: string | null;
  role: 'admin' | 'barber' | 'client';
  email_verified: boolean;
};

export type ProfileChanges = Partial<Pick<AccountUser, 'full_name' | 'phone' | 'avatar_url'>>;

export type AccountStatus = 'loading' | 'ready' | 'unauthenticated' | 'error';

export function useAccount() {
  const [user, setUser] = useState<AccountUser | null>(null);
  const [status, setStatus] = useState<AccountStatus>('loading');
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    let active = true;
    api
      .get<AccountUser>('/auth/me')
      .then((response) => {
        if (!active) return;
        setUser(response.data);
        setStatus('ready');
      })
      .catch((error) => {
        if (!active) return;
        // 401 depois do refresh falhar, ou 403 sem token: precisa entrar de novo.
        const code = isAxiosError(error) ? error.response?.status : undefined;
        if (code === 401 || code === 403) {
          setStatus('unauthenticated');
        } else {
          setLoadError(apiErrorMessage(error, 'Não foi possível carregar seus dados.'));
          setStatus('error');
        }
      });
    return () => {
      active = false;
    };
  }, []);

  /** Envia só os campos alterados e passa a mostrar o usuário como o backend devolveu. */
  const saveProfile = useCallback(async (changes: ProfileChanges) => {
    const response = await api.put<AccountUser>('/auth/me', changes);
    setUser(response.data);
    return response.data;
  }, []);

  /** Troca a senha e devolve a mensagem de confirmação do backend. */
  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    const response = await api.put<{ message: string }>('/auth/me/password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data.message;
  }, []);

  return { user, status, loadError, saveProfile, changePassword };
}
