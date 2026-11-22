"""
Trim — Auth Security

Funções utilitárias para segurança: hash de senha, verificação e manipulação de JWT.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import bcrypt

from src.backend.config import settings
from src.backend.modules.auth.models import UserRole

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto plano bate com o hash bcrypt."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def get_password_hash(password: str) -> str:
    """Gera um hash bcrypt para a senha."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, role: UserRole) -> tuple[str, int]:
    """
    Cria um JWT access token.
    A duração depende do role:
    - Client: 30 minutos
    - Barber / Admin: 12 horas
    Retorna uma tupla com o token e o tempo de expiração em segundos.
    """
    to_encode = data.copy()
    
    if role == UserRole.CLIENT:
        expire_minutes = 30
    else:
        expire_minutes = 12 * 60  # 12 horas
        
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    
    return encoded_jwt, expire_minutes * 60


def refresh_token_lifetime(role: UserRole) -> timedelta:
    """Validade do refresh token: 7 dias para cliente, 30 dias para barbeiro e admin."""
    return timedelta(days=7 if role == UserRole.CLIENT else 30)


def create_refresh_token(
    data: dict, role: UserRole, jti: str | None = None, expire: datetime | None = None
) -> tuple[str, int]:
    """
    Cria um JWT refresh token.
    A duração depende do role (ver `refresh_token_lifetime`).
    `jti` é o id da linha em `refresh_tokens`, e `expire` o vencimento gravado nela.
    Retorna uma tupla com o token e o tempo de expiração em segundos.
    """
    to_encode = data.copy()
    lifetime = refresh_token_lifetime(role)
    expire = expire or datetime.now(timezone.utc) + lifetime
    to_encode.update({"exp": expire, "type": "refresh"})
    if jti is not None:
        to_encode["jti"] = jti
    
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    
    return encoded_jwt, int(lifetime.total_seconds())


def decode_token(token: str) -> dict[str, Any] | None:
    """
    Decodifica e valida um JWT.
    Retorna o payload se válido, ou None se inválido/expirado.
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except jwt.PyJWTError:
        return None
