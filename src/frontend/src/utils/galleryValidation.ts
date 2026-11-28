import { fitsTrimmed } from './textValidation';

// Validação dos campos da galeria no painel, com as regras do backend
// (src/backend/modules/gallery/schemas.py; SPEC/2026-11-26-painel-galeria.md).
// Cada validate* devolve a mensagem de erro, ou null quando o valor serve.

export const IMAGE_URL_MAX = 1000;
export const PHOTO_DESCRIPTION_MAX = 500;
export const REASON_MAX = 500;
export const TAG_NAME_MAX = 50;

export const IMAGE_URL_ERROR = 'Informe a URL da imagem (http ou https, até 1.000 caracteres)';
export const PHOTO_DESCRIPTION_ERROR = `Descrição deve ter até ${PHOTO_DESCRIPTION_MAX} caracteres`;
export const BARBER_ERROR = 'Escolha o barbeiro da foto';
export const REASON_ERROR = `O motivo deve ter entre 1 e ${REASON_MAX} caracteres`;
export const TAG_NAME_ERROR = `Nome da tag deve ter entre 1 e ${TAG_NAME_MAX} caracteres`;

/** URL http(s) sem espaços, até o tamanho da coluna. */
export function validateImageUrl(text: string): string | null {
  const url = text.trim();
  return /^https?:\/\/\S+$/i.test(url) && url.length <= IMAGE_URL_MAX ? null : IMAGE_URL_ERROR;
}

/** A descrição é opcional: vazia serve. */
export function validatePhotoDescription(text: string): string | null {
  return text.trim().length <= PHOTO_DESCRIPTION_MAX ? null : PHOTO_DESCRIPTION_ERROR;
}

export function validateReason(text: string): string | null {
  return fitsTrimmed(text, REASON_MAX) ? null : REASON_ERROR;
}

export function validateTagName(text: string): string | null {
  return fitsTrimmed(text, TAG_NAME_MAX) ? null : TAG_NAME_ERROR;
}
