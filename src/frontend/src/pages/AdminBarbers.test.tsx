// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import type { AdminBarber } from '../hooks/useAdminBarbers';
import { PER_PAGE } from '../hooks/useAdminUsers';
import { barber, defaultWeek } from '../testUtils/barbers';
import { httpError } from '../testUtils/httpError';
import AdminBarbers from './AdminBarbers';

// SPEC/2026-11-26-painel-barbeiros.md: a aba "Barbeiros" do painel do admin (#102).

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock; delete: Mock };

const ANA = barber('ana', 'Ana', { commission_rate: '40.00' });
const BRUNO = barber('bruno', 'Bruno', { is_active: false, user_is_active: false });
const CARLA = { id: 'u-carla', email: 'carla@teste.com', full_name: 'Carla', role: 'client' };
const CATALOG = [{ id: 'barba', name: 'Barba', is_active: true }, { id: 'corte', name: 'Corte', is_active: true }];

/** API simulada: as listagens respondem pelo endereço; `linked` são os serviços de cada barbeiro. */
function mockApi(barbers: AdminBarber[] = [ANA, BRUNO], linked: Record<string, string[]> = {}) {
  mocked.get.mockImplementation(async (url: string) => {
    if (url === '/barbers/admin') return { data: barbers };
    if (url === '/services/admin') return { data: CATALOG };
    if (url === '/auth/users') {
      const users = [CARLA, { id: ANA.user_id, email: ANA.email, full_name: 'Ana', role: 'barber' }];
      return { data: { users, total: 2, page: 1, per_page: PER_PAGE, total_pages: 1 } };
    }
    if (url.startsWith('/services/barber/')) return { data: (linked[url.split('/')[3]] ?? []).map((id) => ({ id })) };
    if (url.endsWith('/schedule')) return { data: defaultWeek() };
    throw new Error(`GET inesperado: ${url}`);
  });
}

const row = (name: string) => screen.getByRole('row', { name });
const click = (name: string, scope: HTMLElement = document.body) =>
  fireEvent.click(within(scope).getByRole('button', { name }));
const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const barbersLoads = () => mocked.get.mock.calls.filter(([url]) => url === '/barbers/admin').length;

async function renderPage(barbers?: AdminBarber[], linked?: Record<string, string[]>) {
  mockApi(barbers, linked);
  render(<AdminBarbers />);
  await screen.findByRole('row', { name: 'Ana' });
}

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});
afterEach(cleanup);

describe('AdminBarbers: lista', () => {
  it('lista ativos e desativados com comissão e situação', async () => {
    await renderPage();
    expect(mocked.get).toHaveBeenCalledWith('/barbers/admin');
    expect(within(row('Ana')).getByText('40,00%')).toBeTruthy();
    expect(within(row('Ana')).getByText('Ativo')).toBeTruthy();
    expect(within(row('Bruno')).getByText('Desativado')).toBeTruthy();
    expect(within(row('Bruno')).getByText('Conta desativada')).toBeTruthy();
  });

  it('sem barbeiros, diz isso', async () => {
    mockApi([]);
    render(<AdminBarbers />);
    expect(await screen.findByText('Nenhum barbeiro cadastrado.')).toBeTruthy();
  });

  it('falha da carga mostra a mensagem e "Tentar de novo" carrega de novo', async () => {
    mocked.get.mockRejectedValueOnce(httpError(403, 'Acesso restrito a administradores.'));
    render(<AdminBarbers />);
    expect((await screen.findByRole('alert')).textContent).toBe('Acesso restrito a administradores.');
    expect(screen.getByRole('button', { name: '+ Novo Barbeiro' })).toHaveProperty('disabled', true);

    mockApi();
    click('Tentar de novo');
    expect(await screen.findByRole('row', { name: 'Ana' })).toBeTruthy();
  });
});

describe('AdminBarbers: ativar e desativar', () => {
  it('desativar pede confirmação e manda is_active false', async () => {
    await renderPage();
    mocked.put.mockResolvedValue({ data: { ...ANA, is_active: false } });
    click('Desativar', row('Ana'));
    click('Confirmar', row('Ana'));

    expect((await screen.findByRole('status')).textContent).toBe('Barbeiro desativado.');
    expect(mocked.put).toHaveBeenCalledWith('/barbers/ana', { is_active: false });
    expect(within(row('Ana')).getByText('Desativado')).toBeTruthy();
  });

  it('a recusa por agendamentos futuros aparece, e o barbeiro continua ativo', async () => {
    await renderPage();
    const refusal = 'O barbeiro tem 3 agendamento(s) futuro(s). Cancele ou remaneje antes de desativá-lo.';
    mocked.put.mockRejectedValue(httpError(400, refusal));
    click('Desativar', row('Ana'));
    click('Confirmar', row('Ana'));

    expect((await screen.findByRole('alert')).textContent).toBe(refusal);
    expect(within(row('Ana')).getByText('Ativo')).toBeTruthy();
  });

  it('reativar manda is_active true, sem confirmação', async () => {
    await renderPage();
    mocked.put.mockResolvedValue({ data: { ...BRUNO, is_active: true } });
    click('Reativar', row('Bruno'));

    expect((await screen.findByRole('status')).textContent).toBe('Barbeiro reativado.');
    expect(mocked.put).toHaveBeenCalledWith('/barbers/bruno', { is_active: true });
  });
});

