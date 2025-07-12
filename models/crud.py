from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from . import models, schemas

def create_message(db: Session, message: schemas.MessageCreate) -> models.Message:
    """
    Crea un nuevo mensaje en la base de datos.
    """
    db_message = models.Message(
        content=message.content,
        user_id=message.user_id,
        is_bot=message.is_bot,
        created_at=datetime.utcnow()
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_messages_by_user(
    db: Session,
    user_id: int,
    limit: int = 50
) -> List[models.Message]:
    """
    Obtiene los mensajes de un usuario específico.
    """
    return (
        db.query(models.Message)
        .filter(models.Message.user_id == user_id)
        .order_by(models.Message.created_at.desc())
        .limit(limit)
        .all()
    )

def create_chat_session(db: Session, user_id: int) -> models.ChatSession:
    """
    Crea una nueva sesión de chat.
    """
    db_session = models.ChatSession(
        user_id=user_id,
        started_at=datetime.utcnow()
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_chat_session(db: Session, session_id: int) -> Optional[models.ChatSession]:
    """
    Obtiene una sesión de chat específica.
    """
    return (
        db.query(models.ChatSession)
        .filter(models.ChatSession.id == session_id)
        .first()
    )

def end_chat_session(db: Session, session_id: int) -> Optional[models.ChatSession]:
    """
    Finaliza una sesión de chat.
    """
    db_session = get_chat_session(db, session_id)
    if db_session:
        db_session.ended_at = datetime.utcnow()
        db.commit()
        db.refresh(db_session)
    return db_session 