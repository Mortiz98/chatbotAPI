from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: Optional[datetime] = None 

class UserBase(BaseSchema):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=8)

class UserInDB(UserBase, TimestampSchema):
    id: int
    hashed_password: str

class UserResponse(UserBase, TimestampSchema):
    id: int
    
class MessageBase(BaseSchema):
    content: str = Field(..., min_length=1)
    is_bot: bool = False

class MessageCreate(MessageBase):
    user_id: int

class MessageInDB(MessageBase, TimestampSchema):
    id: int
    user_id: int

class MessageResponse(MessageBase, TimestampSchema):
    id: int
    user_id: int

class ChatSession(BaseSchema):
    id: int
    messages: List[MessageResponse]
    started_at: datetime
    ended_at: Optional[datetime] = None 

class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseSchema):
    email: Optional[str] = None
    user_id: Optional[int] = None

class UserLogin(BaseSchema):
    email: str
    password: str
    
    
__all__ = [
    "UserBase", "UserCreate", "UserUpdate", "UserInDB", "UserResponse",
    "MessageBase", "MessageCreate", "MessageInDB", "MessageResponse", "ChatSession",
    "Token", "TokenData", "Login"
] 