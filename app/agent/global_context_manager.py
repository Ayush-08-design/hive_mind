import asyncio

from app.agent.local_context_manager import ContextManager


class GlobalContextManager:
    def __init__(self):
        
        self._sessions: dict[str, ContextManager] = {}
        self._global_lock = asyncio.Lock()

    async def _get_session(self, session_id: str) -> ContextManager:
        if session_id in self._sessions:
            return self._sessions[session_id]
        async with self._global_lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = ContextManager(session_id)
        return self._sessions[session_id]
        
    async def clear_session(self, session_id: str):
        if session_id in self._sessions:
            async with self._sessions[session_id].local_lock:
                del self._sessions[session_id]
                

global_ctx_manager = None

def get_global_context_manager() -> GlobalContextManager:
    global global_ctx_manager
    if global_ctx_manager is None:
        global_ctx_manager = GlobalContextManager()
    return global_ctx_manager