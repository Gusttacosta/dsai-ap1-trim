import { render } from '@testing-library/react';
import type { ReactNode } from 'react';

// Renderiza uma linha (<tr>) dentro de uma tabela válida, para os testes das linhas do painel.
export function renderInTable(row: ReactNode) {
  return render(
    <table>
      <tbody>{row}</tbody>
    </table>,
  );
}
