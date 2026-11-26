import { useState, type ReactNode } from 'react';
import styles from './AdminShared.module.css';
import ConfirmButton from '../components/ConfirmButton';
import LoadState, { ActionFeedback } from '../components/LoadState';
import NameList from '../components/names/NameList';
import PhotoTable from '../components/gallery/PhotoTable';
import PhotoUploadForm from '../components/gallery/PhotoUploadForm';
import RejectButton from '../components/gallery/RejectButton';
import {
  sendPhoto,
  useBarberNames,
  useGalleryModeration,
  useGalleryTags,
  type Photo,
  type PhotoInput,
} from '../hooks/useGallery';
import { useRowAction } from '../hooks/useRowAction';
import { validateTagName } from '../utils/galleryValidation';

// Aba "Galeria" do painel (SPEC/2026-11-26-painel-galeria.md). Admin e barbeiro enviam fotos; só
// o admin vê a moderação (pendentes e publicadas) e o cadastro de tags, e só para ele a tela
// chama as rotas de admin (SPEC/2026-11-25-galeria-permissoes.md).

export const SENT_FOR_REVIEW = 'Foto enviada. Ela aparece na galeria depois da aprovação.';
export const PUBLISHED = 'Foto publicada.';

const AdminGallery = ({ isAdmin }: { isAdmin: boolean }) => {
  const tags = useGalleryTags();
  const { barbers, nameOf } = useBarberNames();
  const moderation = useGalleryModeration(isAdmin);
  const { pending, published } = moderation;
  const [sending, setSending] = useState(false);
  const { busyId, message, actionError, run, clear, setMessage } = useRowAction();

  const send = async (input: PhotoInput) => {
    const photo = await sendPhoto(input);
    if (isAdmin) moderation.place(photo);
    setMessage(photo.is_approved ? PUBLISHED : SENT_FOR_REVIEW);
    setSending(false);
  };

  const remove = (photo: Photo) =>
    run(photo.id, () => moderation.remove(photo.id), 'Foto excluída.');

  const deleteButton = (photo: Photo, children: ReactNode) => (
    <ConfirmButton
      label="Excluir"
      question="Excluir a foto? Não dá para desfazer."
      onConfirm={() => remove(photo)}
      busy={busyId === photo.id}
    >
      {children}
    </ConfirmButton>
  );

  const pendingActions = (photo: Photo) => {
    const busy = busyId === photo.id;
    const reject = async (reason: string) =>
      (await run(photo.id, () => moderation.reject(photo.id, reason).then(() => true), 'Foto recusada. O barbeiro foi avisado.')) === true;
    return (
      <RejectButton busy={busy} onReject={reject}>
        {deleteButton(
          photo,
          <button className={styles.btnIcon} onClick={() => run(photo.id, () => moderation.approve(photo.id), 'Foto aprovada.')} disabled={busy}>
            Aprovar
          </button>,
        )}
      </RejectButton>
    );
  };

  const publishedActions = (photo: Photo) =>
    deleteButton(
      photo,
      <button
        className={styles.btnIcon}
        onClick={() => run(photo.id, () => moderation.unapprove(photo.id), 'Foto tirada da galeria. Ela voltou para as pendentes.')}
        disabled={busyId === photo.id}
      >
        Desaprovar
      </button>,
    );

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>📸 Galeria</h2>
        <button
          className={styles.btnAction}
          onClick={() => {
            clear();
            setSending(true);
          }}
          disabled={tags.status === 'loading'}
        >
          + Enviar foto
        </button>
      </div>

      {sending && (
        <PhotoUploadForm isAdmin={isAdmin} tags={tags.items} barbers={barbers} onSend={send} onCancel={() => setSending(false)} />
      )}

      <ActionFeedback message={message} error={actionError} />

      {isAdmin && (
        <>
          <h3 className={styles.title}>Pendentes</h3>
          <LoadState status={pending.status} loadError={pending.loadError} reload={pending.reload} loadingText="Carregando fotos pendentes...">
            <PhotoTable label="Pendentes" photos={pending.data} empty="Nenhuma foto pendente." nameOf={nameOf} actions={pendingActions} />
          </LoadState>

          <h3 className={styles.title} style={{ marginTop: '2.5rem' }}>Publicadas</h3>
          <LoadState status={published.status} loadError={published.loadError} reload={published.reload} loadingText="Carregando fotos publicadas...">
            <PhotoTable label="Publicadas" photos={published.data} empty="Nenhuma foto publicada." nameOf={nameOf} actions={publishedActions} />
          </LoadState>

          <NameList
            resource={tags}
            title="Tags"
            noun="Tag"
            deleteQuestion="Excluir a tag? As fotos ficam sem ela."
            validate={validateTagName}
          />
        </>
      )}
    </div>
  );
};

export default AdminGallery;
