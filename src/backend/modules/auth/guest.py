"""
Trim — Cliente sem conta ("Visitante").

O agendamento exige um `client_id`. Quem agenda pelo site sem conta, ou chega na fila sem
cadastro, passa a usar um único usuário "Visitante", inativo e sem senha utilizável. O nome da
pessoa fica nas observações do agendamento (SPEC/2026-11-25-cliente-sem-conta.md, #21 e #69).
Antes, cada agendamento de visitante criava um `guest_<hex>@trim.local`, que se acumulava no
banco e contava como um cliente novo.
"""

import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.modules.auth.models import User, UserRole

GUEST_EMAIL = "visitante@trim.local"
GUEST_NAME = "Visitante"


async def guest_user_id(db: AsyncSession) -> uuid.UUID:
    """Id do usuário Visitante, criado na primeira vez. Não faz commit: entra na transação de quem
    chama."""
    stmt = select(User.id).where(User.email == GUEST_EMAIL)
    found = (await db.execute(stmt)).scalar_one_or_none()
    if found:
        return found

    guest = User(
        email=GUEST_EMAIL,
        # Nenhuma senha confere com este valor: não é um hash bcrypt.
        hashed_password=f"!sem-login!{secrets.token_hex(16)}",
        full_name=GUEST_NAME,
        role=UserRole.CLIENT,
        is_active=False,
    )
    try:
        async with db.begin_nested():
            db.add(guest)
        return guest.id
    except IntegrityError:
        # Outro pedido criou o Visitante ao mesmo tempo.
        return (await db.execute(stmt)).scalar_one()
