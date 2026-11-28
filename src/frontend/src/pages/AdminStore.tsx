import { useState } from 'react';
import styles from './AdminShared.module.css';
import InventoryHistory from '../components/inventory/InventoryHistory';
import MovementForm from '../components/inventory/MovementForm';
import ProductStockRow from '../components/inventory/ProductStockRow';
import LoadState, { ActionFeedback } from '../components/LoadState';
import { useAdminProducts, type MovementInput, type Product } from '../hooks/useInventory';
import { lowStockSummary } from '../utils/inventory';

// Aba "Loja & Estoque" do painel, só do admin (SPEC/2026-11-26-painel-estoque.md): todos os
// produtos (ativos, desativados e sem estoque) com a quantidade e o aviso de estoque baixo, o
// histórico de movimentações e o registro de entrada e saída com confirmação.

const AdminStore = () => {
  const { products, status, loadError, reload, registerMovement } = useAdminProducts();
  const [moving, setMoving] = useState<Product | null>(null);
  const [history, setHistory] = useState<Product | null>(null);
  // Muda a cada movimentação: recria o histórico aberto, que carrega de novo.
  const [version, setVersion] = useState(0);
  const [message, setMessage] = useState('');

  const openMove = (product: Product) => {
    setMessage('');
    setMoving(product);
  };

  const move = async (input: MovementInput) => {
    if (!moving) return;
    await registerMovement(moving.id, input);
    setMessage('Movimentação registrada.');
    setMoving(null);
    setVersion((n) => n + 1);
  };

  const summary = lowStockSummary(products);

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>📦 Loja & Estoque</h2>
      </div>

      {moving && (
        <MovementForm
          // Trocar de produto recria o formulário com os dados do novo.
          key={moving.id}
          product={moving}
          onSave={move}
          onCancel={() => setMoving(null)}
        />
      )}

      <ActionFeedback message={message} error="" />

      <LoadState status={status} loadError={loadError} reload={reload} loadingText="Carregando produtos...">
        {summary && (
          <p className={styles.stockAlert} role="note">
            {summary}
          </p>
        )}
        {products.length === 0 ? (
          <p>Nenhum produto cadastrado.</p>
        ) : (
          <table className={styles.table} aria-label="Produtos">
            <thead>
              <tr>
                <th>Produto</th>
                <th>Situação</th>
                <th>Preço</th>
                <th>Estoque</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <ProductStockRow
                  key={product.id}
                  product={product}
                  busy={moving !== null}
                  onHistory={setHistory}
                  onMove={openMove}
                />
              ))}
            </tbody>
          </table>
        )}
      </LoadState>

      {history && (
        <InventoryHistory key={`${history.id}-${version}`} product={history} onClose={() => setHistory(null)} />
      )}
    </div>
  );
};

export default AdminStore;
