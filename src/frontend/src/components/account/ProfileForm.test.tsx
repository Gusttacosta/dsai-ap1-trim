// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AccountUser } from '../../hooks/useAccount';
import ProfileForm, { profileChanges } from './ProfileForm';

// SPEC/2026-11-22-auth-perfil-senha.md: formulário de dados pessoais da página "Minha conta".

const USER: AccountUser = {
  id: '1',
  email: 'cliente@teste.com',
  full_name: 'Maria',
  phone: '(91) 99999-0000',
  avatar_url: null,
  role: 'client',
  email_verified: true,
};

function http422(messages: string[]): AxiosError {
  const config = { headers: {} } as InternalAxiosRequestConfig;
  const data = { detail: messages.map((msg) => ({ msg: `Value error, ${msg}` })) };
  const response = { status: 422, data, statusText: '', headers: {}, config } as AxiosResponse;
  return new AxiosError('HTTP 422', AxiosError.ERR_BAD_REQUEST, config, null, response);
}

const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const submit = () => fireEvent.click(screen.getByRole('button', { name: 'Salvar dados' }));

afterEach(cleanup);

describe('profileChanges', () => {
  it('manda só o que mudou, no formato do backend', () => {
    expect(
      profileChanges(USER, { fullName: ' Maria ', phone: '91 99999 0000', avatarUrl: ' https://a.com/f.png ' }),
    ).toEqual({ avatar_url: 'https://a.com/f.png' });
  });

  it('campos apagados viram null', () => {
    expect(profileChanges(USER, { fullName: 'Maria', phone: ' ', avatarUrl: '' })).toEqual({ phone: null });
  });
});

describe('ProfileForm', () => {
  it('começa com os dados do usuário', () => {
    render(<ProfileForm user={USER} onSave={vi.fn()} />);

    expect(screen.getByLabelText('Nome')).toHaveProperty('value', 'Maria');
    expect(screen.getByLabelText('Telefone')).toHaveProperty('value', '(91) 99999-0000');
    expect(screen.getByLabelText('URL da foto')).toHaveProperty('value', '');
  });

  it('salva só os campos alterados e confirma', async () => {
    const onSave = vi.fn().mockResolvedValue(USER);
    render(<ProfileForm user={USER} onSave={onSave} />);

    type('Nome', 'Maria Souza');
    type('Telefone', '9133330000');
    submit();

    expect(await screen.findByRole('status')).toHaveProperty('textContent', 'Dados salvos.');
    expect(onSave).toHaveBeenCalledWith({ full_name: 'Maria Souza', phone: '(91) 3333-0000' });
  });

  it('sem mudanças, não chama o backend', async () => {
    const onSave = vi.fn();
    render(<ProfileForm user={USER} onSave={onSave} />);

    submit();

    expect(await screen.findByRole('status')).toHaveProperty('textContent', 'Nada mudou desde o último salvamento.');
    expect(onSave).not.toHaveBeenCalled();
  });

  it.each([
    ['Nome', 'A', 'Nome deve ter no mínimo 2 caracteres'],
    ['Telefone', '(01) 99999-0000', 'DDD não pode começar com 0'],
    ['URL da foto', 'javascript:alert(1)', 'URL da foto deve começar com http:// ou https:// e ter um endereço'],
  ])('%s inválido (%j) mostra o erro e não envia', async (label, value, message) => {
    const onSave = vi.fn();
    render(<ProfileForm user={USER} onSave={onSave} />);

    type(label, value);
    submit();

    expect(await screen.findByRole('alert')).toHaveProperty('textContent', message);
    expect(onSave).not.toHaveBeenCalled();
  });

  it('mostra o erro do backend em português', async () => {
    const onSave = vi.fn().mockRejectedValue(http422(['Nome deve ter no máximo 255 caracteres']));
    render(<ProfileForm user={USER} onSave={onSave} />);

    type('Nome', 'Outro Nome');
    submit();

    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Nome deve ter no máximo 255 caracteres');
  });

  it('desativa o botão enquanto salva', async () => {
    let finish!: () => void;
    const onSave = vi.fn(() => new Promise<void>((resolve) => (finish = resolve)));
    render(<ProfileForm user={USER} onSave={onSave} />);

    type('Nome', 'Outro Nome');
    submit();

    const button = await screen.findByRole('button', { name: 'Salvando...' });
    expect(button).toHaveProperty('disabled', true);
    finish();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Salvar dados' })).toHaveProperty('disabled', false));
  });

  it('passa a mostrar o que o backend gravou', () => {
    const { rerender } = render(<ProfileForm user={USER} onSave={vi.fn()} />);

    rerender(
      <ProfileForm
        user={{ ...USER, phone: '(91) 3333-0000', full_name: 'Maria S.', avatar_url: 'https://a.com/f.png' }}
        onSave={vi.fn()}
      />,
    );

    expect(screen.getByLabelText('Nome')).toHaveProperty('value', 'Maria S.');
    expect(screen.getByLabelText('Telefone')).toHaveProperty('value', '(91) 3333-0000');
    expect(screen.getByLabelText('URL da foto')).toHaveProperty('value', 'https://a.com/f.png');
  });
});
