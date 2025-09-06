"""
Optimized N8N Integration with Circuit Breaker and Retry Logic
"""
import asyncio
import httpx
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 60
    timeout: int = 30

class CircuitBreaker:
    """Circuit breaker to prevent cascading failures"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("🔄 Circuit breaker: Moving to HALF_OPEN state")
                else:
                    raise Exception("Circuit breaker is OPEN - service unavailable")
            
            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
            except Exception as e:
                await self._on_failure()
                raise e
    
    async def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("✅ Circuit breaker: Service recovered, moving to CLOSED state")
    
    async def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"🚨 Circuit breaker: OPEN after {self.failure_count} failures")

class OptimizedN8NHandler:
    """Optimized N8N integration with retry logic and circuit breaker"""
    
    def __init__(self, n8n_webhook_url: str):
        self.n8n_webhook_url = n8n_webhook_url
        self.circuit_breaker = CircuitBreaker(CircuitBreakerConfig())
        self.session_cache: Dict[str, Any] = {}
        self._cache_lock = asyncio.Lock()
        
        # HTTP client with connection pooling
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
    
    async def process_with_retry(self, request_data: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """Process request with exponential backoff retry"""
        for attempt in range(max_retries + 1):
            try:
                return await self.circuit_breaker.call(self._send_n8n_request, request_data)
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"❌ N8N request failed after {max_retries} retries: {str(e)}")
                    raise
                
                # Exponential backoff: 1s, 2s, 4s
                delay = 2 ** attempt
                logger.warning(f"⚠️ N8N request failed (attempt {attempt + 1}), retrying in {delay}s: {str(e)}")
                await asyncio.sleep(delay)
    
    async def _send_n8n_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to N8N with optimized error handling"""
        start_time = time.time()
        
        try:
            response = await self.http_client.post(
                self.n8n_webhook_url,
                json=request_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"🔗 N8N request completed in {execution_time:.2f}ms")
            
            if response.status_code == 200:
                return response.json()
            else:
                raise httpx.HTTPStatusError(
                    f"N8N returned status {response.status_code}", 
                    request=response.request, 
                    response=response
                )
                
        except httpx.TimeoutException:
            logger.error("⏰ N8N request timed out")
            raise Exception("N8N request timeout")
        except httpx.RequestError as e:
            logger.error(f"🌐 N8N connection error: {str(e)}")
            raise Exception(f"N8N connection failed: {str(e)}")
    
    async def batch_process_requests(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple requests concurrently with rate limiting"""
        semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
        
        async def process_single_request(request_data):
            async with semaphore:
                return await self.process_with_retry(request_data)
        
        try:
            # Process all requests concurrently
            results = await asyncio.gather(
                *[process_single_request(req) for req in requests],
                return_exceptions=True
            )
            
            # Separate successful and failed results
            successful_results = []
            failed_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Batch request {i} failed: {str(result)}")
                    failed_count += 1
                else:
                    successful_results.append(result)
            
            logger.info(f"📊 Batch processing: {len(successful_results)} successful, {failed_count} failed")
            return successful_results
            
        except Exception as e:
            logger.error(f"❌ Batch processing failed: {str(e)}")
            raise
    
    async def get_cached_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached session data to avoid redundant API calls"""
        async with self._cache_lock:
            return self.session_cache.get(session_id)
    
    async def cache_session_data(self, session_id: str, data: Dict[str, Any], ttl: int = 600):
        """Cache session data with TTL"""
        async with self._cache_lock:
            self.session_cache[session_id] = {
                'data': data,
                'timestamp': time.time(),
                'ttl': ttl
            }
    
    async def cleanup_expired_sessions(self):
        """Clean up expired session cache"""
        async with self._cache_lock:
            current_time = time.time()
            expired_sessions = [
                session_id for session_id, session_data in self.session_cache.items()
                if current_time - session_data['timestamp'] > session_data['ttl']
            ]
            
            for session_id in expired_sessions:
                del self.session_cache[session_id]
            
            if expired_sessions:
                logger.info(f"🧹 Cleaned up {len(expired_sessions)} expired sessions")
    
    async def close(self):
        """Clean up resources"""
        await self.http_client.aclose()

# Background task to clean up expired sessions
async def start_session_cleanup_task(n8n_handler: OptimizedN8NHandler):
    """Background task to clean up expired sessions"""
    while True:
        try:
            await asyncio.sleep(300)  # Clean every 5 minutes
            await n8n_handler.cleanup_expired_sessions()
        except Exception as e:
            logger.error(f"❌ Session cleanup error: {str(e)}")