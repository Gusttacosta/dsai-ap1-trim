import { fitsTrimmed, parsePositiveInt } from './textValidation';

// Fidelidade no painel: os prêmios e o ajuste manual de pontos, com as regras do backend
// (src/backend/modules/loyalty/schemas.py; SPEC/2026-11-26-painel-fidelidade.md). Cada validate*
// devolve a mensagem de erro, ou null quando o valor serve.

export const REWARD_NAME_MAX = 150;
export const REWARD_DESCRIPTION_MAX = 500;
/** Teto da tela: o backend não tem, e a coluna é Integer. */
export const POINTS_MAX = 1_000_000;
export const REASON_MIN = 3;
export const REASON_MAX = 200;

export const REWARD_NAME_ERROR = `Nome do prêmio deve ter entre 1 e ${REWARD_NAME_MAX} caracteres`;
export const REWARD_DESCRIPTION_ERROR = `Descrição deve ter até ${REWARD_DESCRIPTION_MAX} caracteres`;
export const POINTS_COST_ERROR = 'Custo deve ser um número inteiro de 1 a 1.000.000 pontos';
export const ADJUST_POINTS_ERROR = 'Pontos devem ser um número inteiro de 1 a 1.000.000';
export const ADJUST_REASON_ERROR = `O motivo deve ter entre ${REASON_MIN} e ${REASON_MAX} caracteres`;

/** Pontos: inteiro de 1 a 1.000.000, ou null quando não serve. */
export const parsePoints = (text: string): number | null => parsePositiveInt(text, POINTS_MAX);

/** "1.200 pts" */
export const formatPoints = (points: number) => `${points.toLocaleString('pt-BR')} pts`;

export function validateRewardName(text: string): string | null {
  return fitsTrimmed(text, REWARD_NAME_MAX) ? null : REWARD_NAME_ERROR;
}

/** A descrição é opcional: vazia serve. */
export function validateRewardDescription(text: string): string | null {
  return text.trim().length <= REWARD_DESCRIPTION_MAX ? null : REWARD_DESCRIPTION_ERROR;
}

export function validatePointsCost(text: string): string | null {
  return parsePoints(text) === null ? POINTS_COST_ERROR : null;
}

export function validateAdjustPoints(text: string): string | null {
  return parsePoints(text) === null ? ADJUST_POINTS_ERROR : null;
}

export function validateAdjustReason(text: string): string | null {
  return fitsTrimmed(text, REASON_MAX) && text.trim().length >= REASON_MIN ? null : ADJUST_REASON_ERROR;
}
