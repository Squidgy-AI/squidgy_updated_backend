"""
Optimized Connection Manager with proper concurrency control
"""
import asyncio
import threading
from typing import Dict, Set
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class ThreadSafeConnectionManager:
    """Thread-safe connection manager to prevent race conditions"""
    
    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}
        self._active_requests: Set[str] = set()
        self._lock = asyncio.Lock()
        self._request_lock = asyncio.Lock()
        
    async def add_connection(self, connection_id: str, websocket: WebSocket):
        """Thread-safe connection addition"""
        async with self._lock:
            self._connections[connection_id] = websocket
            logger.info(f"✅ Added connection: {connection_id}")
    
    async def remove_connection(self, connection_id: str):
        """Thread-safe connection removal"""
        async with self._lock:
            if connection_id in self._connections:
                del self._connections[connection_id]
                logger.info(f"🗑️ Removed connection: {connection_id}")
    
    async def get_connection(self, connection_id: str) -> WebSocket:
        """Thread-safe connection retrieval"""
        async with self._lock:
            return self._connections.get(connection_id)
    
    async def add_active_request(self, request_id: str) -> bool:
        """Thread-safe request tracking - returns False if already exists"""
        async with self._request_lock:
            if request_id in self._active_requests:
                return False
            self._active_requests.add(request_id)
            return True
    
    async def remove_active_request(self, request_id: str):
        """Thread-safe request removal"""
        async with self._request_lock:
            self._active_requests.discard(request_id)
    
    async def get_connection_count(self) -> int:
        """Get current connection count"""
        async with self._lock:
            return len(self._connections)

# Global instance
connection_manager = ThreadSafeConnectionManager()