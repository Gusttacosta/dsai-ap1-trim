import shared from '../pages/AdminShared.module.css';

// "Anterior", "Página X de Y" e "Próxima" de uma listagem paginada do painel
// (SPEC/2026-11-25-admin-usuarios.md). Com uma página só, não aparece.

type Props = {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
  disabled?: boolean;
};

const Pagination = ({ page, totalPages, onChange, disabled = false }: Props) => {
  if (totalPages <= 1) return null;
  return (
    <nav className={shared.pagination} aria-label="Paginação">
      <button className={shared.btnIcon} onClick={() => onChange(page - 1)} disabled={disabled || page <= 1}>
        Anterior
      </button>
      <span>Página {page} de {totalPages}</span>
      <button className={shared.btnIcon} onClick={() => onChange(page + 1)} disabled={disabled || page >= totalPages}>
        Próxima
      </button>
    </nav>
  );
};

export default Pagination;
