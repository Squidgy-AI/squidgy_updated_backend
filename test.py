import requests
from datetime import datetime

def test_presaleskb_agent():
    """
    Test the n8n_main_req endpoint with presaleskb agent
    """
    # Backend URL with agent_name and session_id in path
    base_url = "https://n8n.theaiteam.uk/webhook-test/c2fcbad6-abc0-43af-8aa8-d1661ff4461d"
    #"https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d" - PROD
    #"https://n8n.theaiteam.uk/webhook-test/01ca0029-17f6-4c5f-a859-e4f44484a2c9"
    #"https://squidgy-back-919bc0659e35.herokuapp.com"
    
    # Test parameters
    user_id = "test_user_123"
    session_id = "test_session_456"
    agent_name = "presaleskb"
    
    # Endpoint URL with agent and session in path
    endpoint = base_url
    #f"{base_url}/n8n_main_req/{agent_name}/{session_id}"
    
    # Test message for presaleskb agent (pricing/sales related)
    test_message = "This is my website https://www.green-property.com/ , How can you help me??"
    #"I need a quote for automation services for my business"

    # payload = {
    #     "user_id": "test_user_123",
    #     "user_mssg": "I need you to analyse my website",
    #     "session_id": "test_session_456",
    #     "agent_name": "presaleskb",
    #     "timestamp_of_call_made": datetime.now().isoformat()
    # }
    
    # Request payload
    payload = {
        "user_id": user_id,
        "user_mssg": test_message,
        "session_id": session_id,
        "agent_name": agent_name,
        "timestamp_of_call_made": datetime.now().isoformat()
    }
    
    print(f"Testing endpoint: {endpoint}")
    print(f"Payload: {payload}")
    print("-" * 50)
    
    try:
        # Make the POST request
        response = requests.post(endpoint, json=payload)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print("\n\n")
            print(result)
            # print(f"Status: {result.get('status')}")
            # print(f"Agent: {result.get('agent_name')}")
            # print(f"Response: {result.get('agent_response')}")
            # print(f"Session ID: {result.get('session_id')}")
            # print(f"Request ID: {result.get('request_id')}")
            
            # # Check if website info was requested
            # if result.get('missing_info'):
            #     print(f"Missing info: {result.get('missing_info')}")
            
            return result
        else:
            print(f"❌ Request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None

def test_multiple_scenarios():
    """
    Test multiple scenarios with presaleskb agent
    """
    test_cases = [
        {
            "message": "What are your pricing plans?",
            "description": "Direct pricing inquiry"
        },
        {
            "message": "I need a quote for a website with 50 pages",
            "description": "Specific quote request"
        },
        {
            "message": "What's the ROI on your automation services?",
            "description": "ROI/investment question"
        },
        {
            "message": "My website is https://example.com and I need pricing",
            "description": "Message with website URL"
        }
    ]
    
    base_url = "https://n8n.theaiteam.uk/webhook-test/01ca0029-17f6-4c5f-a859-e4f44484a2c9"
    #"https://squidgy-back-919bc0659e35.herokuapp.com"
    user_id = "test_user_123"
    session_id = "test_session_789"
    agent_name = "presaleskb"
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"Test Case {i+1}: {test_case['description']}")
        print(f"{'='*60}")
        
        endpoint = base_url
        #f"{base_url}/n8n_main_req/{agent_name}/{session_id}"
        
        payload = {
            "user_id": user_id,
            "user_mssg": test_case["message"],
            "session_id": session_id,
            "agent_name": agent_name,
            "timestamp_of_call_made": datetime.now().isoformat()
        }
        
        try:
            response = requests.post(endpoint, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success!")
                print(f"Agent Response: {result.get('agent_response')[:100]}...")
                
                if result.get('status') == 'needs_info':
                    print(f"⚠️  Agent needs: {result.get('missing_info')}")
            else:
                print(f"❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Run single test
    print("Running single test for presaleskb agent...")
    result = test_presaleskb_agent()
    
    # Uncomment to run multiple test scenarios
    # print("\n\nRunning multiple test scenarios...")
    # test_multiple_scenarios()






# import requests

# def call_webhook(message, userid=None, sessionid=None, workflow="w1", agent="soma", tool="t1"):
#     """
#     Makes a POST request to the webhook endpoint.
    
#     Args:
#         message (str): The message to send to the webhook
#         userid (str, optional): The user ID parameter. Defaults to None.
#         sessionid (str, optional): The session ID parameter. Defaults to None.
#         workflow (str, optional): The workflow parameter. Defaults to "w1".
#         agent (str, optional): The agent parameter. Defaults to "soma".
#         tool (str, optional): The tool parameter. Defaults to "t1".
        
#     Returns:
#         dict: The JSON response from the webhook, or None if the request failed
#     """
#     base_url = "https://n8n.theaiteam.uk/webhook/01ca0029-17f6-4c5f-a859-e4f44484a2c9"
#     #"https://n8n.theaiteam.uk/webhook/agentshub"

#     params = {
#         "workflow": workflow,
#         "agent": agent,
#         "message": message,
#         "tool": tool
#     }
    
#     # Add optional parameters if provided
#     if userid is not None:
#         params["userid"] = userid
    
#     if sessionid is not None:
#         params["sessionid"] = sessionid
    
#     try:
#         # Make the POST request
#         response = requests.post(base_url, params=params)
        
#         # Check if the request was successful
#         if response.status_code == 200:
#             try:
#                 return response.json()
#             except requests.exceptions.JSONDecodeError:
#                 # Return text if not JSON
#                 return {"text": response.text}
#         else:
#             print(f"Request failed with status code: {response.status_code}")
#             print(f"Response: {response.text}")
#             return None
            
#     except requests.exceptions.RequestException as e:
#         print(f"Request error: {e}")
#         return None

# # Example usage
# if __name__ == "__main__":
#     result = call_webhook("hello", userid="user123", sessionid="sess456")
#     print(result)



# # main.py - Complete integration with conversational handler and vector search agent matching
# from typing import Dict, Any, Optional, AsyncGenerator, List, Tuple
# import httpx
# from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
# from fastapi.responses import StreamingResponse
# from pydantic import BaseModel
# import json
# import logging
# import time
# import uuid
# import asyncio
# from datetime import datetime
# from enum import Enum
# from supabase import create_client, Client
# import os
# import openai

# # Initialize FastAPI app
# app = FastAPI()
# logger = logging.getLogger(__name__)
# active_connections: Dict[str, WebSocket] = {}
# streaming_sessions: Dict[str, Dict[str, Any]] = {}

# # Environment variables
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# # Initialize Supabase client
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# # Models
# class N8nMainRequest(BaseModel):
#     user_id: str
#     user_mssg: str
#     session_id: str
#     agent_name: str
#     timestamp_of_call_made: Optional[str] = None

# class N8nResponse(BaseModel):
#     user_id: str
#     agent_name: str
#     agent_response: str
#     responses: List[Dict[str, Any]]
#     timestamp: str
#     status: str

# class StreamUpdate(BaseModel):
#     type: str
#     user_id: str
#     agent_name: Optional[str] = None
#     agent_names: Optional[str] = None
#     message: str
#     progress: int
#     agent_response: Optional[str] = None
#     metadata: dict

# class ConversationState(Enum):
#     INITIAL = "initial"
#     COLLECTING_INFO = "collecting_info"
#     PROCESSING = "processing"
#     COMPLETE = "complete"

# # Agent Matcher Class using Vector Search
# class AgentMatcher:
#     def __init__(self, supabase_client, openai_api_key: str = None):
#         self.supabase = supabase_client
#         self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
#         openai.api_key = self.openai_api_key
        
#     async def get_query_embedding(self, text: str) -> List[float]:
#         """Generate embedding for the query text using OpenAI"""
#         try:
#             response = openai.Embedding.create(
#                 model="text-embedding-3-small",
#                 input=text
#             )
#             return response['data'][0]['embedding']
#         except Exception as e:
#             logger.error(f"Error generating embedding: {str(e)}")
#             raise
    
#     async def check_agent_match(self, agent_name: str, user_query: str, threshold: float = 0.7) -> bool:
#         """
#         Function 1: Check if a specific agent matches the user query using vector similarity
        
#         Args:
#             agent_name: Name of the agent to check
#             user_query: User's query/message
#             threshold: Similarity threshold (0-1), default 0.7
            
#         Returns:
#             bool: True if agent is suitable for the query, False otherwise
#         """
#         try:
#             # Get embedding for the user query
#             query_embedding = await self.get_query_embedding(user_query)
            
#             # Perform similarity search for specific agent
#             result = self.supabase.rpc(
#                 'match_agent_documents',
#                 {
#                     'query_embedding': query_embedding,
#                     'match_threshold': threshold,
#                     'match_count': 1,
#                     'filter_agent': agent_name
#                 }
#             ).execute()
            
#             # If we found matching documents for this agent above threshold
#             return len(result.data) > 0 and result.data[0]['similarity'] >= threshold
            
#         except Exception as e:
#             logger.error(f"Error checking agent match: {str(e)}")
#             # Fallback to checking if agent exists
#             agent_check = self.supabase.table('agent_documents')\
#                 .select('id')\
#                 .eq('agent_name', agent_name)\
#                 .limit(1)\
#                 .execute()
#             return len(agent_check.data) > 0
    
#     async def find_best_agents(self, user_query: str, top_n: int = 3) -> List[Tuple[str, float]]:
#         """
#         Function 2: Find the best matching agents for a user query using vector similarity
        
#         Args:
#             user_query: User's query/message
#             top_n: Number of top agents to return (default: 3)
            
#         Returns:
#             List of tuples (agent_name, match_percentage) sorted by similarity
#         """
#         try:
#             # Get embedding for the user query
#             query_embedding = await self.get_query_embedding(user_query)
            
#             # Perform similarity search across all agents
#             result = self.supabase.rpc(
#                 'match_agents_by_similarity',
#                 {
#                     'query_embedding': query_embedding,
#                     'match_threshold': 0.5,  # Lower threshold to get more results
#                     'match_count': top_n * 5  # Get more results to ensure we have enough unique agents
#                 }
#             ).execute()
            
#             if not result.data:
#                 # Fallback to default agent
#                 return [('re-engage', 50.0)]
            
#             # Group by agent and take highest similarity
#             agent_scores = {}
#             for item in result.data:
#                 agent_name = item['agent_name']
#                 similarity = item['similarity'] * 100  # Convert to percentage
                
#                 if agent_name not in agent_scores or similarity > agent_scores[agent_name]:
#                     agent_scores[agent_name] = similarity
            
#             # Sort by similarity and return top N
#             sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
#             return sorted_agents[:top_n]
            
#         except Exception as e:
#             logger.error(f"Error finding best agents: {str(e)}")
#             # Fallback to default agent
#             return [('re-engage', 50.0)]
    
#     async def get_recommended_agent(self, user_query: str) -> str:
#         """Get the single best recommended agent for a query"""
#         best_agents = await self.find_best_agents(user_query, top_n=1)
        
#         if best_agents and best_agents[0][1] >= 60:  # If top agent has at least 60% match
#             return best_agents[0][0]
        
#         # Default to re-engage for general queries
#         return 're-engage'

# # Initialize agent matcher
# agent_matcher = AgentMatcher(supabase_client=supabase)

# # Conversational Handler Class
# class ConversationalHandler:
#     def __init__(self, supabase_client, n8n_webhook_url: str):
#         self.supabase = supabase_client
#         self.n8n_url = n8n_webhook_url
#         self.conversation_states: Dict[str, Dict[str, Any]] = {}
        
#     async def get_conversation_context(self, session_id: str, user_id: str) -> Dict[str, Any]:
#         """Get conversation context from Supabase"""
#         try:
#             result = self.supabase.rpc('get_conversation_context', {
#                 'p_session_id': session_id,
#                 'p_user_id': user_id
#             }).execute()
            
#             if result.data:
#                 return result.data[0]
#             return {
#                 'session_id': session_id,
#                 'user_id': user_id,
#                 'website_data': None,
#                 'client_niche': None,
#                 'conversation_history': []
#             }
#         except Exception as e:
#             logger.error(f"Error getting conversation context: {str(e)}")
#             return {}
    
#     async def check_agent_requirements(self, agent_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
#         """Check what information is missing for the agent"""
#         missing_info = []
        
#         # Define requirements per agent
#         agent_requirements = {
#             'presaleskb': {
#                 'website': lambda ctx: ctx.get('website_data') is not None,
#                 'niche': lambda ctx: ctx.get('client_niche') is not None
#             },
#             'manager': {
#                 'website': lambda ctx: ctx.get('website_data') is not None
#             },
#             're-engage': {
#                 'website': lambda ctx: ctx.get('website_data') is not None
#             }
#         }
        
#         if agent_name in agent_requirements:
#             for req_name, check_func in agent_requirements[agent_name].items():
#                 if not check_func(context):
#                     missing_info.append(req_name)
        
#         return {
#             'has_all_required': len(missing_info) == 0,
#             'missing_info': missing_info
#         }
    
#     async def analyze_user_intent(self, user_message: str, agent_name: str) -> Dict[str, Any]:
#         """Analyze what the user is asking for"""
#         message_lower = user_message.lower()
        
#         # Check if this is a follow-up response
#         if any(keyword in message_lower for keyword in ['http://', 'https://', '.com', '.org', '.net']):
#             return {'type': 'website_provided', 'value': user_message.strip()}
        
#         # Check if user is providing niche information
#         niche_keywords = ['we are', 'our business', 'we specialize', 'our company', 'we do', 'our focus']
#         if any(keyword in message_lower for keyword in niche_keywords):
#             return {'type': 'niche_provided', 'value': user_message.strip()}
        
#         # Check if asking about pricing/quotes (needs website info)
#         pricing_keywords = ['price', 'cost', 'quote', 'roi', 'investment', 'budget']
#         needs_website = any(keyword in message_lower for keyword in pricing_keywords)
        
#         return {
#             'type': 'general_query',
#             'needs_website': needs_website,
#             'original_message': user_message
#         }
    
#     async def generate_contextual_prompt(self, user_message: str, missing_info: List[str], context: Dict[str, Any]) -> str:
#         """Generate a prompt that will make the agent ask for missing info naturally"""
#         conversation_history = context.get('conversation_history', [])
        
#         # Build conversation context
#         history_text = "\n".join([f"{msg['role']}: {msg['message']}" for msg in conversation_history[-5:]])
        
#         # Create a prompt that instructs the agent to collect missing info
#         prompt = f"""Previous conversation:
# {history_text}

# User's current message: {user_message}

# You need to collect the following information before you can fully answer: {', '.join(missing_info)}

# Instructions:
# 1. First acknowledge the user's question
# 2. If you can provide partial information, do so
# 3. Then naturally ask for the missing information
# 4. Explain why you need this information
# 5. Be conversational and helpful

# Missing information needed:
# {chr(10).join([f"- {info}: " + self.get_info_description(info) for info in missing_info])}

# Respond naturally while collecting this information."""
        
#         return prompt
    
#     def get_info_description(self, info_type: str) -> str:
#         """Get description for each type of information"""
#         descriptions = {
#             'website': "Company website URL to understand their business and provide accurate quotes",
#             'niche': "Business niche or industry focus to tailor recommendations",
#             'property_address': "Property address for location-specific analysis",
#             'budget': "Budget range to suggest appropriate solutions",
#             'timeline': "Implementation timeline to plan accordingly"
#         }
#         return descriptions.get(info_type, f"{info_type} information")
    
#     async def process_follow_up_info(self, session_id: str, user_id: str, info_type: str, info_value: str):
#         """Process and store follow-up information"""
#         try:
#             if info_type == 'website':
#                 # Analyze website using Perplexity
#                 analysis = await self.analyze_website_with_perplexity(info_value)
                
#                 # Store in website_data table
#                 self.supabase.table('website_data').upsert({
#                     'session_id': session_id,
#                     'url': info_value,
#                     'analysis': json.dumps(analysis) if analysis else None
#                 }).execute()
                
#                 # Extract niche from analysis if available
#                 if analysis and 'niche' in analysis:
#                     self.supabase.table('conversation_context').upsert({
#                         'session_id': session_id,
#                         'user_id': user_id,
#                         'client_niche': analysis['niche']
#                     }).execute()
            
#             elif info_type == 'niche':
#                 # Update conversation context
#                 self.supabase.table('conversation_context').upsert({
#                     'session_id': session_id,
#                     'user_id': user_id,
#                     'client_niche': info_value
#                 }).execute()
            
#             # Update other fields as needed
#             else:
#                 self.supabase.rpc('update_conversation_context', {
#                     'p_session_id': session_id,
#                     'p_user_id': user_id,
#                     'p_field': info_type,
#                     'p_value': info_value
#                 }).execute()
                
#         except Exception as e:
#             logger.error(f"Error processing follow-up info: {str(e)}")
    
#     async def analyze_website_with_perplexity(self, url: str) -> Optional[Dict[str, Any]]:
#         """Analyze website using Perplexity API"""
#         try:
#             headers = {
#                 "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
#                 "Content-Type": "application/json"
#             }
            
#             prompt = f"""Please analyze the website {url} and provide a summary in exactly this format:
# --- *Company name*: [Extract company name]
# --- *Website*: {url}
# --- *Contact Information*: [Any available contact details]
# --- *Description*: [2-3 sentence summary of what the company does]
# --- *Tags*: [Main business categories, separated by periods]
# --- *Takeaways*: [Key business value propositions]
# --- *Niche*: [Specific market focus or specialty]"""
            
#             async with httpx.AsyncClient() as client:
#                 response = await client.post(
#                     "https://api.perplexity.ai/chat/completions",
#                     headers=headers,
#                     json={
#                         "model": "sonar-reasoning-pro",
#                         "messages": [{"role": "user", "content": prompt}],
#                         "max_tokens": 1000
#                     }
#                 )
                
#                 if response.status_code == 200:
#                     result = response.json()
#                     analysis_text = result["choices"][0]["message"]["content"]
                    
#                     # Parse the analysis into structured data
#                     parsed = self.parse_perplexity_analysis(analysis_text)
#                     return parsed
                    
#         except Exception as e:
#             logger.error(f"Error analyzing website: {str(e)}")
#             return None
    
#     def parse_perplexity_analysis(self, analysis_text: str) -> Dict[str, Any]:
#         """Parse Perplexity analysis into structured format"""
#         parsed = {}
#         lines = analysis_text.split('\n')
        
#         for line in lines:
#             if '*Company name*:' in line:
#                 parsed['company_name'] = line.split(':', 1)[1].strip()
#             elif '*Description*:' in line:
#                 parsed['description'] = line.split(':', 1)[1].strip()
#             elif '*Niche*:' in line:
#                 parsed['niche'] = line.split(':', 1)[1].strip()
#             elif '*Tags*:' in line:
#                 parsed['tags'] = line.split(':', 1)[1].strip()
        
#         return parsed
    
#     async def handle_message(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
#         """Main handler for processing messages with conversational flow"""
#         user_id = request_data['user_id']
#         session_id = request_data['session_id']
#         user_message = request_data['user_mssg']
#         agent_name = request_data['agent_name']
        
#         # Auto-select best agent if not specified or if 'auto' is passed
#         if not agent_name or agent_name == 'auto':
#             agent_name = await agent_matcher.get_recommended_agent(user_message)
#             request_data['agent_name'] = agent_name
#             request_data['_auto_selected_agent'] = True
#             logger.info(f"Auto-selected agent: {agent_name} for query: {user_message}")
        
#         # Validate if the selected agent is appropriate
#         else:
#             is_appropriate = await agent_matcher.check_agent_match(agent_name, user_message)
#             if not is_appropriate:
#                 # Get better recommendations
#                 better_agents = await agent_matcher.find_best_agents(user_message, top_n=1)
#                 if better_agents and better_agents[0][1] > 70:
#                     request_data['_suggested_agent'] = better_agents[0][0]
#                     request_data['_suggestion_confidence'] = better_agents[0][1]
#                     logger.warning(f"Agent mismatch: {agent_name} may not be optimal. Suggested: {better_agents[0][0]}")
        
#         # Get conversation context
#         context = await self.get_conversation_context(session_id, user_id)
        
#         # Analyze user intent
#         intent = await self.analyze_user_intent(user_message, agent_name)
        
#         # Handle follow-up information
#         if intent['type'] in ['website_provided', 'niche_provided']:
#             info_type = 'website' if intent['type'] == 'website_provided' else 'niche'
#             await self.process_follow_up_info(session_id, user_id, info_type, intent['value'])
            
#             # Update context after processing
#             context = await self.get_conversation_context(session_id, user_id)
        
#         # Check agent requirements
#         requirements = await self.check_agent_requirements(agent_name, context)
        
#         # Prepare n8n payload
#         n8n_payload = request_data.copy()
        
#         # If missing critical info, modify the prompt to collect it
#         if not requirements['has_all_required'] and intent['type'] == 'general_query':
#             # Add context to make agent ask for missing info
#             contextual_prompt = await self.generate_contextual_prompt(
#                 user_message, 
#                 requirements['missing_info'], 
#                 context
#             )
#             n8n_payload['user_mssg'] = contextual_prompt
#             n8n_payload['_original_message'] = user_message
#             n8n_payload['_missing_info'] = requirements['missing_info']
        
#         # Return the prepared payload
#         return n8n_payload
    
#     async def save_to_history(self, session_id: str, user_id: str, user_message: str, agent_response: str):
#         """Save messages to chat history"""
#         try:
#             # Save user message
#             supabase.table('chat_history').insert({
#                 'session_id': session_id,
#                 'user_id': user_id,
#                 'sender': 'user',
#                 'message': user_message,
#                 'timestamp': datetime.now().isoformat()
#             }).execute()
            
#             # Save agent response
#             if agent_response:
#                 supabase.table('chat_history').insert({
#                     'session_id': session_id,
#                     'user_id': user_id,
#                     'sender': 'agent',
#                     'message': agent_response,
#                     'timestamp': datetime.now().isoformat()
#                 }).execute()
                
#         except Exception as e:
#             logger.error(f"Error saving to history: {str(e)}")\
            

# # Add these models and endpoints to your main.py

# # Models for the new endpoint
# class AgentKBQueryRequest(BaseModel):
#     user_id: str
#     user_mssg: str
#     agent: str

# class AgentKBQueryResponse(BaseModel):
#     user_id: str
#     agent: str
#     response_type: str  # "direct_answer", "needs_tools", "needs_info"
#     agent_response: Optional[str] = None
#     required_tools: Optional[List[Dict[str, Any]]] = None
#     follow_up_questions: Optional[List[str]] = None
#     missing_information: Optional[List[Dict[str, Any]]] = None
#     confidence_score: float
#     kb_context_used: bool
#     status: str

# class DynamicAgentKBHandler:
#     """Handler that dynamically loads agent context from KB"""
    
#     def __init__(self, supabase_client, openai_api_key: str = None):
#         self.supabase = supabase_client
#         self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
#         openai.api_key = self.openai_api_key
        
#     async def get_agent_context_from_kb(self, agent_name: str) -> Dict[str, Any]:
#         """Extract agent context from agent_documents table"""
#         try:
#             # Get agent documents
#             result = self.supabase.table('agent_documents')\
#                 .select('content, metadata')\
#                 .eq('agent_name', agent_name)\
#                 .order('metadata->chunk_index')\
#                 .execute()
            
#             if not result.data:
#                 return {
#                     'role': 'AI Assistant',
#                     'tools': [],
#                     'must_questions': [],
#                     'expertise': []
#                 }
            
#             # Combine all chunks
#             full_content = '\n'.join([doc['content'] for doc in result.data])
            
#             # Extract information from content
#             agent_context = {
#                 'role': self._extract_role(full_content),
#                 'tools': self._extract_tools(full_content),
#                 'must_questions': self._extract_must_questions(full_content),
#                 'expertise': self._extract_expertise(full_content),
#                 'full_content': full_content
#             }
            
#             return agent_context
            
#         except Exception as e:
#             logger.error(f"Error getting agent context from KB: {str(e)}")
#             return {
#                 'role': 'AI Assistant',
#                 'tools': [],
#                 'must_questions': [],
#                 'expertise': []
#             }
    
#     def _extract_role(self, content: str) -> str:
#         """Extract agent role from content"""
#         lines = content.split('\n')
#         for line in lines:
#             if 'You are' in line and ('named' in line or 'expert' in line or 'specialist' in line):
#                 return line.strip()
#         return 'AI Assistant'
    
#     def _extract_tools(self, content: str) -> List[Dict[str, str]]:
#         """Extract tools from agent KB content"""
#         tools = []
#         in_tools_section = False
        
#         for line in content.split('\n'):
#             if 'Tools_names:' in line or 'Tools:' in line:
#                 in_tools_section = True
#                 continue
            
#             if in_tools_section and line.strip():
#                 if line.strip().startswith('-'):
#                     # Parse tool line like: - analyze_with_perplexity(url) for business analysis
#                     tool_line = line.strip()[1:].strip()
#                     if '(' in tool_line and ')' in tool_line:
#                         # Extract function name and description
#                         func_start = tool_line.find('(')
#                         func_name = tool_line[:func_start]
                        
#                         # Find description after 'for' or 'to'
#                         desc_start = tool_line.find(')') + 1
#                         description = tool_line[desc_start:].strip()
#                         if description.startswith('for '):
#                             description = description[4:]
#                         elif description.startswith('to '):
#                             description = description[3:]
                        
#                         tools.append({
#                             'name': func_name.strip(),
#                             'description': description.strip()
#                         })
#                 elif not line.startswith(' ') and line.strip():
#                     # End of tools section
#                     in_tools_section = False
        
#         return tools
    
#     def _extract_must_questions(self, content: str) -> List[str]:
#         """Extract MUST questions from agent KB"""
#         must_questions = []
#         in_must_section = False
        
#         for line in content.split('\n'):
#             if 'MUST Questions:' in line or 'Required Information:' in line:
#                 in_must_section = True
#                 continue
            
#             if in_must_section and line.strip():
#                 if line.strip()[0].isdigit() and '.' in line:
#                     # Extract numbered questions
#                     question = line.split('.', 1)[1].strip()
#                     must_questions.append(question)
#                 elif not line.startswith(' ') and line.strip() and not line.strip()[0].isdigit():
#                     # End of MUST section
#                     in_must_section = False
        
#         return must_questions
    
#     def _extract_expertise(self, content: str) -> List[str]:
#         """Extract expertise areas from content"""
#         expertise = []
        
#         # Look for numbered lists or bullet points describing capabilities
#         for line in content.split('\n'):
#             if line.strip() and (
#                 ('expertise' in line.lower() and ':' in line) or
#                 ('role combines' in line.lower()) or
#                 ('responsibilities' in line.lower())
#             ):
#                 # Process the next few lines
#                 continue
            
#             # Extract numbered expertise items
#             if line.strip() and line.strip()[0].isdigit() and '.' in line:
#                 if any(keyword in line.lower() for keyword in ['analyze', 'present', 'explain', 'collect', 'handle', 'discuss']):
#                     expertise_item = line.split('.', 1)[1].strip()
#                     expertise.append(expertise_item)
        
#         return expertise[:5]  # Limit to top 5
    
#     async def get_client_industry_context(self, user_id: str) -> Dict[str, Any]:
#         """Get client's industry/niche from their KB"""
#         try:
#             # Get client KB
#             kb_data = await client_kb_manager.get_client_kb(user_id, 'website_info')
            
#             if not kb_data:
#                 return {
#                     'industry': 'Unknown',
#                     'niche': 'Unknown',
#                     'company_type': 'Unknown',
#                     'jargon': []
#                 }
            
#             content = kb_data.get('content', {})
#             website_info = content.get('website_info', {})
            
#             # Extract industry context
#             niche = website_info.get('niche', 'Unknown')
#             tags = website_info.get('tags', '')
#             description = website_info.get('description', '')
            
#             # Generate industry-specific jargon using AI
#             industry_context = await self._generate_industry_jargon(niche, tags, description)
            
#             return {
#                 'industry': niche,
#                 'niche': niche,
#                 'company_type': self._determine_company_type(tags, description),
#                 'jargon': industry_context.get('jargon', []),
#                 'key_metrics': industry_context.get('metrics', [])
#             }
            
#         except Exception as e:
#             logger.error(f"Error getting client industry context: {str(e)}")
#             return {
#                 'industry': 'Unknown',
#                 'niche': 'Unknown',
#                 'company_type': 'Unknown',
#                 'jargon': []
#             }
    
#     def _determine_company_type(self, tags: str, description: str) -> str:
#         """Determine company type from tags and description"""
#         combined_text = f"{tags} {description}".lower()
        
#         if any(term in combined_text for term in ['saas', 'software', 'app', 'platform']):
#             return 'Technology/Software'
#         elif any(term in combined_text for term in ['retail', 'store', 'shop', 'commerce']):
#             return 'Retail/E-commerce'
#         elif any(term in combined_text for term in ['consulting', 'agency', 'services']):
#             return 'Professional Services'
#         elif any(term in combined_text for term in ['manufacturing', 'production', 'factory']):
#             return 'Manufacturing'
#         elif any(term in combined_text for term in ['real estate', 'property', 'realty']):
#             return 'Real Estate'
#         else:
#             return 'General Business'
    
#     async def _generate_industry_jargon(self, niche: str, tags: str, description: str) -> Dict[str, Any]:
#         """Use AI to generate industry-specific jargon and metrics"""
#         try:
#             prompt = f"""
# Given this business context:
# - Niche: {niche}
# - Tags: {tags}
# - Description: {description}

# Generate industry-specific terminology and metrics that would be relevant.
# Return as JSON with two arrays:
# 1. "jargon": 10-15 industry-specific terms
# 2. "metrics": 5-8 key performance indicators for this industry

# Example format:
# {{
#     "jargon": ["term1", "term2", ...],
#     "metrics": ["metric1", "metric2", ...]
# }}
# """
            
#             response = openai.ChatCompletion.create(
#                 model="gpt-3.5-turbo",
#                 messages=[
#                     {"role": "system", "content": "You are an industry expert. Generate relevant terminology."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 temperature=0.3,
#                 max_tokens=300
#             )
            
#             return json.loads(response.choices[0].message.content)
            
#         except Exception as e:
#             logger.error(f"Error generating industry jargon: {str(e)}")
#             return {'jargon': [], 'metrics': []}
    
#     async def analyze_query_with_context(self, user_query: str, agent_context: Dict[str, Any], 
#                                        client_context: Dict[str, Any], kb_context: Dict[str, Any]) -> Dict[str, Any]:
#         """Analyze query using both agent and client context"""
        
#         # Build comprehensive analysis prompt
#         analysis_prompt = f"""
# You are acting as: {agent_context.get('role', 'AI Assistant')}

# Agent Capabilities:
# - Available tools: {', '.join([t['name'] for t in agent_context.get('tools', [])])}
# - Must have information: {', '.join(agent_context.get('must_questions', []))}
# - Expertise areas: {', '.join(agent_context.get('expertise', []))}

# Client Context:
# - Industry/Niche: {client_context.get('industry', 'Unknown')}
# - Company Type: {client_context.get('company_type', 'Unknown')}
# - Current KB Status: {'Complete' if kb_context.get('website_url') else 'Missing website info'}

# User Query: "{user_query}"

# Analyze and determine:
# 1. Can this query be answered with current information? (yes/no)
# 2. What specific information is missing from MUST questions?
# 3. Which tools would be needed to answer this query?
# 4. How confident are you in understanding this query? (0-1)
# 5. Does this query match the agent's expertise? (yes/no)

# Consider the client's industry context and use appropriate terminology.

# Return as JSON with keys: can_answer, missing_info, required_tools, confidence, in_expertise
# """
        
#         try:
#             response = openai.ChatCompletion.create(
#                 model="gpt-4",
#                 messages=[
#                     {"role": "system", "content": "You are an expert analyst. Return valid JSON only."},
#                     {"role": "user", "content": analysis_prompt}
#                 ],
#                 temperature=0.3,
#                 max_tokens=400
#             )
            
#             return json.loads(response.choices[0].message.content)
            
#         except Exception as e:
#             logger.error(f"Error analyzing query: {str(e)}")
#             return {
#                 "can_answer": False,
#                 "missing_info": ["Unable to analyze query"],
#                 "required_tools": [],
#                 "confidence": 0.5,
#                 "in_expertise": True
#             }
    
#     async def generate_contextual_response(self, user_query: str, agent_context: Dict[str, Any],
#                                          client_context: Dict[str, Any], kb_context: Dict[str, Any],
#                                          tools_to_use: List[Dict[str, Any]]) -> str:
#         """Generate response using full context"""
        
#         response_prompt = f"""
# You are: {agent_context.get('role', 'AI Assistant')}

# Your full context and instructions:
# {agent_context.get('full_content', '')[:1000]}  # First 1000 chars of agent KB

# Client Information:
# - Company: {kb_context.get('company_name', 'Not specified')}
# - Industry: {client_context.get('industry', 'Not specified')}
# - Website: {kb_context.get('website_url', 'Not provided')}
# - Services: {', '.join(kb_context.get('services', []) or ['Not specified'])}

# Industry-specific terminology to use when relevant:
# {', '.join(client_context.get('jargon', [])[:10])}

# User Query: "{user_query}"

# Tools you will use:
# {chr(10).join([f"- {tool['name']}: {tool['description']}" for tool in tools_to_use])}

# Instructions:
# 1. Respond according to your role and expertise
# 2. Use industry-appropriate language for their {client_context.get('industry')} business
# 3. If using tools, explain what each will do
# 4. Be specific to their business context
# 5. Follow any specific instructions from your agent KB

# Generate your response:
# """
        
#         try:
#             response = openai.ChatCompletion.create(
#                 model="gpt-4",
#                 messages=[
#                     {"role": "system", "content": "You are an expert assistant. Be professional and helpful."},
#                     {"role": "user", "content": response_prompt}
#                 ],
#                 temperature=0.7,
#                 max_tokens=800
#             )
            
#             return response.choices[0].message.content
            
#         except Exception as e:
#             logger.error(f"Error generating response: {str(e)}")
#             return "I apologize, but I'm having trouble generating a response. Please try again."
    
#     async def generate_contextual_questions(self, user_query: str, agent_context: Dict[str, Any],
#                                           missing_info: List[str], client_context: Dict[str, Any]) -> List[str]:
#         """Generate follow-up questions based on context"""
        
#         questions_prompt = f"""
# As {agent_context.get('role', 'AI Assistant')}, you need to collect missing information.

# MUST have information for this agent:
# {chr(10).join([f"- {q}" for q in agent_context.get('must_questions', [])])}

# Currently missing: {', '.join(missing_info)}
# Client's industry: {client_context.get('industry', 'Unknown')}
# User asked: "{user_query}"

# Generate 2-3 natural follow-up questions that:
# 1. Collect the missing MUST information
# 2. Are relevant to their {client_context.get('industry')} industry
# 3. Explain why you need this information
# 4. Use appropriate industry terminology

# Return as a JSON array of question strings.
# """
        
#         try:
#             response = openai.ChatCompletion.create(
#                 model="gpt-3.5-turbo",
#                 messages=[
#                     {"role": "system", "content": "Generate professional follow-up questions. Return only JSON array."},
#                     {"role": "user", "content": questions_prompt}
#                 ],
#                 temperature=0.5,
#                 max_tokens=300
#             )
            
#             return json.loads(response.choices[0].message.content)[:3]
            
#         except Exception as e:
#             logger.error(f"Error generating questions: {str(e)}")
#             return ["Could you provide more details about your requirements?"]

# # Initialize the dynamic handler
# dynamic_agent_kb_handler = DynamicAgentKBHandler(supabase_client=supabase)

# # Main endpoint for agent KB queries
# @app.post("/api/agent/query")
# async def agent_kb_query(request: AgentKBQueryRequest):
#     """
#     Query agent with user message using dynamic KB context
    
#     This endpoint:
#     1. Loads agent context from agent_documents
#     2. Loads client context from client_kb
#     3. Analyzes query requirements
#     4. Provides appropriate response or asks follow-up questions
#     """
#     try:
#         # Get agent context from KB
#         agent_context = await dynamic_agent_kb_handler.get_agent_context_from_kb(request.agent)
        
#         # Get client industry context
#         client_context = await dynamic_agent_kb_handler.get_client_industry_context(request.user_id)
        
#         # Get client KB data
#         kb_data = await client_kb_manager.get_client_kb(request.user_id, 'website_info')
        
#         kb_context = {}
#         if kb_data:
#             content = kb_data.get('content', {})
#             website_info = content.get('website_info', {})
#             chat_insights = content.get('chat_insights', {})
            
#             kb_context = {
#                 'company_name': website_info.get('company_name'),
#                 'website_url': website_info.get('url'),
#                 'services': website_info.get('services', []),
#                 'description': website_info.get('description'),
#                 'topics': chat_insights.get('topics', []),
#                 'interaction_count': content.get('interaction_history', {}).get('total_messages', 0)
#             }
        
#         # Check MUST questions from agent KB
#         must_questions = agent_context.get('must_questions', [])
#         missing_must_info = []
        
#         for must_q in must_questions:
#             if 'website' in must_q.lower() and not kb_context.get('website_url'):
#                 missing_must_info.append('website_url')
#             elif 'niche' in must_q.lower() and client_context.get('niche') == 'Unknown':
#                 missing_must_info.append('client_niche')
#             elif 'property address' in must_q.lower() and not kb_context.get('property_address'):
#                 missing_must_info.append('property_address')
        
#         # If critical info is missing, ask for it first
#         if 'website_url' in missing_must_info:
#             follow_up_questions = await dynamic_agent_kb_handler.generate_contextual_questions(
#                 request.user_mssg,
#                 agent_context,
#                 ['website_url'],
#                 client_context
#             )
            
#             return AgentKBQueryResponse(
#                 user_id=request.user_id,
#                 agent=request.agent,
#                 response_type="needs_info",
#                 follow_up_questions=follow_up_questions,
#                 missing_information=[{
#                     "field": "website_url",
#                     "reason": "Required by agent's MUST questions to provide accurate analysis",
#                     "priority": "critical"
#                 }],
#                 confidence_score=0.9,
#                 kb_context_used=False,
#                 status="missing_critical_info"
#             )
        
#         # Analyze query with full context
#         analysis = await dynamic_agent_kb_handler.analyze_query_with_context(
#             request.user_mssg,
#             agent_context,
#             client_context,
#             kb_context
#         )
        
#         # Determine response based on analysis
#         if analysis.get('can_answer') and analysis.get('confidence', 0) > 0.7:
#             # Get required tools from agent's available tools
#             available_tools = agent_context.get('tools', [])
#             required_tool_names = analysis.get('required_tools', [])
#             tools_to_use = [t for t in available_tools if t['name'] in required_tool_names]
            
#             # Generate contextual response
#             agent_response = await dynamic_agent_kb_handler.generate_contextual_response(
#                 request.user_mssg,
#                 agent_context,
#                 client_context,
#                 kb_context,
#                 tools_to_use
#             )
            
#             return AgentKBQueryResponse(
#                 user_id=request.user_id,
#                 agent=request.agent,
#                 response_type="needs_tools" if tools_to_use else "direct_answer",
#                 agent_response=agent_response,
#                 required_tools=tools_to_use if tools_to_use else None,
#                 confidence_score=analysis.get('confidence', 0.8),
#                 kb_context_used=bool(kb_context.get('company_name')),
#                 status="success"
#             )
        
#         else:
#             # Need more information
#             all_missing = missing_must_info + analysis.get('missing_info', [])
            
#             follow_up_questions = await dynamic_agent_kb_handler.generate_contextual_questions(
#                 request.user_mssg,
#                 agent_context,
#                 all_missing,
#                 client_context
#             )
            
#             # Format missing information
#             missing_info_formatted = []
#             for info in all_missing:
#                 missing_info_formatted.append({
#                     "field": info,
#                     "reason": f"Required by {request.agent} agent to provide accurate response",
#                     "priority": "high" if info in missing_must_info else "medium"
#                 })
            
#             return AgentKBQueryResponse(
#                 user_id=request.user_id,
#                 agent=request.agent,
#                 response_type="needs_info",
#                 follow_up_questions=follow_up_questions,
#                 missing_information=missing_info_formatted,
#                 confidence_score=analysis.get('confidence', 0.5),
#                 kb_context_used=bool(kb_context.get('company_name')),
#                 status="needs_more_info"
#             )
            
#     except Exception as e:
#         logger.error(f"Error in agent_kb_query: {str(e)}")
#         return AgentKBQueryResponse(
#             user_id=request.user_id,
#             agent=request.agent,
#             response_type="error",
#             agent_response="I encountered an error processing your request. Please try again.",
#             confidence_score=0.0,
#             kb_context_used=False,
#             status="error"
#         )

# # N8N webhook version
# @app.post("/n8n/agent/query")
# async def n8n_agent_kb_query(request: Dict[str, Any]):
#     """
#     N8N-compatible version of agent KB query endpoint
    
#     Expected payload:
#     {
#         "user_id": "user123",
#         "user_mssg": "I need a pricing quote for automation",
#         "agent": "presaleskb"
#     }
#     """
#     try:
#         # Create request object
#         query_request = AgentKBQueryRequest(
#             user_id=request.get('user_id'),
#             user_mssg=request.get('user_mssg'),
#             agent=request.get('agent')
#         )
        
#         # Get response from main handler
#         response = await agent_kb_query(query_request)
        
#         # Convert to n8n format
#         n8n_response = response.dict()
        
#         # Add n8n routing information
#         if response.response_type == "direct_answer":
#             n8n_response['workflow_action'] = 'send_response'
#             n8n_response['next_node'] = 'format_and_send'
            
#         elif response.response_type == "needs_tools":
#             n8n_response['workflow_action'] = 'execute_tools'
#             n8n_response['next_node'] = 'tool_executor'
#             n8n_response['tool_sequence'] = [t['name'] for t in (response.required_tools or [])]
            
#         elif response.response_type == "needs_info":
#             n8n_response['workflow_action'] = 'collect_information'
#             n8n_response['next_node'] = 'info_collector'
#             n8n_response['ui_action'] = 'show_form'
            
#         # Add execution metadata
#         n8n_response['execution_metadata'] = {
#             'timestamp': datetime.now().isoformat(),
#             'agent_type': request.get('agent'),
#             'has_context': response.kb_context_used,
#             'confidence': response.confidence_score
#         }
        
#         return n8n_response
        
#     except Exception as e:
#         logger.error(f"Error in n8n_agent_kb_query: {str(e)}")
#         return {
#             'status': 'error',
#             'error': str(e),
#             'workflow_action': 'handle_error',
#             'next_node': 'error_handler'
#         }

# # Helper endpoint to refresh agent KB
# @app.post("/api/agent/refresh_kb")
# async def refresh_agent_kb(agent_name: str):
#     """
#     Refresh agent KB by re-reading from agent_documents
#     Useful after updating agent KB files
#     """
#     try:
#         # Clear any cached context (if you implement caching)
#         # For now, just verify the agent exists
#         result = supabase.table('agent_documents')\
#             .select('id')\
#             .eq('agent_name', agent_name)\
#             .limit(1)\
#             .execute()
        
#         if result.data:
#             return {
#                 'status': 'success',
#                 'message': f'Agent KB for {agent_name} is available',
#                 'document_count': len(result.data)
#             }
#         else:
#             return {
#                 'status': 'not_found',
#                 'message': f'No KB documents found for agent: {agent_name}'
#             }
            
#     except Exception as e:
#         logger.error(f"Error refreshing agent KB: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# # Initialize conversational handler
# conversational_handler = ConversationalHandler(
#     supabase_client=supabase,
#     n8n_webhook_url="https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d"
# )

# # Your existing save_message_to_history function
# async def save_message_to_history(session_id: str, sender: str, message: str):
#     """Save a message to the appropriate history table"""
#     await conversational_handler.save_to_history(
#         session_id=session_id,
#         user_id="", # You might need to pass user_id here
#         user_message=message if sender == "User" else "",
#         agent_response=message if sender == "AI" else ""
#     )

# # n8n integration function with conversational logic
# async def call_n8n_webhook(payload: Dict[str, Any]):
#     """Call the n8n webhook and return the response"""
#     n8n_url = "https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d"
    
#     async with httpx.AsyncClient(timeout=60.0) as client:
#         try:
#             response = await client.post(n8n_url, json=payload)
#             response.raise_for_status()
#             return response.json()
#         except httpx.HTTPStatusError as e:
#             logger.error(f"N8N HTTP error: {e.response.status_code} - {e.response.text}")
#             raise HTTPException(status_code=e.response.status_code, detail=f"N8N error: {e.response.text}")
#         except Exception as e:
#             logger.error(f"N8N request error: {str(e)}")
#             raise HTTPException(status_code=500, detail=f"Failed to connect to n8n: {str(e)}")

# # N8N-specific request models
# class N8nCheckAgentMatchRequest(BaseModel):
#     agent_name: str
#     user_query: str
#     threshold: Optional[float] = 0.7

# class N8nFindBestAgentsRequest(BaseModel):
#     user_query: str
#     top_n: Optional[int] = 3
#     min_threshold: Optional[float] = 0.5

# # N8N webhook endpoint for checking agent match
# @app.post("/n8n/check_agent_match")
# async def n8n_check_agent_match(request: N8nCheckAgentMatchRequest):
#     """
#     N8N webhook endpoint to check if a specific agent matches the user query
    
#     Expected payload:
#     {
#         "agent_name": "presaleskb",
#         "user_query": "I need help with pricing for my website",
#         "threshold": 0.7  // Optional, defaults to 0.7
#     }
    
#     Returns:
#     {
#         "agent_name": "presaleskb",
#         "user_query": "I need help with pricing for my website",
#         "is_match": true,
#         "confidence": 0.85,
#         "threshold_used": 0.7,
#         "recommendation": "Agent is suitable for this query"
#     }
#     """
#     try:
#         # Check if agent matches using vector similarity
#         is_match = await agent_matcher.check_agent_match(
#             agent_name=request.agent_name,
#             user_query=request.user_query,
#             threshold=request.threshold
#         )
        
#         # Get similarity score for more detailed response
#         query_embedding = await agent_matcher.get_query_embedding(request.user_query)
        
#         result = agent_matcher.supabase.rpc(
#             'match_agent_documents',
#             {
#                 'query_embedding': query_embedding,
#                 'match_threshold': request.threshold,
#                 'match_count': 1,
#                 'filter_agent': request.agent_name
#             }
#         ).execute()
        
#         confidence = result.data[0]['similarity'] if result.data else 0.0
        
#         # Prepare recommendation message
#         if is_match:
#             recommendation = f"Agent '{request.agent_name}' is suitable for this query"
#         else:
#             recommendation = f"Agent '{request.agent_name}' may not be optimal for this query"
        
#         return {
#             "agent_name": request.agent_name,
#             "user_query": request.user_query,
#             "is_match": is_match,
#             "confidence": round(confidence, 3),
#             "threshold_used": request.threshold,
#             "recommendation": recommendation,
#             "status": "success"
#         }
        
#     except Exception as e:
#         logger.error(f"Error in n8n_check_agent_match: {str(e)}")
#         return {
#             "agent_name": request.agent_name,
#             "user_query": request.user_query,
#             "is_match": False,
#             "error": str(e),
#             "status": "error"
#         }

# # N8N webhook endpoint for finding best agents
# @app.post("/n8n/find_best_agents")
# async def n8n_find_best_agents(request: N8nFindBestAgentsRequest):
#     """
#     N8N webhook endpoint to find the best matching agents for a user query
    
#     Expected payload:
#     {
#         "user_query": "I need help setting up automated workflows",
#         "top_n": 3,  // Optional, defaults to 3
#         "min_threshold": 0.5  // Optional, defaults to 0.5
#     }
    
#     Returns:
#     {
#         "user_query": "I need help setting up automated workflows",
#         "best_agent": "manager",
#         "best_agent_confidence": 92.5,
#         "recommendations": [
#             {
#                 "agent_name": "manager",
#                 "match_percentage": 92.5,
#                 "rank": 1,
#                 "description": "Excellent match - specializes in workflow automation"
#             },
#             {
#                 "agent_name": "presaleskb",
#                 "match_percentage": 75.3,
#                 "rank": 2,
#                 "description": "Good match - can provide technical guidance"
#             }
#         ],
#         "total_agents_found": 2,
#         "status": "success"
#     }
#     """
#     try:
#         # Find best matching agents
#         best_agents = await agent_matcher.find_best_agents(
#             user_query=request.user_query,
#             top_n=request.top_n
#         )
        
#         # Filter by minimum threshold if specified
#         if request.min_threshold:
#             best_agents = [(name, score) for name, score in best_agents if score >= request.min_threshold * 100]
        
#         # Create detailed recommendations
#         recommendations = []
#         for idx, (agent_name, score) in enumerate(best_agents):
#             # Determine match quality description
#             if score >= 90:
#                 quality = "Excellent match"
#             elif score >= 75:
#                 quality = "Good match"
#             elif score >= 60:
#                 quality = "Fair match"
#             else:
#                 quality = "Possible match"
            
#             # Add agent-specific descriptions
#             agent_descriptions = {
#                 "presaleskb": "specializes in sales and pricing queries",
#                 "manager": "handles project management and workflows",
#                 "re-engage": "general purpose assistant for various queries",
#                 "real-estate": "expert in property-related questions",
#                 "branding": "focuses on brand strategy and marketing"
#             }
            
#             description = f"{quality} - {agent_descriptions.get(agent_name, 'handles specialized queries')}"
            
#             recommendations.append({
#                 "agent_name": agent_name,
#                 "match_percentage": round(score, 1),
#                 "rank": idx + 1,
#                 "description": description
#             })
        
#         # Prepare response
#         response = {
#             "user_query": request.user_query,
#             "recommendations": recommendations,
#             "total_agents_found": len(recommendations),
#             "status": "success"
#         }
        
#         # Add best agent info if available
#         if recommendations:
#             response["best_agent"] = recommendations[0]["agent_name"]
#             response["best_agent_confidence"] = recommendations[0]["match_percentage"]
#         else:
#             response["best_agent"] = "re-engage"  # Default fallback
#             response["best_agent_confidence"] = 50.0
#             response["message"] = "No agents found above threshold, using default agent"
        
#         return response
        
#     except Exception as e:
#         logger.error(f"Error in n8n_find_best_agents: {str(e)}")
#         return {
#             "user_query": request.user_query,
#             "best_agent": "re-engage",  # Fallback to default
#             "best_agent_confidence": 50.0,
#             "recommendations": [],
#             "error": str(e),
#             "status": "error",
#             "message": "Error finding agents, using default"
#         }

# # Combined endpoint for n8n workflows that need both checks
# @app.post("/n8n/analyze_agent_query")
# async def n8n_analyze_agent_query(request: Dict[str, Any]):
#     """
#     Combined N8N webhook endpoint that performs both agent checking and recommendation
    
#     Expected payload:
#     {
#         "user_query": "I need help with pricing",
#         "current_agent": "manager",  // Optional - to check if current agent is suitable
#         "get_recommendations": true,  // Optional - whether to get other recommendations
#         "top_n": 3  // Optional - number of recommendations
#     }
    
#     Returns comprehensive analysis for n8n workflows
#     """
#     try:
#         user_query = request.get("user_query", "")
#         current_agent = request.get("current_agent")
#         get_recommendations = request.get("get_recommendations", True)
#         top_n = request.get("top_n", 3)
        
#         response = {
#             "user_query": user_query,
#             "analysis_timestamp": datetime.now().isoformat(),
#             "status": "success"
#         }
        
#         # Check current agent if provided
#         if current_agent:
#             is_match = await agent_matcher.check_agent_match(current_agent, user_query)
#             response["current_agent_analysis"] = {
#                 "agent_name": current_agent,
#                 "is_suitable": is_match,
#                 "recommendation": "Keep current agent" if is_match else "Consider switching agents"
#             }
        
#         # Get recommendations if requested
#         if get_recommendations:
#             best_agents = await agent_matcher.find_best_agents(user_query, top_n)
            
#             response["recommended_agents"] = [
#                 {
#                     "agent_name": name,
#                     "confidence": round(score, 1),
#                     "rank": idx + 1
#                 }
#                 for idx, (name, score) in enumerate(best_agents)
#             ]
            
#             # Add routing decision
#             if best_agents:
#                 best_agent, best_score = best_agents[0]
                
#                 # Make routing decision
#                 if current_agent and current_agent == best_agent:
#                     response["routing_decision"] = "keep_current"
#                     response["routing_message"] = f"Current agent '{current_agent}' is optimal"
#                 elif best_score >= 70:
#                     response["routing_decision"] = "switch_agent"
#                     response["suggested_agent"] = best_agent
#                     response["routing_message"] = f"Switch to '{best_agent}' (confidence: {best_score}%)"
#                 else:
#                     response["routing_decision"] = "use_default"
#                     response["suggested_agent"] = "re-engage"
#                     response["routing_message"] = "No strong match found, use general agent"
        
#         return response
        
#     except Exception as e:
#         logger.error(f"Error in n8n_analyze_agent_query: {str(e)}")
#         return {
#             "user_query": request.get("user_query", ""),
#             "error": str(e),
#             "status": "error",
#             "routing_decision": "use_default",
#             "suggested_agent": "re-engage"
#         }

# # Health check endpoint for n8n agent matching service
# @app.get("/n8n/agent_matcher/health")
# async def n8n_agent_matcher_health():
#     """Health check for agent matching service"""
#     try:
#         # Test database connection
#         test_result = agent_matcher.supabase.table('agent_documents').select('id').limit(1).execute()
        
#         return {
#             "service": "agent_matcher",
#             "status": "healthy",
#             "database": "connected",
#             "endpoints": [
#                 "/n8n/check_agent_match",
#                 "/n8n/find_best_agents",
#                 "/n8n/analyze_agent_query"
#             ],
#             "timestamp": datetime.now().isoformat()
#         }
#     except Exception as e:
#         return {
#             "service": "agent_matcher",
#             "status": "unhealthy",
#             "error": str(e),
#             "timestamp": datetime.now().isoformat()
#         }
    
# # Add these to your main.py file

# # First, update the website_data table to include user_id
# """
# ALTER TABLE public.website_data ADD COLUMN user_id text NOT NULL;
# CREATE INDEX idx_website_data_user ON public.website_data USING btree (user_id);
# """

# # Models for Client KB
# class ClientKBCheckRequest(BaseModel):
#     user_id: str
#     session_id: Optional[str] = None
#     force_refresh: Optional[bool] = False

# class ClientKBResponse(BaseModel):
#     user_id: str
#     has_website_info: bool
#     website_url: Optional[str] = None
#     website_analysis: Optional[Dict[str, Any]] = None
#     company_info: Optional[Dict[str, Any]] = None
#     kb_status: str
#     message: str
#     action_required: Optional[str] = None
#     last_updated: Optional[str] = None

# class ClientKBManager:
#     """Manager class for client knowledge base operations"""
    
#     def __init__(self, supabase_client, openai_api_key: str = None):
#         supabase = supabase_client
#         self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
#         openai.api_key = self.openai_api_key
    
#     async def get_client_kb(self, user_id: str, kb_type: str = "website_info") -> Optional[Dict[str, Any]]:
#         """Retrieve client KB entry"""
#         try:
#             result = supabase.table('client_kb')\
#                 .select('*')\
#                 .eq('client_id', user_id)\
#                 .eq('kb_type', kb_type)\
#                 .single()\
#                 .execute()
            
#             return result.data if result.data else None
#         except Exception as e:
#             logger.error(f"Error getting client KB: {str(e)}")
#             return None
    
#     async def update_client_kb(self, user_id: str, kb_type: str, content: Dict[str, Any]):
#         """Update or create client KB entry"""
#         try:
#             # Prepare the KB entry
#             kb_entry = {
#                 'client_id': user_id,
#                 'kb_type': kb_type,
#                 'content': content,
#                 'updated_at': datetime.now().isoformat()
#             }
            
#             # Upsert the KB entry
#             result = supabase.table('client_kb')\
#                 .upsert(kb_entry, on_conflict='client_id,kb_type')\
#                 .execute()
            
#             return result.data[0] if result.data else None
#         except Exception as e:
#             logger.error(f"Error updating client KB: {str(e)}")
#             return None
    
#     async def generate_embedding(self, text: str) -> List[float]:
#         """Generate embedding for text content"""
#         try:
#             response = openai.Embedding.create(
#                 model="text-embedding-3-small",
#                 input=text
#             )
#             return response['data'][0]['embedding']
#         except Exception as e:
#             logger.error(f"Error generating embedding: {str(e)}")
#             return []
    
#     async def analyze_and_update_kb(self, user_id: str, website_data: Dict[str, Any], chat_history: List[Dict[str, Any]]):
#         """Analyze website data and chat history to update KB"""
#         try:
#             # Extract key information from website analysis
#             website_info = {
#                 'url': website_data.get('url'),
#                 'company_name': website_data.get('analysis', {}).get('company_name'),
#                 'description': website_data.get('analysis', {}).get('description'),
#                 'niche': website_data.get('analysis', {}).get('niche'),
#                 'tags': website_data.get('analysis', {}).get('tags'),
#                 'services': website_data.get('analysis', {}).get('services', []),
#                 'contact_info': website_data.get('analysis', {}).get('contact_info', {}),
#                 'last_analyzed': website_data.get('created_at')
#             }
            
#             # Extract insights from chat history
#             chat_insights = await self.extract_chat_insights(chat_history)
            
#             # Combine all information
#             kb_content = {
#                 'website_info': website_info,
#                 'chat_insights': chat_insights,
#                 'extracted_requirements': [],
#                 'preferences': {},
#                 'interaction_history': {
#                     'total_messages': len(chat_history),
#                     'last_interaction': chat_history[-1]['timestamp'] if chat_history else None
#                 }
#             }
            
#             # Generate searchable text for embeddings
#             searchable_text = f"""
#             Company: {website_info.get('company_name', 'Unknown')}
#             Description: {website_info.get('description', '')}
#             Niche: {website_info.get('niche', '')}
#             Services: {', '.join(website_info.get('services', []))}
#             Chat Topics: {', '.join(chat_insights.get('topics', []))}
#             Requirements: {', '.join(chat_insights.get('requirements', []))}
#             """
            
#             # Generate embedding for fast vector search
#             embedding = await self.generate_embedding(searchable_text)
#             kb_content['embedding'] = embedding
#             kb_content['searchable_text'] = searchable_text
            
#             # Update the KB
#             await self.update_client_kb(user_id, 'website_info', kb_content)
            
#             # Also store specialized KBs for different aspects
#             if website_info.get('services'):
#                 await self.update_client_kb(user_id, 'services', {'services': website_info['services']})
            
#             if chat_insights.get('requirements'):
#                 await self.update_client_kb(user_id, 'requirements', {'requirements': chat_insights['requirements']})
            
#             return kb_content
            
#         except Exception as e:
#             logger.error(f"Error analyzing and updating KB: {str(e)}")
#             return None
    
#     async def extract_chat_insights(self, chat_history: List[Dict[str, Any]]) -> Dict[str, Any]:
#         """Extract insights from chat history using AI"""
#         if not chat_history:
#             return {'topics': [], 'requirements': [], 'questions': []}
        
#         try:
#             # Prepare chat transcript
#             transcript = "\n".join([
#                 f"{msg['sender']}: {msg['message']}" 
#                 for msg in chat_history[-20:]  # Last 20 messages
#             ])
            
#             # Use OpenAI to extract insights
#             response = openai.ChatCompletion.create(
#                 model="gpt-3.5-turbo",
#                 messages=[
#                     {
#                         "role": "system",
#                         "content": "Extract key topics, requirements, and questions from this chat transcript. Return as JSON with keys: topics (list), requirements (list), questions (list), pain_points (list)."
#                     },
#                     {
#                         "role": "user",
#                         "content": transcript
#                     }
#                 ],
#                 temperature=0.3,
#                 max_tokens=500
#             )
            
#             insights = json.loads(response.choices[0].message.content)
#             return insights
            
#         except Exception as e:
#             logger.error(f"Error extracting chat insights: {str(e)}")
#             return {'topics': [], 'requirements': [], 'questions': []}

# # Initialize Client KB Manager
# client_kb_manager = ClientKBManager(supabase_client=supabase)

# # Main endpoint to check client KB status
# @app.post("/api/client/check_kb")
# async def check_client_kb(request: ClientKBCheckRequest):
#     """
#     Check if client has website information in KB and return appropriate response
    
#     Returns:
#     - If website info exists: All relevant client information
#     - If not: Request to collect website URL
#     """
#     try:
#         # Check if client has website info in KB
#         kb_data = await client_kb_manager.get_client_kb(request.user_id, 'website_info')
        
#         if kb_data and not request.force_refresh:
#             # Client has website info
#             content = kb_data.get('content', {})
#             website_info = content.get('website_info', {})
            
#             return ClientKBResponse(
#                 user_id=request.user_id,
#                 has_website_info=True,
#                 website_url=website_info.get('url'),
#                 website_analysis=website_info,
#                 company_info={
#                     'name': website_info.get('company_name'),
#                     'niche': website_info.get('niche'),
#                     'description': website_info.get('description'),
#                     'services': website_info.get('services', [])
#                 },
#                 kb_status='complete',
#                 message='Client information found',
#                 last_updated=kb_data.get('updated_at')
#             )
        
#         # Check if we have website data but no KB entry (or force refresh)
#         website_result = None
#         if request.session_id:
#             website_result = supabase.table('website_data')\
#                 .select('*')\
#                 .eq('user_id', request.user_id)\
#                 .eq('session_id', request.session_id)\
#                 .order('created_at', desc=True)\
#                 .limit(1)\
#                 .execute()
#         else:
#             # Get most recent website data for user
#             website_result = supabase.table('website_data')\
#                 .select('*')\
#                 .eq('user_id', request.user_id)\
#                 .order('created_at', desc=True)\
#                 .limit(1)\
#                 .execute()
        
#         if website_result and website_result.data:
#             # We have website data, update KB
#             website_data = website_result.data[0]
            
#             # Get chat history
#             chat_history_result = supabase.table('chat_history')\
#                 .select('*')\
#                 .eq('user_id', request.user_id)\
#                 .order('timestamp', desc=False)\
#                 .execute()
            
#             chat_history = chat_history_result.data if chat_history_result else []
            
#             # Analyze and update KB
#             kb_content = await client_kb_manager.analyze_and_update_kb(
#                 request.user_id,
#                 website_data,
#                 chat_history
#             )
            
#             if kb_content:
#                 website_info = kb_content.get('website_info', {})
#                 return ClientKBResponse(
#                     user_id=request.user_id,
#                     has_website_info=True,
#                     website_url=website_info.get('url'),
#                     website_analysis=website_info,
#                     company_info={
#                         'name': website_info.get('company_name'),
#                         'niche': website_info.get('niche'),
#                         'description': website_info.get('description'),
#                         'services': website_info.get('services', [])
#                     },
#                     kb_status='updated',
#                     message='Client KB updated with latest information',
#                     last_updated=datetime.now().isoformat()
#                 )
        
#         # No website info available
#         return ClientKBResponse(
#             user_id=request.user_id,
#             has_website_info=False,
#             kb_status='missing_website',
#             message='Please provide your website URL to continue',
#             action_required='collect_website_url'
#         )
        
#     except Exception as e:
#         logger.error(f"Error checking client KB: {str(e)}")
#         return ClientKBResponse(
#             user_id=request.user_id,
#             has_website_info=False,
#             kb_status='error',
#             message=f'Error checking client information: {str(e)}',
#             action_required='retry'
#         )

# # Endpoint to update client KB when website is provided
# @app.post("/api/client/update_website")
# async def update_client_website(request: Dict[str, Any]):
#     """
#     Update client KB when website URL is provided
    
#     Expected payload:
#     {
#         "user_id": "user123",
#         "session_id": "session456",
#         "website_url": "https://example.com"
#     }
#     """
#     try:
#         user_id = request.get('user_id')
#         session_id = request.get('session_id')
#         website_url = request.get('website_url')
        
#         if not all([user_id, website_url]):
#             raise HTTPException(status_code=400, detail="Missing required fields")
        
#         # Analyze website using Perplexity (using existing function)
#         analysis = await conversational_handler.analyze_website_with_perplexity(website_url)
        
#         # Store in website_data table
#         website_entry = {
#             'user_id': user_id,
#             'session_id': session_id or str(uuid.uuid4()),
#             'url': website_url,
#             'analysis': json.dumps(analysis) if analysis else None,
#             'created_at': datetime.now().isoformat()
#         }
        
#         website_result = supabase.table('website_data')\
#             .upsert(website_entry, on_conflict='session_id,url')\
#             .execute()
        
#         if website_result.data:
#             # Get chat history
#             chat_history_result = supabase.table('chat_history')\
#                 .select('*')\
#                 .eq('user_id', user_id)\
#                 .order('timestamp', desc=False)\
#                 .execute()
            
#             chat_history = chat_history_result.data if chat_history_result else []
            
#             # Update KB
#             kb_content = await client_kb_manager.analyze_and_update_kb(
#                 user_id,
#                 website_result.data[0],
#                 chat_history
#             )
            
#             return {
#                 'status': 'success',
#                 'user_id': user_id,
#                 'website_url': website_url,
#                 'analysis': analysis,
#                 'kb_updated': bool(kb_content),
#                 'message': 'Website information saved and KB updated'
#             }
        
#     except Exception as e:
#         logger.error(f"Error updating client website: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# # Endpoint to get client context for agents
# @app.get("/api/client/context/{user_id}")
# async def get_client_context(user_id: str):
#     """Get complete client context for agent use"""
#     try:
#         # Get all KB entries for client
#         kb_results = supabase.table('client_kb')\
#             .select('*')\
#             .eq('client_id', user_id)\
#             .execute()
        
#         context = {
#             'user_id': user_id,
#             'kb_entries': {}
#         }
        
#         if kb_results.data:
#             for entry in kb_results.data:
#                 context['kb_entries'][entry['kb_type']] = entry['content']
        
#         # Get recent chat history
#         chat_history = supabase.table('chat_history')\
#             .select('*')\
#             .eq('user_id', user_id)\
#             .order('timestamp', desc=False)\
#             .limit(50)\
#             .execute()
        
#         context['recent_conversations'] = chat_history.data if chat_history else []
        
#         # Get website data
#         website_data = supabase.table('website_data')\
#             .select('*')\
#             .eq('user_id', user_id)\
#             .order('created_at', desc=True)\
#             .limit(1)\
#             .execute()
        
#         if website_data and website_data.data:
#             context['current_website'] = website_data.data[0]
        
#         return context
        
#     except Exception as e:
#         logger.error(f"Error getting client context: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# # N8N webhook endpoint for KB check
# @app.post("/n8n/check_client_kb")
# async def n8n_check_client_kb(request: Dict[str, Any]):
#     """
#     N8N-specific endpoint for checking client KB
    
#     Expected payload:
#     {
#         "user_id": "user123",
#         "session_id": "session456",  // Optional
#         "force_refresh": false  // Optional
#     }
#     """
#     try:
#         kb_request = ClientKBCheckRequest(
#             user_id=request.get('user_id'),
#             session_id=request.get('session_id'),
#             force_refresh=request.get('force_refresh', False)
#         )
        
#         response = await check_client_kb(kb_request)
        
#         # Add n8n-specific fields for workflow routing
#         n8n_response = response.dict()
        
#         # Add routing information
#         if response.has_website_info:
#             n8n_response['next_action'] = 'proceed_with_agent'
#             n8n_response['routing'] = 'continue'
#         else:
#             n8n_response['next_action'] = 'request_website'
#             n8n_response['routing'] = 'collect_info'
#             n8n_response['prompt_message'] = "To provide you with accurate information about our services and pricing, could you please share your website URL?"
        
#         return n8n_response
        
#     except Exception as e:
#         logger.error(f"Error in n8n_check_client_kb: {str(e)}")
#         return {
#             'status': 'error',
#             'error': str(e),
#             'next_action': 'handle_error',
#             'routing': 'error'
#         }

# @app.get("/")
# async def health_check():
#     return {"status": "healthy", "message": "Squidgy AI WebSocket Server is running"}

# # API endpoints for agent matching
# @app.post("/api/agents/check-match")
# async def check_agent_match_endpoint(agent_name: str, user_query: str):
#     """API endpoint to check if an agent matches a query using vector similarity"""
#     try:
#         is_match = await agent_matcher.check_agent_match(agent_name, user_query)
#         return {
#             "agent_name": agent_name,
#             "user_query": user_query,
#             "is_match": is_match
#         }
#     except Exception as e:
#         logger.error(f"Error checking agent match: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/api/agents/find-best")
# async def find_best_agents_endpoint(user_query: str, top_n: int = 3):
#     """API endpoint to find best matching agents using vector similarity"""
#     try:
#         best_agents = await agent_matcher.find_best_agents(user_query, top_n)
#         return {
#             "user_query": user_query,
#             "recommendations": [
#                 {
#                     "agent_name": agent_name,
#                     "match_percentage": round(score, 2),
#                     "rank": idx + 1
#                 }
#                 for idx, (agent_name, score) in enumerate(best_agents)
#             ]
#         }
#     except Exception as e:
#         logger.error(f"Error finding best agents: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# # Streaming endpoint to receive updates from n8n
# @app.post("/api/stream")
# async def receive_stream_update(update: StreamUpdate):
#     """Endpoint that receives streaming updates from n8n and forwards to WebSocket clients"""
#     try:
#         connection_id = f"{update.user_id}_{update.metadata.get('session_id', '')}"
        
#         # Store the update for HTTP streaming
#         session_key = f"{update.user_id}:{update.metadata.get('request_id', '')}"
#         if session_key not in streaming_sessions:
#             streaming_sessions[session_key] = {
#                 "updates": [],
#                 "complete": False
#             }
        
#         streaming_sessions[session_key]["updates"].append(update.dict())
        
#         # Mark as complete if this is the final update
#         if update.type in ["complete", "final"]:
#             streaming_sessions[session_key]["complete"] = True
        
#         # Forward to WebSocket if client is connected
#         if connection_id in active_connections:
#             websocket = active_connections[connection_id]
#             await websocket.send_json({
#                 "type": update.type,
#                 "agent": update.agent_name or update.agent_names,
#                 "message": update.message,
#                 "progress": update.progress,
#                 "requestId": update.metadata.get("request_id"),
#                 "metadata": update.metadata,
#                 "timestamp": int(time.time() * 1000)
#             })
            
#             # Send the actual response if this is the complete update
#             if update.type == "complete" and update.agent_response:
#                 await websocket.send_json({
#                     "type": "agent_response",
#                     "agent": update.agent_name,
#                     "message": update.agent_response,
#                     "requestId": update.metadata.get("request_id"),
#                     "final": True,
#                     "timestamp": int(time.time() * 1000)
#                 })
        
#         return {"status": "received", "connection_id": connection_id}
        
#     except Exception as e:
#         logger.error(f"Error in receive_stream_update: {str(e)}")
#         return {"status": "error", "error": str(e)}

# # Streaming n8n integration
# async def stream_n8n_response(payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
#     """Stream response from n8n webhook using SSE"""
#     n8n_stream_url = "https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d/stream"
    
#     async with httpx.AsyncClient(timeout=60.0) as client:
#         try:
#             async with client.stream("POST", n8n_stream_url, json=payload) as response:
#                 async for line in response.aiter_lines():
#                     if line.strip():
#                         yield f"data: {line}\n\n"
#         except Exception as e:
#             logger.error(f"N8N streaming error: {str(e)}")
#             yield f"data: {json.dumps({'error': str(e)})}\n\n"

# # Main n8n request endpoint with conversational logic
# @app.post("/n8n_main_req")
# async def n8n_main_request(request: N8nMainRequest):
#     """Handle main request to n8n workflow with conversational logic"""
#     try:
#         # Generate request_id for tracking
#         request_id = str(uuid.uuid4())
        
#         # Add timestamp if not provided
#         if not request.timestamp_of_call_made:
#             request.timestamp_of_call_made = datetime.now().isoformat()
        
#         # Prepare request data
#         request_data = {
#             "user_id": request.user_id,
#             "user_mssg": request.user_mssg,
#             "session_id": request.session_id,
#             "agent_name": request.agent_name,
#             "timestamp_of_call_made": request.timestamp_of_call_made,
#             "request_id": request_id
#         }
        
#         # Process through conversational handler
#         n8n_payload = await conversational_handler.handle_message(request_data)
        
#         logger.info(f"Sending to n8n: {n8n_payload}")
        
#         # Call n8n webhook
#         n8n_response = await call_n8n_webhook(n8n_payload)
        
#         logger.info(f"Received from n8n: {n8n_response}")
        
#         # Format response
#         formatted_response = {
#             "user_id": n8n_response.get("user_id", request.user_id),
#             "agent_name": n8n_response.get("agent_name", request.agent_name),
#             "agent_response": n8n_response.get("agent_response", n8n_response.get("agent_responses", "")),
#             "responses": n8n_response.get("responses", []),
#             "timestamp": n8n_response.get("timestamp", datetime.now().isoformat()),
#             "status": n8n_response.get("status", "success"),
#             "request_id": request_id,
#             "conversation_state": n8n_response.get("conversation_state", "complete"),
#             "missing_info": n8n_response.get("missing_info", [])
#         }
        
#         # Save to history
#         await conversational_handler.save_to_history(
#             request.session_id,
#             request.user_id,
#             request_data.get("_original_message", request.user_mssg),
#             formatted_response["agent_response"]
#         )
        
#         return formatted_response
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error in n8n_main_request: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# # Streaming n8n request endpoint
# @app.post("/n8n_main_req_stream")
# async def n8n_main_request_stream(request: N8nMainRequest):
#     """Handle streaming request to n8n workflow"""
#     try:
#         # Add timestamp if not provided
#         if not request.timestamp_of_call_made:
#             request.timestamp_of_call_made = datetime.now().isoformat()
        
#         # Prepare request data
#         request_data = {
#             "user_id": request.user_id,
#             "user_mssg": request.user_mssg,
#             "session_id": request.session_id,
#             "agent_name": request.agent_name,
#             "timestamp_of_call_made": request.timestamp_of_call_made
#         }
        
#         # Process through conversational handler
#         n8n_payload = await conversational_handler.handle_message(request_data)
        
#         # Return streaming response
#         return StreamingResponse(
#             stream_n8n_response(n8n_payload),
#             media_type="text/event-stream"
#         )
        
#     except Exception as e:
#         logger.error(f"Error in n8n_main_request_stream: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# # Async handler for n8n requests with conversational logic
# async def process_n8n_request_async(payload: dict, websocket: WebSocket, request_id: str):
#     """Process n8n request asynchronously with conversational logic"""
#     try:
#         # Process through conversational handler
#         n8n_payload = await conversational_handler.handle_message(payload)
        
#         # Call n8n webhook
#         n8n_response = await call_n8n_webhook(n8n_payload)
        
#         # Check if we got a direct response (non-streaming)
#         if n8n_response.get("status") == "success" and "agent_response" in n8n_response:
#             agent_response = n8n_response.get("agent_response", "")
            
#             # Send final response
#             await websocket.send_json({
#                 "type": "agent_response",
#                 "agent": n8n_response.get("agent_name", "Squidgy"),
#                 "message": agent_response,
#                 "requestId": request_id,
#                 "final": True,
#                 "timestamp": int(time.time() * 1000),
#                 "conversation_state": n8n_response.get("conversation_state", "complete"),
#                 "missing_info": n8n_response.get("missing_info", [])
#             })
            
#             # Save to chat history
#             await save_message_to_history(payload["session_id"], "User", payload.get("_original_message", payload["user_mssg"]))
#             await save_message_to_history(payload["session_id"], "AI", agent_response)
            
#     except Exception as e:
#         logger.error(f"Error in process_n8n_request_async: {str(e)}")
#         await websocket.send_json({
#             "type": "error",
#             "message": f"Error processing request: {str(e)}",
#             "requestId": request_id,
#             "timestamp": int(time.time() * 1000)
#         })

# # WebSocket endpoint with streaming support and conversational logic
# @app.websocket("/ws/{user_id}/{session_id}")
# async def websocket_endpoint(websocket: WebSocket, user_id: str, session_id: str):
#     """WebSocket endpoint that routes through n8n with streaming support and conversational logic"""
#     connection_id = f"{user_id}_{session_id}"
#     logger.info(f"New WebSocket connection: {connection_id}")
    
#     # Accept the connection
#     await websocket.accept()
    
#     # Store connection
#     active_connections[connection_id] = websocket
    
#     try:
#         # Send connection confirmation
#         await websocket.send_json({
#             "type": "connection_status",
#             "status": "connected",
#             "message": "WebSocket connection established",
#             "timestamp": int(time.time() * 1000)
#         })
        
#         # Handle incoming messages
#         while True:
#             # Wait for a message from the client
#             data = await websocket.receive_text()
#             message_data = json.loads(data)
            
#             # Generate a unique request ID
#             request_id = message_data.get("requestId", str(uuid.uuid4()))
            
#             # Extract the message content
#             user_input = message_data.get("message", "").strip()
            
#             # Send acknowledgment
#             await websocket.send_json({
#                 "type": "ack",
#                 "requestId": request_id,
#                 "message": "Message received, processing...",
#                 "timestamp": int(time.time() * 1000)
#             })
            
#             # Prepare n8n request with request_id
#             n8n_payload = {
#                 "user_id": user_id,
#                 "user_mssg": user_input,
#                 "session_id": session_id,
#                 "agent_name": message_data.get("agent", "re-engage"),
#                 "timestamp_of_call_made": datetime.now().isoformat(),
#                 "request_id": request_id
#             }
            
#             # Call n8n asynchronously with conversational logic
#             asyncio.create_task(
#                 process_n8n_request_async(n8n_payload, websocket, request_id)
#             )
            
#     except WebSocketDisconnect:
#         # Clean up on disconnect
#         if connection_id in active_connections:
#             del active_connections[connection_id]
#         logger.info(f"Client disconnected: {connection_id}")
        
#     except Exception as e:
#         logger.exception(f"WebSocket error: {str(e)}")
#         if connection_id in active_connections:
#             del active_connections[connection_id]

# # Health check endpoint
# @app.get("/health")
# async def health_check():
#     return {
#         "status": "healthy",
#         "active_connections": len(active_connections),
#         "streaming_sessions": len(streaming_sessions)
#     }

# # Process chat via n8n with conversational logic
# async def process_chat_via_n8n(user_id: str, session_id: str, user_input: str, request_id: str, connection_id: str, websocket: WebSocket):
#     """Process chat through n8n workflow with conversational logic"""
#     try:
#         # Default to re-engage agent if not specified
#         agent_name = "re-engage"
        
#         # Prepare n8n payload
#         n8n_payload = {
#             "user_id": user_id,
#             "user_mssg": user_input,
#             "session_id": session_id,
#             "agent_name": agent_name,
#             "timestamp_of_call_made": datetime.now().isoformat(),
#             "request_id": request_id
#         }
        
#         # Process through conversational handler
#         processed_payload = await conversational_handler.handle_message(n8n_payload)
        
#         # Call n8n workflow
#         n8n_response = await call_n8n_webhook(processed_payload)
        
#         # Process n8n response
#         if n8n_response.get("status") == "success":
#             # Extract the response message
#             agent_response = n8n_response.get("agent_response", n8n_response.get("agent_responses", ""))
            
#             # Send final response to websocket
#             await websocket.send_json({
#                 "type": "agent_response",
#                 "agent": n8n_response.get("agent_name", "Squidgy"),
#                 "message": agent_response,
#                 "requestId": request_id,
#                 "final": True,
#                 "timestamp": int(time.time() * 1000),
#                 "conversation_state": n8n_response.get("conversation_state", "complete"),
#                 "missing_info": n8n_response.get("missing_info", [])
#             })
            
#             # Save to chat history
#             await save_message_to_history(session_id, "User", user_input)
#             await save_message_to_history(session_id, "AI", agent_response)
            
#         else:
#             # Handle error from n8n
#             error_message = n8n_response.get("error", "Unknown error occurred")
#             await websocket.send_json({
#                 "type": "error",
#                 "message": error_message,
#                 "requestId": request_id,
#                 "timestamp": int(time.time() * 1000)
#             })
            
#     except Exception as e:
#         logger.error(f"Error in process_chat_via_n8n: {str(e)}")
#         await websocket.send_json({
#             "type": "error",
#             "message": f"Error processing request: {str(e)}",
#             "requestId": request_id,
#             "timestamp": int(time.time() * 1000)
#         })

# # Process chat via n8n with streaming and conversational logic
# async def process_chat_via_n8n_streaming(user_id: str, session_id: str, user_input: str, request_id: str, connection_id: str, websocket: WebSocket):
#     """Process chat through n8n workflow with streaming support and conversational logic"""
#     try:
#         # Default to re-engage agent if not specified
#         agent_name = "re-engage"
        
#         # Prepare n8n payload
#         n8n_payload = {
#             "user_id": user_id,
#             "user_mssg": user_input,
#             "session_id": session_id,
#             "agent_name": agent_name,
#             "timestamp_of_call_made": datetime.now().isoformat(),
#             "request_id": request_id
#         }
        
#         # Process through conversational handler
#         processed_payload = await conversational_handler.handle_message(n8n_payload)
        
#         # Create a session for this request
#         session_key = f"{user_id}:{request_id}"
#         streaming_sessions[session_key] = {
#             "updates": [],
#             "complete": False
#         }
        
#         # Call n8n webhook with streaming support
#         n8n_url = "https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d"
        
#         async with httpx.AsyncClient(timeout=60.0) as client:
#             try:
#                 # Make the call to n8n (this will trigger the workflow)
#                 response = await client.post(n8n_url, json=processed_payload)
                
#                 # If we get an immediate response, send it
#                 if response.status_code == 200:
#                     result = response.json()
#                     if result.get("status") == "success":
#                         agent_response = result.get("agent_response", result.get("agent_responses", ""))
                        
#                         await websocket.send_json({
#                             "type": "agent_response",
#                             "agent": result.get("agent_name", "Squidgy"),
#                             "message": agent_response,
#                             "requestId": request_id,
#                             "final": True,
#                             "timestamp": int(time.time() * 1000),
#                             "conversation_state": result.get("conversation_state", "complete"),
#                             "missing_info": result.get("missing_info", [])
#                         })
                        
#                         # Save to chat history
#                         await save_message_to_history(session_id, "User", user_input)
#                         await save_message_to_history(session_id, "AI", agent_response)
#                 else:
#                     raise HTTPException(status_code=response.status_code, detail=response.text)
                    
#             except Exception as e:
#                 logger.error(f"Error calling n8n: {str(e)}")
#                 await websocket.send_json({
#                     "type": "error",
#                     "message": f"Error processing request: {str(e)}",
#                     "requestId": request_id,
#                     "timestamp": int(time.time() * 1000)
#                 })
                
#     except Exception as e:
#         logger.error(f"Error in process_chat_via_n8n_streaming: {str(e)}")
#         await websocket.send_json({
#             "type": "error",
#             "message": f"Error processing request: {str(e)}",
#             "requestId": request_id,
#             "timestamp": int(time.time() * 1000)
#         })
#     finally:
#         # Clean up streaming session
#         session_key = f"{user_id}:{request_id}"
#         if session_key in streaming_sessions:
#             del streaming_sessions[session_key]

# # CORS middleware
# from fastapi.middleware.cors import CORSMiddleware

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Configure this properly in production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)