from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
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
        if self.db.query(models.User).filter(models.User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
        
        # Verificar si el username ya existe
        if self.db.query(models.User).filter(models.User.username == user_data.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está en uso"
            )

        # Crear el nuevo usuario
        db_user = models.User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password),
            created_at=datetime.utcnow(),
            is_active=True
        )

        try:
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            return UserResponse.model_validate(db_user)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear el usuario"
            )

    def authenticate_user(self, user_data: UserLogin) -> Token:
        """
        Autentica un usuario y retorna los tokens de acceso y actualización.
        """
        user = self.db.query(models.User).filter(models.User.email == user_data.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas"
            )

        if not verify_password(user_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas"
            )

        # Generar tokens
        access_token = create_access_token({"user_id": user.id})
        refresh_token = create_refresh_token({"user_id": user.id})

        return Token(
            access_token=access_token,
            refresh_token=refresh_token
        )

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

    def deactivate_user(self, user_id: int) -> None:
        """
        Desactiva un usuario en el sistema.
        """
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            user.is_active = False
            user.updated_at = datetime.utcnow()
            self.db.commit()





          