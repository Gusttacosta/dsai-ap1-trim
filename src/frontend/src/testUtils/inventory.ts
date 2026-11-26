import type { Movement, Product } from '../hooks/useInventory';

// Produtos e movimentações como a API os devolve, para os testes do estoque no painel
// (SPEC/2026-11-26-painel-estoque.md).

export function makeProduct(id: string, extra: Partial<Product> = {}): Product {
  return {
    id,
    name: `Produto ${id}`,
    description: null,
    sku: null,
    price: '45.00',
    cost_price: '20.00',
    stock_quantity: 10,
    is_active: true,
    image_url: null,
    created_at: '2026-11-20T12:00:00Z',
    updated_at: '2026-11-20T12:00:00Z',
    ...extra,
  };
}

export const OLEO = makeProduct('oleo', { name: 'Óleo de barba', sku: 'OL-01', stock_quantity: 0 });
export const PENTE = makeProduct('pente', { name: 'Pente', price: '15.50', stock_quantity: 0, is_active: false });
export const POMADA = makeProduct('pomada', { name: 'Pomada', sku: 'PO-01', stock_quantity: 3 });
export const SHAMPOO = makeProduct('shampoo', { name: 'Shampoo', price: '32.90', stock_quantity: 20 });

export function makeMovement(id: string, product: Product, extra: Partial<Movement> = {}): Movement {
  return {
    id,
    product_id: product.id,
    user_id: 'admin',
    quantity: 10,
    movement_type: 'restock',
    notes: null,
    created_at: '2026-11-26T17:30:00Z',
    ...extra,
  };
}
