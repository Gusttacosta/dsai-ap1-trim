"""
Trim — Auth Service

Camada de serviço (regras de negócio) para o módulo de autenticação.
Manipula usuários, tokens, e controla taxa de login.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config import settings
from src.backend.modules.auth import security
from src.backend.modules.auth.models import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    User,
    UserRole,
)
from src.backend.modules.auth.schemas import UserRegisterRequest, UserUpdateRequest

logger = logging.getLogger(__name__)

# Um refresh token trocado há menos que isto e apresentado de novo é tratado como corrida entre
# abas, não como reuso de um token copiado (SPEC/2026-11-22-auth-refresh-logout.md).
REFRESH_REUSE_GRACE = timedelta(seconds=10)


class WrongCurrentPassword(Exception):
    """A senha atual informada na troca de senha não confere."""


class SamePassword(Exception):
    """A senha nova é igual à atual."""


class InvalidRefreshToken(Exception):
    """O refresh token não serve para renovar a sessão (ausente, inválido, revogado ou vencido)."""


@dataclass
class IssuedTokens:
    """Tokens emitidos no login, no cadastro ou no refresh."""

    user: User
    access_token: str
    expires_in: int
    refresh_token: str
    refresh_max_age: int


TOKEN_OMITTED = "envio de email nao configurado (token omitido fora de development)."


def log_mock_email(user: User, subject: str, dev_message: str, *dev_args) -> None:
    """Registra o "e-mail falso" no lugar do envio, que ainda não existe (#30).

    Em development, mostra o e-mail e o token, para testar sem servidor de e-mail. Fora dele, o log
    do servidor não pode ter o token: quem lesse o log tomaria a conta. Fica só o id do usuário.
    """
    if settings.is_development:
        logger.info(dev_message, *dev_args)
    else:
        logger.info("[MOCK EMAIL] %s gerada para o usuario %s; %s", subject, user.id, TOKEN_OMITTED)


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
        
        log_mock_email(
            new_user,
            "Verificacao de email",
            "[MOCK EMAIL] Para verificar o email de %s, use o token: %s",
            new_user.email,
            token_str,
        )

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
        
        log_mock_email(
            user,
            "Redefinicao de senha",
            "[MOCK EMAIL] Link de reset para %s: /reset-password?token=%s",
            user.email,
            token_str,
        )
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

        # Quem redefiniu a senha pode estar tirando alguém da conta: encerra todas as sessões.
        await self.revoke_user_sessions(token_obj.user_id)

        await self.db.commit()
        return True

    # ── perfil e troca de senha ──────────────────────────

    async def update_profile(self, user: User, data: UserUpdateRequest) -> User:
        """Atualiza só os campos enviados (nome, telefone e foto) do próprio usuário."""
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(user, field, value)
        if changes:
            await self.db.commit()
            await self.db.refresh(user)
        return user

    async def change_password(
        self, user: User, current_password: str, new_password: str, refresh_token: str | None
    ) -> None:
        """Troca a senha conferindo a atual e encerra as outras sessões.

        A sessão do cookie de quem fez a troca (`refresh_token`), se houver, continua valendo. Os
        tokens de redefinição pendentes deixam de valer.
        """
        if not security.verify_password(current_password, user.hashed_password):
            raise WrongCurrentPassword()
        if security.verify_password(new_password, user.hashed_password):
            raise SamePassword()

        user.hashed_password = security.get_password_hash(new_password)
        current = await self._refresh_row(refresh_token)
        # A revogação filtra por user_id: o cookie de outra pessoa não preserva nenhuma sessão.
        keep = current.family_id if current is not None else None
        await self.revoke_user_sessions(user.id, except_family=keep)
        await self.db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.is_used == False)  # noqa: E712
            .values(is_used=True)
        )
        await self.db.commit()

    # ── sessões (refresh tokens) ─────────────────────────

    async def issue_tokens(self, user: User, family_id: uuid.UUID | None = None) -> IssuedTokens:
        """Grava um refresh token novo (numa família nova ou na informada) e emite os dois JWT."""
        expires_at = datetime.now(timezone.utc) + security.refresh_token_lifetime(user.role)
        row = RefreshToken(
            id=uuid.uuid4(),
            user_id=user.id,
            family_id=family_id or uuid.uuid4(),
            expires_at=expires_at,
        )
        self.db.add(row)

        payload = {"user_id": str(user.id), "email": user.email, "role": user.role}
        access_token, expires_in = security.create_access_token(payload, user.role)
        refresh_token, max_age = security.create_refresh_token(
            payload, user.role, jti=str(row.id), expire=expires_at
        )
        await self.db.commit()
        await self.db.refresh(user)
        return IssuedTokens(user, access_token, expires_in, refresh_token, max_age)

    async def _refresh_row(self, token: str | None, *, lock: bool = False) -> RefreshToken | None:
        """Linha de `refresh_tokens` do JWT, ou None se ele não for um refresh token nosso."""
        payload = security.decode_token(token) if token else None
        if not payload or payload.get("type") != "refresh":
            return None
        try:
            jti = uuid.UUID(str(payload.get("jti")))
        except ValueError:
            return None
        stmt = select(RefreshToken).where(RefreshToken.id == jti)
        if lock:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def rotate_refresh_token(self, token: str | None) -> IssuedTokens:
        """Troca um refresh token válido por um novo na mesma família (rotação).

        Um token já trocado indica cópia: a família inteira é revogada, salvo dentro da janela de
        corrida `REFRESH_REUSE_GRACE`. Levanta `InvalidRefreshToken` em qualquer recusa.
        """
        row = await self._refresh_row(token, lock=True)
        if row is None:
            raise InvalidRefreshToken()

        now = datetime.now(timezone.utc)
        if row.revoked_at is not None:
            if now - row.revoked_at > REFRESH_REUSE_GRACE:
                logger.warning("Reuso de refresh token; sessao %s revogada", row.family_id)
                await self.revoke_family(row.family_id)
                await self.db.commit()
            raise InvalidRefreshToken()
        if row.expires_at <= now:
            raise InvalidRefreshToken()

        user = await self.get_user_by_id(row.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshToken()

        row.revoked_at = now
        return await self.issue_tokens(user, family_id=row.family_id)

    async def logout(self, token: str | None) -> None:
        """Revoga a sessão (família) do refresh token, se ele for válido. Nunca falha."""
        row = await self._refresh_row(token)
        if row is not None:
            await self.revoke_family(row.family_id)
            await self.db.commit()

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        """Revoga todos os tokens ainda ativos de uma sessão."""
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )

    async def revoke_user_sessions(
        self, user_id: uuid.UUID, except_family: uuid.UUID | None = None
    ) -> None:
        """Revoga as sessões de um usuário, menos `except_family` se houver (não faz commit)."""
        stmt = update(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
        )
        if except_family is not None:
            stmt = stmt.where(RefreshToken.family_id != except_family)
        await self.db.execute(stmt.values(revoked_at=datetime.now(timezone.utc)))
