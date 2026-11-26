import { useCallback } from 'react';
import api from '../api';
import type { AdminService } from './useAdminServices';
import { useApiResource } from './useApiResource';

// Barbeiros no painel do admin: a listagem (GET /barbers/admin), as ações sobre o perfil e os
// vínculos com os serviços (SPEC/2026-11-26-painel-barbeiros.md). As ações devolvem o que o
// backend gravou e lançam o erro da API, para quem chamou mostrar a mensagem.

export type AdminBarber = {
  id: string;
  user_id: string;
  full_name: string;
  email: string;
  avatar_url: string | null;
  bio: string | null;
  instagram_url: string | null;
  /** O backend serializa o Decimal como texto ("50.00"). */
  commission_rate: string;
  /** Perfil de barbeiro ativo. */
  is_active: boolean;
  /** Conta do usuário ativa. */
  user_is_active: boolean;
};

/** Campos da criação, já no formato da API. */
export type BarberInput = {
  user_id: string;
  commission_rate: string;
  bio?: string;
  instagram_url?: string;
};

/** Alteração parcial: só os campos que mudaram. `null` apaga a bio e o Instagram. */
export type BarberChanges = Partial<{
  bio: string | null;
  instagram_url: string | null;
  commission_rate: string;
  is_active: boolean;
}>;

const LOAD_ERROR = 'Não foi possível carregar os barbeiros.';
const loadBarbers = async () => (await api.get<AdminBarber[]>('/barbers/admin')).data;

export function useAdminBarbers() {
  const {
    data: barbers,
    setData: setBarbers,
    status,
    loadError,
    reload,
  } = useApiResource(loadBarbers, [] as AdminBarber[], LOAD_ERROR);

  /**
   * Cria o perfil e carrega a lista de novo: a resposta da criação não traz o nome nem o e-mail.
   * Devolve o id do barbeiro criado.
   */
  const createBarber = useCallback(
    async (input: BarberInput) => {
      const { data } = await api.post<{ id: string }>('/barbers', input);
      reload();
      return data.id;
    },
    [reload],
  );

  /** Troca o barbeiro da lista pelo que o backend devolveu (a ordem, por nome, não muda). */
  const updateBarber = useCallback(async (id: string, changes: BarberChanges) => {
    const { data: saved } = await api.put<AdminBarber>(`/barbers/${id}`, changes);
    setBarbers((current) => current.map((b) => (b.id === saved.id ? saved : b)));
    return saved;
  }, []);

  const setActive = useCallback(
    (id: string, isActive: boolean) => updateBarber(id, { is_active: isActive }),
    [updateBarber],
  );

  return { barbers, status, loadError, reload, createBarber, updateBarber, setActive };
}

// ── Serviços do barbeiro ─────────────────────────────────

/** Ids dos serviços ativos vinculados ao barbeiro. */
export async function fetchBarberServiceIds(barberId: string): Promise<string[]> {
  const { data } = await api.get<{ id: string }[]>(`/services/barber/${barberId}`);
  return data.map((s) => s.id);
}

/**
 * Deixa o barbeiro com exatamente os serviços `wanted`: vincula os que faltam e desvincula os
 * que sobram. Os vínculos atuais são lidos na hora, para uma nova tentativa depois de uma falha
 * no meio não repetir o que já foi gravado. Para no primeiro erro da API.
 */
export async function syncBarberServices(barberId: string, wanted: string[]): Promise<void> {
  const current = await fetchBarberServiceIds(barberId);
  for (const id of wanted.filter((s) => !current.includes(s))) {
    await api.post(`/services/${id}/barbers/${barberId}`);
  }
  for (const id of current.filter((s) => !wanted.includes(s))) {
    await api.delete(`/services/${id}/barbers/${barberId}`);
  }
}

export type ServiceChoices = { options: AdminService[]; linkedIds: string[] };

/**
 * O que o formulário do barbeiro precisa para os serviços: os ativos do catálogo, para marcar,
 * e os já vinculados ao barbeiro (nenhum na criação, sem `barberId`).
 */
export function useBarberServiceChoices(barberId: string | null) {
  const load = useCallback(async (): Promise<ServiceChoices> => {
    const [catalog, linkedIds] = await Promise.all([
      api.get<AdminService[]>('/services/admin').then((r) => r.data),
      barberId ? fetchBarberServiceIds(barberId) : Promise.resolve([]),
    ]);
    return { options: catalog.filter((s) => s.is_active), linkedIds };
  }, [barberId]);

  return useApiResource(load, { options: [], linkedIds: [] } as ServiceChoices, 'Não foi possível carregar os serviços.');
}
