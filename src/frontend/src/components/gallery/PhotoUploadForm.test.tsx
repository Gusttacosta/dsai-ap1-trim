// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { BARBA, CARLOS, FADE, JOAO } from '../../testUtils/gallery';
import { httpError } from '../../testUtils/httpError';
import { BARBER_ERROR, IMAGE_URL_ERROR, PHOTO_DESCRIPTION_ERROR } from '../../utils/galleryValidation';
import PhotoUploadForm, { photoInput } from './PhotoUploadForm';

// SPEC/2026-11-26-painel-galeria.md: o formulário de envio, para o barbeiro e para o admin.

const onSend = vi.fn();
const onCancel = vi.fn();

function renderForm(isAdmin: boolean) {
  render(<PhotoUploadForm isAdmin={isAdmin} tags={[BARBA, FADE]} barbers={[JOAO, CARLOS]} onSend={onSend} onCancel={onCancel} />);
}

const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const submit = () => fireEvent.click(screen.getByRole('button', { name: 'Enviar foto' }));
const alertText = async () => (await screen.findByRole('alert')).textContent;

beforeEach(() => {
  onSend.mockReset().mockResolvedValue(undefined);
  onCancel.mockReset();
});

afterEach(cleanup);

describe('PhotoUploadForm: barbeiro', () => {
  it('manda URL, descrição e tags aparadas, sem barber_id e sem a escolha do barbeiro', async () => {
    renderForm(false);
    expect(screen.queryByLabelText('Barbeiro')).toBeNull();

    type('URL da imagem', ' https://exemplo.com/a.jpg ');
    type('Descrição (opcional)', '  Degradê navalhado ');
    fireEvent.click(screen.getByLabelText('Fade'));
    submit();

    await waitFor(() =>
      expect(onSend).toHaveBeenCalledWith({
        image_url: 'https://exemplo.com/a.jpg',
        description: 'Degradê navalhado',
        tag_ids: ['fade'],
      }),
    );
  });

  it.each([
    ['vazia', ''],
    ['sem http', 'exemplo.com/a.jpg'],
    ['longa demais', `https://exemplo.com/${'a'.repeat(1000)}`],
  ])('URL %s é recusada na tela, sem envio', async (_, url) => {
    renderForm(false);

    type('URL da imagem', url);
    submit();

    expect(await alertText()).toBe(IMAGE_URL_ERROR);
    expect(onSend).not.toHaveBeenCalled();
  });

  it('descrição com mais de 500 caracteres é recusada', async () => {
    renderForm(false);

    type('URL da imagem', 'https://exemplo.com/a.jpg');
    type('Descrição (opcional)', 'a'.repeat(501));
    submit();

    expect(await alertText()).toBe(PHOTO_DESCRIPTION_ERROR);
    expect(onSend).not.toHaveBeenCalled();
  });

  it('o erro da API aparece no formulário', async () => {
    onSend.mockRejectedValue(httpError(404, 'Perfil de barbeiro não encontrado.'));
    renderForm(false);

    type('URL da imagem', 'https://exemplo.com/a.jpg');
    submit();

    expect(await alertText()).toBe('Perfil de barbeiro não encontrado.');
  });

  it('"Cancelar" fecha sem enviar', () => {
    renderForm(false);

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

    expect(onCancel).toHaveBeenCalled();
    expect(onSend).not.toHaveBeenCalled();
  });
});

describe('PhotoUploadForm: admin', () => {
  it('sem barbeiro escolhido é recusado na tela', async () => {
    renderForm(true);

    type('URL da imagem', 'https://exemplo.com/a.jpg');
    submit();

    expect(await alertText()).toBe(BARBER_ERROR);
    expect(onSend).not.toHaveBeenCalled();
  });

  it('manda o barber_id escolhido; sem descrição, ela não vai', async () => {
    renderForm(true);

    type('URL da imagem', 'https://exemplo.com/a.jpg');
    type('Barbeiro', CARLOS.id);
    fireEvent.click(screen.getByLabelText('Barba'));
    fireEvent.click(screen.getByLabelText('Fade'));
    fireEvent.click(screen.getByLabelText('Barba'));
    submit();

    await waitFor(() =>
      expect(onSend).toHaveBeenCalledWith({ image_url: 'https://exemplo.com/a.jpg', tag_ids: ['fade'], barber_id: 'b2' }),
    );
  });
});

describe('photoInput', () => {
  it('só põe a descrição e o barbeiro quando há', () => {
    expect(photoInput(' https://a.com/x.jpg ', '  ', [], '')).toEqual({ image_url: 'https://a.com/x.jpg', tag_ids: [] });
  });
});
