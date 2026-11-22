import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import { describe, expect, it } from 'vitest';
import { apiErrorMessage } from './apiError';

function httpError(status: number, data: unknown): AxiosError {
  const config = { headers: {} } as InternalAxiosRequestConfig;
  const response = { status, data, statusText: '', headers: {}, config } as AxiosResponse;
  return new AxiosError(`HTTP ${status}`, AxiosError.ERR_BAD_REQUEST, config, null, response);
}

describe('apiErrorMessage', () => {
  it('usa o detail em texto (400, 401, 403)', () => {
    expect(apiErrorMessage(httpError(400, { detail: 'Senha atual incorreta.' }))).toBe('Senha atual incorreta.');
  });

  it('junta as mensagens do 422 sem o prefixo "Value error, "', () => {
    const error = httpError(422, {
      detail: [
        { loc: ['body', 'phone'], msg: 'Value error, DDD não pode começar com 0' },
        { loc: ['body', 'role'], msg: 'Extra inputs are not permitted' },
      ],
    });

    expect(apiErrorMessage(error)).toBe('DDD não pode começar com 0 | Extra inputs are not permitted');
  });

  it('cai no texto padrão quando o corpo não tem detail', () => {
    expect(apiErrorMessage(httpError(500, 'Internal Server Error'), 'Falhou')).toBe('Falhou');
    expect(apiErrorMessage(httpError(422, { detail: [] }), 'Falhou')).toBe('Falhou');
  });

  it('avisa quando não houve resposta (sem rede)', () => {
    const error = new AxiosError('Network Error', AxiosError.ERR_NETWORK);

    expect(apiErrorMessage(error)).toBe('Sem conexão com o servidor. Verifique a internet e tente de novo.');
  });

  it('erros que não são do axios usam o texto padrão', () => {
    expect(apiErrorMessage(new Error('boom'))).toBe('Não foi possível concluir. Tente de novo.');
  });
});
