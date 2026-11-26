import React, { useState } from 'react';
import shared from '../../pages/AdminShared.module.css';
import { ROLE_LABELS, ROLES, type UserRole } from '../../utils/roles';

// Busca por nome ou e-mail e filtro de perfil do painel de usuários
// (SPEC/2026-11-25-admin-usuarios.md). A busca vai ao enviar o formulário, não a cada tecla.

type Props = {
  role: UserRole | '';
  onSearch: (q: string) => void;
  onRoleChange: (role: UserRole | '') => void;
};

const UserFilters = ({ role, onSearch, onRoleChange }: Props) => {
  const [draft, setDraft] = useState('');

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    onSearch(draft);
  };

  return (
    <form className={shared.filters} onSubmit={submit} role="search">
      <input
        type="search"
        aria-label="Buscar por nome ou e-mail"
        placeholder="Nome ou e-mail"
        value={draft}
        maxLength={100}
        onChange={(e) => setDraft(e.target.value)}
      />
      <button type="submit" className={shared.btnIcon}>Buscar</button>
      <select aria-label="Perfil" value={role} onChange={(e) => onRoleChange(e.target.value as UserRole | '')}>
        <option value="">Todos os perfis</option>
        {ROLES.map((r) => (
          <option key={r} value={r}>{ROLE_LABELS[r]}</option>
        ))}
      </select>
    </form>
  );
};

export default UserFilters;
