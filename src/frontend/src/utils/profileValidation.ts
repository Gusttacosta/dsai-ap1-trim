// Validações da página "Minha conta", com as mesmas regras do backend
// (src/backend/modules/auth/schemas.py; SPEC/2026-11-22-auth-perfil-senha.md).
// Cada função devolve a mensagem de erro, ou null quando o valor serve.

export const FULL_NAME_MAX = 255;
export const AVATAR_URL_MAX = 2048;

const PHONE_CHARS = /^\+?[\d\s()-]+$/;

export function validateFullName(name: string): string | null {
  const trimmed = name.trim();
  if (trimmed.length < 2) return 'Nome deve ter no mínimo 2 caracteres';
  if (trimmed.length > FULL_NAME_MAX) return `Nome deve ter no máximo ${FULL_NAME_MAX} caracteres`;
  return null;
}

/** Dígitos do telefone sem o +55, ou a mensagem de erro. Vazio vira ''. */
function phoneDigits(phone: string): { digits: string } | { error: string } {
  const value = phone.trim();
  if (!value) return { digits: '' };
  if (!PHONE_CHARS.test(value)) {
    return { error: 'Telefone deve ter só números, espaços, parênteses, hífen e o prefixo +55' };
  }
  let digits = value.replace(/\D/g, '');
  if (value.startsWith('+')) {
    if (!digits.startsWith('55')) return { error: 'Telefone deve ser brasileiro (+55)' };
    digits = digits.slice(2);
  }
  if (digits.length !== 10 && digits.length !== 11) {
    return { error: 'Telefone deve ter o DDD e 8 dígitos (fixo) ou 9 dígitos (celular)' };
  }
  if (digits[0] === '0') return { error: 'DDD não pode começar com 0' };
  if (digits.length === 11 && digits[2] !== '9') return { error: 'Celular deve começar com 9 depois do DDD' };
  return { digits };
}

export function validatePhone(phone: string): string | null {
  const result = phoneDigits(phone);
  return 'error' in result ? result.error : null;
}

/** Telefone no formato que o backend grava: (91) 99999-0000. Vazio vira ''. */
export function formatPhone(phone: string): string {
  const result = phoneDigits(phone);
  if ('error' in result) throw new Error(result.error);
  const { digits } = result;
  if (!digits) return '';
  const number = digits.slice(2);
  return `(${digits.slice(0, 2)}) ${number.slice(0, -4)}-${number.slice(-4)}`;
}

export function validateAvatarUrl(url: string): string | null {
  const value = url.trim();
  if (!value) return null;
  if (value.length > AVATAR_URL_MAX) return `URL da foto deve ter no máximo ${AVATAR_URL_MAX} caracteres`;
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    parsed = new URL('invalid:');
  }
  if ((parsed.protocol !== 'http:' && parsed.protocol !== 'https:') || !parsed.host) {
    return 'URL da foto deve começar com http:// ou https:// e ter um endereço';
  }
  return null;
}

/** Senha forte (regra 2 da AP1), mais a confirmação e a diferença para a atual. */
export function validateNewPassword(current: string, next: string, confirmation: string): string | null {
  if (!current) return 'Informe a senha atual';
  if (next.length < 8) return 'Nova senha deve ter no mínimo 8 caracteres';
  if (!/[a-zA-Z]/.test(next)) return 'Nova senha deve conter pelo menos 1 letra';
  if (!/\d/.test(next)) return 'Nova senha deve conter pelo menos 1 número';
  if (next === current) return 'A nova senha precisa ser diferente da atual.';
  if (next !== confirmation) return 'A confirmação não é igual à nova senha';
  return null;
}
