"""
Apoio aos testes de integração pela API (#3).

Cria usuários direto no banco e gera o access token com `security.create_access_token`, sem passar
pelo login. Os testes do próprio login e do cadastro ficam em tests/test_auth_integracao.py.
"""

from src.backend.modules.auth import security
from src.backend.modules.auth.models import User, UserRole


async def add_user(maker, email, role=UserRole.CLIENT, *, full_name=None, is_active=True, avatar_url=None):
    """Grava um usuário com o perfil pedido e devolve o objeto já com o id."""
    async with maker() as db:
        user = User(
            email=email,
            hashed_password="x",
            full_name=full_name or email.split("@")[0].capitalize(),
            role=role,
            is_active=is_active,
            avatar_url=avatar_url,
        )
        db.add(user)
        await db.commit()
        return user


def token_for(user):
    payload = {"user_id": str(user.id), "email": user.email, "role": user.role}
    token, _ = security.create_access_token(payload, user.role)
    return token


def auth(user):
    """Cabeçalho `Authorization` com um access token válido do usuário."""
    return {"Authorization": f"Bearer {token_for(user)}"}
