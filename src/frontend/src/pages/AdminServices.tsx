import { useState } from 'react';
import styles from './AdminShared.module.css';
import LoadState, { ActionFeedback } from '../components/LoadState';
import ServiceForm from '../components/services/ServiceForm';
import ServiceRow from '../components/services/ServiceRow';
import {
  useAdminServices,
  type AdminService,
  type ServiceChanges,
  type ServiceInput,
} from '../hooks/useAdminServices';
import { useRowAction } from '../hooks/useRowAction';

// Gestão do catálogo pelo painel do admin (SPEC/2026-11-23-painel-servicos.md).

/** Formulário aberto: nenhum, o de criação ou o de edição de um serviço. */
type Editing = null | 'new' | AdminService;

const AdminServices = () => {
  const { services, status, loadError, reload, createService, updateService, deactivateService, reactivateService } =
    useAdminServices();
  const [editing, setEditing] = useState<Editing>(null);
  const [showInactive, setShowInactive] = useState(true);
  const { busyId, message, actionError, run, clear, setMessage } = useRowAction();

  const open = (target: Editing) => {
    clear();
    setEditing(target);
  };

  const save = async (data: ServiceInput | ServiceChanges) => {
    if (editing === 'new') {
      await createService(data as ServiceInput);
      setMessage('Serviço criado.');
    } else if (editing) {
      await updateService(editing.id, data);
      setMessage('Serviço atualizado.');
    }
    setEditing(null);
  };

  const visible = showInactive ? services : services.filter((s) => s.is_active);

  let content;
  if (visible.length === 0) {
    content = <p>{services.length === 0 ? 'Nenhum serviço cadastrado.' : 'Nenhum serviço ativo.'}</p>;
  } else {
    content = (
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Serviço</th>
            <th>Duração</th>
            <th>Preço</th>
            <th>Situação</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((service) => (
            <ServiceRow
              key={service.id}
              service={service}
              busy={busyId === service.id}
              onEdit={open}
              onDeactivate={(s) => run(s.id, () => deactivateService(s.id), 'Serviço desativado.')}
              onReactivate={(s) => run(s.id, () => reactivateService(s.id), 'Serviço reativado.')}
            />
          ))}
        </tbody>
      </table>
    );
  }

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>✂️ Gestão de Serviços</h2>
        <button className={styles.btnAction} onClick={() => open('new')} disabled={status !== 'ready'}>
          + Novo Serviço
        </button>
      </div>

      {editing && (
        <ServiceForm
          // Trocar de serviço recria o formulário com os dados do novo.
          key={editing === 'new' ? 'new' : editing.id}
          service={editing === 'new' ? undefined : editing}
          onSave={save}
          onCancel={() => setEditing(null)}
        />
      )}

      <ActionFeedback message={message} error={actionError} />

      {status === 'ready' && services.length > 0 && (
        <label style={{ display: 'block', margin: '0 0 1rem' }}>
          <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />{' '}
          Mostrar desativados
        </label>
      )}

      <LoadState status={status} loadError={loadError} reload={reload} loadingText="Carregando serviços...">
        {content}
      </LoadState>
    </div>
  );
};

export default AdminServices;
