import React, { useState } from 'react';
import shared from '../../pages/AdminShared.module.css';
import LoadState, { ActionFeedback } from '../LoadState';
import type { ExpenseCategory, useExpenseCategories } from '../../hooks/useAdminExpenses';
import { useRowAction } from '../../hooks/useRowAction';
import { validateCategoryName } from '../../utils/expenseValidation';
import CategoryRow from './CategoryRow';

// Gestão das categorias de despesa, na tela de despesas (SPEC/2026-11-26-painel-despesas.md):
// criar, renomear e excluir. O nome é conferido antes da API; a recusa da API (nome repetido)
// aparece no topo da seção.

type Props = {
  resource: ReturnType<typeof useExpenseCategories>;
  /** A categoria foi renomeada (com o nome novo) ou excluída (null): a lista de despesas acompanha. */
  onChanged: (id: string, category: ExpenseCategory | null) => void;
};

const ExpenseCategories = ({ resource, onChanged }: Props) => {
  const { categories, status, loadError, reload, createCategory, renameCategory, deleteCategory } = resource;
  const { busyId, message, actionError, run, clear } = useRowAction();
  const [newName, setNewName] = useState('');
  const [invalid, setInvalid] = useState('');

  /** Confere o nome antes da API. Devolve false (e mostra o erro) quando não serve. */
  const check = (name: string) => {
    clear();
    const problem = validateCategoryName(name);
    setInvalid(problem ?? '');
    return problem === null;
  };

  const add = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!check(newName)) return;
    if (await run('new', () => createCategory(newName.trim()), 'Categoria criada.')) setNewName('');
  };

  const rename = async (category: ExpenseCategory, name: string) => {
    if (!check(name)) return false;
    const saved = await run(category.id, () => renameCategory(category.id, name.trim()), 'Categoria renomeada.');
    if (saved) onChanged(category.id, saved);
    return saved !== undefined;
  };

  const remove = async (category: ExpenseCategory) => {
    setInvalid('');
    const done = await run(category.id, async () => {
      await deleteCategory(category.id);
      return true;
    }, 'Categoria excluída.');
    if (done) onChanged(category.id, null);
  };

  return (
    <section aria-label="Categorias" style={{ marginTop: '2.5rem' }}>
      <h3 className={shared.title}>Categorias</h3>

      <form className={shared.filters} onSubmit={add} noValidate>
        <input aria-label="Nova categoria" placeholder="Nova categoria" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <button type="submit" className={shared.btnAction} disabled={status !== 'ready' || busyId === 'new'}>
          Adicionar
        </button>
      </form>

      <ActionFeedback message={message} error={invalid || actionError} />

      <LoadState status={status} loadError={loadError} reload={reload} loadingText="Carregando categorias...">
        {categories.length === 0 ? (
          <p>Nenhuma categoria cadastrada.</p>
        ) : (
          <table className={shared.table}>
            <thead>
              <tr>
                <th>Categoria</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((category) => (
                <CategoryRow
                  key={category.id}
                  category={category}
                  busy={busyId === category.id}
                  onRename={rename}
                  onDelete={remove}
                />
              ))}
            </tbody>
          </table>
        )}
      </LoadState>
    </section>
  );
};

export default ExpenseCategories;
