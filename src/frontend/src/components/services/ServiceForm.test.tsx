// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AdminService } from '../../hooks/useAdminServices';
import { httpError } from '../../testUtils/httpError';
import { DURATION_ERROR, NAME_ERROR, PRICE_ERROR } from '../../utils/serviceValidation';
import ServiceForm, { serviceChanges, serviceInput } from './ServiceForm';

// SPEC/2026-11-23-painel-servicos.md: formulário de criação e de edição do painel.

const CORTE: AdminService = {
  id: 'c1',
  name: 'Corte',
  description: 'Tesoura e máquina',
  price: '35.00',
  duration_minutes: 30,
  is_active: true,
};

const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const submit = () => fireEvent.click(screen.getByRole('button', { name: 'Salvar serviço' }));

function fillNew(values: Partial<Record<'Nome' | 'Descrição (opcional)' | 'Preço (R$)' | 'Duração (min)', string>>) {
  const all = { Nome: 'Barba', 'Preço (R$)': '25', 'Duração (min)': '20', ...values };
  for (const [label, value] of Object.entries(all)) type(label, value);
}

afterEach(cleanup);

describe('serviceInput e serviceChanges', () => {
  it('serviceInput converte para o formato da API', () => {
    expect(serviceInput({ name: ' Corte ', description: '  ', price: '35,5', duration: ' 30 ' })).toEqual({
      name: 'Corte',
      description: null,
      price: '35.50',
      duration_minutes: 30,
    });
  });

  it('serviceChanges só traz o que mudou', () => {
    const fields = { name: 'Corte', description: 'Tesoura e máquina', price: '35', duration: '45' };
    expect(serviceChanges(CORTE, fields)).toEqual({ duration_minutes: 45 });
  });

  it('o preço é comparado pelo valor, e apagar a descrição manda null', () => {
    const fields = { name: 'Corte', description: '', price: '35,00', duration: '30' };
    expect(serviceChanges(CORTE, fields)).toEqual({ description: null });
  });

  it('descrição vazia no backend e campo vazio não contam como mudança', () => {
    const semDescricao = { ...CORTE, description: '' };
    expect(serviceChanges(semDescricao, { name: 'Corte', description: '', price: '35', duration: '30' })).toEqual({});
  });
});

