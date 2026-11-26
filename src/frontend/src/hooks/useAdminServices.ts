import { useCallback } from 'react';
import api from '../api';
import { useApiResource, type LoadStatus } from './useApiResource';

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

export type ServicesStatus = LoadStatus;

/** Mesma ordem do backend: alfabética, sem diferenciar maiúsculas. */
function sortByName(services: AdminService[]): AdminService[] {
  return [...services].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR', { sensitivity: 'base' }));
}

const loadServices = async () => (await api.get<AdminService[]>('/services/admin')).data;

export function useAdminServices() {
  const {
    data: services,
    setData: setServices,
    status,
    loadError,
    reload,
  } = useApiResource(loadServices, [] as AdminService[], 'Não foi possível carregar os serviços.');

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
