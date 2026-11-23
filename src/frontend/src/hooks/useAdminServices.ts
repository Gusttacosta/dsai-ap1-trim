import { useCallback, useEffect, useState } from 'react';
import api from '../api';
import { apiErrorMessage } from '../utils/apiError';

// Catálogo de serviços do painel do admin: carga pelo GET /services/admin e as ações sobre
// a API (SPEC/2026-11-23-painel-servicos.md). As ações devolvem o serviço como o backend
// gravou e lançam o erro da API, para quem chamou mostrar a mensagem.

export type AdminService = {
  id: string;
  name: string;
  description: string | null;
  /** O backend serializa o Decimal como texto ("35.00"). */
  price: string;
  duration_minutes: number;
  is_active: boolean;
};

/** Campos da criação, já no formato da API. */
export type ServiceInput = Pick<AdminService, 'name' | 'description' | 'price' | 'duration_minutes'>;
/** Alteração parcial: só os campos que mudaram. */
export type ServiceChanges = Partial<ServiceInput & Pick<AdminService, 'is_active'>>;

export type ServicesStatus = 'loading' | 'ready' | 'error';

/** Mesma ordem do backend: alfabética, sem diferenciar maiúsculas. */
function sortByName(services: AdminService[]): AdminService[] {
  return [...services].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR', { sensitivity: 'base' }));
}

export function useAdminServices() {
  const [services, setServices] = useState<AdminService[]>([]);
  const [status, setStatus] = useState<ServicesStatus>('loading');
  const [loadError, setLoadError] = useState('');
  // Mudar o número pede uma nova carga ("Tentar de novo").
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setStatus('loading');
    api
      .get<AdminService[]>('/services/admin')
      .then((response) => {
        if (!active) return;
        setServices(response.data);
        setStatus('ready');
      })
      .catch((error) => {
        if (!active) return;
        setLoadError(apiErrorMessage(error, 'Não foi possível carregar os serviços.'));
        setStatus('error');
      });
    return () => {
      active = false;
    };
  }, [attempt]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);

  /** Põe o serviço gravado na lista, no lugar do antigo ou como novo, mantendo a ordem. */
  const store = useCallback((saved: AdminService) => {
    setServices((current) => sortByName([...current.filter((s) => s.id !== saved.id), saved]));
    return saved;
  }, []);

  const createService = useCallback(
    async (input: ServiceInput) => store((await api.post<AdminService>('/services', input)).data),
    [store],
  );

  const updateService = useCallback(
    async (id: string, changes: ServiceChanges) =>
      store((await api.put<AdminService>(`/services/${id}`, changes)).data),
    [store],
  );

  /** O DELETE só desativa (soft delete) e não devolve corpo: a lista marca o serviço. */
  const deactivateService = useCallback(async (id: string) => {
    await api.delete(`/services/${id}`);
    setServices((current) => current.map((s) => (s.id === id ? { ...s, is_active: false } : s)));
  }, []);

  const reactivateService = useCallback(
    (id: string) => updateService(id, { is_active: true }),
    [updateService],
  );

  return {
    services,
    status,
    loadError,
    reload,
    createService,
    updateService,
    deactivateService,
    reactivateService,
  };
}
