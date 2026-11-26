// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import UserFilters from './UserFilters';

// Busca e filtro de perfil do painel de usuários (SPEC/2026-11-25-admin-usuarios.md).

afterEach(cleanup);

describe('UserFilters', () => {
  it('busca só ao enviar, com o texto digitado', () => {
    const onSearch = vi.fn();
    render(<UserFilters role="" onSearch={onSearch} onRoleChange={vi.fn()} />);

    fireEvent.change(screen.getByLabelText('Buscar por nome ou e-mail'), { target: { value: 'ana' } });
    expect(onSearch).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Buscar' }));

    expect(onSearch).toHaveBeenCalledWith('ana');
  });

  it('o perfil muda na hora, e "Todos os perfis" volta a vazio', () => {
    const onRoleChange = vi.fn();
    const { rerender } = render(<UserFilters role="" onSearch={vi.fn()} onRoleChange={onRoleChange} />);

    fireEvent.change(screen.getByLabelText('Perfil'), { target: { value: 'barber' } });
    expect(onRoleChange).toHaveBeenLastCalledWith('barber');

    rerender(<UserFilters role="barber" onSearch={vi.fn()} onRoleChange={onRoleChange} />);
    fireEvent.change(screen.getByLabelText('Perfil'), { target: { value: '' } });
    expect(onRoleChange).toHaveBeenLastCalledWith('');
  });
});
