import { describe, expect, it } from 'vitest';
import { CHANGE_PASSWORD_PATH, homeFor, pathAfterLogin } from './afterLogin';

// SPEC/2026-11-25-admin-usuarios.md: a troca obrigatória vem antes de entrar.

describe('pathAfterLogin', () => {
  it.each([
    ['client', '/'],
    ['barber', '/admin'],
    ['admin', '/admin'],
  ] as const)('%s sem troca pendente vai para %s', (role, path) => {
    expect(homeFor(role)).toBe(path);
    expect(pathAfterLogin({ role, must_change_password: false })).toBe(path);
  });

  it.each(['client', 'barber', 'admin'] as const)('%s com a troca pendente vai para a troca de senha', (role) => {
    expect(pathAfterLogin({ role, must_change_password: true })).toBe(CHANGE_PASSWORD_PATH);
  });
});
