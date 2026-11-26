import React, { useState } from 'react';
import shared from '../../pages/AdminShared.module.css';
import LoadState, { ActionFeedback } from '../LoadState';
import type { NamedItem, NameListResource } from '../../hooks/useNameList';
import { useRowAction } from '../../hooks/useRowAction';
import NameRow from './NameRow';

// Gestão de uma lista de nomes do painel: criar, renomear e excluir. Usada pelas categorias de
// despesa (SPEC/2026-11-26-painel-despesas.md) e pelas tags da galeria
// (SPEC/2026-11-26-painel-galeria.md). O nome é conferido antes da API; a recusa da API (nome
// repetido) aparece no topo da seção.

type Props<T extends NamedItem> = {
  resource: NameListResource<T>;
  /** Título da seção, no plural ("Categorias"). */
  title: string;
  /**
   * Nome de um item, no singular e feminino ("Categoria", "Tag"): forma o cabeçalho, o campo
   * ("Nova categoria") e as mensagens ("Categoria criada.").
   */
  noun: string;
  deleteQuestion: string;
  /** Confere o nome: a mensagem do problema, ou null. */
  validate: (name: string) => string | null;
  /** O item foi renomeado (com o nome novo) ou excluído (null). */
  onChanged?: (id: string, item: T | null) => void;
};

const NameList = <T extends NamedItem>({ resource, title, noun, deleteQuestion, validate, onChanged }: Props<T>) => {
  const { items, status, loadError, reload, create, rename, remove } = resource;
  const { busyId, message, actionError, run, clear } = useRowAction();
  const [newName, setNewName] = useState('');
  const [invalid, setInvalid] = useState('');
  const lower = noun.toLowerCase();

  /** Confere o nome antes da API. Devolve false (e mostra o erro) quando não serve. */
  const check = (name: string) => {
    clear();
    const problem = validate(name);
    setInvalid(problem ?? '');
    return problem === null;
  };

  const add = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!check(newName)) return;
    if (await run('new', () => create(newName.trim()), `${noun} criada.`)) setNewName('');
  };

  const save = async (item: T, name: string) => {
    if (!check(name)) return false;
    const saved = await run(item.id, () => rename(item.id, name.trim()), `${noun} renomeada.`);
    if (saved) onChanged?.(item.id, saved);
    return saved !== undefined;
  };

  const drop = async (item: T) => {
    setInvalid('');
    const done = await run(item.id, async () => {
      await remove(item.id);
      return true;
    }, `${noun} excluída.`);
    if (done) onChanged?.(item.id, null);
  };

  return (
    <section aria-label={title} style={{ marginTop: '2.5rem' }}>
      <h3 className={shared.title}>{title}</h3>

      <form className={shared.filters} onSubmit={add} noValidate>
        <input aria-label={`Nova ${lower}`} placeholder={`Nova ${lower}`} value={newName} onChange={(e) => setNewName(e.target.value)} />
        <button type="submit" className={shared.btnAction} disabled={status !== 'ready' || busyId === 'new'}>
          Adicionar
        </button>
      </form>

      <ActionFeedback message={message} error={invalid || actionError} />

      <LoadState status={status} loadError={loadError} reload={reload} loadingText={`Carregando ${title.toLowerCase()}...`}>
        {items.length === 0 ? (
          <p>{`Nenhuma ${lower} cadastrada.`}</p>
        ) : (
          <table className={shared.table}>
            <thead>
              <tr>
                <th>{noun}</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <NameRow
                  key={item.id}
                  item={item}
                  busy={busyId === item.id}
                  deleteQuestion={deleteQuestion}
                  onRename={save}
                  onDelete={drop}
                />
              ))}
            </tbody>
          </table>
        )}
      </LoadState>
    </section>
  );
};

export default NameList;
