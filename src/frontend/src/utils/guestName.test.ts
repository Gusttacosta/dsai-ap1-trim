import { describe, expect, it } from 'vitest';
import {
  CHARACTERS_ERROR,
  FIRST_AND_LAST_ERROR,
  TOO_LONG_ERROR,
  cleanGuestName,
  validateGuestName,
} from './guestName';

// SPEC/2026-11-23-nome-do-visitante.md: os mesmos casos de tests/test_nome_do_visitante.py.

const NAME_255 = 'A'.repeat(127) + ' ' + 'B'.repeat(127);
const NAME_256 = 'A'.repeat(128) + ' ' + 'B'.repeat(127);

describe('validateGuestName', () => {
  it.each([
    ['', FIRST_AND_LAST_ERROR],
    ['     ', FIRST_AND_LAST_ERROR],
    ['sev', FIRST_AND_LAST_ERROR],
    ['Visitante', FIRST_AND_LAST_ERROR],
    ['  Severino  ', FIRST_AND_LAST_ERROR],
    ['Ana S', FIRST_AND_LAST_ERROR],
    ['A B', FIRST_AND_LAST_ERROR],
    ['Ana 123', CHARACTERS_ERROR],
    ['Ana Silva2', CHARACTERS_ERROR],
    ['Ana Silva²', CHARACTERS_ERROR],
    ['Ana @Silva', CHARACTERS_ERROR],
    ['Ana <b>Silva</b>', CHARACTERS_ERROR],
    ['Ana_Maria Silva', CHARACTERS_ERROR],
    ['Ana -- Silva', CHARACTERS_ERROR],
    [NAME_256, TOO_LONG_ERROR],
    ['Ana ' + 'x'.repeat(300), TOO_LONG_ERROR],
  ])('recusa %j', (name, message) => {
    expect(validateGuestName(name)).toBe(message);
  });

  it.each([
    'Ana Sá',
    'João da Silva',
    'Li Wu',
    "Maria D'Ávila",
    'Maria D’Ávila',
    'Maria-José Souza',
    'José Souza Jr.',
    'ÉLIO ÇARDOSO',
    '  ana   de \t souza ',
    NAME_255,
    '   ' + NAME_255.replace(' ', '     ') + '   ',
  ])('aceita %j', (name) => {
    expect(validateGuestName(name)).toBeNull();
  });

  it('conta letras fora do plano básico como um caractere só, como o backend', () => {
    // "𝒜" (U+1D49C) é uma letra e ocupa duas unidades UTF-16.
    expect(validateGuestName('𝒜𝒜 Silva')).toBeNull();
    expect(validateGuestName('𝒜 Silva')).toBe(FIRST_AND_LAST_ERROR);
  });
});

describe('cleanGuestName', () => {
  it('remove os espaços das pontas e junta os repetidos', () => {
    expect(cleanGuestName('  ana   de \t souza ')).toBe('ana de souza');
  });

  it('nome só com espaços vira vazio', () => {
    expect(cleanGuestName('   ')).toBe('');
  });
});
