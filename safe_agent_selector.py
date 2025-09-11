"""
Safe Agent Selector with Loop Prevention and Fallback Logic
"""
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SelectionStrategy(Enum):
    ORIGINAL_AGENT_VALID = "original_agent_valid"
    BEST_AGENT_FOUND = "best_agent_found"
    FALLBACK_REQUIRED = "fallback_required"
    ERROR_FALLBACK = "error_fallback"

@dataclass
class AgentSelectionResult:
    selected_agent: str
    strategy_used: SelectionStrategy
    confidence_score: float
    attempt_count: int
    fallback_reason: Optional[str] = None
    original_agent: Optional[str] = None
    processing_time_ms: int = 0

class SafeAgentSelector:
    """Safe agent selector with loop prevention and comprehensive fallbacks"""
    
    def __init__(self, supabase_client, agent_matcher):
        self.supabase = supabase_client
        self.agent_matcher = agent_matcher
        self.max_attempts = 3
        self.default_fallback_agent = "presaleskb"
        self.selection_cache = {}  # Cache recent selections
        self.cache_ttl = 300  # 5 minutes
    
    async def select_optimal_agent(
        self, 
        user_query: str, 
        requested_agent: str, 
        session_id: str,
        attempt_count: int = 0
    ) -> AgentSelectionResult:
        """
        Safely select the optimal agent with loop prevention and fallbacks
        """
        start_time = time.time()
        
        try:
            # Prevent infinite loops
            if attempt_count >= self.max_attempts:
                logger.warning(f"🚨 Max attempts ({self.max_attempts}) reached for session {session_id}")
                return AgentSelectionResult(
                    selected_agent=self.default_fallback_agent,
                    strategy_used=SelectionStrategy.FALLBACK_REQUIRED,
                    confidence_score=0.5,
                    attempt_count=attempt_count,
                    fallback_reason=f"Max attempts ({self.max_attempts}) exceeded",
                    original_agent=requested_agent,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # Check cache first to prevent repeated processing
            cache_key = f"{session_id}_{requested_agent}_{hash(user_query)}"
            cached_result = self._get_cached_selection(cache_key)
            if cached_result:
                logger.info(f"🎯 Using cached agent selection for session {session_id}")
                return cached_result
            
            # Step 1: Check if requested agent is suitable
            original_agent_suitable = await self._check_agent_suitability(
                requested_agent, user_query, threshold=0.2
            )
            
            if original_agent_suitable:
                result = AgentSelectionResult(
                    selected_agent=requested_agent,
                    strategy_used=SelectionStrategy.ORIGINAL_AGENT_VALID,
                    confidence_score=original_agent_suitable,
                    attempt_count=attempt_count,
                    original_agent=requested_agent,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
                self._cache_selection(cache_key, result)
                return result
            
            # Step 2: Find best alternative agents
            best_agents = await self._find_best_alternative_agents(
                user_query, exclude_agent=requested_agent
            )
            
            if best_agents and len(best_agents) > 0:
                selected_agent = best_agents[0]['agent_name']
                confidence = best_agents[0]['confidence']
                
                result = AgentSelectionResult(
                    selected_agent=selected_agent,
                    strategy_used=SelectionStrategy.BEST_AGENT_FOUND,
                    confidence_score=confidence,
                    attempt_count=attempt_count,
                    original_agent=requested_agent,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
                self._cache_selection(cache_key, result)
                return result
            
            # Step 3: Apply intelligent fallback logic
            fallback_agent = await self._apply_intelligent_fallback(
                user_query, requested_agent, session_id
            )
            
            result = AgentSelectionResult(
                selected_agent=fallback_agent,
                strategy_used=SelectionStrategy.FALLBACK_REQUIRED,
                confidence_score=0.3,  # Low confidence but functional
                attempt_count=attempt_count,
                fallback_reason="No suitable agents found, using intelligent fallback",
                original_agent=requested_agent,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            self._cache_selection(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in agent selection: {str(e)}")
            return AgentSelectionResult(
                selected_agent=self.default_fallback_agent,
                strategy_used=SelectionStrategy.ERROR_FALLBACK,
                confidence_score=0.1,
                attempt_count=attempt_count,
                fallback_reason=f"Error in selection process: {str(e)}",
                original_agent=requested_agent,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def _check_agent_suitability(
        self, 
        agent_name: str, 
        user_query: str, 
        threshold: float = 0.2
    ) -> Optional[float]:
        """Check if an agent is suitable for the query"""
        try:
            is_match = await self.agent_matcher.check_agent_match(
                agent_name=agent_name,
                user_query=user_query,
                threshold=threshold
            )
            
            if is_match:
                # Get confidence score from vector similarity
                query_embedding = await self.agent_matcher.get_query_embedding(user_query)
                result = self.supabase.rpc(
                    'match_documents',
                    {
                        'query_embedding': query_embedding,
                        'match_threshold': threshold,
                        'match_count': 1,
                        'filter_agent': agent_name
                    }
                ).execute()
                
                if result.data and len(result.data) > 0:
                    return result.data[0].get('similarity', 0.3)
                return 0.3  # Default confidence if match found but no similarity score
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error checking agent suitability: {str(e)}")
            return None
    
    async def _find_best_alternative_agents(
        self, 
        user_query: str, 
        exclude_agent: str = None
    ) -> List[Dict]:
        """Find best alternative agents excluding the current one"""
        try:
            best_agents = await self.agent_matcher.find_best_agents(
                user_query=user_query,
                top_n=3
            )
            
            # Filter out the excluded agent
            if exclude_agent:
                best_agents = [
                    agent for agent in best_agents 
                    if agent.get('agent_name') != exclude_agent
                ]
            
            # Add confidence scores and validate agents exist
            validated_agents = []
            for agent in best_agents:
                agent_name = agent.get('agent_name')
                if agent_name and await self._validate_agent_exists(agent_name):
                    # Add confidence score based on similarity
                    confidence = agent.get('similarity', 0.2)
                    validated_agents.append({
                        'agent_name': agent_name,
                        'confidence': confidence,
                        'reason': 'vector_similarity_match'
                    })
            
            return validated_agents
            
        except Exception as e:
            logger.error(f"❌ Error finding best alternative agents: {str(e)}")
            return []
    
    async def _validate_agent_exists(self, agent_name: str) -> bool:
        """Validate that an agent exists in the system"""
        try:
            result = self.supabase.table('agent_documents')\
                .select('id')\
                .eq('agent_name', agent_name)\
                .limit(1)\
                .execute()
            
            return bool(result.data and len(result.data) > 0)
            
        except Exception as e:
            logger.error(f"❌ Error validating agent existence: {str(e)}")
            return False
    
    async def _apply_intelligent_fallback(
        self, 
        user_query: str, 
        requested_agent: str, 
        session_id: str
    ) -> str:
        """Apply intelligent fallback logic based on query analysis"""
        query_lower = user_query.lower()
        
        # Business/sales related queries
        if any(keyword in query_lower for keyword in [
            'business', 'sales', 'revenue', 'pricing', 'cost', 'roi', 'budget'
        ]):
            return 'presaleskb'
        
        # Social media related queries
        elif any(keyword in query_lower for keyword in [
            'social', 'facebook', 'instagram', 'twitter', 'linkedin', 'marketing'
        ]):
            return 'socialmediakb'
        
        # Lead generation related queries
        elif any(keyword in query_lower for keyword in [
            'lead', 'prospect', 'customer', 'contact', 'demo', 'meeting'
        ]):
            return 'leadgenkb'
        
        # Default fallback
        else:
            logger.info(f"🔄 Using default fallback agent for session {session_id}")
            return self.default_fallback_agent
    
    def _get_cached_selection(self, cache_key: str) -> Optional[AgentSelectionResult]:
        """Get cached agent selection if still valid"""
        cached = self.selection_cache.get(cache_key)
        if cached and (time.time() - cached['timestamp']) < self.cache_ttl:
            return cached['result']
        elif cached:
            del self.selection_cache[cache_key]
        return None
    
    def _cache_selection(self, cache_key: str, result: AgentSelectionResult):
        """Cache agent selection result"""
        self.selection_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        # Cleanup old cache entries (simple LRU)
        if len(self.selection_cache) > 1000:
            oldest_key = min(
                self.selection_cache.keys(),
                key=lambda k: self.selection_cache[k]['timestamp']
            )
            del self.selection_cache[oldest_key]

# Integration with main.py
async def safe_agent_selection_endpoint(request_data: Dict, supabase_client=None, agent_matcher_instance=None) -> Dict:
    """
    Safe agent selection endpoint for n8n integration
    """
    try:
        # Use provided instances or raise error if not provided
        if not supabase_client or not agent_matcher_instance:
            raise ValueError("supabase_client and agent_matcher_instance must be provided")
            
        selector = SafeAgentSelector(supabase_client, agent_matcher_instance)
        
        result = await selector.select_optimal_agent(
            user_query=request_data.get('user_query', ''),
            requested_agent=request_data.get('agent_name', 'presaleskb'),
            session_id=request_data.get('session_id', ''),
            attempt_count=request_data.get('attempt_count', 0)
        )
        
        return {
            "agent_name": result.selected_agent,  # Use agent_name for consistency
            "selected_agent": result.selected_agent,  # Keep both for compatibility
            "strategy_used": result.strategy_used.value,
            "confidence_score": result.confidence_score,
            "attempt_count": result.attempt_count,
            "fallback_reason": result.fallback_reason,
            "original_agent": result.original_agent,
            "processing_time_ms": result.processing_time_ms,
            "cache_hit": result.processing_time_ms < 50,  # Indicates cached result
            "success": True
        }
        
    except Exception as e:
        logger.error(f"❌ Safe agent selection failed: {str(e)}")
        return {
            "agent_name": "presaleskb",  # Use agent_name for consistency
            "selected_agent": "presaleskb",  # Keep both for compatibility
            "strategy_used": SelectionStrategy.ERROR_FALLBACK.value,
            "confidence_score": 0.1,
            "error": str(e),
            "success": False
        }