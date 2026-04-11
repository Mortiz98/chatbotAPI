from fastapi import APIRouter, Depends, Response, HTTPException, status
from sqlalchemy.orm import Session
from db.database import get_db
from models.schemas import UserCreate, UserResponse, UserLogin, Token
from services.auth_service import AuthService
from core.security import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """
    Registra un nuevo usuario en el sistema.
    """
    auth_service = AuthService(db)
    return auth_service.register_user(user_data)


@router.post("/login", response_model=Token)
def login(
    user_data: UserLogin, response: Response, db: Session = Depends(get_db)
) -> Token:
    """
    Autentica un usuario y retorna los tokens.
    """
    auth_service = AuthService(db)
    tokens = auth_service.authenticate_user(user_data)

    # Configurar cookies seguras
    # Nota: secure=False para desarrollo local (HTTP)
    # En producción con HTTPS, cambiar a secure=True
    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        httponly=True,
        secure=False,  # False para HTTP en desarrollo
        samesite="lax",
        max_age=1800,  # 30 minutos
    )

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=False,  # False para HTTP en desarrollo
        samesite="lax",
        max_age=86400,  # 24 horas
    )

    return tokens


@router.post("/logout")
def logout(response: Response):
    """
    Cierra la sesión del usuario eliminando las cookies.
    """
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    return {"message": "Sesión cerrada exitosamente"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """
    Retorna la información del usuario actualmente autenticado.
    """
    return current_user


@router.post("/refresh", response_model=Token)
def refresh_token(
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Token:
    """
    Renueva el token de acceso usando el token de actualización.
    """
    auth_service = AuthService(db)
    tokens = auth_service.refresh_access_token(current_user.id)

    # Actualizar cookies seguras
    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        httponly=True,
        secure=False,  # False para HTTP en desarrollo
        samesite="lax",
        max_age=1800,  # 30 minutos
    )

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=False,  # False para HTTP en desarrollo
        samesite="lax",
        max_age=86400,  # 24 horas
    )

    return tokens
