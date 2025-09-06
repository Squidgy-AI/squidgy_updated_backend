# Optimized version of the /n8n/agent/query endpoint

import asyncio
import time
import hashlib
from typing import Dict, List, Any, Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Simple in-memory cache with TTL
class SimpleCache:
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str, ttl_seconds: int = 300) -> Optional[Any]:
        if key in self._cache:
            if time.time() - self._timestamps[key] < ttl_seconds:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamps[key]
        return None
    
    def set(self, key: str, value: Any):
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def clear_old(self, ttl_seconds: int = 300):
        current_time = time.time()
        keys_to_remove = [
            key for key, timestamp in self._timestamps.items()
            if current_time - timestamp > ttl_seconds
        ]
        for key in keys_to_remove:
            del self._cache[key]
            del self._timestamps[key]

# Initialize caches
query_cache = SimpleCache()
embedding_cache = SimpleCache()
context_cache = SimpleCache()

# Timing decorator for monitoring
def log_timing(operation_name: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                logger.info(f"[TIMING] {operation_name}: {duration:.2f}s")
                return result
            except Exception as e:
                duration = time.time() - start
                logger.error(f"[TIMING] {operation_name} failed after {duration:.2f}s: {str(e)}")
                raise
        return wrapper
    return decorator

@app.post("/n8n/agent/query")
async def agent_kb_query_optimized(request: AgentKBQueryRequest):
    """Optimized agent query with parallel operations and caching"""
    try:
        start_time = time.time()
        
        # Check query cache first
        query_hash = hashlib.md5(f"{request.user_id}:{request.agent}:{request.user_mssg}".encode()).hexdigest()
        cached_response = query_cache.get(query_hash, ttl_seconds=120)  # 2-minute cache
        if cached_response:
            logger.info(f"[CACHE HIT] Query returned from cache in {time.time() - start_time:.2f}s")
            return cached_response
        
        # Generate or retrieve cached embedding
        embedding_key = f"emb:{hashlib.md5(request.user_mssg.encode()).hexdigest()}"
        query_embedding = embedding_cache.get(embedding_key, ttl_seconds=3600)  # 1-hour cache
        
        if query_embedding is None:
            query_embedding = await log_timing("embedding_generation")(
                AgentMatcher(supabase).get_query_embedding
            )(request.user_mssg)
            embedding_cache.set(embedding_key, query_embedding)
        else:
            logger.info("[CACHE HIT] Embedding retrieved from cache")
        
        # Parallel execution of main operations
        parallel_start = time.time()
        
        # Define context cache keys
        agent_ctx_key = f"agent_ctx:{request.agent}"
        client_ctx_key = f"client_ctx:{request.user_id}:{query_hash[:8]}"
        agent_know_key = f"agent_know:{request.agent}:{query_hash[:8]}"
        
        # Prepare parallel tasks with caching
        tasks = []
        
        # Agent context (cache for 10 minutes)
        agent_context_cached = context_cache.get(agent_ctx_key, ttl_seconds=600)
        if agent_context_cached:
            agent_context_future = asyncio.create_task(
                asyncio.sleep(0.001).then(lambda: agent_context_cached)
            )
        else:
            agent_context_future = asyncio.create_task(
                log_timing("agent_context_retrieval")(
                    dynamic_agent_kb_handler.get_agent_context_from_kb
                )(request.agent)
            )
        tasks.append(agent_context_future)
        
        # Client context (cache for 5 minutes)
        client_context_cached = context_cache.get(client_ctx_key, ttl_seconds=300)
        if client_context_cached:
            client_context_future = asyncio.create_task(
                asyncio.sleep(0.001).then(lambda: client_context_cached)
            )
        else:
            client_context_future = asyncio.create_task(
                log_timing("client_context_retrieval")(
                    get_optimized_client_context
                )(request.user_id, query_embedding)
            )
        tasks.append(client_context_future)
        
        # Agent knowledge (cache for 5 minutes)
        agent_knowledge_cached = context_cache.get(agent_know_key, ttl_seconds=300)
        if agent_knowledge_cached:
            agent_knowledge_future = asyncio.create_task(
                asyncio.sleep(0.001).then(lambda: agent_knowledge_cached)
            )
        else:
            agent_knowledge_future = asyncio.create_task(
                log_timing("agent_knowledge_retrieval")(
                    get_optimized_agent_knowledge
                )(request.agent, query_embedding)
            )
        tasks.append(agent_knowledge_future)
        
        # Execute all tasks in parallel
        agent_context, client_context, agent_knowledge = await asyncio.gather(*tasks)
        
        logger.info(f"[TIMING] Parallel operations completed in {time.time() - parallel_start:.2f}s")
        
        # Cache the results
        if not agent_context_cached:
            context_cache.set(agent_ctx_key, agent_context)
        if not client_context_cached:
            context_cache.set(client_ctx_key, client_context)
        if not agent_knowledge_cached:
            context_cache.set(agent_know_key, agent_knowledge)
        
        # Build KB context (this is fast, no need to parallelize)
        kb_context = await log_timing("context_building")(
            build_enhanced_kb_context
        )(request.user_id, client_context, agent_knowledge)
        
        # Check for missing info and analyze query in parallel
        must_questions = agent_context.get('must_questions', [])
        
        missing_info_future = asyncio.create_task(
            log_timing("missing_info_check")(
                check_missing_must_info
            )(must_questions, kb_context, client_context)
        )
        
        analysis_future = asyncio.create_task(
            log_timing("query_analysis")(
                dynamic_agent_kb_handler.analyze_query_with_context
            )(request.user_mssg, agent_context, client_context, kb_context)
        )
        
        missing_must_info, analysis = await asyncio.gather(
            missing_info_future,
            analysis_future
        )
        
        # Handle critical missing information
        if 'website_url' in missing_must_info:
            follow_up_questions = await dynamic_agent_kb_handler.generate_contextual_questions(
                request.user_mssg,
                agent_context,
                ['website_url'],
                client_context
            )
            
            response = AgentKBQueryResponse(
                user_id=request.user_id,
                agent=request.agent,
                response_type="needs_info",
                follow_up_questions=follow_up_questions,
                missing_information=[{
                    "field": "website_url",
                    "reason": "Required by agent's MUST questions to provide accurate analysis",
                    "priority": "critical"
                }],
                confidence_score=0.9,
                kb_context_used=bool(kb_context),
                status="missing_critical_info"
            )
            
            # Log performance
            execution_time = int((time.time() - start_time) * 1000)
            await log_performance_metric("agent_query_missing_info", execution_time, {
                "agent": request.agent,
                "user_id": request.user_id,
                "missing_info": missing_must_info,
                "cache_hits": {
                    "embedding": embedding_key in embedding_cache._cache,
                    "agent_context": agent_context_cached is not None,
                    "client_context": client_context_cached is not None,
                    "agent_knowledge": agent_knowledge_cached is not None
                }
            })
            
            # Don't cache responses that need more info
            return response
        
        # Generate response based on analysis
        if analysis.get('can_answer') and analysis.get('confidence', 0) > 0.7:
            available_tools = agent_context.get('tools', [])
            required_tool_names = analysis.get('required_tools', [])
            tools_to_use = [t for t in available_tools if t['name'] in required_tool_names]
            
            agent_response = await log_timing("response_generation")(
                dynamic_agent_kb_handler.generate_contextual_response
            )(request.user_mssg, agent_context, client_context, kb_context, tools_to_use)
            
            response = AgentKBQueryResponse(
                user_id=request.user_id,
                agent=request.agent,
                response_type="needs_tools" if tools_to_use else "direct_answer",
                agent_response=agent_response,
                required_tools=tools_to_use if tools_to_use else None,
                confidence_score=analysis.get('confidence', 0.8),
                kb_context_used=bool(kb_context),
                status="success"
            )
            
            # Cache successful responses
            query_cache.set(query_hash, response)
            
            # Log performance
            execution_time = int((time.time() - start_time) * 1000)
            await log_performance_metric("agent_query_success", execution_time, {
                "agent": request.agent,
                "user_id": request.user_id,
                "confidence": analysis.get('confidence', 0.8),
                "tools_used": len(tools_to_use),
                "context_sources": len(kb_context.get('sources', [])),
                "cache_hits": {
                    "embedding": embedding_key in embedding_cache._cache,
                    "agent_context": agent_context_cached is not None,
                    "client_context": client_context_cached is not None,
                    "agent_knowledge": agent_knowledge_cached is not None
                }
            })
            
            return response
        
        else:
            # Handle insufficient information case
            all_missing = missing_must_info + analysis.get('missing_info', [])
            
            follow_up_questions = await dynamic_agent_kb_handler.generate_contextual_questions(
                request.user_mssg,
                agent_context,
                all_missing,
                client_context
            )
            
            missing_info_formatted = []
            for info in all_missing:
                missing_info_formatted.append({
                    "field": info,
                    "reason": f"Required by {request.agent} agent to provide accurate response",
                    "priority": "high" if info in missing_must_info else "medium"
                })
            
            response = AgentKBQueryResponse(
                user_id=request.user_id,
                agent=request.agent,
                response_type="needs_info",
                follow_up_questions=follow_up_questions,
                missing_information=missing_info_formatted,
                confidence_score=analysis.get('confidence', 0.5),
                kb_context_used=bool(kb_context),
                status="needs_more_info"
            )
            
            # Log performance
            execution_time = int((time.time() - start_time) * 1000)
            await log_performance_metric("agent_query_needs_info", execution_time, {
                "agent": request.agent,
                "user_id": request.user_id,
                "missing_info_count": len(all_missing),
                "confidence": analysis.get('confidence', 0.5)
            })
            
            return response
            
    except Exception as e:
        # Log error performance
        execution_time = int((time.time() - start_time) * 1000)
        await log_performance_metric("agent_query_error", execution_time, {
            "agent": request.agent,
            "user_id": request.user_id,
            "error": str(e)
        }, success=False, error_message=str(e))
        
        logger.error(f"Error in agent_kb_query: {str(e)}")
        return AgentKBQueryResponse(
            user_id=request.user_id,
            agent=request.agent,
            response_type="error",
            error_message=f"An error occurred: {str(e)}",
            status="error"
        )

# Startup optimization - pre-warm the embedding model
async def startup_optimization():
    """Pre-warm services on startup to avoid cold start delays"""
    try:
        # Pre-load embedding model
        from embedding_service import get_embedding_service
        embedding_service = get_embedding_service()
        _ = await asyncio.create_task(
            asyncio.to_thread(embedding_service.get_embedding, "warmup text")
        )
        logger.info("Embedding model pre-warmed successfully")
        
        # Clear old cache entries periodically
        async def cache_cleaner():
            while True:
                await asyncio.sleep(300)  # Every 5 minutes
                query_cache.clear_old(ttl_seconds=120)
                embedding_cache.clear_old(ttl_seconds=3600)
                context_cache.clear_old(ttl_seconds=600)
                logger.debug("Cache cleanup completed")
        
        asyncio.create_task(cache_cleaner())
        
    except Exception as e:
        logger.error(f"Error in startup optimization: {e}")

# Add to your FastAPI startup event
@app.on_event("startup")
async def startup_event():
    await startup_optimization()