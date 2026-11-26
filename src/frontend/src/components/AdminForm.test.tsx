// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { httpError } from '../testUtils/httpError';
import AdminForm, { FormField, StatusBadge } from './AdminForm';

// SPEC/2026-11-26-painel-barbeiros.md: a moldura comum dos formulários do painel.

afterEach(cleanup);

function renderForm(props: Partial<Parameters<typeof AdminForm>[0]> = {}) {
  const handlers = {
    validate: vi.fn(() => null as string | null),
    save: vi.fn(async () => true),
    onCancel: vi.fn(),
    ...props,
  };
  render(
    <AdminForm title="Formulário" submitLabel="Gravar" errorFallback="Falhou." {...handlers}>
      <FormField id="campo" label="Campo" wide>
        <input id="campo" />
      </FormField>
    </AdminForm>,
  );
  return handlers;
}

const submit = () => fireEvent.click(screen.getByRole('button', { name: 'Gravar' }));

describe('AdminForm', () => {
  it('mostra o título e liga o rótulo ao campo', () => {
    renderForm();
    expect(screen.getByRole('form', { name: 'Formulário' })).toBeTruthy();
    expect(screen.getByLabelText('Campo')).toBeTruthy();
  });

  it('erro de validação aparece e não grava', async () => {
    const { save } = renderForm({ validate: () => 'Campo inválido' });
    submit();
    expect((await screen.findByRole('alert')).textContent).toBe('Campo inválido');
    expect(save).not.toHaveBeenCalled();
  });

  it('sem nada para gravar, diz "Nada mudou."', async () => {
    renderForm({ save: vi.fn(async () => false) });
    submit();
    expect((await screen.findByRole('status')).textContent).toBe('Nada mudou.');
    expect(screen.getByRole('button', { name: 'Gravar' })).toHaveProperty('disabled', false);
  });

  it('enquanto grava, o botão diz "Salvando..." e fica desabilitado', async () => {
    renderForm({ save: () => new Promise<boolean>(() => {}) });
    submit();
    expect(await screen.findByRole('button', { name: 'Salvando...' })).toHaveProperty('disabled', true);
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveProperty('disabled', true);
  });

  it('erro da API mostra a mensagem do backend, ou a padrão', async () => {
    renderForm({ save: vi.fn().mockRejectedValueOnce(httpError(400, 'Recusado.')).mockRejectedValueOnce(httpError(500)) });
    submit();
    expect((await screen.findByRole('alert')).textContent).toBe('Recusado.');
    submit();
    expect((await screen.findByText('Falhou.')).getAttribute('role')).toBe('alert');
  });

  it('"Cancelar" chama onCancel', () => {
    const { onCancel } = renderForm();
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(onCancel).toHaveBeenCalled();
  });
});

describe('StatusBadge', () => {
  it('diz "Ativo" ou "Desativado"', () => {
    render(<><StatusBadge active /><StatusBadge active={false} /></>);
    expect(screen.getByText('Ativo')).toBeTruthy();
    expect(screen.getByText('Desativado')).toBeTruthy();
  });
});
