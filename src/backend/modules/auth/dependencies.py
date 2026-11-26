"""
Trim — Auth Dependencies

Injeção de dependência para endpoints protegidos no FastAPI.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.modules.auth import security
from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.auth.service import AuthService

# auto_error=False: a partir do FastAPI 0.12x, o HTTPBearer responde 401 sem token. A API sempre
# respondeu 403 "Not authenticated" nesse caso, e os testes e o frontend contam com isso (#77).
security_scheme = HTTPBearer(auto_error=False)


PASSWORD_CHANGE_REQUIRED = "Troque a senha temporária para continuar."


async def get_user_with_pending_password(
    token: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extrai, valida o JWT e retorna o usuário do banco, mesmo com a troca de senha pendente.

    Só `GET /me` e `PUT /me/password` usam esta dependência direto (#99)."""
    if token is None or token.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated")
    payload = security.decode_token(token.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Refresh token não pode ser usado como access token
    if payload.get("type") == "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token não pode ser usado para acesso.",
        )

    user_id_str = payload.get("user_id")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Payload inválido.",
        )

    service = AuthService(db)
    import uuid
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Payload inválido.",
        )

    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo.",
        )

    return user


async def get_current_user(user: User = Depends(get_user_with_pending_password)) -> User:
    """Usuário logado. Com uma senha temporária ainda não trocada, a API responde 403 (#99)."""
    if user.must_change_password:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=PASSWORD_CHANGE_REQUIRED)
    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Verifica se o usuário atual é admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito para administradores.",
        )
    return current_user


async def get_current_barber_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Verifica se o usuário é admin ou barbeiro."""
    if current_user.role not in [UserRole.ADMIN, UserRole.BARBER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito para barbeiros ou administradores.",
        )
    return current_user
