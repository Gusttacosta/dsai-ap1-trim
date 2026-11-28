import type { ReactNode } from 'react';
import shared from '../../pages/AdminShared.module.css';
import type { Photo } from '../../hooks/useGallery';
import { formatShopDate } from '../../utils/shopDate';

// Tabela de fotos da moderação (SPEC/2026-11-26-painel-galeria.md): miniatura, barbeiro,
// descrição, tags, data de envio e as ações de cada foto, que quem usa fornece.

type Props = {
  /** Nome acessível da tabela ("Pendentes", "Publicadas"). */
  label: string;
  photos: Photo[];
  empty: string;
  nameOf: (barberId: string) => string;
  actions: (photo: Photo) => ReactNode;
};

/** Nome da linha: a descrição, ou o id quando a foto não tem descrição. */
export const photoLabel = (photo: Photo) => photo.description || `Foto ${photo.id}`;

const PhotoTable = ({ label, photos, empty, nameOf, actions }: Props) => {
  if (photos.length === 0) return <p>{empty}</p>;
  return (
    <table className={shared.table} aria-label={label}>
      <thead>
        <tr>
          <th>Foto</th>
          <th>Barbeiro</th>
          <th>Descrição</th>
          <th>Tags</th>
          <th>Enviada em</th>
          <th>Ações</th>
        </tr>
      </thead>
      <tbody>
        {photos.map((photo) => (
          <tr key={photo.id} aria-label={photoLabel(photo)}>
            <td>
              <img src={photo.image_url} alt={photoLabel(photo)} style={{ width: 72, height: 72, objectFit: 'cover', borderRadius: 8 }} />
            </td>
            <td>{nameOf(photo.barber_id)}</td>
            <td style={{ color: '#fff' }}>{photo.description ?? '—'}</td>
            <td>{photo.tags.map((t) => t.name).join(', ') || '—'}</td>
            <td>{formatShopDate(photo.created_at)}</td>
            <td>{actions(photo)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default PhotoTable;
