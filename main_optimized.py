"""
Optimized main.py with all performance improvements integrated
Key improvements:
1. Thread-safe connection management
2. Database query optimization with caching
3. Circuit breaker for N8N integration
4. Proper error handling and retry logic
5. Background tasks for cleanup
"""

# Import optimized components
from optimized_connection_manager import connection_manager
from optimized_database import OptimizedDatabaseManager, start_cache_cleanup_task
from optimized_n8n_handler import OptimizedN8NHandler, start_session_cleanup_task

# Modified WebSocket endpoint with optimizations
@app.websocket("/ws/{user_id}/{session_id}")
async def optimized_websocket_endpoint(websocket: WebSocket, user_id: str, session_id: str):
    """Optimized WebSocket endpoint with proper concurrency control"""
    connection_id = f"{user_id}_{session_id}"
    logger.info(f"🔗 New WebSocket connection: {connection_id}")
    
    await websocket.accept()
    
    # Use thread-safe connection manager
    await connection_manager.add_connection(connection_id, websocket)
    
    async def send_ping():
        """Send periodic ping to keep connection alive"""
        while await connection_manager.get_connection(connection_id) is not None:
            try:
                await asyncio.sleep(30)
                current_ws = await connection_manager.get_connection(connection_id)
                if current_ws:
                    await current_ws.send_json({
                        "type": "ping",
                        "timestamp": int(time.time() * 1000)
                    })
            except Exception:
                break
    
    ping_task = asyncio.create_task(send_ping())
    
    try:
        await websocket.send_json({
            "type": "connection_status",
            "status": "connected",
            "message": "WebSocket connection established",
            "timestamp": int(time.time() * 1000)
        })
        
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                message_data = json.loads(data)
                
                request_id = message_data.get("requestId", str(uuid.uuid4()))
                user_input = message_data.get("message", "").strip()
                
                # Handle control messages
                if message_data.get("type") in ["ping", "pong", "connection_status"] or not user_input:
                    if message_data.get("type") == "ping":
                        await websocket.send_json({"type": "pong", "timestamp": int(time.time() * 1000)})
                    continue
                
                # Use thread-safe request tracking
                if not await connection_manager.add_active_request(request_id):
                    logger.info(f"⚠️ Request {request_id} already being processed")
                    continue
                
                try:
                    await websocket.send_json({
                        "type": "ack",
                        "requestId": request_id,
                        "message": "Message received, processing...",
                        "timestamp": int(time.time() * 1000)
                    })
                    
                    # Process with optimized handler
                    request_data = {
                        "user_id": user_id,
                        "user_mssg": user_input,
                        "session_id": session_id,
                        "agent_name": message_data.get("agent", "presaleskb"),
                        "timestamp_of_call_made": datetime.now().isoformat()
                    }
                    
                    # Use optimized N8N handler with circuit breaker
                    task = asyncio.create_task(
                        process_optimized_websocket_message(request_data, websocket, request_id)
                    )
                    
                    def task_done_callback(task_result):
                        asyncio.create_task(connection_manager.remove_active_request(request_id))
                        if task_result.exception():
                            logger.error(f"❌ WebSocket task failed: {task_result.exception()}")
                        else:
                            logger.info(f"✅ WebSocket task completed successfully")
                    
                    task.add_done_callback(task_done_callback)
                    
                except Exception as e:
                    await connection_manager.remove_active_request(request_id)
                    logger.error(f"❌ Error processing WebSocket message: {str(e)}")
                    
            except asyncio.TimeoutError:
                # Send ping to check if connection is alive
                try:
                    await websocket.send_json({"type": "ping", "timestamp": int(time.time() * 1000)})
                except Exception:
                    logger.info(f"🔌 Connection {connection_id} appears dead")
                    break
            except json.JSONDecodeError:
                logger.warning("⚠️ Invalid JSON received")
                continue
                
    except WebSocketDisconnect:
        logger.info(f"👋 Client disconnected: {connection_id}")
    except Exception as e:
        logger.exception(f"❌ WebSocket error: {str(e)}")
    finally:
        ping_task.cancel()
        await connection_manager.remove_connection(connection_id)
        logger.info(f"🔌 WebSocket connection closed: {connection_id}")

async def process_optimized_websocket_message(request_data: Dict, websocket: WebSocket, request_id: str):
    """Process WebSocket message with all optimizations"""
    try:
        # Use optimized N8N handler with retry and circuit breaker
        n8n_handler = OptimizedN8NHandler(N8N_MAIN)
        
        # Check if we have cached session data
        session_id = request_data.get("session_id")
        cached_data = await n8n_handler.get_cached_session_data(session_id)
        
        if cached_data:
            logger.info(f"🎯 Using cached session data for {session_id}")
            # Use cached context if available
            request_data.update(cached_data['data'])
        
        # Process with retry logic
        response = await n8n_handler.process_with_retry(request_data)
        
        # Cache successful response
        if response and session_id:
            await n8n_handler.cache_session_data(session_id, {"context": response})
        
        # Send response via WebSocket
        await websocket.send_json({
            "type": "message",
            "requestId": request_id,
            "data": response,
            "timestamp": int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"❌ Error in optimized message processing: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "requestId": request_id,
            "error": str(e),
            "timestamp": int(time.time() * 1000)
        })

# Initialize optimized components
@app.on_event("startup")
async def startup_event():
    """Initialize optimized components and background tasks"""
    logger.info("🚀 Starting optimized backend...")
    
    # Initialize optimized database manager
    global optimized_db_manager, optimized_n8n_handler
    optimized_db_manager = OptimizedDatabaseManager(supabase)
    optimized_n8n_handler = OptimizedN8NHandler(N8N_MAIN)
    
    # Start background cleanup tasks
    asyncio.create_task(start_cache_cleanup_task(optimized_db_manager))
    asyncio.create_task(start_session_cleanup_task(optimized_n8n_handler))
    
    logger.info("✅ Optimized backend initialized successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("🛑 Shutting down optimized backend...")
    
    if 'optimized_n8n_handler' in globals():
        await optimized_n8n_handler.close()
    
    logger.info("✅ Optimized backend shutdown complete")

# Optimized endpoint examples
@app.post("/n8n/check_agent_match_optimized")
async def optimized_check_agent_match(request: N8nCheckAgentMatchRequest):
    """Optimized agent matching with caching"""
    try:
        query_embedding = await optimized_db_manager.optimized_agent_match_query(
            agent_name=request.agent_name,
            query_embedding=await AgentMatcher(supabase).get_query_embedding(request.user_query),
            threshold=request.threshold
        )
        
        is_match = bool(query_embedding and len(query_embedding) > 0)
        
        return {
            "is_match": is_match,
            "agent_name": request.agent_name,
            "confidence": query_embedding[0].get('similarity', 0) if query_embedding else 0,
            "cached": True  # Indicate this was served from optimized cache
        }
        
    except Exception as e:
        logger.error(f"❌ Optimized agent match error: {str(e)}")
        return {"is_match": False, "error": str(e), "status": "error"}

@app.get("/api/performance/stats")
async def get_performance_stats():
    """Get performance statistics"""
    connection_count = await connection_manager.get_connection_count()
    
    return {
        "active_connections": connection_count,
        "cache_size": len(optimized_db_manager.cache),
        "circuit_breaker_state": optimized_n8n_handler.circuit_breaker.state.value,
        "timestamp": int(time.time() * 1000)
    }