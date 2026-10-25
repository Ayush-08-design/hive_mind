import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum

import tiktoken


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: str
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_api_dict(self) -> dict:
        msg : dict = {"role": self.role, "content": self.content or ''}
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        return msg

    
    def get_hash(self):
        run_id = hashlib.md5(f"{time.time()}:{self.content}".encode()).hexdigest()[:8]
        return run_id

class ContextManager:

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history: list[Message]
        self._encoder = tiktoken.get_encoding("cl100k_base")
        self.max_tokens: int = 128_000
        self.total_tokens: int
        self.system_msg: Message | None = None
        self.local_lock = asyncio.Lock()

    async def build_context(self) -> list[dict]:
        async with self.local_lock:
            messages = []
            if self.system_msg:
                messages.append(self.system_msg.to_api_dict())
            messages.extend(msg.to_api_dict() for msg in self.history)
            return messages

    async def add_message(self, role: str, content: str):
        async with self.local_lock:
            self.history.append({"role": role, "content": content})

    def within_budget(self):
        return self.total_tokens < (self.max_tokens * 0.8)

    async def count_tokens(self, text: str) -> int:
        return len(self._encoder.encode(text))

    async def count_message_tokens(self, msg: Message) -> int:
        return self.count_tokens(msg.content or "") + 4

    def total_history_tokens(self) -> int:
        return sum(self.count_message_tokens(msg) for msg in self.history)

    def _enforce_budget(self) -> None:
        budget = self.max_tokens * 0.8
        while self.total_history_tokens() > budget and len(self.history) > 2:
            dropped = self.history.pop(1)
            if dropped.tool_calls:
                while len(self.history) > 1 and self.history[1].role == Role.TOOL:
                    self.history.pop(1)
    