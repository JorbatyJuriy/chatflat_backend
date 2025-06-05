from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# 1.) Дані про користувачів
class UserTableItems(BaseModel):
    user_id: str = Field(..., alias='id_user')
    email: Optional[EmailStr] = None

    class Config:
        populate_by_name = True # Використовуйте populate_by_name замість validate_by_name для Pydantic v2+

# 2.) Payload при створенні користувача(локально)
class UserCreatePayload(BaseModel):
    email: EmailStr

# 3.) JWT-користувач який приходить у токені Cognito
class CognitoUser(BaseModel):
    sub: str

    username: str # Якщо 'username' завжди присутній і не може бути None

    email: Optional[str] = None # Залишаємо Optional, бо email може бути не у всіх токенах
    token_use: str
    exp: int
    iat: int
    iss: Optional[str] = None
    auth_time: Optional[int] = None


    class Config:
        populate_by_name = True #