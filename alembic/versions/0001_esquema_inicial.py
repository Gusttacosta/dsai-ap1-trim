"""Esquema inicial: as 26 tabelas dos modelos atuais (#6).

Gerada com o autogenerate do Alembic a partir de `Base.metadata`
(SPEC/2026-11-25-alembic-migracoes.md). Bancos que já tinham as tabelas criadas pelo
`create_all` (como o de produção) recebem só o `stamp` desta revisão, em `scripts/migrate.py`.

Revision ID: 0001
Revises:
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('email_verification_tokens',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token', sa.String(length=255), nullable=False),
    sa.Column('is_used', sa.Boolean(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_verification_tokens_token'), 'email_verification_tokens', ['token'], unique=True)
    op.create_index(op.f('ix_email_verification_tokens_user_id'), 'email_verification_tokens', ['user_id'], unique=False)
    op.create_table('expense_categories',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('gallery_tags',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('password_reset_tokens',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token', sa.String(length=255), nullable=False),
    sa.Column('is_used', sa.Boolean(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_password_reset_tokens_token'), 'password_reset_tokens', ['token'], unique=True)
    op.create_index(op.f('ix_password_reset_tokens_user_id'), 'password_reset_tokens', ['user_id'], unique=False)
    op.create_table('products',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('sku', sa.String(length=50), nullable=True),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('cost_price', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('stock_quantity', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('image_url', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('stock_quantity >= 0', name='chk_stock_non_negative'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=True)
    op.create_table('rewards',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('points_cost', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('services',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('duration_minutes', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_services_id'), 'services', ['id'], unique=False)
    op.create_table('subscription_plans',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('monthly_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('included_cuts', sa.Integer(), nullable=False),
    sa.Column('included_shaves', sa.Integer(), nullable=False),
    sa.Column('discount_percentage', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_subscription_plans_id'), 'subscription_plans', ['id'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('avatar_url', sa.Text(), nullable=True),
    sa.Column('role', sa.Enum('ADMIN', 'BARBER', 'CLIENT', name='user_role', create_constraint=True), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('email_verified', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_table('barbers',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('bio', sa.Text(), nullable=True),
    sa.Column('instagram_url', sa.String(length=255), nullable=True),
    sa.Column('commission_rate', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_barbers_id'), 'barbers', ['id'], unique=False)
    op.create_table('expenses',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('category_id', sa.UUID(), nullable=True),
    sa.Column('description', sa.String(length=255), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('payment_date', sa.Date(), nullable=False),
    sa.Column('is_recurring', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['expense_categories.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expenses_category_id'), 'expenses', ['category_id'], unique=False)
    op.create_index(op.f('ix_expenses_payment_date'), 'expenses', ['payment_date'], unique=False)
    op.create_table('inventory_movements',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('movement_type', sa.Enum('SALE', 'RESTOCK', 'LOSS', 'ADJUSTMENT', name='movement_type', create_constraint=True), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_movements_product_id'), 'inventory_movements', ['product_id'], unique=False)
    op.create_index(op.f('ix_inventory_movements_user_id'), 'inventory_movements', ['user_id'], unique=False)
    op.create_table('loyalty_wallets',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('balance', sa.Integer(), nullable=False),
    sa.Column('lifetime_points', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('balance >= 0', name='ck_loyalty_wallets_balance_non_negative'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_loyalty_wallets_user_id'), 'loyalty_wallets', ['user_id'], unique=True)
    op.create_table('notifications',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('type', sa.Enum('APPOINTMENT_REMINDER', 'LOYALTY_UPDATE', 'SUBSCRIPTION_NOTICE', 'SYSTEM_ALERT', name='notification_type', create_constraint=True), nullable=False),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_table('refresh_tokens',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('family_id', sa.UUID(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_refresh_tokens_family_id'), 'refresh_tokens', ['family_id'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    op.create_table('transactions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('type', sa.Enum('APPOINTMENT', 'PRODUCT_SALE', 'SUBSCRIPTION', name='transaction_type', create_constraint=True), nullable=False),
    sa.Column('reference_id', sa.UUID(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('payment_method', sa.Enum('CASH', 'CREDIT_CARD', 'DEBIT_CARD', 'PIX', 'TRIM_CLUB_CREDIT', name='payment_method', create_constraint=True), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False)
    op.create_index(op.f('ix_transactions_reference_id'), 'transactions', ['reference_id'], unique=False)
    op.create_index(op.f('ix_transactions_user_id'), 'transactions', ['user_id'], unique=False)
    op.create_table('user_subscriptions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('plan_id', sa.UUID(), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'CANCELED', 'PAST_DUE', name='subscription_status', create_constraint=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_subscriptions_user_id'), 'user_subscriptions', ['user_id'], unique=True)
    op.create_table('appointments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('client_id', sa.UUID(), nullable=False),
    sa.Column('barber_id', sa.UUID(), nullable=False),
    sa.Column('start_datetime', sa.DateTime(timezone=True), nullable=False),
    sa.Column('end_datetime', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED', 'NO_SHOW', name='appointment_status', create_constraint=True), nullable=False),
    sa.Column('total_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['barber_id'], ['barbers.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['client_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_appointments_barber_id'), 'appointments', ['barber_id'], unique=False)
    op.create_index(op.f('ix_appointments_client_id'), 'appointments', ['client_id'], unique=False)
    op.create_index(op.f('ix_appointments_id'), 'appointments', ['id'], unique=False)
    op.create_index(op.f('ix_appointments_start_datetime'), 'appointments', ['start_datetime'], unique=False)
    op.create_index(op.f('ix_appointments_status'), 'appointments', ['status'], unique=False)
    op.create_table('barber_commissions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('barber_id', sa.UUID(), nullable=False),
    sa.Column('transaction_id', sa.UUID(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('is_paid', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['barber_id'], ['barbers.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_barber_commissions_barber_id'), 'barber_commissions', ['barber_id'], unique=False)
    op.create_table('barber_services',
    sa.Column('barber_id', sa.UUID(), nullable=False),
    sa.Column('service_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['barber_id'], ['barbers.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('barber_id', 'service_id')
    )
    op.create_table('portfolio_images',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('image_url', sa.String(length=1000), nullable=False),
    sa.Column('barber_id', sa.UUID(), nullable=False),
    sa.Column('service_id', sa.UUID(), nullable=True),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('is_approved', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['barber_id'], ['barbers.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolio_images_barber_id'), 'portfolio_images', ['barber_id'], unique=False)
    op.create_index(op.f('ix_portfolio_images_is_approved'), 'portfolio_images', ['is_approved'], unique=False)
    op.create_table('reward_redemptions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('wallet_id', sa.UUID(), nullable=False),
    sa.Column('reward_id', sa.UUID(), nullable=False),
    sa.Column('points_spent', sa.Integer(), nullable=False),
    sa.Column('redeemed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['reward_id'], ['rewards.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['wallet_id'], ['loyalty_wallets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reward_redemptions_wallet_id'), 'reward_redemptions', ['wallet_id'], unique=False)
    op.create_table('walk_in_queue',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('customer_name', sa.String(length=150), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('requested_service_id', sa.UUID(), nullable=False),
    sa.Column('requested_barber_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.Enum('WAITING', 'ATTENDING', 'CANCELLED', name='walkin_status', create_constraint=True), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['requested_barber_id'], ['barbers.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['requested_service_id'], ['services.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_walk_in_queue_joined_at'), 'walk_in_queue', ['joined_at'], unique=False)
    op.create_index(op.f('ix_walk_in_queue_user_id'), 'walk_in_queue', ['user_id'], unique=False)
    op.create_table('work_schedules',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('barber_id', sa.UUID(), nullable=False),
    sa.Column('day_of_week', sa.Integer(), nullable=False),
    sa.Column('start_time', sa.Time(), nullable=False),
    sa.Column('end_time', sa.Time(), nullable=False),
    sa.Column('break_start', sa.Time(), nullable=True),
    sa.Column('break_end', sa.Time(), nullable=True),
    sa.Column('is_working', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['barber_id'], ['barbers.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_work_schedules_barber_id'), 'work_schedules', ['barber_id'], unique=False)
    op.create_table('appointment_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('appointment_id', sa.UUID(), nullable=False),
    sa.Column('service_id', sa.UUID(), nullable=True),
    sa.Column('service_name', sa.String(length=100), nullable=False),
    sa.Column('locked_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('duration_minutes', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_appointment_items_appointment_id'), 'appointment_items', ['appointment_id'], unique=False)
    op.create_table('portfolio_image_tags',
    sa.Column('image_id', sa.UUID(), nullable=False),
    sa.Column('tag_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['image_id'], ['portfolio_images.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tag_id'], ['gallery_tags.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('image_id', 'tag_id')
    )


def downgrade() -> None:
    op.drop_table('portfolio_image_tags')
    op.drop_index(op.f('ix_appointment_items_appointment_id'), table_name='appointment_items')
    op.drop_table('appointment_items')
    op.drop_index(op.f('ix_work_schedules_barber_id'), table_name='work_schedules')
    op.drop_table('work_schedules')
    op.drop_index(op.f('ix_walk_in_queue_user_id'), table_name='walk_in_queue')
    op.drop_index(op.f('ix_walk_in_queue_joined_at'), table_name='walk_in_queue')
    op.drop_table('walk_in_queue')
    op.drop_index(op.f('ix_reward_redemptions_wallet_id'), table_name='reward_redemptions')
    op.drop_table('reward_redemptions')
    op.drop_index(op.f('ix_portfolio_images_is_approved'), table_name='portfolio_images')
    op.drop_index(op.f('ix_portfolio_images_barber_id'), table_name='portfolio_images')
    op.drop_table('portfolio_images')
    op.drop_table('barber_services')
    op.drop_index(op.f('ix_barber_commissions_barber_id'), table_name='barber_commissions')
    op.drop_table('barber_commissions')
    op.drop_index(op.f('ix_appointments_status'), table_name='appointments')
    op.drop_index(op.f('ix_appointments_start_datetime'), table_name='appointments')
    op.drop_index(op.f('ix_appointments_id'), table_name='appointments')
    op.drop_index(op.f('ix_appointments_client_id'), table_name='appointments')
    op.drop_index(op.f('ix_appointments_barber_id'), table_name='appointments')
    op.drop_table('appointments')
    op.drop_index(op.f('ix_user_subscriptions_user_id'), table_name='user_subscriptions')
    op.drop_table('user_subscriptions')
    op.drop_index(op.f('ix_transactions_user_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_reference_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_id'), table_name='transactions')
    op.drop_table('transactions')
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_family_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_is_read'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_loyalty_wallets_user_id'), table_name='loyalty_wallets')
    op.drop_table('loyalty_wallets')
    op.drop_index(op.f('ix_inventory_movements_user_id'), table_name='inventory_movements')
    op.drop_index(op.f('ix_inventory_movements_product_id'), table_name='inventory_movements')
    op.drop_table('inventory_movements')
    op.drop_index(op.f('ix_expenses_payment_date'), table_name='expenses')
    op.drop_index(op.f('ix_expenses_category_id'), table_name='expenses')
    op.drop_table('expenses')
    op.drop_index(op.f('ix_barbers_id'), table_name='barbers')
    op.drop_table('barbers')
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_subscription_plans_id'), table_name='subscription_plans')
    op.drop_table('subscription_plans')
    op.drop_index(op.f('ix_services_id'), table_name='services')
    op.drop_table('services')
    op.drop_table('rewards')
    op.drop_index(op.f('ix_products_sku'), table_name='products')
    op.drop_index(op.f('ix_products_id'), table_name='products')
    op.drop_table('products')
    op.drop_index(op.f('ix_password_reset_tokens_user_id'), table_name='password_reset_tokens')
    op.drop_index(op.f('ix_password_reset_tokens_token'), table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
    op.drop_table('gallery_tags')
    op.drop_table('expense_categories')
    op.drop_index(op.f('ix_email_verification_tokens_user_id'), table_name='email_verification_tokens')
    op.drop_index(op.f('ix_email_verification_tokens_token'), table_name='email_verification_tokens')
    op.drop_table('email_verification_tokens')
    # O PostgreSQL guarda os enums como tipos próprios: o drop_table não os apaga.
    for name in ('appointment_status', 'movement_type', 'notification_type', 'payment_method', 'subscription_status', 'transaction_type', 'user_role', 'walkin_status'):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
