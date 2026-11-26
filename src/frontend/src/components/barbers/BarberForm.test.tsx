// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../../api';
import { barber } from '../../testUtils/barbers';
import { httpError } from '../../testUtils/httpError';
import { BIO_ERROR, COMMISSION_ERROR, INSTAGRAM_ERROR } from '../../utils/barberValidation';
import BarberForm, { barberChanges } from './BarberForm';

// SPEC/2026-11-26-painel-barbeiros.md: criar e editar um barbeiro, com os serviços.

vi.mock('../../api', () => ({ default: { get: vi.fn() } }));
const get = (api as unknown as { get: ReturnType<typeof vi.fn> }).get;

const service = (id: string, name: string, is_active = true) => ({ id, name, is_active });
const CATALOG = [service('barba', 'Barba'), service('corte', 'Corte'), service('velho', 'Velho', false)];

/** Catálogo do admin e serviços já vinculados ao barbeiro. */
function mockServices(linked: string[] = [], catalog = CATALOG) {
  get.mockImplementation(async (url: string) =>
    url === '/services/admin' ? { data: catalog } : { data: linked.map((id) => ({ id })) },
  );
}

const ANA = barber('ana', 'Ana', { bio: 'Degradê', instagram_url: 'https://instagram.com/ana', commission_rate: '40.00' });
const USER = { id: 'u1', full_name: 'Carla', email: 'carla@teste.com' };

const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const submit = () => fireEvent.click(screen.getByRole('button', { name: 'Salvar barbeiro' }));

function renderForm(props: Partial<Parameters<typeof BarberForm>[0]> = {}) {
  const handlers = { onSave: vi.fn(async () => undefined), onCancel: vi.fn(), ...props };
  render(<BarberForm {...handlers} />);
  return handlers;
}

beforeEach(() => {
  get.mockReset();
});
afterEach(cleanup);

describe('BarberForm: criação', () => {
  it('parte do usuário escolhido, com comissão 50, e manda o perfil e os serviços marcados', async () => {
    mockServices();
    const onChangeUser = vi.fn();
    const { onSave } = renderForm({ user: USER, onChangeUser });

    expect(screen.getByRole('form', { name: 'Novo barbeiro' })).toBeTruthy();
    expect(screen.getByText('carla@teste.com')).toBeTruthy();
    expect(screen.getByLabelText('Comissão (%)')).toHaveProperty('value', '50');
    // Só os serviços ativos aparecem.
    fireEvent.click(await screen.findByLabelText('Corte'));
    expect(screen.queryByLabelText('Velho')).toBeNull();
    type('Comissão (%)', '35,5');
    type('Bio (opcional)', '  Navalha  ');
    submit();

    await waitFor(() => expect(onSave).toHaveBeenCalled());
    expect(onSave).toHaveBeenCalledWith({
      kind: 'create',
      input: { user_id: 'u1', commission_rate: '35.50', bio: 'Navalha' },
      serviceIds: ['corte'],
    });

    fireEvent.click(screen.getByRole('button', { name: 'Trocar' }));
    expect(onChangeUser).toHaveBeenCalled();
  });

  it('sem serviço marcado, manda serviceIds null', async () => {
    mockServices();
    const { onSave } = renderForm({ user: USER });
    await screen.findByLabelText('Corte');
    submit();
    await waitFor(() =>
      expect(onSave).toHaveBeenCalledWith({ kind: 'create', input: { user_id: 'u1', commission_rate: '50.00' }, serviceIds: null }),
    );
  });

  it.each([
    ['Comissão (%)', '101', COMMISSION_ERROR],
    ['Instagram (opcional)', 'instagram.com/x', INSTAGRAM_ERROR],
    ['Bio (opcional)', 'a'.repeat(501), BIO_ERROR],
  ])('%s inválido é recusado sem salvar', async (label, value, message) => {
    mockServices();
    const { onSave } = renderForm({ user: USER });
    type(label, value);
    submit();
    expect((await screen.findByRole('alert')).textContent).toBe(message);
    expect(onSave).not.toHaveBeenCalled();
  });

  it('erro da API aparece no formulário', async () => {
    mockServices();
    renderForm({ user: USER, onSave: vi.fn().mockRejectedValue(httpError(400, 'Usuário já possui perfil de barbeiro.')) });
    submit();
    expect((await screen.findByRole('alert')).textContent).toBe('Usuário já possui perfil de barbeiro.');
  });
});

describe('BarberForm: edição', () => {
  it('mostra os dados e os serviços vinculados', async () => {
    mockServices(['barba']);
    renderForm({ barber: ANA });

    expect(screen.getByRole('form', { name: 'Editar Ana' })).toBeTruthy();
    expect(screen.getByLabelText('Comissão (%)')).toHaveProperty('value', '40,00');
    expect(screen.getByLabelText('Bio (opcional)')).toHaveProperty('value', 'Degradê');
    expect(await screen.findByLabelText('Barba')).toHaveProperty('checked', true);
    expect(screen.getByLabelText('Corte')).toHaveProperty('checked', false);
    expect(get).toHaveBeenCalledWith('/services/barber/ana');
  });

  it('manda só o que mudou, null para o que foi apagado, e os serviços novos', async () => {
    mockServices(['barba']);
    const { onSave } = renderForm({ barber: ANA });
    fireEvent.click(await screen.findByLabelText('Corte'));
    fireEvent.click(screen.getByLabelText('Barba'));
    type('Bio (opcional)', '   ');
    type('Instagram (opcional)', '');
    submit();

    await waitFor(() =>
      expect(onSave).toHaveBeenCalledWith({
        kind: 'update',
        changes: { bio: null, instagram_url: null },
        serviceIds: ['corte'],
      }),
    );
  });

  it('sem mudança (inclusive marcar e desmarcar de volta), diz "Nada mudou." sem salvar', async () => {
    mockServices(['barba']);
    const { onSave } = renderForm({ barber: ANA });
    fireEvent.click(await screen.findByLabelText('Corte'));
    fireEvent.click(screen.getByLabelText('Corte'));
    type('Comissão (%)', '40');
    submit();

    expect((await screen.findByRole('status')).textContent).toBe('Nada mudou.');
    expect(onSave).not.toHaveBeenCalled();
  });

  it('falha ao carregar os serviços mostra o erro e não mexe nos vínculos', async () => {
    get.mockRejectedValue(httpError(500));
    const { onSave } = renderForm({ barber: ANA });
    expect((await screen.findByRole('alert')).textContent).toBe('Não foi possível carregar os serviços.');

    type('Comissão (%)', '45');
    submit();
    await waitFor(() =>
      expect(onSave).toHaveBeenCalledWith({ kind: 'update', changes: { commission_rate: '45.00' }, serviceIds: null }),
    );
  });

  it('barberChanges compara a comissão pelo valor', () => {
    expect(barberChanges(ANA, { commission: '40,0', bio: 'Degradê', instagram: 'https://instagram.com/ana' })).toEqual({});
  });
});
