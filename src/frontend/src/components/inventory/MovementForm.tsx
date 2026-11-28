import { useState } from 'react';
import type { MovementInput, Product } from '../../hooks/useInventory';
import {
  formatUnits,
  movementOptions,
  movementQuestion,
  parseQuantity,
  validateNotes,
  validateQuantity,
  validateStock,
} from '../../utils/inventory';
import AdminForm, { FormField } from '../AdminForm';

// Entrada ou saída de estoque de um produto (SPEC/2026-11-26-painel-estoque.md): o tipo dá o
// sinal da quantidade, que é digitada sem sinal. Confere os campos e o estoque e pede confirmação,
// com o estoque antes e depois, antes de chamar a API.

type Props = {
  product: Product;
  /** Grava a movimentação. O erro da API (estoque insuficiente, desativado) aparece no formulário. */
  onSave: (input: MovementInput) => Promise<unknown>;
  onCancel: () => void;
};

const MovementForm = ({ product, onSave, onCancel }: Props) => {
  const options = movementOptions(product.is_active);
  const [key, setKey] = useState(options[0].key);
  const [quantity, setQuantity] = useState('');
  const [notes, setNotes] = useState('');

  const option = options.find((o) => o.key === key) ?? options[0];
  const amount = () => parseQuantity(quantity) as number;

  const validate = () =>
    validateQuantity(quantity) ?? validateNotes(notes) ?? validateStock(option, amount(), product.stock_quantity);

  const save = async () => {
    await onSave({
      movement_type: option.type,
      quantity: option.direction * amount(),
      notes: notes.trim() || null,
    });
    return true;
  };

  return (
    <AdminForm
      title={`Movimentar estoque de ${product.name}`}
      submitLabel="Registrar movimentação"
      errorFallback="Não foi possível registrar a movimentação."
      validate={validate}
      confirm={() => movementQuestion(product.name, product.stock_quantity, option, amount())}
      save={save}
      onCancel={onCancel}
    >
      <FormField id="estoque-tipo" label="Tipo">
        <select id="estoque-tipo" value={option.key} onChange={(e) => setKey(e.target.value)}>
          {options.map((o) => (
            <option key={o.key} value={o.key}>
              {o.label}
            </option>
          ))}
        </select>
      </FormField>

      <FormField id="estoque-quantidade" label={`Quantidade (em estoque: ${formatUnits(product.stock_quantity)})`}>
        <input
          id="estoque-quantidade"
          inputMode="numeric"
          placeholder="10"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
        />
      </FormField>

      <FormField id="estoque-observacao" label="Observação (opcional)" wide>
        <input id="estoque-observacao" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </FormField>

      {!product.is_active && (
        <p style={{ gridColumn: '1 / -1', margin: 0 }}>Produto desativado: só aceita perda ou ajuste de estoque.</p>
      )}
    </AdminForm>
  );
};

export default MovementForm;
