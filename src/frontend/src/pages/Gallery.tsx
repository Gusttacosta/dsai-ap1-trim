import { useState } from 'react';
import styles from './Gallery.module.css';
import { useBarberNames, useGalleryTags, usePublicGallery } from '../hooks/useGallery';

// Galeria pública (SPEC/2026-11-26-painel-galeria.md): as fotos aprovadas da API, com o nome do
// barbeiro e o filtro por tag (`GET /gallery?tag_id=`). Antes, fotos e tags eram fixas no código.

const ALL = '';

const Gallery = () => {
  const [tagId, setTagId] = useState(ALL);
  const { data: photos, status, loadError, reload } = usePublicGallery(tagId);
  const { items: tags } = useGalleryTags();
  const { nameOf } = useBarberNames();

  const filter = (id: string, name: string) => (
    <button
      key={id || 'todas'}
      className={`${styles.filterBtn} ${tagId === id ? styles.active : ''}`}
      aria-pressed={tagId === id}
      onClick={() => setTagId(id)}
    >
      {name}
    </button>
  );

  let content;
  if (status === 'loading') {
    content = <p className={styles.subtitle}>Carregando fotos...</p>;
  } else if (status === 'error') {
    content = (
      <div className={styles.header}>
        <p className={styles.subtitle} role="alert">{loadError}</p>
        <button className={styles.filterBtn} onClick={reload}>Tentar de novo</button>
      </div>
    );
  } else if (photos.length === 0) {
    content = <p className={styles.subtitle}>Nenhuma foto por aqui ainda.</p>;
  } else {
    content = (
      <div className={styles.grid}>
        {photos.map((photo) => (
          <figure key={photo.id} className={styles.photoCard} aria-label={photo.description || nameOf(photo.barber_id) || 'Foto'}>
            <div className={styles.imageWrapper}>
              <img src={photo.image_url} alt={photo.description || `Corte por ${nameOf(photo.barber_id)}`} className={styles.imagePlaceholder} />
            </div>
            <figcaption className={styles.info}>
              <div className={styles.barberName}>{nameOf(photo.barber_id)}</div>
              <div className={styles.tags}>
                {photo.tags.map((t) => (
                  <span key={t.id} className={styles.tag}>{t.name}</span>
                ))}
              </div>
            </figcaption>
          </figure>
        ))}
      </div>
    );
  }

  return (
    <div className={styles.galleryContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>Nosso Portfólio</h2>
        <p className={styles.subtitle}>Inspire-se com os melhores cortes da Trim.</p>
      </div>

      <div className={styles.filters} role="group" aria-label="Filtrar por tag">
        {filter(ALL, 'Todas')}
        {tags.map((t) => filter(t.id, t.name))}
      </div>

      {content}
    </div>
  );
};

export default Gallery;
