import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

from app.agent.llm.events import (
    StreamEvent,
    StreamEventType,
    TextDelta,
    TokenUsage,
)
from app.config import Config


class LLMClient:
    def __init__(self, config: Config) -> None:
        self._client: AsyncOpenAI | None = None
        self._max_retries: int = 3
        self.config = config

    def get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=self.config.base_url,
                api_key=self.config.api_key,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None


    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
    ) -> AsyncGenerator[StreamEvent, None]:

        client = self.get_client()

        kwargs = {"model": self.config.model_name, "messages": messages, "stream": True}

        for attempt in range(self._max_retries + 1):
            try:
                async for event in self._stream_response(client, kwargs):
                    yield event

            except RateLimitError as e:
                if attempt < self._max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"Rate Limit Exceeded : {e}",
                    )
                return

            except APIConnectionError as e:
                if attempt < self._max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"Connection Error : {e}",
                    )
                    return

            except APIError as e:
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    error=f"API Error : {e}",
                )
                return

    async def _stream_response(
        self, client: AsyncOpenAI, kwargs: dict[str, any]
    ) -> AsyncGenerator[StreamEvent, None]:

        response = await client.chat.completions.create(**kwargs)

        finish_reason: str | None = None
        usage: TokenUsage | None = None

        async for chunk in response:
            if hasattr(chunk, "usage") and chunk.usage:
                usage = TokenUsage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                    cached_tokens=(
                        chunk.usage.prompt_tokens_details.cached_tokens
                        if chunk.usage.prompt_tokens_details
                        else 0
                    ),
                )
            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            if choice.finish_reason:
                finish_reason = choice.finish_reason

            if delta.content:
                yield StreamEvent(
                    type=StreamEventType.TEXT_DELTA,
                    text_delta=TextDelta(delta.content),
                )

        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            finish_reason=finish_reason,
            usage=usage,
        )
