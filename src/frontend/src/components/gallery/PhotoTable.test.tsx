// @vitest-environment jsdom
import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { BARBA, FADE, makePhoto } from '../../testUtils/gallery';
import PhotoTable from './PhotoTable';

// SPEC/2026-11-26-painel-galeria.md: a tabela de fotos da moderação.

afterEach(cleanup);

const nameOf = (id: string) => (id === 'b1' ? 'João Silva' : 'Barbeiro inativo');

describe('PhotoTable', () => {
  it('mostra miniatura, barbeiro, descrição, tags, data e as ações', () => {
    const photo = makePhoto('p1', { description: 'Degradê', tags: [FADE, BARBA], created_at: '2026-11-26T12:00:00Z' });
    render(<PhotoTable label="Pendentes" photos={[photo]} empty="Nada." nameOf={nameOf} actions={() => <button>Aprovar</button>} />);

    const row = within(screen.getByRole('table', { name: 'Pendentes' })).getByRole('row', { name: 'Degradê' });
    expect((within(row).getByRole('img') as HTMLImageElement).src).toBe(photo.image_url);
    expect(within(row).getByText('João Silva')).toBeTruthy();
    expect(within(row).getByText('Fade, Barba')).toBeTruthy();
    expect(within(row).getByText('26/11/2026')).toBeTruthy();
    expect(within(row).getByRole('button', { name: 'Aprovar' })).toBeTruthy();
  });

  it('foto sem descrição nem tags, de barbeiro inativo', () => {
    render(
      <PhotoTable label="Publicadas" photos={[makePhoto('p2', { description: null, barber_id: 'b9' })]} empty="Nada." nameOf={nameOf} actions={() => null} />,
    );

    const row = screen.getByRole('row', { name: 'Foto p2' });
    expect(within(row).getByText('Barbeiro inativo')).toBeTruthy();
    expect(within(row).getAllByText('—')).toHaveLength(2);
  });

  it('sem fotos, mostra o aviso', () => {
    render(<PhotoTable label="Pendentes" photos={[]} empty="Nenhuma foto pendente." nameOf={nameOf} actions={() => null} />);

    expect(screen.getByText('Nenhuma foto pendente.')).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
  });
});
