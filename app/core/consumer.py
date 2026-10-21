import asyncio
import json

import redis.asyncio as aioredis
from fastapi import WebSocket


async def redis_stream_listener(redis_client : aioredis.Redis ,session_id: str, start_id: str, websocket: WebSocket):
    stream_key = f"chat_stream:{session_id}"
    last_id = start_id

    try:
        while True:
            response = await redis_client.xread(
                {stream_key: last_id}, block=0, count=20
            )

            for stream, messages in response:
                for msg_id, data in messages:
                    raw_payload = data["payload"]

                    payload_dict = json.loads(raw_payload)
                    payload_dict["redis_id"] = msg_id

                    # Send data to the user
                    await websocket.send_text(json.dumps(payload_dict))

                    last_id = msg_id

    except asyncio.CancelledError:
        pass