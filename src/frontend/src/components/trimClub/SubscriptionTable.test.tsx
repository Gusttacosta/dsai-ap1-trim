// @vitest-environment jsdom
import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { BASICO, makeSubscription } from '../../testUtils/trimClub';
import SubscriptionTable from './SubscriptionTable';

// SPEC/2026-11-26-painel-trim-club.md: a lista de assinantes do painel.

afterEach(cleanup);

describe('SubscriptionTable', () => {
  it('mostra cliente, plano, datas e situação', () => {
    const ativa = makeSubscription('a', { user_id: 'u1' });
    const vencida = makeSubscription('b', { user_id: 'u2', status: 'past_due', plan: BASICO, end_date: '2026-11-20' });
    const cancelada = makeSubscription('c', { user_id: 'u3', status: 'canceled' });
    render(
      <SubscriptionTable
        subscriptions={[ativa, vencida, cancelada]}
        subscribers={{ u1: { full_name: 'Ana Souza', email: 'ana@x.com' }, u2: { full_name: 'Bruno', email: 'b@x.com' }, u3: null }}
      />,
    );

    const ana = within(screen.getByRole('row', { name: 'Ana Souza' }));
    expect(ana.getByText('ana@x.com')).toBeTruthy();
    expect(ana.getByText('Ouro')).toBeTruthy();
    expect(ana.getByText('26/11/2026')).toBeTruthy();
    expect(ana.getByText('26/12/2026')).toBeTruthy();
    expect(ana.getByText('Ativa')).toBeTruthy();

    const bruno = within(screen.getByRole('row', { name: 'Bruno' }));
    expect(bruno.getByText('Básico')).toBeTruthy();
    expect(bruno.getByText('20/11/2026')).toBeTruthy();
    expect(bruno.getByText('Vencida')).toBeTruthy();

    expect(within(screen.getByRole('row', { name: 'Cliente não encontrado' })).getByText('Cancelada')).toBeTruthy();
  });

  it('sem assinaturas, diz que não há assinantes', () => {
    render(<SubscriptionTable subscriptions={[]} subscribers={{}} />);
    expect(screen.getByText('Nenhum assinante ainda.')).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
  });
});
