import shared from '../../pages/AdminShared.module.css';
import { useInventoryHistory, type Product } from '../../hooks/useInventory';
import { MOVEMENT_LABELS, formatSignedUnits } from '../../utils/inventory';
import { formatShopDateTime } from '../../utils/shopDate';
import LoadState from '../LoadState';

// Histórico das movimentações de um produto, só de leitura (SPEC/2026-11-26-painel-estoque.md):
// a data no fuso da barbearia, o tipo, a quantidade com o sinal e a observação, a mais nova
// primeiro. Quem usa recria o componente (`key`) para recarregar depois de uma movimentação.

type Props = {
  product: Product;
  onClose: () => void;
};

const InventoryHistory = ({ product, onClose }: Props) => {
  const { movements, status, loadError, reload } = useInventoryHistory(product.id);
  const title = `Histórico de ${product.name}`;
  return (
    <section aria-label={title}>
      <div className={shared.sectionHeader}>
        <h3 className={shared.title}>{title}</h3>
        <button className={shared.btnIcon} onClick={onClose}>
          Fechar histórico
        </button>
      </div>
      <LoadState status={status} loadError={loadError} reload={reload} loadingText="Carregando histórico...">
        {movements.length === 0 ? (
          <p>Nenhuma movimentação ainda.</p>
        ) : (
          <table className={shared.table} aria-label="Movimentações">
            <thead>
              <tr>
                <th>Data</th>
                <th>Tipo</th>
                <th>Quantidade</th>
                <th>Observação</th>
              </tr>
            </thead>
            <tbody>
              {movements.map((movement) => (
                <tr key={movement.id}>
                  <td>{formatShopDateTime(movement.created_at)}</td>
                  <td>{MOVEMENT_LABELS[movement.movement_type]}</td>
                  <td>{formatSignedUnits(movement.quantity)}</td>
                  <td>{movement.notes ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </LoadState>
    </section>
  );
};

export default InventoryHistory;
