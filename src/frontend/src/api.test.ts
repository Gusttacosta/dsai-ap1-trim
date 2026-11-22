import { AxiosError, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, logout, TOKEN_KEY } from './api';

// Renovação do access token e logout (SPEC/2026-11-22-auth-refresh-logout.md).
// O backend é trocado por um adapter falso que responde por rota e anota os pedidos.

type Reply = { status: number; data?: unknown };
type Route = (config: InternalAxiosRequestConfig) => Reply | Promise<Reply>;

let routes: Record<string, Route>;
let calls: { url: string; authorization?: string }[];
let storage: Map<string, string>;

const fakeBackend: AxiosAdapter = async (config) => {
  const url = config.url ?? '';
  calls.push({ url, authorization: config.headers?.Authorization as string | undefined });
  const route = routes[url];
  const reply = route ? await route(config) : { status: 404 };
  const response: AxiosResponse = {
    data: reply.data,
    status: reply.status,
    statusText: String(reply.status),
    headers: {},
    config,
  };
  if (reply.status >= 400) {
    throw new AxiosError(`HTTP ${reply.status}`, AxiosError.ERR_BAD_REQUEST, config, null, response);
  }
  return response;
};

/** Rota protegida que só aceita o access token `aceito`. */
const protectedRoute =
  (accepted: string): Route =>
  (config) =>
    config.headers?.Authorization === `Bearer ${accepted}`
      ? { status: 200, data: { ok: true } }
      : { status: 401, data: { detail: 'Token inválido ou expirado.' } };

const refreshTo =
  (token: string): Route =>
  () => ({ status: 200, data: { access_token: token } });

const countOf = (url: string) => calls.filter((c) => c.url === url).length;

beforeEach(() => {
  storage = new Map();
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => storage.get(k) ?? null,
    setItem: (k: string, v: string) => void storage.set(k, v),
    removeItem: (k: string) => void storage.delete(k),
  });
  calls = [];
  routes = {};
  api.defaults.adapter = fakeBackend;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('api', () => {
  it('manda o cookie do refresh (withCredentials)', () => {
    expect(api.defaults.withCredentials).toBe(true);
  });

  it('com o access token vencido, renova pelo /auth/refresh e repete o pedido', async () => {
    storage.set(TOKEN_KEY, 'vencido');
    routes['/auth/me'] = protectedRoute('novo');
    routes['/auth/refresh'] = refreshTo('novo');

    const response = await api.get('/auth/me');

    expect(response.data).toEqual({ ok: true });
    expect(storage.get(TOKEN_KEY)).toBe('novo');
    expect(calls.map((c) => [c.url, c.authorization])).toEqual([
      ['/auth/me', 'Bearer vencido'],
      ['/auth/refresh', 'Bearer vencido'],
      ['/auth/me', 'Bearer novo'],
    ]);
  });

  it('vários 401 ao mesmo tempo compartilham um único refresh', async () => {
    storage.set(TOKEN_KEY, 'vencido');
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    routes['/a'] = protectedRoute('novo');
    routes['/b'] = protectedRoute('novo');
    routes['/c'] = protectedRoute('novo');
    routes['/auth/refresh'] = async () => {
      await gate;
      return { status: 200, data: { access_token: 'novo' } };
    };

    const pending = Promise.all([api.get('/a'), api.get('/b'), api.get('/c')]);
    await vi.waitFor(() => expect(countOf('/auth/refresh')).toBe(1));
    release();
    const responses = await pending;

    expect(responses.map((r) => r.status)).toEqual([200, 200, 200]);
    expect(countOf('/auth/refresh')).toBe(1);
  });

  it('um refresh depois do outro faz duas chamadas (o compartilhado não fica preso)', async () => {
    storage.set(TOKEN_KEY, 'vencido');
    routes['/auth/me'] = protectedRoute('segundo');
    let issued = 0;
    routes['/auth/refresh'] = () => ({ status: 200, data: { access_token: ++issued === 1 ? 'primeiro' : 'segundo' } });

    await expect(api.get('/auth/me')).rejects.toMatchObject({ response: { status: 401 } });
    const response = await api.get('/auth/me');

    expect(response.status).toBe(200);
    expect(countOf('/auth/refresh')).toBe(2);
  });

  it('se o refresh falha, apaga o token local e devolve o 401 original', async () => {
    storage.set(TOKEN_KEY, 'vencido');
    routes['/auth/me'] = protectedRoute('nunca');
    routes['/auth/refresh'] = () => ({ status: 401, data: { detail: 'Sessão inválida ou expirada.' } });

    const error = await api.get('/auth/me').catch((e: AxiosError) => e);

    expect(error).toBeInstanceOf(AxiosError);
    expect((error as AxiosError).config?.url).toBe('/auth/me');
    expect((error as AxiosError).response?.status).toBe(401);
    expect(storage.has(TOKEN_KEY)).toBe(false);
    expect(countOf('/auth/refresh')).toBe(1);
  });

  it('o pedido repetido que volta 401 não dispara outro refresh', async () => {
    storage.set(TOKEN_KEY, 'vencido');
    routes['/auth/me'] = protectedRoute('nunca');
    routes['/auth/refresh'] = refreshTo('novo-mas-recusado');

    await expect(api.get('/auth/me')).rejects.toMatchObject({ response: { status: 401 } });

    expect(countOf('/auth/me')).toBe(2);
    expect(countOf('/auth/refresh')).toBe(1);
  });

  it.each(['/auth/login', '/auth/refresh', '/auth/logout'])('o 401 de %s não dispara refresh', async (url) => {
    routes[url] = () => ({ status: 401, data: { detail: 'E-mail ou senha incorretos' } });

    await expect(api.post(url)).rejects.toMatchObject({ response: { status: 401 } });

    expect(calls.map((c) => c.url)).toEqual([url]);
  });

  it('erros que não são 401 passam direto', async () => {
    storage.set(TOKEN_KEY, 'valido');
    routes['/services'] = () => ({ status: 500 });

    await expect(api.get('/services')).rejects.toMatchObject({ response: { status: 500 } });

    expect(countOf('/auth/refresh')).toBe(0);
    expect(storage.get(TOKEN_KEY)).toBe('valido');
  });
});

describe('logout', () => {
  it('encerra a sessão no servidor e apaga o token local', async () => {
    storage.set(TOKEN_KEY, 'valido');
    routes['/auth/logout'] = () => ({ status: 200, data: { message: 'Logout efetuado com sucesso.' } });

    await logout();

    expect(calls.map((c) => c.url)).toEqual(['/auth/logout']);
    expect(storage.has(TOKEN_KEY)).toBe(false);
  });

  it('apaga o token local mesmo se o servidor falhar', async () => {
    storage.set(TOKEN_KEY, 'valido');
    routes['/auth/logout'] = () => ({ status: 503 });

    await expect(logout()).resolves.toBeUndefined();

    expect(storage.has(TOKEN_KEY)).toBe(false);
  });
});
