import { isAxiosError } from 'axios';

type ValidationIssue = { msg?: string };

/**
 * Mensagem em português para mostrar ao usuário a partir de um erro da API.
 * O 422 do FastAPI traz uma lista de problemas ({ msg }), com o prefixo "Value error, "
 * nas validações escritas no backend; os outros erros trazem `detail` como texto.
 */
export function apiErrorMessage(error: unknown, fallback = 'Não foi possível concluir. Tente de novo.'): string {
  if (!isAxiosError(error)) return fallback;
  if (!error.response) return 'Sem conexão com o servidor. Verifique a internet e tente de novo.';
  const detail = (error.response.data as { detail?: unknown } | undefined)?.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((issue: ValidationIssue) => (issue?.msg ?? '').replace(/^Value error, /, ''))
      .filter(Boolean);
    if (messages.length) return messages.join(' | ');
  }
  return fallback;
}
