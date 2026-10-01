import React, { useState } from 'react';
import styles from './Gallery.module.css';

const MOCK_PHOTOS = [
  { id: 1, barber: 'João Silva', img: 'https://images.unsplash.com/photo-1599351431202-1e0f0137899a?auto=format&fit=crop&w=600&q=80', tags: ['Fade', 'Navalhado'] },
  { id: 2, barber: 'Carlos Santos', img: 'https://images.unsplash.com/photo-1622286342621-4bd786c2447c?auto=format&fit=crop&w=600&q=80', tags: ['Clássico', 'Barba'] },
  { id: 3, barber: 'João Silva', img: 'https://images.unsplash.com/photo-1585747860715-2ba37e788b70?auto=format&fit=crop&w=600&q=80', tags: ['Afro'] },
  { id: 4, barber: 'Marcos Almeida', img: 'https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=600&q=80', tags: ['Fade', 'Platinado'] },
];

const MOCK_TAGS = ['Todos', 'Fade', 'Navalhado', 'Clássico', 'Barba', 'Afro', 'Platinado'];

const Gallery = () => {
  const [activeFilter, setActiveFilter] = useState('Todos');

  const filteredPhotos = activeFilter === 'Todos' 
    ? MOCK_PHOTOS 
    : MOCK_PHOTOS.filter(p => p.tags.includes(activeFilter));

  return (
    <div className={styles.galleryContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>Nosso Portfólio</h2>
        <p className={styles.subtitle}>Inspire-se com os melhores cortes da Trim.</p>
      </div>

      <div className={styles.filters}>
        {MOCK_TAGS.map(tag => (
          <button 
            key={tag}
            className={`${styles.filterBtn} ${activeFilter === tag ? styles.active : ''}`}
            onClick={() => setActiveFilter(tag)}
          >
            {tag}
          </button>
        ))}
      </div>

      <div className={styles.grid}>
        {filteredPhotos.map(photo => (
          <div key={photo.id} className={styles.photoCard}>
            <div className={styles.imageWrapper}>
              <img src={photo.img} alt={`Corte por ${photo.barber}`} className={styles.imagePlaceholder} />
            </div>
            <div className={styles.info}>
              <div className={styles.barberName}>{photo.barber}</div>
              <div className={styles.tags}>
                {photo.tags.map(t => (
                  <span key={t} className={styles.tag}>{t}</span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Gallery;