describe('AdminBarbers: novo barbeiro', () => {
  async function pickCarla() {
    await renderPage();
    click('+ Novo Barbeiro');
    const carla = await screen.findByRole('row', { name: 'Carla' });
    // Ana já é barbeira: não pode ser escolhida.
    expect(within(screen.getAllByRole('row', { name: 'Ana' })[0]).getByText('Já é barbeiro')).toBeTruthy();
    click('Escolher', carla);
    await screen.findByRole('form', { name: 'Novo barbeiro' });
  }

  it('cria o perfil do usuário escolhido, vincula os serviços e carrega a lista de novo', async () => {
    await pickCarla();
    mocked.post.mockImplementation(async (url: string) => (url === '/barbers' ? { data: { id: 'carla' } } : {}));
    fireEvent.click(await screen.findByLabelText('Corte'));
    type('Comissão (%)', '45');
    click('Salvar barbeiro');

    expect((await screen.findByRole('status')).textContent).toBe('Barbeiro criado.');
    expect(mocked.post).toHaveBeenCalledWith('/barbers', { user_id: 'u-carla', commission_rate: '45.00' });
    expect(mocked.post).toHaveBeenCalledWith('/services/corte/barbers/carla');
    expect(screen.queryByRole('form')).toBeNull();
    await waitFor(() => expect(barbersLoads()).toBe(2));
  });

  it('falha nos vínculos depois de criar aparece no topo, com o formulário fechado', async () => {
    await pickCarla();
    mocked.post.mockImplementation(async (url: string) => {
      if (url === '/barbers') return { data: { id: 'carla' } };
      throw httpError(400, 'Barbeiro desativado não pode ser vinculado.');
    });
    fireEvent.click(await screen.findByLabelText('Barba'));
    click('Salvar barbeiro');

    expect((await screen.findByRole('alert')).textContent).toBe('Barbeiro desativado não pode ser vinculado.');
    expect(screen.queryByRole('form')).toBeNull();
  });

  it('erro da criação fica no formulário', async () => {
    await pickCarla();
    mocked.post.mockRejectedValue(httpError(400, 'Usuário já possui perfil de barbeiro.'));
    click('Salvar barbeiro');

    expect((await screen.findByRole('alert')).textContent).toBe('Usuário já possui perfil de barbeiro.');
    expect(screen.getByRole('form', { name: 'Novo barbeiro' })).toBeTruthy();
    expect(barbersLoads()).toBe(1);
  });

  it('"Trocar" volta à busca', async () => {
    await pickCarla();
    click('Trocar');
    expect(await screen.findByRole('region', { name: 'Escolher o usuário' })).toBeTruthy();
  });
});

describe('AdminBarbers: editar e escala', () => {
  it('editar manda só o que mudou e acerta os vínculos', async () => {
    await renderPage(undefined, { ana: ['barba'] });
    mocked.put.mockResolvedValue({ data: { ...ANA, commission_rate: '30.00' } });
    mocked.post.mockResolvedValue({});
    mocked.delete.mockResolvedValue({});
    click('Editar', row('Ana'));
    fireEvent.click(await screen.findByLabelText('Corte'));
    fireEvent.click(screen.getByLabelText('Barba'));
    type('Comissão (%)', '30');
    click('Salvar barbeiro');

    expect((await screen.findByRole('status')).textContent).toBe('Barbeiro atualizado.');
    expect(mocked.put).toHaveBeenCalledWith('/barbers/ana', { commission_rate: '30.00' });
    expect(mocked.post).toHaveBeenCalledWith('/services/corte/barbers/ana');
    expect(mocked.delete).toHaveBeenCalledWith('/services/barba/barbers/ana');
    expect(within(row('Ana')).getByText('30,00%')).toBeTruthy();
  });

  it('só os serviços mudaram: não chama o PUT do perfil', async () => {
    await renderPage();
    mocked.post.mockResolvedValue({});
    click('Editar', row('Ana'));
    fireEvent.click(await screen.findByLabelText('Barba'));
    click('Salvar barbeiro');

    expect((await screen.findByRole('status')).textContent).toBe('Barbeiro atualizado.');
    expect(mocked.put).not.toHaveBeenCalled();
    expect(mocked.post).toHaveBeenCalledWith('/services/barba/barbers/ana');
  });

  it('a escala abre, grava a semana e fecha com a mensagem', async () => {
    await renderPage();
    mocked.put.mockResolvedValue({ data: defaultWeek() });
    click('Escala', row('Ana'));
    await screen.findByRole('form', { name: 'Escala de Ana' });
    type('Segunda: fim', '17:00');
    click('Salvar escala');

    expect((await screen.findByRole('status')).textContent).toBe('Escala salva.');
    expect(mocked.put).toHaveBeenCalledWith('/barbers/ana/schedule', expect.any(Array));
    expect(screen.queryByRole('form')).toBeNull();
  });
});
