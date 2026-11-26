import shared from '../../pages/AdminShared.module.css';
import type { Product } from '../../hooks/useInventory';
import { formatUnits, stockWarning } from '../../utils/inventory';
import { formatPrice } from '../../utils/serviceValidation';
import { StatusBadge } from '../AdminForm';
import styles from '../services/Services.module.css';

// Um produto na tela de estoque (SPEC/2026-11-26-painel-estoque.md): o nome com o SKU, a
// situação, o preço, a quantidade com o aviso de estoque baixo, "Histórico" e "Movimentar".

type Props = {
  product: Product;
  /** Um formulário está aberto: os botões ficam desabilitados. */
  busy: boolean;
  onHistory: (product: Product) => void;
  onMove: (product: Product) => void;
};

const ProductStockRow = ({ product, busy, onHistory, onMove }: Props) => {
  const warning = stockWarning(product);
  return (
    <tr aria-label={product.name} className={product.is_active ? undefined : styles.inactive}>
      <td style={{ color: '#fff', fontWeight: 500 }}>
        {product.name}
        {product.sku && <span className={styles.description}>SKU {product.sku}</span>}
      </td>
      <td>
        <StatusBadge active={product.is_active} />
      </td>
      <td>{formatPrice(product.price)}</td>
      <td>
        {formatUnits(product.stock_quantity)}
        {warning && <span className={shared.stockWarning}>{warning}</span>}
      </td>
      <td>
        <button className={shared.btnIcon} onClick={() => onHistory(product)}>
          Histórico
        </button>
        <button className={shared.btnIcon} onClick={() => onMove(product)} disabled={busy}>
          Movimentar
        </button>
      </td>
    </tr>
  );
};

export default ProductStockRow;
