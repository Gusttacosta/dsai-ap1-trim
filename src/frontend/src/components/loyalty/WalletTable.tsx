import shared from '../../pages/AdminShared.module.css';
import type { Wallet } from '../../hooks/useLoyaltyAdmin';
import { formatPoints } from '../../utils/loyalty';
import styles from '../services/Services.module.css';

// Carteiras dos clientes no painel (SPEC/2026-11-26-painel-fidelidade.md), na ordem do backend
// (do maior saldo para o menor), com "Ajustar pontos" em cada linha.

type Props = {
  wallets: Wallet[];
  /** O formulário de ajuste está aberto: os botões ficam desabilitados. */
  busy: boolean;
  onAdjust: (wallet: Wallet) => void;
};

const WalletTable = ({ wallets, busy, onAdjust }: Props) => {
  if (wallets.length === 0) return <p>Nenhuma carteira ainda.</p>;
  return (
    <table className={shared.table} aria-label="Carteiras">
      <thead>
        <tr>
          <th>Cliente</th>
          <th>Saldo</th>
          <th>Total acumulado</th>
          <th>Ações</th>
        </tr>
      </thead>
      <tbody>
        {wallets.map((wallet) => (
          <tr key={wallet.id} aria-label={wallet.full_name}>
            <td style={{ color: '#fff', fontWeight: 500 }}>
              {wallet.full_name}
              <span className={styles.description}>{wallet.email}</span>
            </td>
            <td>{formatPoints(wallet.balance)}</td>
            <td>{formatPoints(wallet.lifetime_points)}</td>
            <td>
              <button className={shared.btnIcon} onClick={() => onAdjust(wallet)} disabled={busy}>
                Ajustar pontos
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default WalletTable;
