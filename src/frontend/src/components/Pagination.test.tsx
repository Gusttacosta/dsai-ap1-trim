// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Pagination from './Pagination';

// Paginação das listagens do painel (SPEC/2026-11-25-admin-usuarios.md).

afterEach(cleanup);

const button = (name: string) => screen.getByRole('button', { name });

describe('Pagination', () => {
  it('com uma página só, não aparece', () => {
    render(<Pagination page={1} totalPages={1} onChange={vi.fn()} />);
    expect(screen.queryByRole('navigation')).toBeNull();
  });

  it('no meio, anda para os dois lados', () => {
    const onChange = vi.fn();
    render(<Pagination page={2} totalPages={3} onChange={onChange} />);

    expect(screen.getByText('Página 2 de 3')).toBeTruthy();
    fireEvent.click(button('Anterior'));
    fireEvent.click(button('Próxima'));
    expect(onChange.mock.calls).toEqual([[1], [3]]);
  });

  it('nas pontas e desabilitada, os botões param', () => {
    const { rerender } = render(<Pagination page={1} totalPages={3} onChange={vi.fn()} />);
    expect(button('Anterior')).toHaveProperty('disabled', true);
    expect(button('Próxima')).toHaveProperty('disabled', false);

    rerender(<Pagination page={3} totalPages={3} onChange={vi.fn()} />);
    expect(button('Próxima')).toHaveProperty('disabled', true);

    rerender(<Pagination page={2} totalPages={3} onChange={vi.fn()} disabled />);
    expect(button('Anterior')).toHaveProperty('disabled', true);
    expect(button('Próxima')).toHaveProperty('disabled', true);
  });
});
