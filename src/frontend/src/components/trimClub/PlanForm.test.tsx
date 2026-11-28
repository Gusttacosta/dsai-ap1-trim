// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { httpError } from '../../testUtils/httpError';
import { OURO } from '../../testUtils/trimClub';
import {
  DISCOUNT_ERROR,
  MONTHLY_PRICE_ERROR,
  PLAN_NAME_ERROR,
  quantityError,
} from '../../utils/trimClub';
import PlanForm, { planChanges, planInput, type PlanFields } from './PlanForm';

// SPEC/2026-11-26-painel-trim-club.md: formulário de criação e de edição de plano.

const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const submit = () => fireEvent.click(screen.getByRole('button', { name: 'Salvar plano' }));

const FIELDS: PlanFields = {
  name: ' Prata ',
  description: '  ',
  price: '89,9',
  cuts: { text: '4', unlimited: false },
  shaves: { text: '', unlimited: true },
  discount: '',
};

afterEach(cleanup);

describe('planInput e planChanges', () => {
  it('planInput converte para a API: aparado, null nos ilimitados e desconto zero', () => {
    expect(planInput(FIELDS)).toEqual({
      name: 'Prata',
      description: null,
      monthly_price: '89.90',
      included_cuts: 4,
      included_shaves: null,
      discount_percentage: '0.00',
    });
  });

  it('planChanges só traz o que mudou, comparando preço e desconto pelo valor', () => {
    const same: PlanFields = {
      name: 'Ouro',
      description: 'Bebida premium',
      price: '150',
      cuts: { text: '', unlimited: true },
      shaves: { text: '2', unlimited: false },
      discount: '10,00',
    };
    expect(planChanges(OURO, same)).toEqual({});
    expect(planChanges(OURO, { ...same, cuts: { text: '8', unlimited: false }, discount: '' })).toEqual({
      included_cuts: 8,
      discount_percentage: '0.00',
    });
  });
});

describe('PlanForm', () => {
  it('cria com todos os campos no formato da API', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<PlanForm onSave={onSave} onCancel={() => {}} />);

    type('Nome', 'Prata');
    type('Preço mensal (R$)', '89,90');
    type('Cortes inclusos', '4');
    fireEvent.click(screen.getByLabelText('Barbas inclusas: ilimitados'));
    expect(screen.getByLabelText('Barbas inclusas')).toHaveProperty('disabled', true);
    type('Desconto (%)', '5');
    submit();

    await waitFor(() =>
      expect(onSave).toHaveBeenCalledWith({
        name: 'Prata',
        description: null,
        monthly_price: '89.90',
        included_cuts: 4,
        included_shaves: null,
        discount_percentage: '5.00',
      }),
    );
  });

  it.each([
    [{ Nome: '  ' }, PLAN_NAME_ERROR],
    [{ Nome: 'x'.repeat(101) }, PLAN_NAME_ERROR],
    [{ 'Preço mensal (R$)': '0' }, MONTHLY_PRICE_ERROR],
    [{ 'Preço mensal (R$)': 'dez' }, MONTHLY_PRICE_ERROR],
    [{ 'Cortes inclusos': '-1' }, quantityError('Cortes inclusos')],
    [{ 'Barbas inclusas': '1,5' }, quantityError('Barbas inclusas')],
    [{ 'Desconto (%)': '101' }, DISCOUNT_ERROR],
  ])('recusa %o na tela, sem chamar a API', (values, error) => {
    const onSave = vi.fn();
    render(<PlanForm onSave={onSave} onCancel={() => {}} />);
    const all: Record<string, string> = { Nome: 'Prata', 'Preço mensal (R$)': '89', ...values };
    for (const [label, value] of Object.entries(all)) type(label, value);
    submit();

    expect(screen.getByRole('alert').textContent).toBe(error);
    expect(onSave).not.toHaveBeenCalled();
  });

  it('edita com os dados do plano e manda só o que mudou', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<PlanForm plan={OURO} onSave={onSave} onCancel={() => {}} />);

    expect(screen.getByLabelText('Nome')).toHaveProperty('value', 'Ouro');
    expect(screen.getByLabelText('Preço mensal (R$)')).toHaveProperty('value', '150,00');
    expect(screen.getByLabelText('Cortes inclusos: ilimitados')).toHaveProperty('checked', true);
    expect(screen.getByLabelText('Barbas inclusas')).toHaveProperty('value', '2');
    expect(screen.getByLabelText('Desconto (%)')).toHaveProperty('value', '10,00');

    fireEvent.click(screen.getByLabelText('Cortes inclusos: ilimitados'));
    type('Cortes inclusos', '6');
    submit();

    await waitFor(() => expect(onSave).toHaveBeenCalledWith({ included_cuts: 6 }));
  });

  it('sem mudança, diz "Nada mudou." e não chama a API', async () => {
    const onSave = vi.fn();
    render(<PlanForm plan={OURO} onSave={onSave} onCancel={() => {}} />);
    submit();
    expect(await screen.findByText('Nada mudou.')).toBeTruthy();
    expect(onSave).not.toHaveBeenCalled();
  });

  it('o erro da API (nome repetido) aparece no formulário', async () => {
    const onSave = vi.fn().mockRejectedValue(httpError(400, 'Já existe um plano com esse nome.'));
    render(<PlanForm onSave={onSave} onCancel={() => {}} />);
    type('Nome', 'Ouro');
    type('Preço mensal (R$)', '10');
    submit();
    expect((await screen.findByRole('alert')).textContent).toBe('Já existe um plano com esse nome.');
  });
});
