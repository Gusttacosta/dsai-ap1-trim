"""
Trim — Auth Schemas

Schemas Pydantic para validação de entrada/saída do módulo de autenticação.
"""

import re
import uuid
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# ── Enums ────────────────────────────────────────────────
class UserRoleSchema(str):
    """Representação do role do usuário nos schemas."""
    pass


# ── Validações compartilhadas ────────────────────────────
# SPEC/2026-11-22-auth-perfil-senha.md: as mesmas regras valem no cadastro e no perfil.

FULL_NAME_MAX = 255  # tamanho da coluna users.full_name
AVATAR_URL_MAX = 2048
PHONE_CHARS = re.compile(r"^\+?[\d\s()\-]+$")


def strong_password(v: str, label: str = "Senha") -> str:
    """Senha forte (regra 2 da AP1): mínimo 8 chars, pelo menos 1 letra e 1 número."""
    if len(v) < 8:
        raise ValueError(f"{label} deve ter no mínimo 8 caracteres")
    if not re.search(r"[a-zA-Z]", v):
        raise ValueError(f"{label} deve conter pelo menos 1 letra")
    if not re.search(r"\d", v):
        raise ValueError(f"{label} deve conter pelo menos 1 número")
    return v


def clean_full_name(v: str) -> str:
    """Nome sem espaços nas pontas, entre 2 e 255 caracteres."""
    v = v.strip()
    if len(v) < 2:
        raise ValueError("Nome deve ter no mínimo 2 caracteres")
    if len(v) > FULL_NAME_MAX:
        raise ValueError(f"Nome deve ter no máximo {FULL_NAME_MAX} caracteres")
    return v


def normalize_phone(v: str | None) -> str | None:
    """Telefone brasileiro com DDD, gravado como (91) 99999-0000 ou (91) 3333-0000.

    Vazio ou None apaga o telefone. Aceita máscara (espaços, parênteses e hífen) e o prefixo +55.
    """
    if v is None or not v.strip():
        return None
    v = v.strip()
    if not PHONE_CHARS.match(v):
        raise ValueError("Telefone deve ter só números, espaços, parênteses, hífen e o prefixo +55")
    digits = re.sub(r"\D", "", v)
    if v.startswith("+"):
        if not digits.startswith("55"):
            raise ValueError("Telefone deve ser brasileiro (+55)")
        digits = digits[2:]
    if len(digits) not in (10, 11):
        raise ValueError("Telefone deve ter o DDD e 8 dígitos (fixo) ou 9 dígitos (celular)")
    if digits[0] == "0":
        raise ValueError("DDD não pode começar com 0")
    if len(digits) == 11 and digits[2] != "9":
        raise ValueError("Celular deve começar com 9 depois do DDD")
    ddd, number = digits[:2], digits[2:]
    return f"({ddd}) {number[:-4]}-{number[-4:]}"


def normalize_avatar_url(v: str | None) -> str | None:
    """URL http(s) da foto, com até 2.048 caracteres. Vazio ou None apaga a foto."""
    if v is None or not v.strip():
        return None
    v = v.strip()
    if len(v) > AVATAR_URL_MAX:
        raise ValueError(f"URL da foto deve ter no máximo {AVATAR_URL_MAX} caracteres")
    parsed = urlparse(v)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("URL da foto deve começar com http:// ou https:// e ter um endereço")
    return v


# ── Request Schemas ──────────────────────────────────────

class UserRegisterRequest(BaseModel):
    """Schema de cadastro de novo usuário."""
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return strong_password(v)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        return clean_full_name(v)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        return normalize_phone(v)


class UserLoginRequest(BaseModel):
    """Schema de login."""
    email: EmailStr
    password: str


class PasswordChangeRequest(BaseModel):
    """Schema para alteração de senha (exige senha atual)."""
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return strong_password(v, "Nova senha")


class UserUpdateRequest(BaseModel):
    """Atualização parcial do perfil: só nome, telefone e foto (os outros campos dão 422)."""
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str | None) -> str:
        # Só roda quando o campo vem no corpo: null explícito é recusado, o nome é obrigatório.
        if v is None:
            raise ValueError("Nome não pode ser apagado")
        return clean_full_name(v)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        return normalize_phone(v)

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: str | None) -> str | None:
        return normalize_avatar_url(v)


class RoleUpdateRequest(BaseModel):
    """Schema para admin alterar o role de um usuário."""
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = {"admin", "barber", "client"}
        if v not in valid_roles:
            raise ValueError(f"Role deve ser um de: {', '.join(valid_roles)}")
        return v


class StatusUpdateRequest(BaseModel):
    """Schema para admin ativar/desativar um usuário."""
    is_active: bool


class ForgotPasswordRequest(BaseModel):
    """Schema para solicitar reset de senha."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema para redefinir a senha com token."""
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return strong_password(v, "Nova senha")


class VerifyEmailRequest(BaseModel):
    """Schema para verificação de e-mail."""
    token: str


class ResendVerificationRequest(BaseModel):
    """Schema para reenvio de token de verificação."""
    email: EmailStr


# ── Response Schemas ─────────────────────────────────────

class UserResponse(BaseModel):
    """Schema de resposta com dados do usuário (sem senha)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    role: str
    avatar_url: str | None
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """Schema de resposta com tokens JWT."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos até expirar
    user: UserResponse


class MessageResponse(BaseModel):
    """Schema de resposta genérica com mensagem."""
    message: str


class UserListResponse(BaseModel):
    """Schema de resposta para listagem de usuários com paginação."""
    users: list[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
