import { useCallback, useState } from 'react';
import { apiErrorMessage } from '../utils/apiError';

// Ação sobre uma linha de uma tabela do painel: a linha fica ocupada enquanto a ação roda, e o
// resultado aparece no topo, como mensagem ou erro da API. Usado pelos painéis de serviços
// (SPEC/2026-11-23-painel-servicos.md) e de usuários (SPEC/2026-11-25-admin-usuarios.md).

export function useRowAction() {
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [actionError, setActionError] = useState('');

  const clear = useCallback(() => {
    setMessage('');
    setActionError('');
  }, []);

  /** Roda `action` com a linha `id` ocupada. Devolve o resultado, ou undefined se falhou. */
  const run = useCallback(
    async <T,>(id: string, action: () => Promise<T>, done: string): Promise<T | undefined> => {
      clear();
      setBusyId(id);
      try {
        const result = await action();
        setMessage(done);
        return result;
      } catch (error) {
        setActionError(apiErrorMessage(error, 'Não foi possível concluir a ação.'));
        return undefined;
      } finally {
        setBusyId(null);
      }
    },
    [clear],
  );

  return { busyId, message, actionError, run, clear, setMessage };
}
