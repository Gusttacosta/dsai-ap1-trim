// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import type { AdminService } from '../hooks/useAdminServices';
import { httpError } from '../testUtils/httpError';
import AdminServices from './AdminServices';

// SPEC/2026-11-23-painel-servicos.md: a tela de serviços do painel usa as rotas do admin (#49).

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock; delete: Mock };

const BARBA: AdminService = {
  id: 'b1',
  name: 'Barba',
  description: null,
  price: '25.00',
  duration_minutes: 20,
  is_active: true,
};
const CORTE: AdminService = { ...BARBA, id: 'c1', name: 'Corte', price: '35.00', duration_minutes: 30 };
const PIGMENTACAO: AdminService = { ...BARBA, id: 'p1', name: 'Pigmentação', is_active: false };

const click = (name: string, scope: HTMLElement) => fireEvent.click(within(scope).getByRole('button', { name }));
const clickPage = (name: string) => fireEvent.click(screen.getByRole('button', { name }));
const row = (name: string) => screen.getByRole('row', { name });
const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });

async function renderPage(list: AdminService[] = [BARBA, CORTE, PIGMENTACAO]) {
  mocked.get.mockResolvedValue({ data: list });
  render(<AdminServices />);
  if (list.length) await screen.findByRole('row', { name: list[0].name });
}

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});

afterEach(cleanup);

describe('AdminServices: listagem', () => {
  it('usa a listagem do admin e mostra ativos e desativados com a situação', async () => {
    await renderPage();

    expect(mocked.get).toHaveBeenCalledWith('/services/admin');
    expect(mocked.get).not.toHaveBeenCalledWith('/services');
    expect(within(row('Corte')).getByText('Ativo')).toBeTruthy();
    expect(within(row('Pigmentação')).getByText('Desativado')).toBeTruthy();
  });

  it('o filtro esconde os desativados', async () => {
    await renderPage();

    fireEvent.click(screen.getByLabelText('Mostrar desativados'));

    expect(screen.queryByRole('row', { name: 'Pigmentação' })).toBeNull();
    expect(row('Corte')).toBeTruthy();
  });

  it('sem serviços, avisa', async () => {
    await renderPage([]);

    expect(await screen.findByText('Nenhum serviço cadastrado.')).toBeTruthy();
  });

  it('enquanto carrega, avisa e não deixa abrir o formulário', () => {
    mocked.get.mockReturnValue(new Promise(() => {}));
    render(<AdminServices />);

    expect(screen.getByText('Carregando serviços...')).toBeTruthy();
    expect(screen.getByRole('button', { name: '+ Novo Serviço' })).toHaveProperty('disabled', true);
  });

  it('falha na carga mostra o erro e "Tentar de novo" carrega outra vez', async () => {
    mocked.get.mockRejectedValueOnce(httpError(500)).mockResolvedValueOnce({ data: [CORTE] });
    render(<AdminServices />);

    expect((await screen.findByRole('alert')).textContent).toBe('Não foi possível carregar os serviços.');
    clickPage('Tentar de novo');

    expect(await screen.findByRole('row', { name: 'Corte' })).toBeTruthy();
    expect(mocked.get).toHaveBeenCalledTimes(2);
  });
});

