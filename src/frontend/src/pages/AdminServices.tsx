import { useState } from 'react';
import styles from './AdminShared.module.css';
import ServiceForm from '../components/services/ServiceForm';
import ServiceRow from '../components/services/ServiceRow';
import formStyles from '../components/services/Services.module.css';
import {
  useAdminServices,
  type AdminService,
  type ServiceChanges,
  type ServiceInput,
} from '../hooks/useAdminServices';
import { apiErrorMessage } from '../utils/apiError';

// Gestão do catálogo pelo painel do admin (SPEC/2026-11-23-painel-servicos.md).

/** Formulário aberto: nenhum, o de criação ou o de edição de um serviço. */
type Editing = null | 'new' | AdminService;

const AdminServices = () => {
  const { services, status, loadError, reload, createService, updateService, deactivateService, reactivateService } =
    useAdminServices();
  const [editing, setEditing] = useState<Editing>(null);
  const [showInactive, setShowInactive] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [actionError, setActionError] = useState('');

  const open = (target: Editing) => {
    setMessage('');
    setActionError('');
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

  /** Ação de uma linha: desabilita a linha enquanto roda e mostra o resultado no topo. */
  const runRowAction = async (service: AdminService, action: () => Promise<unknown>, done: string) => {
    setMessage('');
    setActionError('');
    setBusyId(service.id);
    try {
      await action();
      setMessage(done);
    } catch (error) {
      setActionError(apiErrorMessage(error, 'Não foi possível concluir a ação.'));
    } finally {
      setBusyId(null);
    }
  };

  const visible = showInactive ? services : services.filter((s) => s.is_active);

  let content;
  if (status === 'loading') {
    content = <p>Carregando serviços...</p>;
  } else if (status === 'error') {
    content = (
      <div>
        <p className={formStyles.error} role="alert">{loadError}</p>
        <button className={styles.btnAction} onClick={reload}>Tentar de novo</button>
      </div>
    );
  } else if (visible.length === 0) {
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
              onDeactivate={(s) => runRowAction(s, () => deactivateService(s.id), 'Serviço desativado.')}
              onReactivate={(s) => runRowAction(s, () => reactivateService(s.id), 'Serviço reativado.')}
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

      {message && <p className={formStyles.info} role="status">{message}</p>}
      {actionError && <p className={formStyles.error} role="alert">{actionError}</p>}

      {status === 'ready' && services.length > 0 && (
        <label style={{ display: 'block', margin: '0 0 1rem' }}>
          <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />{' '}
          Mostrar desativados
        </label>
      )}

      {content}
    </div>
  );
};

export default AdminServices;
