import type { UserRole } from './roles';

// Para onde vai quem acabou de entrar (SPEC/2026-11-25-admin-usuarios.md): quem está com uma
// senha temporária troca a senha antes de tudo; os outros vão para a área do seu perfil.

export const CHANGE_PASSWORD_PATH = '/trocar-senha';

/** Área inicial do perfil: o cliente no site, o admin e o barbeiro no painel. */
export function homeFor(role: UserRole): string {
  return role === 'client' ? '/' : '/admin';
}

export function pathAfterLogin(user: { role: UserRole; must_change_password?: boolean }): string {
  return user.must_change_password ? CHANGE_PASSWORD_PATH : homeFor(user.role);
}
