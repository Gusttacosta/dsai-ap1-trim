import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

// Em `npm run dev`, sem VITE_API_URL, usa o backend local. O build exige a
// variável (ver vite.config.ts), então produção nunca cai neste padrão.
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const TOKEN_KEY = 'token';

// Rotas cujo 401 não se resolve com um refresh: credenciais erradas no login,
// sessão encerrada no próprio refresh, ou o logout (SPEC/2026-11-22-auth-refresh-logout.md).
const NO_REFRESH_ROUTES = ['/auth/login', '/auth/refresh', '/auth/logout'];

// withCredentials: o refresh token vai num cookie httpOnly que só o navegador conhece.
export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

type RetriableConfig = InternalAxiosRequestConfig & { _refreshed?: boolean };

let pendingRefresh: Promise<string> | null = null;

/**
 * Troca o cookie de refresh por um access token novo e o guarda.
 * Vários pedidos que recebem 401 ao mesmo tempo compartilham uma única chamada.
 */
export function refreshAccessToken(): Promise<string> {
  pendingRefresh ??= api
    .post('/auth/refresh')
    .then((response) => {
      const token: string = response.data.access_token;
      localStorage.setItem(TOKEN_KEY, token);
      return token;
    })
    .finally(() => {
      pendingRefresh = null;
    });
  return pendingRefresh;
}

function canRefresh(config: RetriableConfig | undefined): config is RetriableConfig {
  if (!config || config._refreshed) return false;
  return !NO_REFRESH_ROUTES.some((route) => config.url?.endsWith(route));
}

api.interceptors.response.use(undefined, async (error: AxiosError) => {
  const config = error.config as RetriableConfig | undefined;
  if (error.response?.status !== 401 || !canRefresh(config)) {
    throw error;
  }
  config._refreshed = true;
  try {
    await refreshAccessToken();
  } catch {
    localStorage.removeItem(TOKEN_KEY);
    throw error;
  }
  return api(config);
});

/** Encerra a sessão no servidor (revoga o refresh token) e apaga o token local. */
export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout');
  } catch {
    // Sem rede ou sessão já encerrada: o token local sai do mesmo jeito.
  } finally {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export default api;
