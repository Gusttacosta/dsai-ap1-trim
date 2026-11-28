// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import TrimClub from './TrimClub';

// SPEC/2026-11-25-alembic-migracoes.md: preço mensal da API, plano sem descrição e "Ilimitados" (#16).

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn() } }));
const mocked = api as unknown as { get: ReturnType<typeof vi.fn> };

afterEach(cleanup);

describe('TrimClub', () => {
  it('mostra o preço mensal, as quantidades e aceita plano sem descrição', async () => {
    mocked.get.mockResolvedValue({
      data: [
        { id: 'p1', name: 'Executivo', description: 'Bebida premium, Prioridade na fila', monthly_price: '150.00', included_cuts: null, included_shaves: 2 },
        { id: 'p2', name: 'Básico', description: null, monthly_price: '80.00', included_cuts: 2, included_shaves: 0 },
      ],
    });
    render(
      <MemoryRouter>
        <TrimClub />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Cortes: Ilimitados')).toBeTruthy();
    expect(screen.getByText('Barbas: 2 por mês')).toBeTruthy();
    expect(screen.getByText('Cortes: 2 por mês')).toBeTruthy();
    expect(screen.getByText('Prioridade na fila')).toBeTruthy();
    expect(screen.getByText(/R\$ 150,00/)).toBeTruthy();
    expect(screen.queryByText(/NaN/)).toBeNull();
    expect(screen.queryAllByText(/Barbas:/)).toHaveLength(1);
  });
});