describe('ServiceForm: criação', () => {
  it('começa vazio, com o título de novo serviço', () => {
    render(<ServiceForm onSave={vi.fn()} onCancel={vi.fn()} />);

    expect(screen.getByRole('heading', { name: 'Novo serviço' })).toBeTruthy();
    expect(screen.getByLabelText('Nome')).toHaveProperty('value', '');
    expect(screen.getByLabelText('Preço (R$)')).toHaveProperty('value', '');
  });

  it('envia todos os campos no formato da API', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<ServiceForm onSave={onSave} onCancel={vi.fn()} />);

    fillNew({ Nome: ' Barba completa ', 'Preço (R$)': '35,5', 'Duração (min)': '40' });
    submit();

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(onSave).toHaveBeenCalledWith({
      name: 'Barba completa',
      description: null,
      price: '35.50',
      duration_minutes: 40,
    });
  });

  it.each([
    ['Nome', '', NAME_ERROR],
    ['Nome', ' C ', NAME_ERROR],
    ['Nome', 'x'.repeat(101), NAME_ERROR],
    ['Preço (R$)', '', PRICE_ERROR],
    ['Preço (R$)', '-3', PRICE_ERROR],
    ['Preço (R$)', '10,999', PRICE_ERROR],
    ['Preço (R$)', '100000000', PRICE_ERROR],
    ['Duração (min)', '0', DURATION_ERROR],
    ['Duração (min)', '721', DURATION_ERROR],
    ['Duração (min)', '15,5', DURATION_ERROR],
  ])('%s = %j mostra o erro e não envia', async (label, value, message) => {
    const onSave = vi.fn();
    render(<ServiceForm onSave={onSave} onCancel={vi.fn()} />);

    fillNew({ [label]: value });
    submit();

    expect((await screen.findByRole('alert')).textContent).toBe(message);
    expect(onSave).not.toHaveBeenCalled();
  });

  it.each([
    ['Nome', 'Co'],
    ['Nome', 'x'.repeat(100)],
    ['Preço (R$)', '0'],
    ['Preço (R$)', '99999999,99'],
    ['Duração (min)', '1'],
    ['Duração (min)', '720'],
  ])('%s = %j no limite é aceito', async (label, value) => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<ServiceForm onSave={onSave} onCancel={vi.fn()} />);

    fillNew({ [label]: value });
    submit();

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('o erro 400 do backend aparece e os valores digitados continuam', async () => {
    const onSave = vi.fn().mockRejectedValue(httpError(400, "Já existe um serviço com o nome 'Barba'."));
    render(<ServiceForm onSave={onSave} onCancel={vi.fn()} />);

    fillNew({ 'Preço (R$)': '25,90' });
    submit();

    expect((await screen.findByRole('alert')).textContent).toBe("Já existe um serviço com o nome 'Barba'.");
    expect(screen.getByLabelText('Nome')).toHaveProperty('value', 'Barba');
    expect(screen.getByLabelText('Preço (R$)')).toHaveProperty('value', '25,90');
    expect(screen.getByRole('button', { name: 'Salvar serviço' })).toHaveProperty('disabled', false);
  });

  it('o erro 422 do backend aparece em português', async () => {
    const onSave = vi.fn().mockRejectedValue(httpError(422, [{ msg: 'Value error, Campo obrigatório não pode ser nulo' }]));
    render(<ServiceForm onSave={onSave} onCancel={vi.fn()} />);

    fillNew({});
    submit();

    expect((await screen.findByRole('alert')).textContent).toBe('Campo obrigatório não pode ser nulo');
  });

  it('enquanto salva, os botões ficam desabilitados', async () => {
    const onSave = vi.fn().mockReturnValue(new Promise(() => {}));
    render(<ServiceForm onSave={onSave} onCancel={vi.fn()} />);

    fillNew({});
    submit();

    expect(await screen.findByRole('button', { name: 'Salvando...' })).toHaveProperty('disabled', true);
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveProperty('disabled', true);
  });

  it('Cancelar não envia nada', () => {
    const onSave = vi.fn();
    const onCancel = vi.fn();
    render(<ServiceForm onSave={onSave} onCancel={onCancel} />);

    fillNew({});
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSave).not.toHaveBeenCalled();
  });
});

describe('ServiceForm: edição', () => {
  it('começa com os dados do serviço', () => {
    render(<ServiceForm service={CORTE} onSave={vi.fn()} onCancel={vi.fn()} />);

    expect(screen.getByRole('heading', { name: 'Editar serviço' })).toBeTruthy();
    expect(screen.getByLabelText('Nome')).toHaveProperty('value', 'Corte');
    expect(screen.getByLabelText('Descrição (opcional)')).toHaveProperty('value', 'Tesoura e máquina');
    expect(screen.getByLabelText('Preço (R$)')).toHaveProperty('value', '35,00');
    expect(screen.getByLabelText('Duração (min)')).toHaveProperty('value', '30');
  });

  it('envia só os campos alterados', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<ServiceForm service={CORTE} onSave={onSave} onCancel={vi.fn()} />);

    type('Preço (R$)', '40');
    type('Nome', 'Corte social');
    submit();

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(onSave).toHaveBeenCalledWith({ name: 'Corte social', price: '40.00' });
  });

  it('sem mudança, não envia e avisa', async () => {
    const onSave = vi.fn();
    render(<ServiceForm service={CORTE} onSave={onSave} onCancel={vi.fn()} />);

    type('Preço (R$)', '35');
    submit();

    expect((await screen.findByRole('status')).textContent).toBe('Nada mudou.');
    expect(onSave).not.toHaveBeenCalled();
  });

  it('a validação vale também na edição', async () => {
    const onSave = vi.fn();
    render(<ServiceForm service={CORTE} onSave={onSave} onCancel={vi.fn()} />);

    type('Duração (min)', '');
    submit();

    expect((await screen.findByRole('alert')).textContent).toBe(DURATION_ERROR);
    expect(onSave).not.toHaveBeenCalled();
  });
});
