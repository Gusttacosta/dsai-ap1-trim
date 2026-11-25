"""
Trim — Auth Router

Definição dos endpoints REST para o módulo de autenticação.
"""

import math
import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config import settings
from src.backend.database import get_db
from src.backend.modules.auth.dependencies import get_current_admin, get_current_user
from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.auth.schemas import (
    ForgotPasswordRequest,
    MessageResponse,
    PasswordChangeRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    RoleUpdateRequest,
    StatusUpdateRequest,
    UserListResponse,
)
from src.backend.modules.auth.rate_limit import login_limiter
from src.backend.modules.auth.service import (
    AuthService,
    InvalidRefreshToken,
    IssuedTokens,
    SamePassword,
    WrongCurrentPassword,
)

router = APIRouter()

REFRESH_COOKIE = "refresh_token"
# O cookie só vai para as rotas de /api/auth (refresh e logout), não para o resto da API.
REFRESH_COOKIE_PATH = "/api/auth"


def set_refresh_cookie(response: Response, tokens: IssuedTokens) -> None:
    """Grava o refresh token em cookie httpOnly com a validade dele (regra 4 da spec)."""
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=tokens.refresh_token,
        max_age=tokens.refresh_max_age,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=True,
        samesite=settings.refresh_cookie_samesite,
    )


def clear_refresh_cookie(response: Response) -> None:
    """Apaga o cookie com os mesmos atributos com que ele foi gravado."""
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=True,
        samesite=settings.refresh_cookie_samesite,
    )


def token_response(response: Response, tokens: IssuedTokens) -> TokenResponse:
    set_refresh_cookie(response, tokens)
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        user=tokens.user,
    )


def require_allowed_origin(request: Request) -> None:
    """Recusa pedidos de outros sites às rotas que usam o cookie (SameSite=None não os barra)."""
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.cors_origins_list:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origem não permitida.",
        )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo usuário",
)
async def register(
    request: Request,
    user_in: UserRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Cria um novo usuário (cliente por padrão) e retorna os tokens."""
    # TODO: Implementar Rate Limiting por IP
    
    service = AuthService(db)
    try:
        user = await service.create_user(user_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    return token_response(response, await service.issue_tokens(user))


@router.post("/login", response_model=TokenResponse, summary="Faz login")
async def login(
    request: Request,
    login_data: UserLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Autentica o usuário e retorna tokens JWT.

    Depois de 5 falhas do mesmo IP e e-mail em 15 minutos, responde 429 até a janela passar (#35)."""
    key = login_limiter.key(request.client.host if request.client else None, login_data.email)
    wait = login_limiter.retry_after(key)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente de novo em alguns minutos.",
            headers={"Retry-After": str(wait)},
        )

    service = AuthService(db)
    user = await service.authenticate_user(login_data.email, login_data.password)

    if not user:
        login_limiter.record_failure(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    login_limiter.reset(key)
    return token_response(response, await service.issue_tokens(user))


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renova o access token",
    dependencies=[Depends(require_allowed_origin)],
)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Troca o refresh token do cookie por um novo e devolve um access token novo."""
    try:
        tokens = await AuthService(db).rotate_refresh_token(refresh_token)
    except InvalidRefreshToken:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada. Entre novamente.",
        )
    return token_response(response, tokens)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Faz logout",
    dependencies=[Depends(require_allowed_origin)],
)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Revoga a sessão do refresh token no servidor e apaga o cookie."""
    await AuthService(db).logout(refresh_token)
    clear_refresh_cookie(response)
    return MessageResponse(message="Logout efetuado com sucesso.")


@router.get("/me", response_model=UserResponse, summary="Obtém usuário logado")
async def get_me(current_user: User = Depends(get_current_user)):
    """Retorna os dados do próprio usuário autenticado."""
    return current_user


@router.put("/me", response_model=UserResponse, summary="Atualiza o próprio perfil")
async def update_me(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza nome, telefone e foto do usuário logado (só os campos enviados)."""
    return await AuthService(db).update_profile(current_user, data)


@router.put("/me/password", response_model=MessageResponse, summary="Troca a própria senha")
async def change_my_password(
    data: PasswordChangeRequest,
    refresh_token: str | None = Cookie(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Troca a senha conferindo a atual e encerra as outras sessões do usuário."""
    try:
        await AuthService(db).change_password(
            current_user, data.current_password, data.new_password, refresh_token
        )
    except WrongCurrentPassword:
        # 400, e não 401: um 401 faria o frontend tentar o refresh e repetir o pedido.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta.")
    except SamePassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha precisa ser diferente da atual.",
        )
    return MessageResponse(message="Senha alterada. As outras sessões foram encerradas.")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    request_data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)
):
    """Verifica o e-mail do usuário usando o token gerado no cadastro."""
    service = AuthService(db)
    success = await service.verify_email(request_data.token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado.",
        )
    return MessageResponse(message="E-mail verificado com sucesso.")


@router.post("/verify-email/resend", response_model=MessageResponse)
async def resend_verification(
    request_data: ResendVerificationRequest, db: AsyncSession = Depends(get_db)
):
    """Gera um novo token de verificação de e-mail (#35)."""
    await AuthService(db).resend_verification(request_data.email)
    # Mesma resposta sempre, para não revelar quais e-mails existem ou já foram verificados.
    return MessageResponse(message="Se a conta existir e ainda não estiver verificada, um novo link será enviado.")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request_data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """Gera um token de redefinição de senha e envia para o e-mail."""
    service = AuthService(db)
    await service.create_password_reset_token(request_data.email)
    # Sempre retorna sucesso para não vazar quais e-mails estão cadastrados
    return MessageResponse(
        message="Se o e-mail existir, um link de recuperação será enviado."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request_data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """Redefine a senha do usuário."""
    service = AuthService(db)
    success = await service.reset_password(
        request_data.token, request_data.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de reset inválido ou expirado.",
        )
    return MessageResponse(message="Senha redefinida com sucesso.")

# ── Administração de usuários (admin, #35) ─────────────

USER_NOT_FOUND = "Usuário não encontrado."


@router.get("/users", response_model=UserListResponse, summary="Lista usuários (admin)")
async def list_users(
    role: UserRole | None = Query(None),
    is_active: bool | None = Query(None),
    q: str | None = Query(None, max_length=100, description="Busca no nome ou no e-mail"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    users, total = await AuthService(db).list_users(
        role=role, is_active=is_active, search=q, page=page, per_page=per_page
    )
    return UserListResponse(
        users=users, total=total, page=page, per_page=per_page, total_pages=math.ceil(total / per_page)
    )


@router.get("/users/{user_id}", response_model=UserResponse, summary="Detalha um usuário (admin)")
async def get_user(
    user_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)
):
    user = await AuthService(db).get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    return user


@router.put("/users/{user_id}/role", response_model=UserResponse, summary="Muda o perfil de acesso (admin)")
async def update_user_role(
    user_id: uuid.UUID, data: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin),
):
    try:
        user = await AuthService(db).set_role(admin, user_id, UserRole(data.role))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if user is None:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    return user


@router.put("/users/{user_id}/status", response_model=UserResponse, summary="Ativa ou desativa (admin)")
async def update_user_status(
    user_id: uuid.UUID, data: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin),
):
    try:
        user = await AuthService(db).set_status(admin, user_id, data.is_active)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if user is None:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    return user
