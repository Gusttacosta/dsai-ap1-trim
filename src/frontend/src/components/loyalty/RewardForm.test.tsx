// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { httpError } from '../../testUtils/httpError';
import { CORTE } from '../../testUtils/loyalty';
import { POINTS_COST_ERROR, REWARD_DESCRIPTION_ERROR, REWARD_NAME_ERROR } from '../../utils/loyalty';
import RewardForm, { rewardChanges } from './RewardForm';

// SPEC/2026-11-26-painel-fidelidade.md: o formulário de prêmio.

afterEach(cleanup);

function renderForm(reward = undefined as typeof CORTE | undefined, onSave = vi.fn(async () => undefined)) {
  render(<RewardForm reward={reward} onSave={onSave} onCancel={vi.fn()} />);
  return onSave;
}

const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const submit = () => fireEvent.click(screen.getByRole('button', { name: 'Salvar prêmio' }));

describe('RewardForm', () => {
  it('cria com os campos aparados, a descrição vazia como null e o custo inteiro', async () => {
    const onSave = renderForm();
    type('Nome', '  Pomada  ');
    type('Custo (pontos)', ' 120 ');
    submit();
    await vi.waitFor(() => expect(onSave).toHaveBeenCalledWith({ name: 'Pomada', description: null, points_cost: 120 }));
  });

  it.each([
    ['Nome', '   ', REWARD_NAME_ERROR],
    ['Nome', 'x'.repeat(151), REWARD_NAME_ERROR],
    ['Descrição (opcional)', 'x'.repeat(501), REWARD_DESCRIPTION_ERROR],
    ['Custo (pontos)', '0', POINTS_COST_ERROR],
    ['Custo (pontos)', '12,5', POINTS_COST_ERROR],
    ['Custo (pontos)', '1000001', POINTS_COST_ERROR],
  ])('recusa %s = %j sem chamar a API', async (label, value, message) => {
    const onSave = renderForm();
    type('Nome', 'Pomada');
    type('Custo (pontos)', '120');
    type(label, value);
    submit();
    expect((await screen.findByRole('alert')).textContent).toBe(message);
    expect(onSave).not.toHaveBeenCalled();
  });

  it('a edição abre com os dados do prêmio e manda só o que mudou', async () => {
    const onSave = renderForm(CORTE);
    expect(screen.getByLabelText('Nome')).toHaveProperty('value', 'Corte grátis');
    expect(screen.getByLabelText('Custo (pontos)')).toHaveProperty('value', '300');
    type('Custo (pontos)', '350');
    type('Descrição (opcional)', '');
    submit();
    await vi.waitFor(() => expect(onSave).toHaveBeenCalledWith({ description: null, points_cost: 350 }));
  });

  it('sem mudança, diz "Nada mudou." e não chama a API', async () => {
    const onSave = renderForm(CORTE);
    submit();
    expect(await screen.findByText('Nada mudou.')).toBeTruthy();
    expect(onSave).not.toHaveBeenCalled();
  });

  it('o erro da API aparece no formulário', async () => {
    renderForm(undefined, vi.fn().mockRejectedValue(httpError(400, "Já existe um prêmio chamado 'Pomada'.")));
    type('Nome', 'Pomada');
    type('Custo (pontos)', '120');
    submit();
    expect((await screen.findByRole('alert')).textContent).toBe("Já existe um prêmio chamado 'Pomada'.");
  });
});

describe('rewardChanges', () => {
  it('compara o nome aparado e mantém a descrição nula como estava', () => {
    expect(rewardChanges({ ...CORTE, description: null }, { name: ' Corte grátis ', description: ' ', cost: '300' })).toEqual({});
  });
});
