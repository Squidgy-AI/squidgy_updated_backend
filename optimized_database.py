"""
Optimized Database Operations with Connection Pooling and Caching
"""
import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    data: Any
    timestamp: datetime
    ttl: int  # Time to live in seconds

class OptimizedDatabaseManager:
    """Optimized database manager with connection pooling and caching"""
    
    def __init__(self, supabase_client, cache_ttl: int = 300):
        self.supabase = supabase_client
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_ttl = cache_ttl
        self._cache_lock = asyncio.Lock()
        
        # Connection pool settings
        self.max_concurrent_queries = 10
        self.query_semaphore = asyncio.Semaphore(self.max_concurrent_queries)
    
    async def _get_cache_key(self, table: str, filters: Dict, operation: str) -> str:
        """Generate cache key for query"""
        return f"{table}_{operation}_{hash(str(sorted(filters.items())))}"
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Thread-safe cache retrieval"""
        async with self._cache_lock:
            entry = self.cache.get(cache_key)
            if entry and (datetime.now() - entry.timestamp).total_seconds() < entry.ttl:
                logger.debug(f"🎯 Cache hit: {cache_key}")
                return entry.data
            elif entry:
                # Remove expired entry
                del self.cache[cache_key]
        return None
    
    async def _set_cache(self, cache_key: str, data: Any, ttl: int = None):
        """Thread-safe cache storage"""
        ttl = ttl or self.cache_ttl
        async with self._cache_lock:
            self.cache[cache_key] = CacheEntry(
                data=data,
                timestamp=datetime.now(),
                ttl=ttl
            )
            logger.debug(f"💾 Cache set: {cache_key}")
    
    async def optimized_agent_match_query(self, agent_name: str, query_embedding: List[float], threshold: float = 0.2):
        """Optimized agent matching with caching and connection pooling"""
        cache_key = await self._get_cache_key(
            'agent_documents', 
            {'agent_name': agent_name, 'threshold': threshold}, 
            'match'
        )
        
        # Check cache first
        cached_result = await self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Use semaphore to limit concurrent database connections
        async with self.query_semaphore:
            try:
                start_time = time.time()
                
                # Optimized query with LIMIT to reduce data transfer
                result = self.supabase.rpc(
                    'match_documents',
                    {
                        'query_embedding': query_embedding,
                        'match_threshold': threshold,
                        'match_count': 5,  # Limit results
                        'filter_agent': agent_name
                    }
                ).execute()
                
                execution_time = (time.time() - start_time) * 1000
                logger.info(f"🔍 Agent match query executed in {execution_time:.2f}ms")
                
                # Cache successful results
                await self._set_cache(cache_key, result.data, ttl=600)  # Cache for 10 minutes
                
                return result.data
                
            except Exception as e:
                logger.error(f"❌ Agent match query failed: {str(e)}")
                raise
    
    async def batch_client_context_update(self, updates: List[Dict[str, Any]]):
        """Batch update client context to reduce database round trips"""
        if not updates:
            return []
        
        async with self.query_semaphore:
            try:
                start_time = time.time()
                
                # Use batch upsert for better performance
                result = self.supabase.table('client_context')\
                    .upsert(updates, on_conflict='client_id,context_type')\
                    .execute()
                
                execution_time = (time.time() - start_time) * 1000
                logger.info(f"📦 Batch context update: {len(updates)} records in {execution_time:.2f}ms")
                
                # Invalidate related cache entries
                for update in updates:
                    client_id = update.get('client_id')
                    if client_id:
                        cache_pattern = f"client_context_{client_id}"
                        await self._invalidate_cache_pattern(cache_pattern)
                
                return result.data
                
            except Exception as e:
                logger.error(f"❌ Batch context update failed: {str(e)}")
                raise
    
    async def _invalidate_cache_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        async with self._cache_lock:
            keys_to_remove = [key for key in self.cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self.cache[key]
            if keys_to_remove:
                logger.debug(f"🧹 Invalidated {len(keys_to_remove)} cache entries for pattern: {pattern}")
    
    async def get_agent_documents_optimized(self, agent_name: str, limit: int = 5):
        """Optimized agent documents retrieval with caching"""
        cache_key = await self._get_cache_key(
            'agent_documents', 
            {'agent_name': agent_name, 'limit': limit}, 
            'select'
        )
        
        cached_result = await self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        async with self.query_semaphore:
            try:
                start_time = time.time()
                
                # Use index-optimized query
                result = self.supabase.table('agent_documents')\
                    .select('content, metadata, created_at')\
                    .eq('agent_name', agent_name)\
                    .order('created_at', desc=True)\
                    .limit(limit)\
                    .execute()
                
                execution_time = (time.time() - start_time) * 1000
                logger.info(f"📚 Agent documents query: {execution_time:.2f}ms")
                
                # Cache results for 15 minutes
                await self._set_cache(cache_key, result.data, ttl=900)
                
                return result.data
                
            except Exception as e:
                logger.error(f"❌ Agent documents query failed: {str(e)}")
                raise
    
    async def cleanup_expired_cache(self):
        """Clean up expired cache entries periodically"""
        async with self._cache_lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self.cache.items()
                if (now - entry.timestamp).total_seconds() > entry.ttl
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.info(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")

# Initialize background cache cleanup
async def start_cache_cleanup_task(db_manager: OptimizedDatabaseManager):
    """Background task to clean up expired cache entries"""
    while True:
        try:
            await asyncio.sleep(300)  # Clean every 5 minutes
            await db_manager.cleanup_expired_cache()
        except Exception as e:
            logger.error(f"❌ Cache cleanup error: {str(e)}")