"""
Trim — Auth Service

Camada de serviço (regras de negócio) para o módulo de autenticação.
Manipula usuários, tokens, e controla taxa de login.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.modules.auth import security
from src.backend.modules.auth.models import EmailVerificationToken, PasswordResetToken, User, UserRole
from src.backend.modules.auth.schemas import UserRegisterRequest


class AuthService:
    """Serviço com regras de negócio de autenticação e usuários."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Busca um usuário pelo email."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Busca um usuário pelo ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, user_in: UserRegisterRequest) -> User:
        """
        Cria um novo usuário.
        O primeiro usuário do sistema será automaticamente ADMIN.
        """
        # Verifica se o email já existe
        existing_user = await self.get_user_by_email(user_in.email)
        if existing_user:
            raise ValueError("Email já cadastrado.")

        # Verifica se é o primeiro usuário (para ser admin)
        stmt_count = select(User.id).limit(1)
        result_count = await self.db.execute(stmt_count)
        is_first_user = result_count.first() is None

        role = UserRole.ADMIN if is_first_user else UserRole.CLIENT

        # Hash da senha
        hashed_password = security.get_password_hash(user_in.password)

        # Criação do usuário
        new_user = User(
            email=user_in.email,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            phone=user_in.phone,
            role=role,
        )

        self.db.add(new_user)
        await self.db.flush()  # Para obter o ID do usuário sem commitar a transação

        # Geração do token de verificação de email
        token_str = str(uuid.uuid4())
        expire_at = datetime.now(timezone.utc) + timedelta(hours=24)
        verification_token = EmailVerificationToken(
            user_id=new_user.id,
            token=token_str,
            expires_at=expire_at
        )
        self.db.add(verification_token)
        
        # Em dev, imprime o token. Em prod, enviaria email.
        print(f"📧 [MOCK EMAIL] Para verificar o email de {new_user.email}, use o token: {token_str}")

        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user

    async def verify_email(self, token_str: str) -> bool:
        """Verifica o e-mail do usuário através do token."""
        stmt = select(EmailVerificationToken).where(
            EmailVerificationToken.token == token_str,
            EmailVerificationToken.is_used == False,
            EmailVerificationToken.expires_at > datetime.now(timezone.utc)
        )
        result = await self.db.execute(stmt)
        token_obj = result.scalar_one_or_none()

        if not token_obj:
            return False

        # Marca token como usado
        token_obj.is_used = True
        
        # Atualiza usuário
        stmt_update_user = update(User).where(User.id == token_obj.user_id).values(email_verified=True)
        await self.db.execute(stmt_update_user)
        
        await self.db.commit()
        return True

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Verifica credenciais e retorna o usuário se forem válidas."""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not user.is_active:
            # Soft delete ou banido
            return None
        if not security.verify_password(password, user.hashed_password):
            return None
        return user

    async def create_password_reset_token(self, email: str) -> Optional[str]:
        """Cria token de reset de senha se o e-mail existir."""
        user = await self.get_user_by_email(email)
        if not user:
            return None

        token_str = str(uuid.uuid4())
        expire_at = datetime.now(timezone.utc) + timedelta(hours=1)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token_str,
            expires_at=expire_at
        )
        self.db.add(reset_token)
        await self.db.commit()
        
        print(f"🔑 [MOCK EMAIL] Link de reset para {user.email}: /reset-password?token={token_str}")
        return token_str

    async def reset_password(self, token_str: str, new_password: str) -> bool:
        """Redefine a senha se o token for válido e não expirado."""
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token == token_str,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires_at > datetime.now(timezone.utc)
        )
        result = await self.db.execute(stmt)
        token_obj = result.scalar_one_or_none()

        if not token_obj:
            return False

        # Marca token como usado
        token_obj.is_used = True
        
        # Atualiza senha do usuário
        hashed_password = security.get_password_hash(new_password)
        stmt_update_user = update(User).where(User.id == token_obj.user_id).values(hashed_password=hashed_password)
        await self.db.execute(stmt_update_user)
        
        await self.db.commit()
        return True