describe('AdminServices: criar e editar', () => {
  it('+ Novo Serviço cria pelo POST e o serviço entra na lista em ordem', async () => {
    await renderPage();
    const novo = { ...BARBA, id: 'h1', name: 'Hidratação', price: '35.50', duration_minutes: 40 };
    mocked.post.mockResolvedValue({ data: novo });

    clickPage('+ Novo Serviço');
    type('Nome', 'Hidratação');
    type('Preço (R$)', '35,5');
    type('Duração (min)', '40');
    clickPage('Salvar serviço');

    expect((await screen.findByRole('status')).textContent).toBe('Serviço criado.');
    expect(mocked.post).toHaveBeenCalledWith('/services', {
      name: 'Hidratação',
      description: null,
      price: '35.50',
      duration_minutes: 40,
    });
    expect(screen.queryByRole('form', { name: 'Novo serviço' })).toBeNull();
    const nomes = screen.getAllByRole('row').slice(1).map((r) => r.getAttribute('aria-label'));
    expect(nomes).toEqual(['Barba', 'Corte', 'Hidratação', 'Pigmentação']);
  });

  it('Editar abre o formulário com os dados e envia só o que mudou', async () => {
    await renderPage();
    mocked.put.mockResolvedValue({ data: { ...CORTE, price: '40.00' } });

    click('Editar', row('Corte'));
    expect(screen.getByLabelText('Nome')).toHaveProperty('value', 'Corte');
    type('Preço (R$)', '40');
    clickPage('Salvar serviço');

    expect((await screen.findByRole('status')).textContent).toBe('Serviço atualizado.');
    expect(mocked.put).toHaveBeenCalledWith('/services/c1', { price: '40.00' });
    expect(row('Corte').textContent?.replace(/\s/g, ' ')).toContain('R$ 40,00');
  });

  it('trocar de serviço em edição recarrega o formulário', async () => {
    await renderPage();

    click('Editar', row('Corte'));
    type('Nome', 'Rascunho');
    click('Editar', row('Barba'));

    expect(screen.getByLabelText('Nome')).toHaveProperty('value', 'Barba');
  });

  it('nome repetido: o erro do backend aparece e o formulário fica aberto', async () => {
    await renderPage();
    mocked.post.mockRejectedValue(httpError(400, "Já existe um serviço com o nome 'Corte'."));

    clickPage('+ Novo Serviço');
    type('Nome', 'corte');
    type('Preço (R$)', '30');
    type('Duração (min)', '30');
    clickPage('Salvar serviço');

    const form = await screen.findByRole('form', { name: 'Novo serviço' });
    expect((await within(form).findByRole('alert')).textContent).toBe("Já existe um serviço com o nome 'Corte'.");
    expect(screen.getByLabelText('Nome')).toHaveProperty('value', 'corte');
    expect(screen.getAllByRole('row')).toHaveLength(4);
  });

  it('valor inválido não chama a API', async () => {
    await renderPage();

    clickPage('+ Novo Serviço');
    type('Nome', 'Hidratação');
    type('Preço (R$)', '30');
    type('Duração (min)', '0');
    clickPage('Salvar serviço');

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(mocked.post).not.toHaveBeenCalled();
  });

  it('Cancelar fecha o formulário sem enviar', async () => {
    await renderPage();

    clickPage('+ Novo Serviço');
    clickPage('Cancelar');

    expect(screen.queryByRole('form', { name: 'Novo serviço' })).toBeNull();
    expect(mocked.post).not.toHaveBeenCalled();
  });
});

describe('AdminServices: desativar e reativar', () => {
  it('Desativar só chama o DELETE depois de Confirmar', async () => {
    await renderPage();
    mocked.delete.mockResolvedValue({ data: '' });

    click('Desativar', row('Corte'));
    expect(mocked.delete).not.toHaveBeenCalled();
    click('Confirmar', row('Corte'));

    expect((await screen.findByRole('status')).textContent).toBe('Serviço desativado.');
    expect(mocked.delete).toHaveBeenCalledWith('/services/c1');
    expect(within(row('Corte')).getByText('Desativado')).toBeTruthy();
    expect(within(row('Corte')).getByRole('button', { name: 'Reativar' })).toBeTruthy();
  });

  it('Voltar não desativa', async () => {
    await renderPage();

    click('Desativar', row('Corte'));
    click('Voltar', row('Corte'));

    expect(mocked.delete).not.toHaveBeenCalled();
    expect(within(row('Corte')).getByText('Ativo')).toBeTruthy();
  });

  it('Reativar envia o PUT com is_active true e a linha volta a Ativo', async () => {
    await renderPage();
    mocked.put.mockResolvedValue({ data: { ...PIGMENTACAO, is_active: true } });

    click('Reativar', row('Pigmentação'));

    expect((await screen.findByRole('status')).textContent).toBe('Serviço reativado.');
    expect(mocked.put).toHaveBeenCalledWith('/services/p1', { is_active: true });
    expect(within(row('Pigmentação')).getByText('Ativo')).toBeTruthy();
  });

  it('enquanto a ação roda, os botões da linha ficam desabilitados', async () => {
    await renderPage();
    mocked.put.mockReturnValue(new Promise(() => {}));

    click('Reativar', row('Pigmentação'));

    await waitFor(() =>
      expect(within(row('Pigmentação')).getByRole('button', { name: 'Reativar' })).toHaveProperty('disabled', true),
    );
    expect(within(row('Corte')).getByRole('button', { name: 'Editar' })).toHaveProperty('disabled', false);
  });

  it('falha na ação mostra o erro e o serviço fica como estava', async () => {
    await renderPage();
    mocked.delete.mockRejectedValue(httpError(404, 'Serviço não encontrado.'));

    click('Desativar', row('Corte'));
    click('Confirmar', row('Corte'));

    expect((await screen.findByRole('alert')).textContent).toBe('Serviço não encontrado.');
    expect(within(row('Corte')).getByText('Ativo')).toBeTruthy();
    expect(within(row('Corte')).getByRole('button', { name: 'Desativar' })).toHaveProperty('disabled', false);
  });
});
