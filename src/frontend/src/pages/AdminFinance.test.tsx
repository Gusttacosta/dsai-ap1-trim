// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import AdminFinance from './AdminFinance';

// SPEC/2026-11-26-painel-despesas.md: o Financeiro aponta para a aba Despesas, no lugar da tabela
// que nunca era preenchida e do botão sem ação.

vi.mock('../api', () => ({ default: { get: vi.fn() } }));
const mockedGet = api.get as unknown as ReturnType<typeof vi.fn>;

afterEach(cleanup);

describe('AdminFinance', () => {
  it('leva às despesas pelo link, sem a tabela falsa nem o botão sem ação', async () => {
    mockedGet.mockResolvedValue({ data: { total_revenue: 1000, total_expenses: 400, net_profit: 600 } });
    render(
      <MemoryRouter>
        <AdminFinance />
      </MemoryRouter>,
    );

    expect(await screen.findByText('R$ 600.00')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Gerenciar despesas' }).getAttribute('href')).toBe('/admin/despesas');
    expect(screen.queryByRole('table')).toBeNull();
    expect(screen.queryByRole('button', { name: '+ Lançar Despesa' })).toBeNull();
    expect(mockedGet).toHaveBeenCalledWith('/reports/financial-summary');
  });
});
