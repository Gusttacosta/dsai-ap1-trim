"""Leva aos bancos antigos o que a 0001 já cria nos novos: a trava de saldo da fidelidade (#6, #73).

O banco de produção foi criado pelo `create_all` antes do CHECK (balance >= 0) existir, e o
`create_all` não altera tabelas que já existem. Depois do `stamp` da 0001, esta revisão adiciona a
restrição só onde ela falta. `NOT VALID` não deixa a migração falhar por algum saldo antigo: a
restrição vale para toda escrita nova (SPEC/2026-11-25-alembic-migracoes.md).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT = "ck_loyalty_wallets_balance_non_negative"


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                WHERE c.conname = '{CONSTRAINT}' AND t.relname = 'loyalty_wallets'
                  AND t.relnamespace = to_regnamespace(current_schema())
            ) THEN
                ALTER TABLE loyalty_wallets ADD CONSTRAINT {CONSTRAINT} CHECK (balance >= 0) NOT VALID;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # A restrição faz parte do esquema da 0001: voltar para ela não a remove.
    pass
