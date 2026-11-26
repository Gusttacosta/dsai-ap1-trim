// Perfis de acesso e os nomes deles na tela: "Minha conta" (SPEC/2026-11-22-auth-perfil-senha.md)
// e o painel de usuários (SPEC/2026-11-25-admin-usuarios.md).

export type UserRole = 'admin' | 'barber' | 'client';

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Administrador',
  barber: 'Barbeiro',
  client: 'Cliente',
};

/** Os perfis na ordem em que aparecem nos seletores. */
export const ROLES = Object.keys(ROLE_LABELS) as UserRole[];
