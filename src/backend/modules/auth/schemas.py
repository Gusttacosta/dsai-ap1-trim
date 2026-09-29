"""
Trim — Auth Schemas

Schemas Pydantic para validação de entrada/saída do módulo de autenticação.
"""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# ── Enums ────────────────────────────────────────────────
class UserRoleSchema(str):
    """Representação do role do usuário nos schemas."""
    pass


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
        """Senha forte: mínimo 8 chars, pelo menos 1 letra e 1 número."""
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("Senha deve conter pelo menos 1 letra")
        if not re.search(r"\d", v):
            raise ValueError("Senha deve conter pelo menos 1 número")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Nome deve ter pelo menos 2 caracteres."""
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Nome deve ter no mínimo 2 caracteres")
        return v


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
        """Mesmas regras de senha forte."""
        if len(v) < 8:
            raise ValueError("Nova senha deve ter no mínimo 8 caracteres")
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("Nova senha deve conter pelo menos 1 letra")
        if not re.search(r"\d", v):
            raise ValueError("Nova senha deve conter pelo menos 1 número")
        return v


class UserUpdateRequest(BaseModel):
    """Schema para atualização de perfil."""
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) < 2:
                raise ValueError("Nome deve ter no mínimo 2 caracteres")
        return v


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
        if len(v) < 8:
            raise ValueError("Nova senha deve ter no mínimo 8 caracteres")
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("Nova senha deve conter pelo menos 1 letra")
        if not re.search(r"\d", v):
            raise ValueError("Nova senha deve conter pelo menos 1 número")
        return v


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
