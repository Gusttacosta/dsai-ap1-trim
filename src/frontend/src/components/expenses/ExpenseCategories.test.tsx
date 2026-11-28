// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../../api';
import { useExpenseCategories, type ExpenseCategory } from '../../hooks/useAdminExpenses';
import { ALUGUEL, LUZ, expenseCategory } from '../../testUtils/expenses';
import { httpError } from '../../testUtils/httpError';
import { CATEGORY_NAME_ERROR } from '../../utils/expenseValidation';
import ExpenseCategories from './ExpenseCategories';

// SPEC/2026-11-26-painel-despesas.md: criar, renomear e excluir categorias, com a API simulada.

vi.mock('../../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock; delete: Mock };

const onChanged = vi.fn();

const Section = () => <ExpenseCategories resource={useExpenseCategories()} onChanged={onChanged} />;

async function renderSection(list: ExpenseCategory[] = [ALUGUEL, LUZ]) {
  mocked.get.mockResolvedValue({ data: list });
  render(<Section />);
  if (list.length) await screen.findByRole('row', { name: list[0].name });
}

const row = (name: string) => screen.getByRole('row', { name });
const click = (name: string, scope: HTMLElement = document.body) =>
  fireEvent.click(within(scope).getByRole('button', { name }));
const names = () => screen.getAllByRole('row').slice(1).map((r) => r.getAttribute('aria-label'));

function add(name: string) {
  fireEvent.change(screen.getByLabelText('Nova categoria'), { target: { value: name } });
  click('Adicionar');
}

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
  onChanged.mockReset();
});

afterEach(cleanup);

describe('ExpenseCategories: lista', () => {
  it('carrega as categorias', async () => {
    await renderSection();

    expect(mocked.get).toHaveBeenCalledWith('/expenses/categories');
    expect(names()).toEqual(['Aluguel', 'Luz']);
  });

  it('sem categorias, avisa', async () => {
    await renderSection([]);

    expect(await screen.findByText('Nenhuma categoria cadastrada.')).toBeTruthy();
  });

  it('falha na carga mostra o erro e "Tentar de novo" carrega outra vez', async () => {
    mocked.get.mockRejectedValueOnce(httpError(500)).mockResolvedValueOnce({ data: [LUZ] });
    render(<Section />);

    expect((await screen.findByRole('alert')).textContent).toBe('Não foi possível carregar as categorias.');
    click('Tentar de novo');

    expect(await screen.findByRole('row', { name: 'Luz' })).toBeTruthy();
  });
});

describe('ExpenseCategories: criar', () => {
  it('manda o nome aparado, põe na lista e limpa o campo', async () => {
    await renderSection();
    mocked.post.mockResolvedValue({ data: expenseCategory('Internet') });

    add('  Internet ');

    expect(await screen.findByText('Categoria criada.')).toBeTruthy();
    expect(mocked.post).toHaveBeenCalledWith('/expenses/categories', { name: 'Internet' });
    expect(names()).toEqual(['Aluguel', 'Internet', 'Luz']);
    expect((screen.getByLabelText('Nova categoria') as HTMLInputElement).value).toBe('');
  });

  it('nome vazio é recusado na tela, sem chamada', async () => {
    await renderSection();

    add('   ');

    expect(screen.getByRole('alert').textContent).toBe(CATEGORY_NAME_ERROR);
    expect(mocked.post).not.toHaveBeenCalled();
  });

  it('nome repetido mostra o 400 da API e mantém o campo', async () => {
    await renderSection();
    mocked.post.mockRejectedValue(httpError(400, "Já existe uma categoria chamada 'Luz'."));

    add('Luz');

    expect((await screen.findByRole('alert')).textContent).toBe("Já existe uma categoria chamada 'Luz'.");
    expect(names()).toEqual(['Aluguel', 'Luz']);
    expect((screen.getByLabelText('Nova categoria') as HTMLInputElement).value).toBe('Luz');
  });
});

describe('ExpenseCategories: renomear', () => {
  function rename(from: string, to: string) {
    click('Renomear', row(from));
    fireEvent.change(screen.getByLabelText(`Novo nome de ${from}`), { target: { value: to } });
    click('Salvar', row(from));
  }

  it('manda o nome novo, sai da edição e avisa a lista de despesas', async () => {
    await renderSection();
    const renamed = { ...ALUGUEL, name: 'Templo' };
    mocked.put.mockResolvedValue({ data: renamed });

    rename('Aluguel', 'Templo');

    expect(await screen.findByRole('row', { name: 'Templo' })).toBeTruthy();
    expect(mocked.put).toHaveBeenCalledWith('/expenses/categories/aluguel', { name: 'Templo' });
    expect(onChanged).toHaveBeenCalledWith('aluguel', renamed);
    expect(screen.queryByLabelText('Novo nome de Aluguel')).toBeNull();
  });

  it('nome repetido mostra o 400 e a linha continua em edição', async () => {
    await renderSection();
    mocked.put.mockRejectedValue(httpError(400, "Já existe uma categoria chamada 'Luz'."));

    rename('Aluguel', 'Luz');

    expect((await screen.findByRole('alert')).textContent).toBe("Já existe uma categoria chamada 'Luz'.");
    expect(screen.getByLabelText('Novo nome de Aluguel')).toBeTruthy();
    expect(onChanged).not.toHaveBeenCalled();
  });

  it('nome vazio é recusado na tela; "Cancelar" volta ao nome', async () => {
    await renderSection();

    rename('Aluguel', ' ');
    expect(screen.getByRole('alert').textContent).toBe(CATEGORY_NAME_ERROR);
    expect(mocked.put).not.toHaveBeenCalled();

    click('Cancelar', row('Aluguel'));
    expect(within(row('Aluguel')).getByText('Aluguel')).toBeTruthy();
  });
});

describe('ExpenseCategories: excluir', () => {
  it('pede confirmação, chama o DELETE e avisa a lista de despesas', async () => {
    await renderSection();
    mocked.delete.mockResolvedValue({});

    click('Excluir', row('Luz'));
    expect(mocked.delete).not.toHaveBeenCalled();
    expect(screen.getByText('Excluir a categoria? As despesas ficam sem categoria.')).toBeTruthy();
    click('Confirmar', row('Luz'));

    expect(await screen.findByText('Categoria excluída.')).toBeTruthy();
    expect(mocked.delete).toHaveBeenCalledWith('/expenses/categories/luz');
    expect(names()).toEqual(['Aluguel']);
    expect(onChanged).toHaveBeenCalledWith('luz', null);
  });

  it('a falha mostra a mensagem da API e a categoria continua', async () => {
    await renderSection();
    mocked.delete.mockRejectedValue(httpError(404, 'Categoria não encontrada.'));

    click('Excluir', row('Luz'));
    click('Confirmar', row('Luz'));

    expect((await screen.findByRole('alert')).textContent).toBe('Categoria não encontrada.');
    await waitFor(() => expect(names()).toEqual(['Aluguel', 'Luz']));
    expect(onChanged).not.toHaveBeenCalled();
  });
});
