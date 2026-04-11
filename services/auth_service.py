from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from core.logging_config import logger
from db import models
from models.schemas import UserCreate, UserResponse, UserLogin, Token


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register_user(self, user_data: UserCreate) -> UserResponse:
        """
        Registra un nuevo usuario en el sistema.
        Verifica que el email y username no existan previamente.
        """
        # Verificar si el email ya existe
        if (
            self.db.query(models.User)
            .filter(models.User.email == user_data.email)
            .first()
        ):
            logger.warning(
                f"Registration attempt with existing email: {user_data.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado",
            )

        # Verificar si el username ya existe
        if (
            self.db.query(models.User)
            .filter(models.User.username == user_data.username)
            .first()
        ):
            logger.warning(
                f"Registration attempt with existing username: {user_data.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está en uso",
            )

        # Crear el nuevo usuario
        db_user = models.User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password),
            is_active=True,
        )

        try:
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            logger.info(f"User registered successfully: {user_data.email}")
            return UserResponse.model_validate(db_user)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user {user_data.email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear el usuario",
            )

    def authenticate_user(self, user_data: UserLogin) -> Token:
        """
        Autentica un usuario y retorna los tokens de acceso y actualización.
        """
        user = (
            self.db.query(models.User)
            .filter(models.User.email == user_data.email)
            .first()
        )

        if not user:
            logger.warning(
                f"Authentication attempt with non-existent email: {user_data.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
            )

        if not verify_password(user_data.password, str(user.hashed_password)):
            logger.warning(f"Failed authentication attempt for user: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
            )

        # Generar tokens
        access_token = create_access_token({"user_id": user.id})
        refresh_token = create_refresh_token({"user_id": user.id})

        logger.info(f"User authenticated successfully: {user_data.email}")

        return Token(access_token=access_token, refresh_token=refresh_token)

    def get_user_by_id(self, user_id: int) -> Optional[UserResponse]:
        """
        Obtiene un usuario por su ID.
        """
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return None
        return UserResponse.model_validate(user)

    def update_last_login(self, user_id: int) -> None:
        """
        Actualiza la fecha del último login del usuario.
        """
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            user.updated_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Updated last login for user_id: {user_id}")

    def deactivate_user(self, user_id: int) -> None:
        """
        Desactiva un usuario en el sistema.
        """
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            user.is_active = False
            user.updated_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"User deactivated: user_id {user_id}")

    def refresh_access_token(self, user_id: int) -> Token:
        """
        Genera un nuevo token de acceso y de actualización.
        """
        user = self.db.query(models.User).filter(models.User.id == user_id).first()

        if not user:
            logger.warning(f"Token refresh attempt for non-existent user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado"
            )

        if not bool(user.is_active):
            logger.warning(f"Token refresh attempt for inactive user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo"
            )

        # Generar nuevos tokens
        access_token = create_access_token({"user_id": user.id})
        refresh_token = create_refresh_token({"user_id": user.id})

        logger.info(f"Tokens refreshed for user: {user_id}")

        return Token(access_token=access_token, refresh_token=refresh_token)
