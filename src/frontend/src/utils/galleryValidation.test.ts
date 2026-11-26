import { describe, expect, it } from 'vitest';
import {
  IMAGE_URL_ERROR,
  PHOTO_DESCRIPTION_ERROR,
  REASON_ERROR,
  TAG_NAME_ERROR,
  validateImageUrl,
  validatePhotoDescription,
  validateReason,
  validateTagName,
} from './galleryValidation';

// SPEC/2026-11-26-painel-galeria.md: as regras do backend conferidas antes da API.

describe('validateImageUrl', () => {
  it.each(['https://fotos.exemplo.com/a.jpg', 'http://exemplo.com/a.png', '  https://exemplo.com/b.jpg  '])(
    'aceita %s',
    (url) => expect(validateImageUrl(url)).toBeNull(),
  );

  it.each(['', '   ', 'fotos.exemplo.com/a.jpg', 'ftp://exemplo.com/a.jpg', 'https://exemplo.com/a b.jpg', 'https://'])(
    'recusa "%s"',
    (url) => expect(validateImageUrl(url)).toBe(IMAGE_URL_ERROR),
  );

  it('aceita até 1.000 caracteres e recusa 1.001', () => {
    const base = 'https://exemplo.com/';
    expect(validateImageUrl(base + 'a'.repeat(1000 - base.length))).toBeNull();
    expect(validateImageUrl(base + 'a'.repeat(1001 - base.length))).toBe(IMAGE_URL_ERROR);
  });
});

describe('validatePhotoDescription', () => {
  it('vazia serve; até 500 caracteres serve; 501 não', () => {
    expect(validatePhotoDescription('')).toBeNull();
    expect(validatePhotoDescription('a'.repeat(500))).toBeNull();
    expect(validatePhotoDescription('a'.repeat(501))).toBe(PHOTO_DESCRIPTION_ERROR);
  });
});

describe('validateReason', () => {
  it('exige de 1 a 500 caracteres, sem contar os espaços das pontas', () => {
    expect(validateReason('Foto desfocada')).toBeNull();
    expect(validateReason('  ')).toBe(REASON_ERROR);
    expect(validateReason(` ${'a'.repeat(500)} `)).toBeNull();
    expect(validateReason('a'.repeat(501))).toBe(REASON_ERROR);
  });
});

describe('validateTagName', () => {
  it('exige de 1 a 50 caracteres, sem contar os espaços das pontas', () => {
    expect(validateTagName(' Degradê ')).toBeNull();
    expect(validateTagName('')).toBe(TAG_NAME_ERROR);
    expect(validateTagName('a'.repeat(50))).toBeNull();
    expect(validateTagName('a'.repeat(51))).toBe(TAG_NAME_ERROR);
  });
});
