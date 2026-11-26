// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ANA, BRUNO, POMADA, makeRedemption, makeWallet } from '../../testUtils/loyalty';
import RedemptionTable from './RedemptionTable';
import WalletTable from './WalletTable';

// SPEC/2026-11-26-painel-fidelidade.md: as carteiras e o histórico de resgates.

afterEach(cleanup);

describe('WalletTable', () => {
  it('mostra o cliente, o saldo e o total acumulado, e "Ajustar pontos" abre o ajuste', () => {
    const onAdjust = vi.fn();
    render(<WalletTable wallets={[makeWallet('u9', { full_name: 'Caio', balance: 1200, lifetime_points: 5000 }), BRUNO]} busy={false} onAdjust={onAdjust} />);
    const row = screen.getByRole('row', { name: 'Caio' });
    expect(within(row).getByText('u9@x.com')).toBeTruthy();
    expect(within(row).getByText('1.200 pts')).toBeTruthy();
    expect(within(row).getByText('5.000 pts')).toBeTruthy();

    fireEvent.click(within(screen.getByRole('row', { name: 'Bruno Reis' })).getByRole('button', { name: 'Ajustar pontos' }));
    expect(onAdjust).toHaveBeenCalledWith(BRUNO);
  });

  it('com o ajuste aberto, os botões ficam desabilitados', () => {
    render(<WalletTable wallets={[ANA]} busy onAdjust={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Ajustar pontos' })).toHaveProperty('disabled', true);
  });

  it('vazia, diz que não há carteiras', () => {
    render(<WalletTable wallets={[]} busy={false} onAdjust={vi.fn()} />);
    expect(screen.getByText('Nenhuma carteira ainda.')).toBeTruthy();
  });
});

describe('RedemptionTable', () => {
  it('mostra a data no fuso da barbearia, o nome do cliente, o prêmio e os pontos', () => {
    render(<RedemptionTable redemptions={[makeRedemption('r1', ANA, POMADA, '2026-11-26T17:30:00Z')]} wallets={[ANA]} />);
    const cells = within(screen.getByRole('table', { name: 'Resgates' })).getAllByRole('cell').map((c) => c.textContent);
    expect(cells).toEqual(['qui., 26/11/2026 às 14:30', 'Ana Lima', 'Pomada', '120 pts']);
  });

  it('o cliente fora da lista de carteiras aparece como "Cliente não encontrado"', () => {
    render(<RedemptionTable redemptions={[makeRedemption('r1', ANA, POMADA)]} wallets={[]} />);
    expect(screen.getByText('Cliente não encontrado')).toBeTruthy();
  });

  it('vazio, diz que não há resgates', () => {
    render(<RedemptionTable redemptions={[]} wallets={[ANA]} />);
    expect(screen.getByText('Nenhum resgate ainda.')).toBeTruthy();
  });
});
