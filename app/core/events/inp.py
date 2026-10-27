from typing import Literal

from pydantic import BaseModel, Field


class JoinMessage(BaseModel):
    """Message sent when a user joins a session"""

    type: str = Field(default="join")
    user_id: str
    username: str
    session_id: str | None = None
    last_seen_id: str = "0"

    
class UserMessage(BaseModel):
    type: Literal["chat", "agent", "cancel"]
    sender_id: str
    sender_name: str
    content: str
    timestamp: str