// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { httpError } from '../../testUtils/httpError';
import { ANA } from '../../testUtils/loyalty';
import { ADJUST_POINTS_ERROR, ADJUST_REASON_ERROR } from '../../utils/loyalty';
import AdjustPointsForm, { adjustQuestion } from './AdjustPointsForm';

// SPEC/2026-11-26-painel-fidelidade.md: o ajuste manual de pontos, com motivo e confirmação.

afterEach(cleanup);

function renderForm(onSave: (...args: unknown[]) => Promise<unknown> = vi.fn(async () => undefined)) {
  render(<AdjustPointsForm wallet={ANA} onSave={onSave} onCancel={vi.fn()} />);
  return onSave;
}

const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const REASON = 'Motivo (o cliente vê na notificação)';
const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }));

describe('AdjustPointsForm', () => {
  it('mostra a pergunta com o saldo antes e depois, e só grava no "Confirmar"', async () => {
    const onSave = renderForm();
    expect(screen.getByRole('form', { name: 'Ajustar pontos de Ana Lima' })).toBeTruthy();
    type('Pontos', '50');
    type(REASON, '  Aniversário  ');
    click('Ajustar pontos');

    expect(
      await screen.findByText('Adicionar 50 pts a Ana Lima? O saldo passa de 120 para 170 pts. Motivo: Aniversário.'),
    ).toBeTruthy();
    expect(onSave).not.toHaveBeenCalled();

    click('Confirmar');
    await vi.waitFor(() => expect(onSave).toHaveBeenCalledWith('add', 50, 'Aniversário'));
  });

  it('retirar pergunta com o saldo menor e grava "remove"', async () => {
    const onSave = renderForm();
    type('Operação', 'remove');
    type('Pontos', '20');
    type(REASON, 'Lançamento em dobro');
    click('Ajustar pontos');
    expect(
      await screen.findByText('Retirar 20 pts de Ana Lima? O saldo passa de 120 para 100 pts. Motivo: Lançamento em dobro.'),
    ).toBeTruthy();
    click('Confirmar');
    await vi.waitFor(() => expect(onSave).toHaveBeenCalledWith('remove', 20, 'Lançamento em dobro'));
  });

  it.each([
    ['', 'Aniversário', ADJUST_POINTS_ERROR],
    ['0', 'Aniversário', ADJUST_POINTS_ERROR],
    ['2,5', 'Aniversário', ADJUST_POINTS_ERROR],
    ['50', '', ADJUST_REASON_ERROR],
    ['50', '  ab ', ADJUST_REASON_ERROR],
    ['50', 'x'.repeat(201), ADJUST_REASON_ERROR],
  ])('recusa pontos %j com motivo %j, sem pergunta nem chamada', async (points, reason, message) => {
    const onSave = renderForm();
    type('Pontos', points);
    type(REASON, reason);
    click('Ajustar pontos');
    expect((await screen.findByRole('alert')).textContent).toBe(message);
    expect(screen.queryByRole('button', { name: 'Confirmar' })).toBeNull();
    expect(onSave).not.toHaveBeenCalled();
  });

  it('"Voltar" volta ao formulário sem gravar', async () => {
    const onSave = renderForm();
    type('Pontos', '50');
    type(REASON, 'Aniversário');
    click('Ajustar pontos');
    click('Voltar');
    expect(screen.getByRole('button', { name: 'Ajustar pontos' })).toBeTruthy();
    expect(onSave).not.toHaveBeenCalled();
  });

  it('o saldo insuficiente da API aparece no formulário', async () => {
    const detail = 'Saldo insuficiente para retirar 500 pts. O cliente possui 120 pts.';
    renderForm(vi.fn().mockRejectedValue(httpError(400, detail)));
    type('Operação', 'remove');
    type('Pontos', '500');
    type(REASON, 'Correção');
    click('Ajustar pontos');
    click('Confirmar');
    expect((await screen.findByRole('alert')).textContent).toBe(detail);
  });
});

describe('adjustQuestion', () => {
  it('separa o milhar nos pontos e no saldo', () => {
    const rich = { ...ANA, balance: 1500 };
    expect(adjustQuestion(rich, 'add', 1000, 'Campanha')).toBe(
      'Adicionar 1.000 pts a Ana Lima? O saldo passa de 1.500 para 2.500 pts. Motivo: Campanha.',
    );
  });
});
