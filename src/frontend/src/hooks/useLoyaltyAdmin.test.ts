// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { httpError } from '../testUtils/httpError';
import { ANA, BRUNO, CORTE, POMADA, makeRedemption, makeReward, walletResponse } from '../testUtils/loyalty';
import { useAdminRewards, useRedemptions, useWallets } from './useLoyaltyAdmin';

// SPEC/2026-11-26-painel-fidelidade.md: as rotas de /loyalty usadas pelo painel.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock };

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});

async function ready<T extends { status: string }>(hook: () => T) {
  const rendered = renderHook(hook);
  await waitFor(() => expect(rendered.result.current.status).not.toBe('loading'));
  return rendered.result;
}

describe('useAdminRewards', () => {
  it('carrega os prêmios e põe o novo na ordem de custo', async () => {
    mocked.get.mockResolvedValue({ data: [POMADA, CORTE] });
    const result = await ready(() => useAdminRewards());
    expect(mocked.get).toHaveBeenCalledWith('/loyalty/rewards');

    const barba = makeReward('barba', { name: 'Barba', points_cost: 200 });
    mocked.post.mockResolvedValue({ data: barba });
    const input = { name: 'Barba', description: null, points_cost: 200 };
    await act(() => result.current.createReward(input));

    expect(mocked.post).toHaveBeenCalledWith('/loyalty/rewards', input);
    expect(result.current.rewards.map((r) => r.id)).toEqual(['pomada', 'barba', 'corte']);
  });

  it('edita pelo PUT e troca a linha pelo que o backend gravou', async () => {
    mocked.get.mockResolvedValue({ data: [POMADA, CORTE] });
    const result = await ready(() => useAdminRewards());
    mocked.put.mockResolvedValue({ data: { ...POMADA, points_cost: 500 } });

    await act(() => result.current.updateReward('pomada', { points_cost: 500 }));

    expect(mocked.put).toHaveBeenCalledWith('/loyalty/rewards/pomada', { points_cost: 500 });
    expect(result.current.rewards.map((r) => r.id)).toEqual(['corte', 'pomada']);
  });

  it('desativar manda is_active: false e tira o prêmio; a falha lança e o prêmio fica', async () => {
    mocked.get.mockResolvedValue({ data: [POMADA, CORTE] });
    const result = await ready(() => useAdminRewards());

    mocked.put.mockRejectedValueOnce(httpError(404, 'Prêmio não encontrado.'));
    await expect(act(() => result.current.deactivateReward('corte'))).rejects.toThrow();
    expect(result.current.rewards).toHaveLength(2);

    mocked.put.mockResolvedValueOnce({ data: { ...CORTE, is_active: false } });
    await act(() => result.current.deactivateReward('corte'));
    expect(mocked.put).toHaveBeenLastCalledWith('/loyalty/rewards/corte', { is_active: false });
    expect(result.current.rewards.map((r) => r.id)).toEqual(['pomada']);
  });

  it('a falha na carga vira a mensagem da API', async () => {
    mocked.get.mockRejectedValue(httpError(403, 'Acesso restrito a administradores.'));
    const result = await ready(() => useAdminRewards());
    expect(result.current.status).toBe('error');
    expect(result.current.loadError).toBe('Acesso restrito a administradores.');
  });
});

describe('useWallets', () => {
  it('adiciona com os pontos e o motivo na query e reordena pelo saldo, mantendo o cliente', async () => {
    mocked.get.mockResolvedValue({ data: [ANA, BRUNO] });
    const result = await ready(() => useWallets());
    expect(mocked.get).toHaveBeenCalledWith('/loyalty/wallets');
    mocked.post.mockResolvedValue({ data: walletResponse(BRUNO, 240, 240) });

    await act(() => result.current.adjust(BRUNO, 'add', 200, 'Aniversário'));

    expect(mocked.post).toHaveBeenCalledWith('/loyalty/wallet/u2/add', null, {
      params: { points: 200, reason: 'Aniversário' },
    });
    expect(result.current.wallets.map((w) => [w.full_name, w.balance])).toEqual([
      ['Bruno Reis', 240],
      ['Ana Lima', 120],
    ]);
  });

  it('retirar chama o /remove; a falha lança e o saldo fica', async () => {
    mocked.get.mockResolvedValue({ data: [ANA, BRUNO] });
    const result = await ready(() => useWallets());

    mocked.post.mockRejectedValueOnce(httpError(400, 'Saldo insuficiente para retirar 500 pts. O cliente possui 120 pts.'));
    await expect(act(() => result.current.adjust(ANA, 'remove', 500, 'Correção'))).rejects.toThrow();
    expect(result.current.wallets[0].balance).toBe(120);

    mocked.post.mockResolvedValueOnce({ data: walletResponse(ANA, 20) });
    await act(() => result.current.adjust(ANA, 'remove', 100, 'Correção'));
    expect(mocked.post).toHaveBeenLastCalledWith('/loyalty/wallet/u1/remove', null, {
      params: { points: 100, reason: 'Correção' },
    });
    expect(result.current.wallets.map((w) => [w.full_name, w.balance, w.lifetime_points])).toEqual([
      ['Bruno Reis', 40, 40],
      ['Ana Lima', 20, 300],
    ]);
  });
});

describe('useRedemptions', () => {
  it('carrega o histórico de resgates', async () => {
    const redemption = makeRedemption('r1', ANA, POMADA);
    mocked.get.mockResolvedValue({ data: [redemption] });
    const result = await ready(() => useRedemptions());
    expect(mocked.get).toHaveBeenCalledWith('/loyalty/redemptions');
    expect(result.current.redemptions).toEqual([redemption]);
  });
});
