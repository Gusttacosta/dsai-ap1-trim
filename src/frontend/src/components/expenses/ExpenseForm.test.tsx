// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ALUGUEL, LUZ, makeExpense } from '../../testUtils/expenses';
import { httpError } from '../../testUtils/httpError';
import { AMOUNT_ERROR, DATE_ERROR, DESCRIPTION_ERROR } from '../../utils/expenseValidation';
import ExpenseForm, { expenseChanges, expenseInput } from './ExpenseForm';

// SPEC/2026-11-26-painel-despesas.md: formulário de criação e de edição de uma despesa.

const RENT = makeExpense('e1', { description: 'Aluguel de novembro', amount: '1500.00', payment_date: '2026-11-05' }, ALUGUEL);
const FIELDS = { description: 'Aluguel de novembro', amount: '1500', date: '2026-11-05', categoryId: 'aluguel', recurring: false };

const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const submit = () => fireEvent.click(screen.getByRole('button', { name: 'Salvar despesa' }));

function renderForm(expense = RENT as typeof RENT | undefined) {
  const onSave = vi.fn().mockResolvedValue(undefined);
  render(<ExpenseForm expense={expense} categories={[ALUGUEL, LUZ]} onSave={onSave} onCancel={vi.fn()} />);
  return onSave;
}

function fillNew(values: Record<string, string> = {}) {
  const all = { Descrição: 'Conta de luz', 'Valor (R$)': '230,5', 'Data do pagamento': '2026-11-10', ...values };
  for (const [label, value] of Object.entries(all)) type(label, value);
}

afterEach(cleanup);

describe('expenseInput e expenseChanges', () => {
  it('expenseInput converte para o formato da API', () => {
    expect(expenseInput({ ...FIELDS, description: ' Luz ', amount: '230,5', categoryId: '', recurring: true })).toEqual({
      category_id: null,
      description: 'Luz',
      amount: '230.50',
      payment_date: '2026-11-05',
      is_recurring: true,
    });
  });

  it('sem mudança, nada; o valor é comparado pelo número', () => {
    expect(expenseChanges(RENT, { ...FIELDS, amount: '1500,00' })).toEqual({});
  });

  it('só traz o que mudou, e "Sem categoria" manda null', () => {
    expect(expenseChanges(RENT, { ...FIELDS, categoryId: '', recurring: true, date: '2026-11-06' })).toEqual({
      category_id: null,
      payment_date: '2026-11-06',
      is_recurring: true,
    });
  });
});

describe('ExpenseForm: criação', () => {
  it('manda todos os campos, com a categoria e a recorrência', async () => {
    const onSave = renderForm(undefined);
    fillNew({ Categoria: 'luz' });
    fireEvent.click(screen.getByLabelText('Despesa recorrente'));

    submit();

    await waitFor(() => expect(onSave).toHaveBeenCalledWith({
      category_id: 'luz',
      description: 'Conta de luz',
      amount: '230.50',
      payment_date: '2026-11-10',
      is_recurring: true,
    }));
  });

  it.each([
    [{ Descrição: '   ' }, DESCRIPTION_ERROR],
    [{ 'Valor (R$)': '0' }, AMOUNT_ERROR],
    [{ 'Valor (R$)': '-10' }, AMOUNT_ERROR],
    [{ 'Valor (R$)': '10,555' }, AMOUNT_ERROR],
    [{ 'Valor (R$)': '100000000' }, AMOUNT_ERROR],
    [{ 'Data do pagamento': '' }, DATE_ERROR],
  ])('recusa %j na tela, sem chamar a API', (values, message) => {
    const onSave = renderForm(undefined);
    fillNew(values);

    submit();

    expect(screen.getByRole('alert').textContent).toBe(message);
    expect(onSave).not.toHaveBeenCalled();
  });

  it('o 422 da API aparece no formulário', async () => {
    const onSave = renderForm(undefined);
    onSave.mockRejectedValue(httpError(422, [{ msg: 'Value error, Campo obrigatório não pode ser nulo' }]));
    fillNew();

    submit();

    expect((await screen.findByRole('alert')).textContent).toBe('Campo obrigatório não pode ser nulo');
  });

  it('o 400 da API aparece no formulário', async () => {
    const onSave = renderForm(undefined);
    onSave.mockRejectedValue(httpError(400, 'Categoria informada não existe.'));
    fillNew();

    submit();

    expect((await screen.findByRole('alert')).textContent).toBe('Categoria informada não existe.');
  });
});

describe('ExpenseForm: edição', () => {
  it('começa com os dados da despesa', () => {
    renderForm();

    expect(screen.getByRole('heading', { name: 'Editar despesa' })).toBeTruthy();
    expect((screen.getByLabelText('Valor (R$)') as HTMLInputElement).value).toBe('1500,00');
    expect((screen.getByLabelText('Categoria') as HTMLSelectElement).value).toBe('aluguel');
  });

  it('manda só o que mudou', async () => {
    const onSave = renderForm();
    type('Valor (R$)', '1600');
    type('Categoria', '');

    submit();

    await waitFor(() => expect(onSave).toHaveBeenCalledWith({ amount: '1600.00', category_id: null }));
  });

  it('sem mudança, diz "Nada mudou." sem chamar a API', () => {
    const onSave = renderForm();

    submit();

    return waitFor(() => {
      expect(screen.getByRole('status').textContent).toBe('Nada mudou.');
      expect(onSave).not.toHaveBeenCalled();
    });
  });
});
