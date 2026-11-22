// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import { afterEach, describe, expect, it, vi } from 'vitest';
import PasswordForm from './PasswordForm';

// SPEC/2026-11-22-auth-perfil-senha.md: formulário de troca de senha da página "Minha conta".

const SUCCESS = 'Senha alterada. As outras sessões foram encerradas.';

function http400(detail: string): AxiosError {
  const config = { headers: {} } as InternalAxiosRequestConfig;
  const response = { status: 400, data: { detail }, statusText: '', headers: {}, config } as AxiosResponse;
  return new AxiosError('HTTP 400', AxiosError.ERR_BAD_REQUEST, config, null, response);
}

function fill(current: string, next: string, confirmation = next) {
  fireEvent.change(screen.getByLabelText('Senha atual'), { target: { value: current } });
  fireEvent.change(screen.getByLabelText('Nova senha'), { target: { value: next } });
  fireEvent.change(screen.getByLabelText('Confirme a nova senha'), { target: { value: confirmation } });
  fireEvent.click(screen.getByRole('button', { name: 'Trocar senha' }));
}

const valueOf = (label: string) => (screen.getByLabelText(label) as HTMLInputElement).value;

afterEach(cleanup);

describe('PasswordForm', () => {
  it('troca a senha, mostra a confirmação do backend e limpa os campos', async () => {
    const onChangePassword = vi.fn().mockResolvedValue(SUCCESS);
    render(<PasswordForm onChangePassword={onChangePassword} />);

    fill('senhaAtual1', 'senhaNova2');

    expect(await screen.findByRole('status')).toHaveProperty('textContent', SUCCESS);
    expect(onChangePassword).toHaveBeenCalledWith('senhaAtual1', 'senhaNova2');
    expect([valueOf('Senha atual'), valueOf('Nova senha'), valueOf('Confirme a nova senha')]).toEqual(['', '', '']);
  });

  it.each([
    ['', 'senhaNova2', 'senhaNova2', 'Informe a senha atual'],
    ['senhaAtual1', 'curta1', 'curta1', 'Nova senha deve ter no mínimo 8 caracteres'],
    ['senhaAtual1', 'senhaAtual1', 'senhaAtual1', 'A nova senha precisa ser diferente da atual.'],
    ['senhaAtual1', 'senhaNova2', 'senhaNova3', 'A confirmação não é igual à nova senha'],
  ])('atual=%j nova=%j confirmação=%j: mostra o erro e não envia', async (current, next, confirmation, message) => {
    const onChangePassword = vi.fn();
    render(<PasswordForm onChangePassword={onChangePassword} />);

    fill(current, next, confirmation);

    expect(await screen.findByRole('alert')).toHaveProperty('textContent', message);
    expect(onChangePassword).not.toHaveBeenCalled();
  });

  it('senha atual errada: mostra o erro do backend e mantém os campos', async () => {
    const onChangePassword = vi.fn().mockRejectedValue(http400('Senha atual incorreta.'));
    render(<PasswordForm onChangePassword={onChangePassword} />);

    fill('senhaErrada9', 'senhaNova2');

    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Senha atual incorreta.');
    expect(valueOf('Nova senha')).toBe('senhaNova2');
    expect(screen.queryByRole('status')).toBeNull();
  });

  it('os campos são de senha e têm o autocomplete certo', () => {
    render(<PasswordForm onChangePassword={vi.fn()} />);

    expect(screen.getByLabelText('Senha atual').getAttribute('type')).toBe('password');
    expect(screen.getByLabelText('Senha atual').getAttribute('autocomplete')).toBe('current-password');
    expect(screen.getByLabelText('Nova senha').getAttribute('autocomplete')).toBe('new-password');
  });
});
