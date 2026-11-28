"""Planos do Trim Club com quantidade ilimitada: included_cuts e included_shaves aceitam NULL (#16).

NULL = ilimitado, 0 = não incluso, n = n por ciclo. O plano Executivo, que usava 30 cortes como
aproximação de "ilimitado", passa a NULL (SPEC/2026-11-25-alembic-migracoes.md).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("subscription_plans", "included_cuts", existing_type=sa.Integer(), nullable=True)
    op.alter_column("subscription_plans", "included_shaves", existing_type=sa.Integer(), nullable=True)
    op.execute(
        "UPDATE subscription_plans SET included_cuts = NULL "
        "WHERE name = 'Executivo' AND included_cuts = 30"
    )


def downgrade() -> None:
    # Sem NULL, "ilimitado" volta à aproximação antiga de 30 por mês.
    op.execute("UPDATE subscription_plans SET included_cuts = 30 WHERE included_cuts IS NULL")
    op.execute("UPDATE subscription_plans SET included_shaves = 30 WHERE included_shaves IS NULL")
    op.alter_column("subscription_plans", "included_cuts", existing_type=sa.Integer(), nullable=False)
    op.alter_column("subscription_plans", "included_shaves", existing_type=sa.Integer(), nullable=False)
