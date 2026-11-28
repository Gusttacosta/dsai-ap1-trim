// Nome do visitante no agendamento sem conta, com a regra do backend
// (clean_guest_name em src/backend/modules/appointments/schemas.py;
// SPEC/2026-11-23-nome-do-visitante.md). \p{L} é a mesma classe do str.isalpha do Python.

export const GUEST_NAME_MAX = 255;

export const FIRST_AND_LAST_ERROR = 'Informe nome e sobrenome';
export const CHARACTERS_ERROR = 'Nome deve ter só letras, espaços, apóstrofo, hífen e ponto';
export const TOO_LONG_ERROR = `Nome deve ter no máximo ${GUEST_NAME_MAX} caracteres`;

const GUEST_WORD = /^(?=.*\p{L})[\p{L}'’.-]+$/u;

/** Nome sem os espaços das pontas e com os repetidos trocados por um só, como o backend grava. */
export function cleanGuestName(name: string): string {
  return name.trim().split(/\s+/).filter(Boolean).join(' ');
}

/** Mensagem de erro, ou null quando o nome serve. */
export function validateGuestName(name: string): string | null {
  const words = cleanGuestName(name).split(' ').filter(Boolean);
  // O backend conta caracteres Unicode (code points), como o spread de string.
  if (words.length < 2 || words.some((word) => [...word].length < 2)) return FIRST_AND_LAST_ERROR;
  if (!words.every((word) => GUEST_WORD.test(word))) return CHARACTERS_ERROR;
  if ([...words.join(' ')].length > GUEST_NAME_MAX) return TOO_LONG_ERROR;
  return null;
}
