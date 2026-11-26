"""Troca de senha obrigatória depois de uma senha temporária gerada pelo admin (#99).

`users.must_change_password` nasce `false` em todas as contas existentes
(SPEC/2026-11-25-admin-usuarios.md). `IF NOT EXISTS`, como a 0002: um banco antigo que o
`create_all` criou já com a coluna recebe o `stamp` da 0001 e passa por aqui sem falhar.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT false NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
