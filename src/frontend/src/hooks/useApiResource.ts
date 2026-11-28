import { useCallback, useEffect, useState } from 'react';
import { apiErrorMessage } from '../utils/apiError';

// Carga de dados da API com "carregando", erro em português e "Tentar de novo". Usado pelo
// painel de serviços (SPEC/2026-11-23-painel-servicos.md) e por Meus agendamentos
// (SPEC/2026-11-25-meus-agendamentos.md). `setData` deixa quem usa atualizar a lista depois
// de uma ação, sem carregar de novo. `load` precisa ser estável (função do módulo ou
// useCallback): uma função nova a cada renderização carregaria de novo a cada renderização.

export type LoadStatus = 'loading' | 'ready' | 'error';

export function useApiResource<T>(load: () => Promise<T>, initial: T, fallbackError: string) {
  const [data, setData] = useState<T>(initial);
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [loadError, setLoadError] = useState('');
  // Mudar o número pede uma nova carga ("Tentar de novo").
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setStatus('loading');
    load()
      .then((loaded) => {
        if (!active) return;
        setData(loaded);
        setStatus('ready');
      })
      .catch((error) => {
        if (!active) return;
        setLoadError(apiErrorMessage(error, fallbackError));
        setStatus('error');
      });
    return () => {
      active = false;
    };
  }, [attempt, load, fallbackError]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);

  return { data, setData, status, loadError, reload };
}
