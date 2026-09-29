"""
Trim — Auth Router

Definição dos endpoints REST para o módulo de autenticação.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.modules.auth import security
from src.backend.modules.auth.dependencies import get_current_user
from src.backend.modules.auth.models import User
from src.backend.modules.auth.schemas import (
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    VerifyEmailRequest,
)
from src.backend.modules.auth.service import AuthService

router = APIRouter()


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

    # Gera tokens
    payload = {"user_id": str(user.id), "email": user.email, "role": user.role}
    access_token, expires_in = security.create_access_token(payload, user.role)
    refresh_token, _ = security.create_refresh_token(payload, user.role)

    # Configura o refresh token em cookie httpOnly
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=user,
    )


@router.post("/login", response_model=TokenResponse, summary="Faz login")
async def login(
    request: Request,
    login_data: UserLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Autentica o usuário e retorna tokens JWT."""
    # TODO: Implementar Rate Limiting por IP e Email
    
    service = AuthService(db)
    user = await service.authenticate_user(login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = {"user_id": str(user.id), "email": user.email, "role": user.role}
    access_token, expires_in = security.create_access_token(payload, user.role)
    refresh_token, _ = security.create_refresh_token(payload, user.role)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=user,
    )


@router.post("/logout", response_model=MessageResponse, summary="Faz logout")
async def logout(response: Response):
    """Invalida a sessão removendo o cookie do refresh token."""
    response.delete_cookie("refresh_token")
    return MessageResponse(message="Logout efetuado com sucesso.")


@router.get("/me", response_model=UserResponse, summary="Obtém usuário logado")
async def get_me(current_user: User = Depends(get_current_user)):
    """Retorna os dados do próprio usuário autenticado."""
    return current_user


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
