import shared from '../../pages/AdminShared.module.css';
import type { Redemption, Wallet } from '../../hooks/useLoyaltyAdmin';
import { formatPoints } from '../../utils/loyalty';
import { formatShopDateTime } from '../../utils/shopDate';

// Histórico de resgates no painel, só de leitura (SPEC/2026-11-26-painel-fidelidade.md): a data,
// o cliente (o nome vem da lista de carteiras), o prêmio e os pontos, o mais novo primeiro.

type Props = {
  redemptions: Redemption[];
  wallets: Wallet[];
};

const RedemptionTable = ({ redemptions, wallets }: Props) => {
  if (redemptions.length === 0) return <p>Nenhum resgate ainda.</p>;
  const names = new Map(wallets.map((w) => [w.user_id, w.full_name]));
  return (
    <table className={shared.table} aria-label="Resgates">
      <thead>
        <tr>
          <th>Data</th>
          <th>Cliente</th>
          <th>Prêmio</th>
          <th>Pontos</th>
        </tr>
      </thead>
      <tbody>
        {redemptions.map((redemption) => (
          <tr key={redemption.id}>
            <td>{formatShopDateTime(redemption.redeemed_at)}</td>
            <td style={{ color: '#fff', fontWeight: 500 }}>{names.get(redemption.user_id) ?? 'Cliente não encontrado'}</td>
            <td>{redemption.reward.name}</td>
            <td>{formatPoints(redemption.points_spent)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default RedemptionTable;
