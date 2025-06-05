from openai import base_url
from pydantic import BaseModel, Field
from typing import List, Optional

class MessageTableItem(BaseModel):
    message_id: str = Field(..., alias="id_message")
    user_id: str = Field(..., alias="id_user")
    chat_id: Optional[str] = None
    content: str
    response: Optional[str] = None
    timestamp: str
    is_bot: bool = False

    class Config:
        validate_by_name = True

class MessageTableList(BaseModel):
    messages: List

class MessagePayLoad(BaseModel):
    content: str
    chat_id: Optional[str] = None

