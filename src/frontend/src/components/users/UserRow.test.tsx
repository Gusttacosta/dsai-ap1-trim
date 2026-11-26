// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AdminUser } from '../../hooks/useAdminUsers';
import UserRow from './UserRow';

// Linha da tabela de usuários (SPEC/2026-11-25-admin-usuarios.md).

afterEach(cleanup);

const ANA: AdminUser = {
  id: 'a1',
  email: 'ana@teste.com',
  full_name: 'Ana',
  phone: null,
  role: 'client',
  is_active: true,
  email_verified: true,
  must_change_password: false,
};

function renderRow(user: AdminUser = ANA, { isSelf = false, busy = false } = {}) {
  const handlers = { onChangeRole: vi.fn(), onSetActive: vi.fn(), onGeneratePassword: vi.fn() };
  render(
    <table>
      <tbody>
        <UserRow user={user} isSelf={isSelf} busy={busy} {...handlers} />
      </tbody>
    </table>,
  );
  return handlers;
}

const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }));

describe('UserRow', () => {
  it('mostra nome, e-mail, perfil e situação', () => {
    renderRow();
    expect(screen.getByRole('row', { name: 'Ana' }).textContent).toContain('ana@teste.com');
    expect((screen.getByLabelText('Perfil de Ana') as HTMLSelectElement).value).toBe('client');
    expect(screen.getByText('Ativo')).toBeTruthy();
    expect(screen.queryByText('Troca de senha pendente')).toBeNull();
  });

  it('trocar o perfil chama onChangeRole', () => {
    const { onChangeRole } = renderRow();
    fireEvent.change(screen.getByLabelText('Perfil de Ana'), { target: { value: 'barber' } });
    expect(onChangeRole).toHaveBeenCalledWith(ANA, 'barber');
  });

  it('desativar pede confirmação; "Voltar" não chama nada', () => {
    const { onSetActive } = renderRow();

    click('Desativar');
    expect(screen.getByText('Desativar esta conta?')).toBeTruthy();
    click('Voltar');
    expect(onSetActive).not.toHaveBeenCalled();

    click('Desativar');
    click('Confirmar');
    expect(onSetActive).toHaveBeenCalledWith(ANA, false);
  });

  it('gerar senha temporária pede confirmação', () => {
    const { onGeneratePassword } = renderRow();

    click('Gerar senha temporária');
    expect(onGeneratePassword).not.toHaveBeenCalled();
    click('Confirmar');
    expect(onGeneratePassword).toHaveBeenCalledWith(ANA);
  });

  it('conta desativada: só "Ativar", sem confirmação', () => {
    const { onSetActive } = renderRow({ ...ANA, is_active: false });

    expect(screen.getByText('Desativado')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Gerar senha temporária' })).toBeNull();
    click('Ativar');
    expect(onSetActive).toHaveBeenCalledWith({ ...ANA, is_active: false }, true);
  });

  it('mostra a troca de senha pendente', () => {
    renderRow({ ...ANA, must_change_password: true });
    expect(screen.getByText('Troca de senha pendente')).toBeTruthy();
  });

  it('na linha do próprio admin não há ações nem seletor', () => {
    renderRow({ ...ANA, role: 'admin' }, { isSelf: true });

    expect(screen.queryByRole('combobox')).toBeNull();
    expect(screen.queryByRole('button')).toBeNull();
    expect(screen.getByText('Administrador')).toBeTruthy();
    expect(screen.getByText('Você')).toBeTruthy();
  });

  it('ocupada, desabilita os controles', () => {
    renderRow(ANA, { busy: true });
    expect(screen.getByLabelText('Perfil de Ana')).toHaveProperty('disabled', true);
    expect(screen.getByRole('button', { name: 'Desativar' })).toHaveProperty('disabled', true);
  });
});
