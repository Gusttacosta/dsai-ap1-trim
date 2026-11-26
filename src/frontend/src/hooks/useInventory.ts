import { useCallback } from 'react';
import api from '../api';
import type { MovementType } from '../utils/inventory';
import { useApiResource } from './useApiResource';
import { byName, upsert } from './useNameList';

// Estoque no painel do admin: os produtos (ativos e desativados), o histórico de um produto e o
// registro de uma movimentação, com as rotas de /products (SPEC/2026-11-26-painel-estoque.md). A
// ação devolve o produto que o backend gravou e lança o erro da API, para quem chamou mostrar a
// mensagem.

export type Product = {
  id: string;
  name: string;
  description: string | null;
  sku: string | null;
  price: string;
  cost_price: string | null;
  stock_quantity: number;
  is_active: boolean;
  image_url: string | null;
  created_at: string;
  updated_at: string;
};

export type Movement = {
  id: string;
  product_id: string;
  user_id: string;
  quantity: number;
  movement_type: MovementType;
  notes: string | null;
  created_at: string;
};

/** O corpo do POST: a quantidade já com o sinal do tipo. */
export type MovementInput = Pick<Movement, 'movement_type' | 'quantity' | 'notes'>;

const loadProducts = async () => (await api.get<Product[]>('/products/admin/all')).data;

export function useAdminProducts() {
  const { data: products, setData, status, loadError, reload } = useApiResource(
    loadProducts,
    [] as Product[],
    'Não foi possível carregar os produtos.',
  );

  /** Registra a movimentação e troca a linha pelo produto com o estoque novo. */
  const registerMovement = useCallback(
    async (productId: string, input: MovementInput) => {
      const saved = (await api.post<Product>(`/products/${productId}/inventory`, input)).data;
      setData((current) => upsert(current, saved, byName));
      return saved;
    },
    [setData],
  );

  return { products, status, loadError, reload, registerMovement };
}

export function useInventoryHistory(productId: string) {
  const load = useCallback(async () => (await api.get<Movement[]>(`/products/${productId}/inventory`)).data, [productId]);
  const { data: movements, status, loadError, reload } = useApiResource(
    load,
    [] as Movement[],
    'Não foi possível carregar o histórico.',
  );
  return { movements, status, loadError, reload };
}
