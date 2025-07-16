from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime, nullable=True)
    
    # Relaciones
    messages = relationship("Message", back_populates="user")
    chat_sessions = relationship("ChatSession", back_populates="user")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    is_bot = Column(Boolean, default=False)
    created_at = Column(DateTime)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)
    
    # Relaciones
    user = relationship("User", back_populates="messages")
    session = relationship("ChatSession", back_populates="messages")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime)
    ended_at = Column(DateTime, nullable=True)
    
    # Relaciones
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("Message", back_populates="session") 