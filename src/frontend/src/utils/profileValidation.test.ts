import { describe, expect, it } from 'vitest';
import {
  formatPhone,
  validateAvatarUrl,
  validateFullName,
  validateNewPassword,
  validatePhone,
} from './profileValidation';

// Mesmos casos de tests/test_auth_perfil.py: a tela não pode aceitar o que o backend recusa.

describe('validateFullName', () => {
  it.each(['Ana', '  Jo  ', 'n'.repeat(255)])('aceita %j', (name) => {
    expect(validateFullName(name)).toBeNull();
  });

  it('recusa nome com menos de 2 caracteres, mesmo com espaços em volta', () => {
    expect(validateFullName('  B  ')).toBe('Nome deve ter no mínimo 2 caracteres');
  });

  it('recusa nome acima de 255 caracteres', () => {
    expect(validateFullName('n'.repeat(256))).toBe('Nome deve ter no máximo 255 caracteres');
  });
});

describe('telefone', () => {
  it.each([
    ['(91) 99999-0000', '(91) 99999-0000'],
    ['91999990000', '(91) 99999-0000'],
    ['91 99999 0000', '(91) 99999-0000'],
    ['+55 (11) 98765-4321', '(11) 98765-4321'],
    ['+5511987654321', '(11) 98765-4321'],
    ['(91) 3333-0000', '(91) 3333-0000'],
    ['9133330000', '(91) 3333-0000'],
    ['  (21) 2222-1111  ', '(21) 2222-1111'],
  ])('%j vira %j', (typed, formatted) => {
    expect(validatePhone(typed)).toBeNull();
    expect(formatPhone(typed)).toBe(formatted);
  });

  it.each(['', '   '])('vazio (%j) é aceito e apaga o telefone', (empty) => {
    expect(validatePhone(empty)).toBeNull();
    expect(formatPhone(empty)).toBe('');
  });

  it.each([
    ['(01) 99999-0000', 'DDD não pode começar com 0'],
    ['9999-0000', 'Telefone deve ter o DDD e 8 dígitos (fixo) ou 9 dígitos (celular)'],
    ['919999900001', 'Telefone deve ter o DDD e 8 dígitos (fixo) ou 9 dígitos (celular)'],
    ['(91) 89999-0000', 'Celular deve começar com 9 depois do DDD'],
    ['91 9999a-0000', 'Telefone deve ter só números, espaços, parênteses, hífen e o prefixo +55'],
    ['91+999990000', 'Telefone deve ter só números, espaços, parênteses, hífen e o prefixo +55'],
    ['+1 415 555 0000', 'Telefone deve ser brasileiro (+55)'],
  ])('%j é recusado', (typed, message) => {
    expect(validatePhone(typed)).toBe(message);
    expect(() => formatPhone(typed)).toThrow(message);
  });
});

describe('validateAvatarUrl', () => {
  it.each(['https://cdn.exemplo.com/a.png', 'http://exemplo.com/f?x=1', '', '  '])('aceita %j', (url) => {
    expect(validateAvatarUrl(url)).toBeNull();
  });

  it.each(['javascript:alert(1)', 'ftp://exemplo.com/a.png', 'https://', 'foto.png'])('recusa %j', (url) => {
    expect(validateAvatarUrl(url)).toBe('URL da foto deve começar com http:// ou https:// e ter um endereço');
  });

  it('recusa URL acima de 2.048 caracteres', () => {
    expect(validateAvatarUrl('https://a.com/' + 'x'.repeat(2040))).toBe(
      'URL da foto deve ter no máximo 2048 caracteres',
    );
  });
});

describe('validateNewPassword', () => {
  it('aceita senha forte, diferente da atual e confirmada', () => {
    expect(validateNewPassword('senhaAtual1', 'senhaNova2', 'senhaNova2')).toBeNull();
  });

  it.each([
    ['', 'senhaNova2', 'senhaNova2', 'Informe a senha atual'],
    ['senhaAtual1', 'curta1', 'curta1', 'Nova senha deve ter no mínimo 8 caracteres'],
    ['senhaAtual1', '12345678', '12345678', 'Nova senha deve conter pelo menos 1 letra'],
    ['senhaAtual1', 'somenteletras', 'somenteletras', 'Nova senha deve conter pelo menos 1 número'],
    ['senhaAtual1', 'senhaAtual1', 'senhaAtual1', 'A nova senha precisa ser diferente da atual.'],
    ['senhaAtual1', 'senhaNova2', 'senhaNova3', 'A confirmação não é igual à nova senha'],
  ])('atual=%j nova=%j confirmação=%j → %j', (current, next, confirmation, message) => {
    expect(validateNewPassword(current, next, confirmation)).toBe(message);
  });
});
