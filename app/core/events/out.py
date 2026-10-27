from typing import Literal

from pydantic import BaseModel, Field


class AgentEventMessage(BaseModel):
    type: Literal["start", "chunk", "end", "cancel"] = Field(default='chunk')
    sender_name: Literal["agent" , 'system'] = Field(default='agent')
    turn_id: str
    text_delta: str | None = None
    timestamp: int
    metadata: dict[str , str] = Field(default_factory=dict)

class SessionEventMessage(BaseModel):
    type: Literal["user_joined", "user_left", "typing_indicator"]
    user_id: str
    username: str
    timestamp: int
    metadata: dict[str , str] = Field(default_factory=dict)