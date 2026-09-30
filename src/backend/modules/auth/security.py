"""
Trim — Auth Security

Funções utilitárias para segurança: hash de senha, verificação e manipulação de JWT.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
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


def create_refresh_token(data: dict, role: UserRole) -> tuple[str, int]:
    """
    Cria um JWT refresh token.
    A duração depende do role:
    - Client: 7 dias
    - Barber / Admin: 30 dias
    Retorna uma tupla com o token e o tempo de expiração em segundos.
    """
    to_encode = data.copy()
    
    if role == UserRole.CLIENT:
        expire_days = 7
    else:
        expire_days = 30
        
    expire = datetime.now(timezone.utc) + timedelta(days=expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    
    return encoded_jwt, expire_days * 24 * 60 * 60


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
    except JWTError:
        return None
