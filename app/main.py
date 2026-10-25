import asyncio
import uuid

import redis.asyncio as aioredis
from agent.global_context_manager import (
    GlobalContextManager,
)
from core.agent_worker import (
    append_user_message,
    enqueue_agent_job,
    request_cancel,
)
from core.consumer import redis_stream_listener
from core.events.inp import JoinMessage, UserMessage
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware

# =======================================================================
#  Redis Client Setup
# =======================================================================

redis_client = aioredis.from_url("redis://localhost:6379", decode_responses=True)

app = FastAPI(
    title="HiveMind",
    description="Real-time collaborative chat with a shared LLM",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {'message' : 'Hello from [Hive-Mind]'}

# =========================================================================
#  WebSocket Endpoint
# =========================================================================

@app.websocket("/ws")
async def websocket_endpoint( 
    websocket: WebSocket
):
    await websocket.accept()

    # 1. Accept initialization settings [JoinMessage] from client
    # The client can pass '0' for fresh loads, or their last seen redis ID (e.g. "1718239012-0")
    join_msg_raw = await websocket.receive_text()
    join_message = JoinMessage.model_validate_json(join_msg_raw)
    start_id = join_message.last_seen_id
    
    session_id = join_message.session_id
    
    # Initialize the context manager for this user's session
    ctx_manager = await GlobalContextManager()._get_session(session_id)

    # 2. Start the redis streaming listener
    listener_task = asyncio.create_task(
        redis_stream_listener(redis_client, session_id, start_id, websocket)
    )

    try: 
        while True:
            user_msg_raw = await websocket.receive_text()
            data = UserMessage.model_validate_json(user_msg_raw)
            
            payload = data.model_dump()
            # Common metadata in all types of payloads
            payload["message_id"] = f"msg_{uuid.uuid4().hex[:8]}"
            
            # Trigger LLM background execution loop asynchronously
            if data.type == "agent":

                ctx_manager.add_user_message(session_id , data.content, data.sender_id, data.sender_name)
                enqueue_agent_job(
                    redis_client, session_id, data.sender_id
                )
            if data.type == "cancel":
                await request_cancel(redis_client, session_id)
                continue
            
            else:
                payload["type"] = "chat"
            # Commit the message to the central stream ledger
            await append_user_message(redis_client, session_id, payload)


    except WebSocketDisconnect:
        listener_task.cancel()
        

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True 
    )