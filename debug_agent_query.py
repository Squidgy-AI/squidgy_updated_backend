#!/usr/bin/env python3
"""
Debug the agent query to see exactly what's failing
"""

import asyncio
import sys
import traceback
import logging
from dotenv import load_dotenv

# Set up logging to see errors
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

sys.path.append('/Users/somasekharaddakula/CascadeProjects/SquidgyFullStack/backend')

async def debug_agent_query():
    try:
        from main import (
            AgentKBQueryRequest, 
            dynamic_agent_kb_handler, 
            AgentMatcher, 
            supabase,
            get_optimized_client_context,
            get_optimized_agent_knowledge,
            build_enhanced_kb_context,
            check_missing_must_info
        )
        
        print("🔍 Starting step-by-step debugging...")
        
        # Test request
        request = AgentKBQueryRequest(
            user_id='test_user_123',
            user_mssg='I need help with social media marketing',
            agent='socialmediakb'
        )
        
        # Step 1: Test query embedding generation
        print("\n1️⃣ Testing query embedding generation...")
        try:
            matcher = AgentMatcher(supabase)
            query_embedding = await matcher.get_query_embedding(request.user_mssg)
            print(f"✅ Query embedding: {len(query_embedding) if query_embedding else 0} dimensions")
        except Exception as e:
            print(f"❌ Embedding error: {e}")
            traceback.print_exc()
            return
        
        # Step 2: Test agent context retrieval
        print("\n2️⃣ Testing agent context retrieval...")
        try:
            agent_context = await dynamic_agent_kb_handler.get_agent_context_from_kb(request.agent)
            print(f"✅ Agent context: {type(agent_context)} with {len(agent_context) if agent_context else 0} keys")
            if agent_context:
                print(f"   Keys: {list(agent_context.keys())}")
        except Exception as e:
            print(f"❌ Agent context error: {e}")
            traceback.print_exc()
            return
        
        # Step 3: Test optimized client context
        print("\n3️⃣ Testing optimized client context...")
        try:
            client_context = await get_optimized_client_context(request.user_id, query_embedding)
            print(f"✅ Client context: {type(client_context)} with {len(client_context) if client_context else 0} keys")
            if client_context:
                print(f"   Keys: {list(client_context.keys())}")
        except Exception as e:
            print(f"❌ Client context error: {e}")
            traceback.print_exc()
            # Continue with fallback
            client_context = {}
        
        # Step 4: Test optimized agent knowledge
        print("\n4️⃣ Testing optimized agent knowledge...")
        try:
            agent_knowledge = await get_optimized_agent_knowledge(request.agent, query_embedding)
            print(f"✅ Agent knowledge: {type(agent_knowledge)} with {len(agent_knowledge) if agent_knowledge else 0} keys")
            if agent_knowledge:
                print(f"   Keys: {list(agent_knowledge.keys())}")
        except Exception as e:
            print(f"❌ Agent knowledge error: {e}")
            traceback.print_exc()
            # Continue with fallback
            agent_knowledge = {}
        
        # Step 5: Test KB context building
        print("\n5️⃣ Testing KB context building...")
        try:
            kb_context = await build_enhanced_kb_context(
                request.user_id, 
                client_context, 
                agent_knowledge
            )
            print(f"✅ KB context: {type(kb_context)} with {len(kb_context) if kb_context else 0} keys")
            if kb_context:
                print(f"   Keys: {list(kb_context.keys())}")
                print(f"   Sources: {kb_context.get('sources', [])}")
        except Exception as e:
            print(f"❌ KB context error: {e}")
            traceback.print_exc()
            return
        
        # Step 6: Test missing info check
        print("\n6️⃣ Testing missing info check...")
        try:
            must_questions = agent_context.get('must_questions', [])
            missing_info = await check_missing_must_info(must_questions, kb_context, client_context)
            print(f"✅ Missing info check: {missing_info}")
        except Exception as e:
            print(f"❌ Missing info check error: {e}")
            traceback.print_exc()
            return
        
        # Step 7: Test analysis
        print("\n7️⃣ Testing query analysis...")
        try:
            analysis = await dynamic_agent_kb_handler.analyze_query_with_context(
                request.user_mssg,
                agent_context,
                client_context,
                kb_context
            )
            print(f"✅ Analysis: {analysis}")
        except Exception as e:
            print(f"❌ Analysis error: {e}")
            traceback.print_exc()
            return
        
        print("\n🎉 All steps completed successfully!")
        print("The issue might be in the response generation step.")
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(debug_agent_query())