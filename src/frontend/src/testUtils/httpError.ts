import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';

// Erros da API como o axios os entrega, para os testes dos componentes e hooks.

/** Resposta de erro com o `detail` do FastAPI (texto, ou lista de { msg } no 422). */
export function httpError(status: number, detail?: unknown): AxiosError {
  const config = { headers: {} } as InternalAxiosRequestConfig;
  const data = detail === undefined ? {} : { detail };
  const response = { status, data, statusText: '', headers: {}, config } as AxiosResponse;
  return new AxiosError(`HTTP ${status}`, AxiosError.ERR_BAD_REQUEST, config, null, response);
}

/** Falha sem resposta, como a de rede fora do ar. */
export function networkError(): AxiosError {
  return new AxiosError('Network Error', AxiosError.ERR_NETWORK, { headers: {} } as InternalAxiosRequestConfig);
}
