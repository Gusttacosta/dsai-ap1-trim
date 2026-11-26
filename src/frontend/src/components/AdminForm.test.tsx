// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
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

// SPEC/2026-11-26-painel-fidelidade.md: a confirmação antes de gravar (o ajuste de pontos).
describe('AdminForm com confirm', () => {
  const question = 'Adicionar 50 pts a Ana?';

  it('com os campos válidos, mostra a pergunta e só grava no "Confirmar"', async () => {
    const { save } = renderForm({ confirm: () => question });
    submit();
    expect((await screen.findByRole('status')).textContent).toBe(question);
    expect(save).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }));
    await waitFor(() => expect(save).toHaveBeenCalledTimes(1));
  });

  it('campo inválido não chega à pergunta', async () => {
    const confirm = vi.fn(() => question);
    renderForm({ validate: () => 'Campo inválido', confirm });
    submit();
    expect((await screen.findByRole('alert')).textContent).toBe('Campo inválido');
    expect(confirm).not.toHaveBeenCalled();
  });

  it('"Voltar" e mudar um campo voltam ao formulário sem gravar', async () => {
    const { save, onCancel } = renderForm({ confirm: () => question });
    submit();
    fireEvent.click(await screen.findByRole('button', { name: 'Voltar' }));
    expect(screen.queryByText(question)).toBeNull();
    expect(screen.getByRole('button', { name: 'Gravar' })).toBeTruthy();

    submit();
    await screen.findByText(question);
    fireEvent.change(screen.getByLabelText('Campo'), { target: { value: 'outro' } });
    expect(screen.queryByText(question)).toBeNull();
    expect(save).not.toHaveBeenCalled();
    expect(onCancel).not.toHaveBeenCalled();
  });

  it('o erro da API depois de confirmar aparece e volta ao formulário', async () => {
    renderForm({ confirm: () => question, save: vi.fn().mockRejectedValue(httpError(400, 'Saldo insuficiente.')) });
    submit();
    fireEvent.click(await screen.findByRole('button', { name: 'Confirmar' }));
    expect((await screen.findByRole('alert')).textContent).toBe('Saldo insuficiente.');
    expect(screen.queryByText(question)).toBeNull();
    expect(screen.getByRole('button', { name: 'Gravar' })).toBeTruthy();
  });
});

describe('StatusBadge', () => {
  it('diz "Ativo" ou "Desativado"', () => {
    render(<><StatusBadge active /><StatusBadge active={false} /></>);
    expect(screen.getByText('Ativo')).toBeTruthy();
    expect(screen.getByText('Desativado')).toBeTruthy();
  });

  it('mostra o texto dado, com a cor da situação (SPEC/2026-11-26-painel-trim-club.md)', () => {
    render(<><StatusBadge active label="Ativa" /><StatusBadge active={false} label="Vencida" /></>);
    expect(screen.getByText('Ativa').className).toMatch(/badgeActive/);
    expect(screen.getByText('Vencida').className).toMatch(/badgeInactive/);
  });
});
