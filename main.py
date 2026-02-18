# main.py - Complete integration with conversational handler and vector search agent matching
# Trigger deployment

# Standard library imports
import asyncio
import json
import logging
import os
import time
import uuid
import tempfile
from collections import deque
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Any, Optional, List, Set

# Third-party imports
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, UploadFile, File, Form, Request, Header, Response
from starlette.websockets import WebSocketState
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from twilio.twiml.messaging_response import MessagingResponse as TwilioMessagingResponse
# from openai import OpenAI
from pydantic import BaseModel, validator
from typing import Union
from supabase import create_client, Client
from PIL import Image

# Local imports
from Website.web_scrape import capture_website_screenshot, get_website_favicon_async
from Website.web_analysis import analyze_website as analyze_website_local, extract_colors_from_website
from invitation_handler import InvitationHandler
from file_processing_service import FileProcessingService
from background_text_processor import get_background_processor, initialize_background_processor
from web_analysis_client import WebAnalysisClient

# Handler classes

# AgentMatcher class removed - replaced with simple defaults

# Conversational Handler Class
class ConversationalHandler:
    def __init__(self, supabase_client, n8n_url: str = os.getenv('N8N_MAIN', 'https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d')):
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = 300  # Cache TTL in seconds (5 minutes)
        self.supabase = supabase_client
        self.n8n_url = n8n_url

    async def get_cached_response(self, request_id: str):
        """Get cached response if it exists and is not expired"""
        cache_key = f"response_{request_id}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if (datetime.now() - cached['timestamp']).total_seconds() < self._cache_ttl:
                return cached['response']
            del self._cache[cache_key]
        return None

    async def cache_response(self, request_id: str, response: dict):
        """Cache a response with TTL"""
        cache_key = f"response_{request_id}"
        self._cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now()
        }

    async def save_to_history(self, session_id: str, user_id: str, user_message: str, agent_response: str):
        """Save message to chat history - saves user and agent messages separately with duplicate prevention"""
        try:
            # Check for existing user message to prevent duplicates (within last 10 seconds)
            existing_user = self.supabase.table('chat_history')\
                .select('id, timestamp')\
                .eq('session_id', session_id)\
                .eq('user_id', user_id)\
                .eq('message', user_message)\
                .eq('sender', 'User')\
                .gte('timestamp', (datetime.now() - timedelta(seconds=10)).isoformat())\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            # Only save user message if not duplicate
            user_result = None
            if not existing_user.data:
                user_entry = {
                    'session_id': session_id,
                    'user_id': user_id,
                    'sender': 'User',
                    'message': user_message,
                    'timestamp': datetime.now().isoformat()
                }
                
                try:
                    user_result = self.supabase.table('chat_history')\
                        .insert(user_entry)\
                        .execute()
                except Exception as insert_error:
                    # Handle unique constraint violation gracefully
                    if 'duplicate key value violates unique constraint' in str(insert_error):
                        logger.debug(f"Duplicate message caught by database constraint for session {session_id}")
                        user_result = None
                    else:
                        raise insert_error
            else:
                logger.debug(f"Skipping duplicate user message for session {session_id}")
            
            # Save agent response if provided
            agent_result = None
            if agent_response and agent_response.strip():
                # Check for existing agent response to prevent duplicates (within last 10 seconds)
                existing_agent = self.supabase.table('chat_history')\
                    .select('id, timestamp')\
                    .eq('session_id', session_id)\
                    .eq('user_id', user_id)\
                    .eq('message', agent_response)\
                    .eq('sender', 'Agent')\
                    .gte('timestamp', (datetime.now() - timedelta(seconds=10)).isoformat())\
                    .order('timestamp', desc=True)\
                    .limit(1)\
                    .execute()
                
                if not existing_agent.data:
                    agent_entry = {
                        'session_id': session_id,
                        'user_id': user_id,
                        'sender': 'Agent',
                        'message': agent_response,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    try:
                        agent_result = self.supabase.table('chat_history')\
                            .insert(agent_entry)\
                            .execute()
                    except Exception as insert_error:
                        # Handle unique constraint violation gracefully
                        if 'duplicate key value violates unique constraint' in str(insert_error):
                            logger.debug(f"Duplicate agent response caught by database constraint for session {session_id}")
                            agent_result = None
                        else:
                            raise insert_error
                else:
                    logger.debug(f"Skipping duplicate agent response for session {session_id}")
                
                return {
                    'user_entry': user_result.data[0] if user_result.data else None,
                    'agent_entry': agent_result.data[0] if agent_result.data else None
                }
            
            return {
                'user_entry': user_result.data[0] if user_result.data else None,
                'agent_entry': None
            }
            
        except Exception as e:
            logger.error(f"Error saving to history: {str(e)}")
            return None

    async def handle_message(self, request_data: dict):
        """Handle incoming message with conversational logic"""
        try:
            user_mssg = request_data.get('user_mssg', '')
            session_id = request_data.get('session_id', '')
            user_id = request_data.get('user_id', '')
            agent_name = request_data.get('agent_name', 'presaleskb')
            request_id = request_data.get('request_id', str(uuid.uuid4()))

            # Skip empty messages
            if not user_mssg.strip():
                return {
                    'status': 'error',
                    'message': 'Empty message received'
                }

            # Check cache first
            cached_response = await self.get_cached_response(request_id)
            if cached_response:
                return cached_response

            # Process the message
            response = await self.process_message(user_mssg, session_id, user_id, agent_name, request_id)

            # Cache the response
            await self.cache_response(request_id, response)

            return response

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            raise

    async def process_message(self, user_mssg: str, session_id: str, user_id: str, agent_name: str, request_id: Optional[str] = None):
        """Process the actual message and get response from n8n with full conversation context"""
        try:
            # Generate request_id if not provided
            if not request_id:
                request_id = str(uuid.uuid4())
            
            logger.info(f"🧠 Building conversation context for session {session_id}")
            
            # 1. Get conversation history for context
            chat_history = []
            try:
                chat_result = self.supabase.table('chat_history')\
                    .select('sender, message, timestamp')\
                    .eq('session_id', session_id)\
                    .order('timestamp', desc=False)\
                    .limit(20)\
                    .execute()
                
                if chat_result.data:
                    chat_history = [
                        {
                            'sender': msg['sender'],
                            'message': msg['message'],
                            'timestamp': msg['timestamp']
                        }
                        for msg in chat_result.data
                    ]
                logger.info(f"📚 Retrieved {len(chat_history)} previous messages for context")
            except Exception as e:
                logger.warning(f"Could not retrieve chat history: {str(e)}")
            
            # 2. Get website data for context
            website_context = []
            try:
                website_result = self.supabase.table('website_data')\
                    .select('url, analysis, created_at')\
                    .eq('user_id', user_id)\
                    .order('created_at', desc=True)\
                    .limit(5)\
                    .execute()
                
                if website_result.data:
                    website_context = website_result.data
                logger.info(f"🌐 Retrieved {len(website_context)} website analyses for context")
            except Exception as e:
                logger.warning(f"Could not retrieve website data: {str(e)}")
            
            # 3. Get client KB for context
            client_kb_context = {}
            try:
                kb_result = self.supabase.table('client_kb')\
                    .select('kb_type, content')\
                    .eq('client_id', user_id)\
                    .execute()
                
                if kb_result.data:
                    for entry in kb_result.data:
                        client_kb_context[entry['kb_type']] = entry['content']
                logger.info(f"📊 Retrieved {len(client_kb_context)} KB entries for context")
            except Exception as e:
                logger.warning(f"Could not retrieve client KB: {str(e)}")
            
            # 4. Extract contextual information from conversation
            context_insights = self._extract_conversation_insights(chat_history, website_context)
            logger.info(f"🔍 Extracted context insights: {list(context_insights.keys())}")
                
            # Prepare enhanced payload for n8n with full context
            payload = {
                'user_id': user_id,
                'user_mssg': user_mssg,
                'session_id': session_id,
                'agent_name': agent_name,
                'timestamp_of_call_made': datetime.now().isoformat(),
                'request_id': request_id,
                '_original_message': user_mssg,
                # ENHANCED CONTEXT DATA
                'conversation_history': chat_history,
                'website_data': website_context,
                'client_knowledge_base': client_kb_context,
                'context_insights': context_insights,
                'context_summary': {
                    'total_messages': len(chat_history),
                    'websites_analyzed': len(website_context),
                    'kb_entries': len(client_kb_context),
                    'extracted_insights': len(context_insights)
                }
            }
            
            logger.info(f"🚀 Sending enhanced payload to n8n with {len(chat_history)} messages, {len(website_context)} websites, {len(client_kb_context)} KB entries")

            # Call n8n webhook
            async with httpx.AsyncClient(timeout=None) as client:
                response = await client.post(self.n8n_url, json=payload)
                response.raise_for_status()
                
                # Check if response has content before parsing JSON
                if not response.text.strip():
                    logger.error(f"N8N returned empty response body. Status: {response.status_code}")
                    raise Exception("N8N workflow returned empty response - check workflow configuration")
                
                try:
                    n8n_response = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"N8N returned invalid JSON. Raw response: '{response.text}'")
                    raise Exception(f"N8N workflow returned invalid JSON: {str(e)}")
                
                # Log the full N8N response for testing
                logger.info(f"N8N Response: {json.dumps(n8n_response, indent=2)}")
                print(f"🔍 N8N Response: {json.dumps(n8n_response, indent=2)}")
                
                # Parse n8n response - handle both direct object and array with output field
                parsed_data = {}
                print(f"🔍 STEP 1 - n8n_response type: {type(n8n_response)}")
                print(f"🔍 STEP 1 - n8n_response is list: {isinstance(n8n_response, list)}")
                if isinstance(n8n_response, list):
                    print(f"🔍 STEP 1 - list length: {len(n8n_response)}")
                
                if isinstance(n8n_response, list) and len(n8n_response) > 0:
                    # Handle array format: [{"output": "JSON_STRING"}]
                    first_item = n8n_response[0]
                    print(f"🔍 STEP 2 - first_item: {json.dumps(first_item, indent=2)}")
                    print(f"🔍 STEP 2 - 'output' in first_item: {'output' in first_item}")
                    
                    if 'output' in first_item:
                        try:
                            # Parse the JSON string inside output field
                            output_string = first_item['output']
                            print(f"🔍 STEP 3 - output_string: {output_string}")
                            print(f"🔍 STEP 3 - output_string type: {type(output_string)}")
                            
                            parsed_data = json.loads(output_string)
                            print(f"🔍 STEP 4 - parsed_data: {json.dumps(parsed_data, indent=2)}")
                            print(f"🔍 STEP 4 - parsed_data agent_response: '{parsed_data.get('agent_response', 'NOT_FOUND')}'")
                            
                            logger.info(f"Parsed output data: {json.dumps(parsed_data, indent=2)}")
                            print(f"✅ Parsed output data: {json.dumps(parsed_data, indent=2)}")
                        except json.JSONDecodeError as e:
                            print(f"🔍 STEP 3 - JSON parse error: {e}")
                            logger.error(f"Failed to parse output JSON: {e}")
                            parsed_data = first_item
                    else:
                        print(f"🔍 STEP 2 - No 'output' field, using first_item directly")
                        parsed_data = first_item
                elif isinstance(n8n_response, dict):
                    # Handle direct object format - but check if it has output field first
                    print(f"🔍 STEP 2 - Direct dict format")
                    
                    if 'output' in n8n_response:
                        try:
                            # Parse the JSON string inside output field  
                            output_string = n8n_response['output']
                            print(f"🔍 STEP 2.1 - Dict has 'output' field: {output_string}")
                            print(f"🔍 STEP 2.1 - output_string type: {type(output_string)}")
                            
                            parsed_data = json.loads(output_string)
                            print(f"🔍 STEP 2.2 - parsed dict output: {json.dumps(parsed_data, indent=2)}")
                            print(f"🔍 STEP 2.2 - parsed dict agent_response: '{parsed_data.get('agent_response', 'NOT_FOUND')}'")
                        except json.JSONDecodeError as e:
                            print(f"🔍 STEP 2.1 - Dict JSON parse error: {e}")
                            parsed_data = n8n_response
                    else:
                        print(f"🔍 STEP 2.1 - Dict has no 'output' field, using directly")
                        parsed_data = n8n_response
                else:
                    print(f"🔍 STEP 2 - Unexpected format")
                    logger.error(f"Unexpected n8n response format: {type(n8n_response)}")
                    parsed_data = {}

            # Format response using parsed data
            print(f"🔍 STEP 5 - About to format response using parsed_data")
            print(f"🔍 STEP 5 - parsed_data.get('agent_response'): '{parsed_data.get('agent_response', 'NOT_FOUND')}'")
            
            formatted_response = {
                'status': parsed_data.get('status', 'success'),
                'agent_name': parsed_data.get('agent_name', agent_name),
                'agent_response': parsed_data.get('agent_response', ''),
                'conversation_state': parsed_data.get('conversation_state', 'complete'),
                'missing_info': parsed_data.get('missing_info', []),
                'output_action': parsed_data.get('output_action'),  # Add output_action to response
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"🔍 STEP 6 - Final formatted response agent_response: '{formatted_response.get('agent_response', 'NOT_FOUND')}'")
            
            logger.info(f"Final formatted response: {json.dumps(formatted_response, indent=2)}")
            print(f"📤 Final formatted response: {json.dumps(formatted_response, indent=2)}")

            return formatted_response

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    async def analyze_website_with_perplexity(self, website_url: str):
        """Analyze website using Perplexity API and return structured data"""
        try:
            if not PERPLEXITY_API_KEY:
                logger.error("PERPLEXITY_API_KEY not found in environment variables")
                return {}
                
            headers = {
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""
            Please analyze the website {website_url} and provide a summary in exactly this format:
            --- *Company name*: [Extract company name]
            --- *Website*: {website_url}
            --- *Contact Information*: [Any available contact details]
            --- *Description*: [2-3 sentence summary of what the company does]
            --- *Tags*: [Main business categories, separated by periods]
            --- *Takeaways*: [Key business value propositions]
            --- *Niche*: [Specific market focus or specialty]
            """
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers=headers,
                    json={
                        "model": "sonar-reasoning-pro",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1000,
                        "temperature": 0.2
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    logger.info(f"Perplexity analysis for {website_url}: {content[:200]}...")
                    
                    # Parse the structured response
                    parsed_analysis = {
                        'raw_content': content,
                        'url': website_url,
                        'analyzed_at': datetime.now().isoformat()
                    }
                    
                    # Extract structured data from response
                    for line in content.split('\n'):
                        if '---' in line and ':' in line:
                            key = line.split(':', 1)[0].replace('---', '').replace('*', '').strip().lower().replace(' ', '_')
                            value = line.split(':', 1)[1].strip()
                            parsed_analysis[key] = value
                    
                    return parsed_analysis
                else:
                    logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                    return {
                        'error': f"API request failed with status {response.status_code}",
                        'url': website_url,
                        'analyzed_at': datetime.now().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Error analyzing website {website_url} with Perplexity: {str(e)}")
            return {
                'error': str(e),
                'url': website_url,
                'analyzed_at': datetime.now().isoformat()
            }

    def _extract_conversation_insights(self, chat_history: List[Dict], website_context: List[Dict]) -> Dict[str, Any]:
        """Extract key insights from conversation history and website context"""
        insights = {
            'mentioned_urls': [],
            'user_requests': [],
            'agent_commitments': [],
            'pending_actions': [],
            'user_confirmations': []
        }
        
        try:
            # Extract URLs mentioned in conversation
            url_patterns = [
                r'https?://[^\s]+',
                r'www\.[^\s]+\.[a-zA-Z]{2,}',
                r'[^\s]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'
            ]
            
            for msg in chat_history:
                message_lower = msg['message'].lower()
                
                # Extract URLs
                import re
                for pattern in url_patterns:
                    urls = re.findall(pattern, msg['message'])
                    for url in urls:
                        if url not in insights['mentioned_urls']:
                            insights['mentioned_urls'].append(url)
                
                # Extract user requests and confirmations
                if msg['sender'] == 'User':
                    if any(word in message_lower for word in ['analyze', 'check', 'look at', 'review', 'examine']):
                        insights['user_requests'].append(msg['message'])
                    if any(phrase in message_lower for phrase in ['go ahead', 'please proceed', 'yes', 'continue', 'do it', 'sure']):
                        insights['user_confirmations'].append(msg['message'])
                
                # Extract agent commitments
                elif msg['sender'] == 'Agent':
                    if any(phrase in message_lower for phrase in ['i will', "i'll", 'let me', 'i can', 'i am going to']):
                        insights['agent_commitments'].append(msg['message'])
            
            # Check for pending actions (agent promised but user confirmed)
            if insights['agent_commitments'] and insights['user_confirmations']:
                insights['pending_actions'] = ['User has confirmed to proceed with agent analysis']
            
            # Add website analysis context
            if website_context:
                insights['analyzed_websites'] = [w['url'] for w in website_context]
            
            return insights
            
        except Exception as e:
            logger.warning(f"Error extracting conversation insights: {str(e)}")
            return insights

load_dotenv()
# Initialize FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    force=True
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import threading

# Thread-safe global variables with locks
active_connections: Dict[str, WebSocket] = {}
streaming_sessions: Dict[str, Dict[str, Any]] = {}
request_cache: Dict[str, float] = {}
_connections_lock = threading.Lock()
_requests_lock = threading.Lock()

# File processing status store for SSE streaming
# Key: file_id, Value: {status, message, progress, updated_at}
file_processing_status: Dict[str, Dict[str, Any]] = {}
_file_status_lock = threading.Lock()

def update_file_status(file_id: str, status: str, message: str, progress: int = 0):
    """Update file processing status for SSE streaming"""
    with _file_status_lock:
        file_processing_status[file_id] = {
            "status": status,
            "message": message,
            "progress": progress,
            "updated_at": datetime.utcnow().isoformat()
        }
        logger.info(f"File {file_id} status: {status} - {message} ({progress}%)")

# Environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
N8N_MAIN = os.getenv("N8N_MAIN", "https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d")
N8N_MAIN_TEST = os.getenv("N8N_MAIN_TEST")


print(f"Using Supabase URL: {SUPABASE_URL}")

# Initialize Supabase client
def create_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Initialize handlers
active_requests: Set[str] = set()

# Startup event handler removed - no longer needed

# Initialize Supabase client  
supabase = create_supabase_client()

# Initialize handlers
# agent_matcher = AgentMatcher(supabase_client=supabase)  # Removed
conversational_handler = ConversationalHandler(
    supabase_client=supabase,
    n8n_url=os.getenv('N8N_MAIN', 'https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d')
)
# client_kb_manager = ClientKBManager(supabase_client=supabase)  # Removed
# dynamic_agent_kb_handler = DynamicAgentKBHandler(supabase_client=supabase)  # Removed
file_processing_service = FileProcessingService(supabase_client=supabase)
background_processor = initialize_background_processor(supabase_client=supabase)

print("Application initialized")

background_results = {}
running_tasks: Dict[str, Dict[str, Any]] = {}

# openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

AGENT_DESCRIPTIONS = {
    "PersonalAssistant": "Personal Assistant Agent"
}


# Models
class WebsiteFaviconRequest(BaseModel):
    url: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class N8nMainRequest(BaseModel):
    user_id: str
    user_mssg: str
    session_id: str
    agent_name: str
    timestamp_of_call_made: Optional[str] = None
    request_id: Optional[str] = None

class N8nResponse(BaseModel):
    user_id: str
    agent_name: str
    agent_response: str
    responses: List[Dict[str, Any]]
    timestamp: str
    status: str

class StreamUpdate(BaseModel):
    type: str
    user_id: str
    agent_name: Optional[str] = None
    agent_names: Optional[str] = None
    message: str
    progress: int
    agent_response: Optional[str] = None
    metadata: dict

class ConversationState(Enum):
    INITIAL = "initial"
    COLLECTING_INFO = "collecting_info"
    PROCESSING = "processing"
    COMPLETE = "complete"

class N8nCheckAgentMatchRequest(BaseModel):
    agent_name: str
    user_query: str
    threshold: Optional[float] = 0.3

# GHL Webhook Models
class GHLMessageWebhook(BaseModel):
    """Model for incoming GHL message webhook - Updated to match actual payload"""
    ghl_location_id: str
    ghl_contact_id: str
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None  # Add phone field
    contact_email: Optional[str] = None  # Add email field
    contact_type: Optional[str] = None
    user_message: str
    social_media: Optional[str] = "SMS"  # SMS, Facebook, Instagram, etc.
    user_message_attachment: Optional[str] = None
    tag: Optional[str] = None
    agent_message: Optional[str] = None
    
    # Optional fields that might come from GHL
    timestamp: Optional[str] = None
    conversation_id: Optional[str] = None

class NotificationResponse(BaseModel):
    """Response model for notification endpoints"""
    success: bool
    notification_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None

class N8nFindBestAgentsRequest(BaseModel):
    user_query: str
    top_n: Optional[int] = 3
    min_threshold: Optional[float] = 0.3

class ClientKBCheckRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    force_refresh: Optional[bool] = False
    agent_name: Optional[str] = None

class ClientKBResponse(BaseModel):
    user_id: str
    has_website_info: bool
    website_url: Optional[str] = None
    website_analysis: Optional[Dict[str, Any]] = None
    company_info: Optional[Dict[str, Any]] = None
    kb_status: str
    message: str
    action_required: Optional[str] = None
    last_updated: Optional[str] = None
    agent_name: Optional[str] = None

class AgentKBQueryRequest(BaseModel):
    user_id: str
    user_mssg: str
    agent: str

class AgentKBQueryResponse(BaseModel):
    user_id: str
    agent: str
    response_type: str  # "direct_answer", "needs_tools", "needs_info"
    agent_response: Optional[str] = None
    required_tools: Optional[List[Dict[str, Any]]] = None
    follow_up_questions: Optional[List[str]] = None
    missing_information: Optional[List[Dict[str, Any]]] = None
    confidence_score: float
    kb_context_used: bool
    status: str

class WebsiteAnalysisRequest(BaseModel):
    url: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class WebsiteScreenshotRequest(BaseModel):
    url: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class WebsiteAnalysisRequest(BaseModel):
    url: str
    firm_user_id: str
    agent_id: Optional[str] = None
    firm_id: Optional[str] = None  # Will be auto-fetched from profiles table
    ghl_location_id: Optional[str] = None  # Will be auto-fetched from ghl_subaccounts
    ghl_user_id: Optional[str] = None  # Will be auto-fetched from ghl_subaccounts

# Solar API Models removed - solar_api_connector dependency removed

# New request model for complete website analysis
class WebsiteAnalysisCompleteRequest(BaseModel):
    url: str
    firm_user_id: str
    agent_id: Optional[str] = "web_analysis"

# URL normalization function to ensure consistent URL comparison
def normalize_url(url: str) -> str:
    """
    Normalize URL to consistent format: https://www.domain.com
    - Adds https:// if no protocol
    - Always adds www. prefix if not present
    - Removes trailing slashes
    - Converts to lowercase
    - Example: google.com -> https://www.google.com
    """
    from urllib.parse import urlparse, urlunparse

    url = url.strip().lower()

    # Add https:// if no protocol specified
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    parsed = urlparse(url)

    # Get the netloc (domain) and ensure www. prefix
    netloc = parsed.netloc
    if not netloc.startswith('www.'):
        netloc = 'www.' + netloc

    # Rebuild URL without trailing slash on path
    path = parsed.path.rstrip('/') or ''

    # Return normalized URL (always https://www.domain.com format)
    normalized = urlunparse((
        'https',  # Always use https
        netloc,   # Always www. prefix
        path,
        '',  # params
        '',  # query (remove for base comparison)
        ''   # fragment
    ))

    return normalized

# Conversational Handler Class
# API Endpoints
@app.get("/")
async def health_check():
    return {"status": "healthy", "message": "Squidgy AI WebSocket Server is running"}

@app.get("/health")
async def health_check_detailed():
    return {
        "status": "healthy",
        "active_connections": len(active_connections),
        "streaming_sessions": len(streaming_sessions)
    }

# Email validation endpoint removed - email_validation dependency removed


# WebSocket message processing function that calls n8n
async def process_websocket_message_with_n8n(request_data: Dict[str, Any], websocket: WebSocket, request_id: str):
    """Process WebSocket message through n8n workflow (same as HTTP endpoints)"""
    try:
        logger.info(f"Processing WebSocket message via n8n: {request_id}")
        
        # Use the same conversational handler as HTTP endpoints
        n8n_response = await conversational_handler.handle_message(request_data)
        
        logger.info(f"✅ n8n response received for request {request_id}")
        print(f"✅ n8n response received for request {request_id}")
        
        # Send response back through WebSocket
        try:
            # Check if we need to switch agents based on output_action
            output_action = n8n_response.get("output_action")
            current_agent = request_data.get("agent_name", "AI")
            target_agent = n8n_response.get("agent_name", current_agent)
            
            print(f"🔍 Agent switching check - Current: {current_agent}, Target: {target_agent}, Action: {output_action}")
            
            # Handle agent switching for need_website_info
            if output_action == "need_website_info" and target_agent != current_agent:
                # Send agent switch message
                transition_message = f"Hey, I will be able to better answer your question. {n8n_response.get('agent_response', '')}"
                
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json({
                        "type": "agent_switch",
                        "from_agent": current_agent,
                        "to_agent": target_agent,
                        "message": transition_message,
                        "requestId": request_id,
                        "session_id": request_data.get("session_id"),
                        "maintain_history": True,
                        "timestamp": int(time.time() * 1000)
                    })
                else:
                    logger.warning(f"WebSocket connection closed, cannot send agent switch for {request_id}")
                print(f"✅ Sent agent_switch message from {current_agent} to {target_agent}")
                
            elif n8n_response.get("agent_response"):
                # Normal agent response (same agent or different action)
                final_message = n8n_response.get("agent_response")
                
                # If it's need_website_info but same agent, add transition phrase
                if output_action == "need_website_info" and target_agent == current_agent:
                    final_message = f"Let me help you with that. {final_message}"
                
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json({
                        "type": "agent_response",
                        "agent": target_agent,
                        "message": final_message,
                        "requestId": request_id,
                        "final": True,
                        "output_action": output_action,
                        "timestamp": int(time.time() * 1000)
                    })
                else:
                    logger.warning(f"WebSocket connection closed, cannot send agent response for {request_id}")
                print(f"✅ Sent agent_response via WebSocket: {final_message[:100]}...")
            else:
                print(f"⚠️ No agent_response found in n8n_response to send via WebSocket")
                print(f"⚠️ n8n_response keys: {list(n8n_response.keys())}")
                print(f"⚠️ n8n_response content: {json.dumps(n8n_response, indent=2)}")
            
            logger.info(f"📤 Response sent via WebSocket for request {request_id}")
            print(f"📤 Response sent via WebSocket for request {request_id}")
        except Exception as ws_error:
            logger.error(f"❌ Failed to send WebSocket response for request {request_id}: {ws_error}")
            print(f"❌ Failed to send WebSocket response for request {request_id}: {ws_error}")
            raise
        
        # Save to chat history (same as HTTP endpoints)
        await conversational_handler.save_to_history(
            request_data["session_id"],
            request_data["user_id"], 
            request_data["user_mssg"],
            n8n_response.get("agent_response", "")
        )
        
        logger.info(f"✅ WebSocket message processed successfully: {request_id}")
        
    except Exception as e:
        logger.error(f"❌ Error processing WebSocket message {request_id}: {str(e)}")
        
        # Send error response with connection state check
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json({
                    "type": "error",
                    "requestId": request_id,
                    "error": str(e),
                    "timestamp": int(time.time() * 1000)
                })
            else:
                logger.warning(f"WebSocket connection closed, cannot send error response for {request_id}")
        except Exception as send_error:
            logger.error(f"Failed to send error response: {send_error}")


# Agent KB query endpoints with optimized database schema
@app.post("/n8n/agent/query")
async def agent_kb_query(request: AgentKBQueryRequest):
    """High-performance agent query with parallel processing and multi-level caching"""
    try:
        start_time = time.time()
        print(f"🚀 Starting optimized agent query for {request.agent}")
        
        # Check for URLs in the user message first
        detected_urls = extract_website_urls(request.user_mssg)
        contextual_prefix = ""
        
        if detected_urls:
            logger.info(f"Detected URLs in agent query: {detected_urls}")
            # Generate contextual response for detected URL
            contextual_response = await generate_contextual_response_for_detected_url(
                request.user_mssg, detected_urls[0], request.agent
            )
            
            # For now, return the contextual response immediately
            # This ensures users get immediate feedback instead of null responses
            enhanced_response = f"{contextual_response}\n\nI'm ready to analyze {detected_urls[0]} and provide specific insights about your business needs, pricing options, and recommendations based on what I find."
            
            logger.info(f"Returning immediate contextual response for URL: {detected_urls[0]}")
            return AgentKBQueryResponse(
                user_id=request.user_id,
                agent=request.agent,
                response_type="direct_answer",
                agent_response=enhanced_response,
                required_tools=None,
                confidence_score=0.85,
                kb_context_used=True,
                status="success"
            )
            
            # Keep the original contextual_prefix for additional processing if needed
            contextual_prefix = contextual_response + "\n\nNow let me analyze your website in detail:\n\n"
        
        # Check cache first for entire response
        cache_key = f"agent_query_{request.agent}_{hash(request.user_mssg)}_{request.user_id}"
        cached_response = await conversational_handler.get_cached_response(cache_key)
        if cached_response and not detected_urls:  # Don't use cache for URL queries
            print(f"⚡ Cache hit! Returning cached response in {int((time.time() - start_time) * 1000)}ms")
            return cached_response
        
        # Embedding generation removed - no longer needed
        
        parallel_start = time.time()
        # PARALLEL PROCESSING - Execute all database operations simultaneously
        agent_context_task = dynamic_agent_kb_handler.get_agent_context_from_kb(request.agent)
        client_context_task = get_optimized_client_context(request.user_id)
        agent_knowledge_task = get_optimized_agent_knowledge(request.agent)
        
        # Wait for all operations to complete in parallel
        agent_context, client_context, agent_knowledge = await asyncio.gather(
            agent_context_task,
            client_context_task, 
            agent_knowledge_task,
            return_exceptions=True
        )
        parallel_time = int((time.time() - parallel_start) * 1000)
        print(f"🔄 Parallel operations completed in {parallel_time}ms")
        
        # Handle any exceptions from parallel operations
        if isinstance(agent_context, Exception):
            print(f"⚠️ Agent context error: {agent_context}")
            agent_context = {}
        if isinstance(client_context, Exception):
            print(f"⚠️ Client context error: {client_context}")
            client_context = {}
        if isinstance(agent_knowledge, Exception):
            print(f"⚠️ Agent knowledge error: {agent_knowledge}")
            agent_knowledge = {}
        
        context_start = time.time()
        # Build comprehensive KB context from multiple sources
        kb_context = await build_enhanced_kb_context(
            request.user_id, 
            client_context, 
            agent_knowledge
        )
        context_time = int((time.time() - context_start) * 1000)
        print(f"📚 KB context built in {context_time}ms")
        
        # Check for must-have information requirements
        must_questions = agent_context.get('must_questions', [])
        missing_must_info = await check_missing_must_info(must_questions, kb_context, client_context)
        
        # Handle critical missing information
        if 'website_url' in missing_must_info:
            follow_up_questions = await dynamic_agent_kb_handler.generate_contextual_questions(
                request.user_mssg,
                agent_context,
                ['website_url'],
                client_context
            )
            
            # Log performance metrics
            execution_time = int((time.time() - start_time) * 1000)
            await log_performance_metric("agent_query_missing_info", execution_time, {
                "agent": request.agent,
                "user_id": request.user_id,
                "missing_info": missing_must_info
            })
            
            return AgentKBQueryResponse(
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
        
        # Analyze query with enhanced context
        analysis = await dynamic_agent_kb_handler.analyze_query_with_context(
            request.user_mssg,
            agent_context,
            client_context,
            kb_context
        )
        
        # Generate response based on analysis
        if analysis.get('can_answer') and analysis.get('confidence', 0) > 0.7:
            available_tools = agent_context.get('tools', [])
            required_tool_names = analysis.get('required_tools', [])
            tools_to_use = [t for t in available_tools if t['name'] in required_tool_names]
            
            agent_response = await dynamic_agent_kb_handler.generate_contextual_response(
                request.user_mssg,
                agent_context,
                client_context,
                kb_context,
                tools_to_use
            )
            
            # Prepend contextual prefix if URLs were detected
            if contextual_prefix:
                agent_response = f"{contextual_prefix}{agent_response}"
            
            # Create response object
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
            
            # Cache successful response for 2 minutes
            await conversational_handler.cache_response(cache_key, response, ttl=120)
            
            # Log successful performance with detailed timing
            execution_time = int((time.time() - start_time) * 1000)
            print(f"✅ Optimized agent query completed in {execution_time}ms (Target: <8000ms)")
            print(f"📊 Breakdown: Parallel({parallel_time}ms) + Context({context_time}ms)")
            
            await log_performance_metric("agent_query_success", execution_time, {
                "agent": request.agent,
                "user_id": request.user_id,
                "confidence": analysis.get('confidence', 0.8),
                "tools_used": len(tools_to_use),
                "context_sources": len(kb_context.get('sources', [])),
                "parallel_time_ms": parallel_time,
                "context_time_ms": context_time
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
            
            # Log performance for insufficient info case
            execution_time = int((time.time() - start_time) * 1000)
            await log_performance_metric("agent_query_needs_info", execution_time, {
                "agent": request.agent,
                "user_id": request.user_id,
                "missing_info_count": len(all_missing),
                "confidence": analysis.get('confidence', 0.5)
            })
            
            return AgentKBQueryResponse(
                user_id=request.user_id,
                agent=request.agent,
                response_type="needs_info",
                follow_up_questions=follow_up_questions,
                missing_information=missing_info_formatted,
                confidence_score=analysis.get('confidence', 0.5),
                kb_context_used=bool(kb_context),
                status="needs_more_info"
            )
            
    except Exception as e:
        # Log error performance with timing breakdown
        execution_time = int((time.time() - start_time) * 1000)
        print(f"❌ Agent query failed in {execution_time}ms: {str(e)}")
        
        await log_performance_metric("agent_query_error", execution_time, {
            "agent": request.agent,
            "user_id": request.user_id,
            "error": str(e)
        }, success=False, error_message=str(e))
        
        logger.error(f"Error in optimized agent_kb_query: {str(e)}")
        # If we detected URLs, at least return the contextual response
        error_response = "I encountered an error processing your request. Please try again."
        if contextual_prefix:
            error_response = f"{contextual_prefix}However, I encountered an error with the detailed analysis. Please try again."
        
        return AgentKBQueryResponse(
            user_id=request.user_id,
            agent=request.agent,
            response_type="direct_answer" if contextual_prefix else "error",
            agent_response=error_response,
            confidence_score=0.7 if contextual_prefix else 0.0,
            kb_context_used=bool(contextual_prefix),
            status="success" if contextual_prefix else "error"
        )

@app.post("/n8n/agent/query/wrapper")
async def n8n_agent_kb_query(request: Dict[str, Any]):
    """N8N-compatible version of agent KB query endpoint"""
    try:
        query_request = AgentKBQueryRequest(
            user_id=request.get('user_id'),
            user_mssg=request.get('user_mssg'),
            agent=request.get('agent')
        )
        
        response = await agent_kb_query(query_request)
        
        n8n_response = response.model_dump()
        
        if response.response_type == "direct_answer":
            n8n_response['workflow_action'] = 'send_response'
            n8n_response['next_node'] = 'format_and_send'
            
        elif response.response_type == "needs_tools":
            n8n_response['workflow_action'] = 'execute_tools'
            n8n_response['next_node'] = 'tool_executor'
            n8n_response['tool_sequence'] = [t['name'] for t in (response.required_tools or [])]
            
        elif response.response_type == "needs_info":
            n8n_response['workflow_action'] = 'collect_information'
            n8n_response['next_node'] = 'info_collector'
            n8n_response['ui_action'] = 'show_form'
            
        n8n_response['execution_metadata'] = {
            'timestamp': datetime.now().isoformat(),
            'agent_type': request.get('agent'),
            'has_context': response.kb_context_used,
            'confidence': response.confidence_score
        }
        
        return n8n_response
        
    except Exception as e:
        logger.error(f"Error in n8n_agent_kb_query: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'workflow_action': 'handle_error',
            'next_node': 'error_handler'
        }

@app.post("/n8n/agent/refresh_kb")
async def refresh_agent_kb(agent_name: str):
    """Refresh agent KB by re-reading from agent_documents"""
    try:
        result = supabase.table('agent_documents')\
            .select('id')\
            .eq('agent_name', agent_name)\
            .limit(1)\
            .execute()
        
        if result.data:
            return {
                'status': 'success',
                'message': f'Agent KB for {agent_name} is available',
                'document_count': len(result.data)
            }
        else:
            return {
                'status': 'not_found',
                'message': f'No KB documents found for agent: {agent_name}'
            }
            
    except Exception as e:
        logger.error(f"Error refreshing agent KB: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Main n8n endpoints
@app.post("/n8n_main_req/{agent_name}/{session_id}")
async def n8n_main_request(request: N8nMainRequest, agent_name: str, session_id: str):
    """Handle main request to n8n workflow with conversational logic"""
    try:
        # Generate a unique request ID
        request_id = request.request_id or str(uuid.uuid4())
        
        # Email verification removed - email_validation dependency removed
        
        request.agent_name = agent_name
        request.session_id = session_id
        
        # Skip empty messages
        if not request.user_mssg or request.user_mssg.strip() == "":
            logger.info("Skipping empty message")
            return {
                "status": "success",
                "message": "Empty message ignored",
                "request_id": request_id
            }
        
        # Deduplicate requests
        request_key = f"{session_id}:{request.user_mssg}:{agent_name}"
        current_time = time.time()
        
        # Check if duplicate within 2 seconds
        if request_key in request_cache:
            if current_time - request_cache[request_key] < 2.0:
                logger.info(f"Duplicate request detected: {request.user_mssg[:30]}...")
                return {
                    "status": "success",
                    "message": "Duplicate request ignored",
                    "request_id": request_id,
                    "agent_response": "Processing your previous message..."
                }
        
        request_cache[request_key] = current_time
        
        # Clean old cache entries
        for k in list(request_cache.keys()):
            if current_time - request_cache[k] > 10:
                del request_cache[k]
        
        # Only process the request if it's not an initial message or session change
        if request.user_mssg and request.user_mssg.strip() != "":
            request_data = {
                "user_id": request.user_id,
                "user_mssg": request.user_mssg,
                "session_id": request.session_id,
                "agent_name": request.agent_name,
                "timestamp_of_call_made": datetime.now().isoformat(),
                "request_id": request_id
            }
            
            # Check cache first
            cached_response = await conversational_handler.get_cached_response(request_id)
            if cached_response:
                logger.info(f"Returning cached response for request_id: {request_id}")
                return cached_response
                
            n8n_payload = await conversational_handler.handle_message(request_data)
            logger.info(f"Sending to n8n: {n8n_payload}")
            
            n8n_response = await call_n8n_webhook(n8n_payload)
            
            # Enhanced logging for debugging
            logger.debug(f"N8N Main Request - ID: {request_id}, Session: {session_id}, Agent: {agent_name}, Message: {request.user_mssg}, Response: {json.dumps(n8n_response, indent=2)}")
            
            logger.info(f"Received from n8n: {n8n_response}")
            
            formatted_response = {
                "user_id": n8n_response.get("user_id", request.user_id),
                "agent_name": n8n_response.get("agent_name", request.agent_name),
                "agent_response": n8n_response.get("agent_response", n8n_response.get("agent_responses", "")),
                "responses": n8n_response.get("responses", []),
                "timestamp": n8n_response.get("timestamp", datetime.now().isoformat()),
                "status": n8n_response.get("status", "success"),
                "request_id": request_id,
                "conversation_state": n8n_response.get("conversation_state", "complete"),
                "missing_info": n8n_response.get("missing_info", []),
                "images": extract_image_urls(n8n_response.get("agent_response", ""))
            }
            
            # Cache the response
            await conversational_handler.cache_response(request_id, formatted_response)
            
            await conversational_handler.save_to_history(
                request.session_id,
                request.user_id,
                request_data.get("_original_message", request.user_mssg),
                formatted_response["agent_response"]
            )
            
            return formatted_response
        else:
            # For initial messages or empty messages, just return a success response
            return {
                "status": "success",
                "message": "Initial message received",
                "request_id": request_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in n8n_main_request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/n8n_main_req_stream")
async def n8n_main_request_stream(request: N8nMainRequest):
    """Handle streaming request to n8n workflow"""
    try:
        if not request.timestamp_of_call_made:
            request.timestamp_of_call_made = datetime.now().isoformat()
        
        request_data = {
            "user_id": request.user_id,
            "user_mssg": request.user_mssg,
            "session_id": request.session_id,
            "agent_name": request.agent_name,
            "timestamp_of_call_made": request.timestamp_of_call_made
        }
        
        n8n_payload = await conversational_handler.handle_message(request_data)
        
        return StreamingResponse(
            stream_n8n_response(n8n_payload),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"Error in n8n_main_request_stream: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Streaming endpoint
@app.post("/api/stream")
async def receive_stream_update(update: StreamUpdate):
    """Endpoint that receives streaming updates from n8n and forwards to WebSocket clients"""
    try:
        connection_id = f"{update.user_id}_{update.metadata.get('session_id', '')}"
        
        session_key = f"{update.user_id}:{update.metadata.get('request_id', '')}"
        if session_key not in streaming_sessions:
            streaming_sessions[session_key] = {
                "updates": [],
                "complete": False
            }
        
        streaming_sessions[session_key]["updates"].append(update.model_dump())
        
        if update.type in ["complete", "final"]:
            streaming_sessions[session_key]["complete"] = True
        
        if connection_id in active_connections:
            websocket = active_connections[connection_id]
            await websocket.send_json({
                "type": update.type,
                "agent": update.agent_name or update.agent_names,
                "message": update.message,
                "progress": update.progress,
                "requestId": update.metadata.get("request_id"),
                "metadata": update.metadata,
                "timestamp": int(time.time() * 1000)
            })
            
            if update.type == "complete" and update.agent_response:
                await websocket.send_json({
                    "type": "agent_response",
                    "agent": update.agent_name,
                    "message": update.agent_response,
                    "requestId": update.metadata.get("request_id"),
                    "final": True,
                    "timestamp": int(time.time() * 1000)
                })
        
        return {"status": "received", "connection_id": connection_id}
        
    except Exception as e:
        logger.error(f"Error in receive_stream_update: {str(e)}")
        return {"status": "error", "error": str(e)}

# GHL Message Webhook Endpoint
@app.post("/api/webhooks/ghl/messages")
async def receive_ghl_message(
    webhook_data: GHLMessageWebhook,
    request: Request,
    x_ghl_signature: Optional[str] = Header(None)
):
    """
    Webhook endpoint to receive messages from GHL
    This will be called by GHL when a message is received
    """
    try:
        # Optional: Verify webhook signature if GHL provides one
        # You can set a webhook secret in GHL and verify it here
        webhook_secret = os.getenv("GHL_WEBHOOK_SECRET")
        if webhook_secret and x_ghl_signature:
            # Verify the signature (implementation depends on GHL's signature method)
            # This is a placeholder - adjust based on GHL's actual signature verification
            pass
        
        logger.info(f"Received GHL message webhook: {webhook_data.model_dump()}")
        
        # Generate a unique notification ID
        notification_id = str(uuid.uuid4())
        
        # Timestamp will be auto-generated by database trigger
        
        # Store notification in database with proper field mapping
        notification_data = {
            "id": notification_id,
            "ghl_location_id": webhook_data.ghl_location_id,
            "ghl_contact_id": webhook_data.ghl_contact_id,
            "message_content": webhook_data.user_message,
            "sender_name": webhook_data.contact_name,
            "sender_phone": webhook_data.contact_phone,  # Now provided in webhook
            "sender_email": webhook_data.contact_email,  # Now provided in webhook
            "message_type": webhook_data.social_media,
            # conversation_id will be auto-generated by database trigger
            "contact_type": webhook_data.contact_type,
            "message_attachment": webhook_data.user_message_attachment,
            "tag": webhook_data.tag,
            "agent_message": webhook_data.agent_message,
            "read_status": False,
            "responded_status": False,
            # created_at will be auto-generated by database (NOW())
            "metadata": {
                "original_payload": webhook_data.model_dump(),  # Store original for debugging
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Insert into notifications table
        result = supabase.table("notifications").insert(notification_data).execute()
        
        if result.data:
            logger.info(f"Notification saved successfully: {notification_id}")
            
            # Get the inserted notification with auto-generated fields
            inserted_notification = result.data[0] if result.data else {}
            conversation_id = inserted_notification.get("conversation_id", "")
            
            # Find the user associated with this GHL location
            # Query ghl_subaccounts table to find the user
            user_result = supabase.table("ghl_subaccounts").select("firm_user_id").eq("ghl_location_id", webhook_data.ghl_location_id).execute()
            
            if user_result.data and len(user_result.data) > 0:
                user_id = user_result.data[0]["firm_user_id"]
                logger.info(f"Found user {user_id} for location {webhook_data.ghl_location_id}")
                
                # Log active connections for debugging
                logger.info(f"Active WebSocket connections: {list(active_connections.keys())}")
                
                # Send real-time notification via WebSocket if user is connected
                connections_found = 0
                failed_connections = []
                
                for connection_id, websocket in active_connections.items():
                    if connection_id.startswith(f"{user_id}_"):
                        try:
                            # Check if WebSocket is still alive before sending
                            if websocket.client_state == WebSocketState.CONNECTED:
                                await websocket.send_json({
                                    "type": "notification",
                                    "notification_id": notification_id,
                                    "ghl_location_id": webhook_data.ghl_location_id,
                                    "ghl_contact_id": webhook_data.ghl_contact_id,
                                    "message": webhook_data.user_message,
                                    "sender_name": webhook_data.contact_name,
                                    "sender_phone": webhook_data.contact_phone,  # Add phone for frontend
                                    "sender_email": webhook_data.contact_email,  # Add email for frontend
                                    "message_type": webhook_data.social_media,
                                    "conversation_id": conversation_id,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "metadata": {
                                        "contact_type": webhook_data.contact_type,
                                        "user_message_attachment": webhook_data.user_message_attachment,
                                        "tag": webhook_data.tag,
                                        "agent_message": webhook_data.agent_message
                                    }
                                })
                                connections_found += 1
                                logger.info(f"Real-time notification sent to user {user_id} via connection {connection_id}")
                            else:
                                logger.warning(f"WebSocket connection {connection_id} is not active, marking for cleanup")
                                failed_connections.append(connection_id)
                        except Exception as ws_error:
                            logger.error(f"Error sending WebSocket notification to {connection_id}: {ws_error}")
                            failed_connections.append(connection_id)
                
                # Clean up failed connections
                for failed_connection_id in failed_connections:
                    if failed_connection_id in active_connections:
                        logger.info(f"Removing failed WebSocket connection: {failed_connection_id}")
                        del active_connections[failed_connection_id]
                
                if connections_found == 0:
                    logger.warning(f"No active WebSocket connections found for user {user_id}")
            else:
                logger.warning(f"No user mapping found for location {webhook_data.ghl_location_id}")
            
            return NotificationResponse(
                success=True,
                notification_id=notification_id,
                message="Notification received and stored successfully"
            )
        else:
            logger.error(f"Failed to save notification to database")
            return NotificationResponse(
                success=False,
                error="Failed to save notification to database"
            )
            
    except Exception as e:
        logger.error(f"Error in receive_ghl_message: {str(e)}")
        return NotificationResponse(
            success=False,
            error=str(e)
        )

# API endpoint to fetch notifications for a user
@app.get("/api/notifications/{user_id}")
async def get_user_notifications(
    user_id: str,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    unread_only: Optional[bool] = False
):
    """Get notifications for a specific user based on their GHL locations"""
    try:
        # First, get all GHL locations for this user
        locations_result = supabase.table("ghl_subaccounts").select("ghl_location_id").eq("firm_user_id", user_id).execute()
        
        if not locations_result.data:
            return {"notifications": [], "total": 0, "unread_count": 0}
        
        location_ids = [loc["ghl_location_id"] for loc in locations_result.data]
        
        # Build query for notifications
        query = supabase.table("notifications").select("*").in_("ghl_location_id", location_ids)
        
        if unread_only:
            query = query.eq("read_status", False)
        
        # Get total count
        count_query = supabase.table("notifications").select("*", count="exact").in_("ghl_location_id", location_ids)
        if unread_only:
            count_query = count_query.eq("read_status", False)
        count_result = count_query.execute()
        
        # Get unread count
        unread_count_result = supabase.table("notifications").select("*", count="exact").in_("ghl_location_id", location_ids).eq("read_status", False).execute()
        
        # Get notifications with pagination
        notifications_result = query.order("created_at", desc=True).limit(limit).offset(offset).execute()
        
        return {
            "notifications": notifications_result.data,
            "total": count_result.count if hasattr(count_result, 'count') else len(count_result.data),
            "unread_count": unread_count_result.count if hasattr(unread_count_result, 'count') else len(unread_count_result.data),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Mark notification as read
@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read"""
    try:
        result = supabase.table("notifications").update({"read_status": True}).eq("id", notification_id).execute()
        
        if result.data:
            return {"success": True, "message": "Notification marked as read"}
        else:
            raise HTTPException(status_code=404, detail="Notification not found")
            
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Mark all notifications as read for a user
@app.put("/api/notifications/user/{user_id}/read-all")
async def mark_all_notifications_read(user_id: str):
    """Mark all notifications as read for a user"""
    try:
        # Get user's GHL locations
        locations_result = supabase.table("ghl_subaccounts").select("ghl_location_id").eq("firm_user_id", user_id).execute()
        
        if not locations_result.data:
            return {"success": True, "message": "No notifications to update"}
        
        location_ids = [loc["ghl_location_id"] for loc in locations_result.data]
        
        # Update all unread notifications
        result = supabase.table("notifications").update({"read_status": True}).in_("ghl_location_id", location_ids).eq("read_status", False).execute()
        
        return {
            "success": True,
            "message": f"Marked {len(result.data)} notifications as read"
        }
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/website/analyze")
async def analyze_website_endpoint(request: WebsiteAnalysisRequest):
    """
    Endpoint 1: Analyze website using Perplexity AI - NO TIMEOUTS
    """
    try:
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""
        Please analyze the website {request.url} and provide a summary in exactly this format:
        --- *Company name*: [Extract company name]
        --- *Website*: {request.url}
        --- *Contact Information*: [Any available contact details]
        --- *Description*: [2-3 sentence summary of what the company does]
        --- *Tags*: [Main business categories, separated by periods]
        --- *Takeaways*: [Key business value propositions]
        --- *Niche*: [Specific market focus or specialty]
        """
        
        # NO TIMEOUT - let it take as long as needed
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json={
                    "model": "sonar-reasoning-pro",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis_text = result["choices"][0]["message"]["content"]
                
                # Parse the analysis
                parsed_analysis = {}
                lines = analysis_text.split('\n')
                for line in lines:
                    if '*Company name*:' in line:
                        parsed_analysis['company_name'] = line.split(':', 1)[1].strip()
                    elif '*Description*:' in line:
                        parsed_analysis['description'] = line.split(':', 1)[1].strip()
                    elif '*Niche*:' in line:
                        parsed_analysis['niche'] = line.split(':', 1)[1].strip()
                    elif '*Tags*:' in line:
                        parsed_analysis['tags'] = line.split(':', 1)[1].strip()
                    elif '*Takeaways*:' in line:
                        parsed_analysis['takeaways'] = line.split(':', 1)[1].strip()
                    elif '*Contact Information*:' in line:
                        parsed_analysis['contact_info'] = line.split(':', 1)[1].strip()
                
                # Save to database if user_id provided
                if request.user_id and request.session_id:
                    try:
                        supabase.table('website_data').upsert({
                            'user_id': request.user_id,
                            'session_id': request.session_id,
                            'url': request.url,
                            'analysis': json.dumps(parsed_analysis),
                            'created_at': datetime.now().isoformat()
                        }).execute()
                    except Exception as db_error:
                        logger.error(f"Error saving to database: {db_error}")
                
                return {
                    "status": "success",
                    "url": request.url,
                    "analysis": parsed_analysis,
                    "raw_analysis": analysis_text,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Perplexity API error: {response.status_code}",
                    "details": response.text
                }
                
    except Exception as e:
        logger.error(f"Error in analyze_website_endpoint: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/api/website/screenshot")
async def capture_website_screenshot_endpoint(request: WebsiteScreenshotRequest):
    """
    Endpoint 2: Capture full website screenshot
    Returns screenshot URL from Supabase Storage
    """
    try:
        # Use the async version
        result = await capture_website_screenshot(
            url=request.url,
            session_id=request.session_id
        )
        
        # If successful and user_id provided, update business profile
        if result['status'] == 'success' and request.user_id:
            try:
                # Get user profile to retrieve company_id (firm_id)
                user_profile = supabase.table('profiles')\
                    .select('company_id')\
                    .eq('user_id', request.user_id)\
                    .execute()

                if user_profile.data and len(user_profile.data) > 0:
                    firm_id = user_profile.data[0].get('company_id')

                    supabase.table('business_profiles').upsert({
                        'firm_id': firm_id,
                        'firm_user_id': request.user_id,
                        'screenshot_url': result.get('public_url'),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }, on_conflict='firm_user_id').execute()
                    logger.info(f"Business profile updated with screenshot for user: {request.user_id}")
                else:
                    logger.warning(f"User profile not found for user_id: {request.user_id}, skipping business profile update")
            except Exception as profile_error:
                logger.error(f"Error updating business profile with screenshot: {profile_error}")

        return {
            "status": result['status'],
            "message": result['message'],
            "screenshot_url": result.get('public_url'),
            "storage_path": result.get('path'),
            "filename": result.get('filename'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in capture_website_screenshot_endpoint: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "screenshot_url": None
        }

@app.post("/api/website/favicon")
async def get_website_favicon_endpoint(request: WebsiteFaviconRequest):
    """
    Endpoint 3: Extract and save website favicon/logo
    Returns favicon URL from Supabase Storage
    """
    try:
        # Use the async version
        result = await get_website_favicon_async(
            url=request.url,
            session_id=request.session_id
        )
        
        # If successful and user_id provided, update business profile
        if result['status'] == 'success' and request.user_id:
            try:
                supabase.table('business_profiles').upsert({
                    'firm_user_id': request.user_id,
                    'favicon_url': result.get('public_url'),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }, on_conflict='firm_user_id').execute()
                logger.info(f"Business profile updated with favicon for user: {request.user_id}")
            except Exception as profile_error:
                logger.error(f"Error updating business profile with favicon: {profile_error}")
        
        return {
            "status": result['status'],
            "message": result.get('message', 'Favicon processed'),
            "favicon_url": result.get('public_url'),
            "storage_path": result.get('path'),
            "filename": result.get('filename'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in get_website_favicon_endpoint: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "favicon_url": None
        }


# Add this endpoint to main.py if it doesn't exist
@app.get("/chat-history")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    try:
        result = supabase.table('chat_history')\
            .select('*')\
            .eq('session_id', session_id)\
            .order('timestamp', desc=False)\
            .execute()
        
        if result.data:
            history = []
            for msg in result.data:
                history.append({
                    'sender': 'AI' if msg['sender'] == 'agent' else 'User',
                    'message': msg['message'],
                    'timestamp': msg['timestamp']
                })
            return {'history': history, 'status': 'success'}
        else:
            return {'history': [], 'status': 'success'}
            
    except Exception as e:
        logger.error(f"Error fetching chat history: {str(e)}")
        return {'history': [], 'status': 'error', 'error': str(e)}

# Application logs endpoint

# Keep last 100 log entries in memory
app_logs = deque(maxlen=100)

# Custom log handler to capture logs
class InMemoryLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = {
            'timestamp': record.created,
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName
        }
        app_logs.append(log_entry)

# Add the handler to the logger
memory_handler = InMemoryLogHandler()
memory_handler.setLevel(logging.INFO)
logger.addHandler(memory_handler)

@app.get("/logs")
async def get_application_logs(limit: int = 50):
    """Get recent application logs"""
    try:
        # Get last N logs
        recent_logs = list(app_logs)[-limit:]
        
        # Format logs for response
        formatted_logs = []
        for log in recent_logs:
            formatted_logs.append({
                'timestamp': datetime.fromtimestamp(log['timestamp']).isoformat(),
                'level': log['level'],
                'message': log['message'],
                'module': log['module'],
                'function': log['function']
            })
        
        return {
            'status': 'success',
            'logs': formatted_logs,
            'count': len(formatted_logs),
            'total_available': len(app_logs)
        }
    except Exception as e:
        logger.error(f"Error fetching logs: {str(e)}")
        return {
            'status': 'error',
            'message': str(e),
            'logs': []
        }


# WebSocket endpoint
@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, session_id: str):
    """WebSocket endpoint that routes through n8n with streaming support"""
    connection_id = f"{user_id}_{session_id}"
    logger.debug(f"New WebSocket connection: {connection_id}")
    
    await websocket.accept()
    
    # Email verification removed - email_validation dependency removed
    
    active_connections[connection_id] = websocket
    
    async def send_ping():
        """Send periodic ping to keep connection alive"""
        while connection_id in active_connections:
            try:
                await asyncio.sleep(30)  # Ping every 30 seconds
                if connection_id in active_connections:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": int(time.time() * 1000)
                    })
            except Exception:
                break
    
    # Start ping task
    ping_task = asyncio.create_task(send_ping())
    
    try:
        # Send initial connection status
        await websocket.send_json({
            "type": "connection_status",
            "status": "connected",
            "message": "WebSocket connection established",
            "timestamp": int(time.time() * 1000)
        })
        
        while True:
            try:
                # Use timeout to prevent hanging
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                message_data = json.loads(data)
                
                request_id = message_data.get("requestId", str(uuid.uuid4()))
                
                user_input = message_data.get("message", "").strip()
                
                # Handle ping/pong and skip processing for empty messages  
                if message_data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": int(time.time() * 1000)
                    })
                    continue
                elif message_data.get("type") == "pong":
                    continue
                elif not user_input or message_data.get("type") == "connection_status":
                    continue
                    
                # Check if this request is already being processed
                if request_id in active_requests:
                    logger.info(f"Request {request_id} is already being processed, skipping")
                    continue
                    
                active_requests.add(request_id)
                
                try:
                    await websocket.send_json({
                        "type": "ack",
                        "requestId": request_id,
                        "message": "Message received, processing...",
                        "timestamp": int(time.time() * 1000)
                    })
                    
                    # Use the working conversational handler (same as HTTP endpoints)
                    request_data = {
                        "user_id": user_id,
                        "user_mssg": user_input,
                        "session_id": session_id,
                        "agent_name": message_data.get("agent", "presaleskb"),
                        "timestamp_of_call_made": datetime.now().isoformat()
                    }
                    
                    # Process via conversational handler (calls n8n webhook)
                    # Don't await here to keep WebSocket responsive, but ensure task completion
                    task = asyncio.create_task(
                        process_websocket_message_with_n8n(request_data, websocket, request_id)
                    )
                    
                    # Add task completion callback for debugging
                    def task_done_callback(task_result):
                        try:
                            if task_result.exception():
                                logger.error(f"❌ WebSocket task failed for {request_id}: {task_result.exception()}")
                                print(f"❌ WebSocket task failed for {request_id}: {task_result.exception()}")
                            else:
                                logger.info(f"✅ WebSocket task completed successfully for {request_id}")
                                print(f"✅ WebSocket task completed successfully for {request_id}")
                        except Exception as e:
                            logger.error(f"Error in task callback: {e}")
                            print(f"Error in task callback: {e}")
                    
                    task.add_done_callback(task_done_callback)
                    
                finally:
                    active_requests.discard(request_id)
                    
            except asyncio.TimeoutError:
                # Timeout is normal - just send a ping to verify connection is alive
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": int(time.time() * 1000)
                    })
                except Exception:
                    logger.info(f"Connection {connection_id} appears dead, closing")
                    break
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received, skipping")
                continue
                
    except WebSocketDisconnect:
        logger.debug(f"Client disconnected: {connection_id}")
    
    except ConnectionResetError as conn_err:
        logger.warning(f"Connection reset for {connection_id}: {str(conn_err)}")
        
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {str(e)}")
        
    finally:
        # Cancel ping task
        ping_task.cancel()
        # Remove connection from active connections
        if connection_id in active_connections:
            del active_connections[connection_id]
        logger.debug(f"WebSocket connection closed and cleaned up: {connection_id}")


def extract_image_urls(text: str) -> List[str]:
    """Extract Supabase storage URLs from text"""
    import re
    # Match Supabase storage URLs
    pattern = r'https://[^\s]+\.supabase\.co/storage/v1/[^\s]+\.(png|jpg|jpeg|gif|webp)'
    return re.findall(pattern, text, re.IGNORECASE)

def extract_website_urls(text: str) -> List[str]:
    """Extract website URLs from text"""
    import re
    # Match various URL patterns
    patterns = [
        r'https?://[^\s]+',  # http:// or https://
        r'www\.[^\s]+\.[a-zA-Z]{2,}',  # www.example.com
        r'[^\s]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'  # example.com or example.com/path
    ]
    
    urls = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        urls.extend(matches)
    
    # Filter out obvious non-URLs and clean up
    cleaned_urls = []
    for url in urls:
        # Remove trailing punctuation
        url = re.sub(r'[.,;!?]+$', '', url)
        
        # Skip if it's clearly not a website (email, file extensions, etc.)
        if any(url.lower().endswith(ext) for ext in ['.jpg', '.png', '.pdf', '.doc', '.zip']):
            continue
        if '@' in url and '.' in url:  # Likely an email
            continue
        if len(url.split('.')) < 2:  # Must have at least one dot
            continue
            
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            if url.startswith('www.'):
                url = 'https://' + url
            else:
                # Check if it looks like a domain
                if '.' in url and len(url.split('.')[-1]) >= 2:
                    url = 'https://' + url
        
        cleaned_urls.append(url)
    
    return list(set(cleaned_urls))  # Remove duplicates


@app.post("/api/website/analyze-background")
async def analyze_website_background(request: WebsiteAnalysisRequest, background_tasks: BackgroundTasks):
    """
    Start website analysis in background and return task ID immediately
    This avoids any timeout issues
    """
    task_id = str(uuid.uuid4())
    
    async def run_analysis():
        try:
            result = await analyze_website_endpoint(request)
            background_results[task_id] = {
                "status": "completed",
                "result": result,
                "completed_at": datetime.now().isoformat()
            }
        except Exception as e:
            background_results[task_id] = {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }
    
    # Start the background task
    background_tasks.add_task(run_analysis)
    
    background_results[task_id] = {
        "status": "processing",
        "started_at": datetime.now().isoformat(),
        "url": request.url
    }
    
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Analysis started in background",
        "check_url": f"/api/website/task/{task_id}"
    }

@app.get("/api/website/task/{task_id}")
async def get_background_task_result(task_id: str):
    """Check the status of a background task"""
    if task_id not in background_results:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return background_results[task_id]

@app.post("/api/send-invitation-email")
async def send_invitation_email(request: dict):
    """Send invitation email using Supabase Auth with profile creation"""
    try:
        email = request.get('email')
        token = request.get('token')
        sender_name = request.get('senderName', 'Someone')
        invite_url = request.get('inviteUrl')
        sender_id = request.get('senderId')
        sender_email = request.get('senderEmail')
        company_id = request.get('companyId')
        group_id = request.get('groupId')
        
        if not email or not token or not invite_url:
            return {
                "success": False,
                "error": "Missing required fields",
                "details": f"Missing: {', '.join([k for k, v in {'email': email, 'token': token, 'invite_url': invite_url}.items() if not v])}"
            }
        
        logger.info(f"Creating invitation and sending email to: {email}")
        print(f"Backend: Creating invitation for {email}")
        
        # Initialize invitation handler
        invitation_handler = InvitationHandler(supabase)
        
        # Get sender details if not provided
        if not sender_id or not company_id:
            if sender_email:
                sender_result = supabase.from_('profiles').select(
                    'user_id, company_id, full_name'
                ).eq('email', sender_email.lower()).single().execute()
                
                if sender_result.data:
                    sender_id = sender_result.data['user_id']
                    company_id = sender_result.data['company_id']
                    sender_name = sender_result.data.get('full_name', sender_name)
                else:
                    return {
                        "success": False,
                        "error": "Sender not found",
                        "details": f"No profile found for sender email: {sender_email}"
                    }
            else:
                return {
                    "success": False,
                    "error": "Missing sender information",
                    "details": "Either senderId/companyId or senderEmail must be provided"
                }
        
        # Create invitation with profile
        try:
            print(f"Backend: Creating invitation with profile for {email}")
            
            # Call the database function through RPC
            result = supabase.rpc(
                'create_invitation_with_profile',
                {
                    'p_sender_id': sender_id,
                    'p_recipient_email': email.lower().strip(),
                    'p_sender_company_id': company_id,
                    'p_group_id': group_id,
                    'p_token': token
                }
            ).execute()
            
            # Parse the result
            invitation_result = result.data
            if isinstance(invitation_result, list) and len(invitation_result) > 0:
                invitation_result = invitation_result[0]
            
            if not invitation_result or not invitation_result.get('success'):
                error_msg = invitation_result.get('error', 'Unknown error') if invitation_result else 'No result from database function'
                return {
                    "success": False,
                    "error": "Failed to create invitation",
                    "details": f"Database error: {error_msg}",
                    "fallback_url": invite_url
                }
            
            print(f"Backend: Invitation created successfully - ID: {invitation_result.get('invitation_id')}")
            print(f"Backend: Profile ID: {invitation_result.get('profile_id')}, Recipient ID: {invitation_result.get('recipient_id')}")
            
            # Now send the email
            try:
                response = supabase.auth.admin.invite_user_by_email(
                    email.lower(),
                    {
                        "redirect_to": invite_url,
                        "data": {
                            "invitation_token": token,
                            "sender_name": sender_name,
                            "invitation_id": str(invitation_result.get('invitation_id')),
                            "recipient_id": str(invitation_result.get('recipient_id'))
                        }
                    }
                )
                
                logger.info(f"Invitation created and email sent successfully to {email}")
                
                return {
                    "success": True,
                    "message": "Invitation created and email sent successfully!",
                    "details": invitation_result.get('message', 'Invitation created with profile'),
                    "invitation_id": str(invitation_result.get('invitation_id')),
                    "recipient_id": str(invitation_result.get('recipient_id')),
                    "method": "admin_invite_with_profile"
                }
                
            except Exception as email_error:
                logger.error(f"Email sending error: {str(email_error)}")
                # Invitation created but email failed
                return {
                    "success": True,
                    "message": "Invitation created but email sending failed",
                    "invitation_id": str(invitation_result.get('invitation_id')),
                    "recipient_id": str(invitation_result.get('recipient_id')),
                    "fallback_url": invite_url,
                    "email_error": str(email_error),
                    "suggestion": "Invitation was created successfully. Share the link manually or retry sending email."
                }
                
        except Exception as db_error:
            logger.error(f"Database error creating invitation: {str(db_error)}")
            return {
                "success": False,
                "error": "Failed to create invitation",
                "details": f"Database error: {str(db_error)}",
                "fallback_url": invite_url
            }
            
    except Exception as e:
        logger.error(f"Invitation endpoint error: {str(e)}")
        print(f"Backend: Invitation endpoint error: {str(e)}")
        return {
            "success": False,
            "error": "Backend invitation processing failed",
            "details": str(e)
        }

@app.post("/api/auth/reset-password")
async def reset_password_email(request: dict):
    """Send password reset email using Supabase Auth"""
    try:
        email = request.get('email')
        
        if not email:
            return {
                "success": False,
                "error": "Email is required"
            }
        
        # Get redirect URL from request or use default
        redirect_url = request.get('redirect_url', 'https://boiler-plate-v1-lake.vercel.app/auth/reset-password')
        
        logger.info(f"Sending password reset email to: {email}")
        
        # Use Supabase client to send password reset email
        try:
            # Use the correct method name for the Python client
            response = supabase.auth.reset_password_for_email(
                email=email.lower(),
                options={
                    "redirect_to": redirect_url
                }
            )
            
            logger.info(f"Password reset email sent successfully to {email}")
            
            return {
                "success": True,
                "message": "Password reset link sent! Please check your email."
            }
            
        except Exception as auth_error:
            logger.error(f"Supabase auth error: {str(auth_error)}")
            
            # Return error directly - no retries
            return {
                "success": False,
                "error": str(auth_error),
                "message": "Failed to send password reset email"
            }
            
    except Exception as e:
        logger.error(f"Password reset endpoint error: {str(e)}")
        return {
            "success": False,
            "error": "Failed to process password reset request",
            "details": str(e)
        }

@app.post("/api/auth/update-password")
async def update_password(request: dict):
    """Update user password using reset token"""
    try:
        token = request.get('token')
        new_password = request.get('password')
        
        if not token or not new_password:
            return {
                "success": False,
                "error": "Token and password are required"
            }
        
        # Update password using Supabase Auth with token verification
        try:
            # First verify the token and update password in one go
            response = supabase.auth.verify_otp({
                'token': token,
                'type': 'recovery'  # This is for password reset tokens
            })
            
            if response.user:
                # Now update the password using the verified session
                update_response = supabase.auth.update_user({
                    'password': new_password
                })
                
                if update_response.user:
                    logger.info(f"Password updated successfully for user: {response.user.id}")
                    return {
                        "success": True,
                        "message": "Password updated successfully!",
                        "user_id": response.user.id
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to update password after token verification"
                    }
            else:
                return {
                    "success": False,
                    "error": "Invalid or expired reset token"
                }
                
        except Exception as auth_error:
            logger.error(f"Supabase password update error: {str(auth_error)}")
            return {
                "success": False,
                "error": "Invalid or expired reset token",
                "details": str(auth_error)
            }
            
    except Exception as e:
        logger.error(f"Update password endpoint error: {str(e)}")
        return {
            "success": False,
            "error": "Failed to update password",
            "details": str(e)
        }


@app.post("/api/auth/signup")
async def backend_signup_api(request: dict):
    """Backend signup endpoint to bypass Supabase auth issues"""
    try:
        email = request.get('email')
        password = request.get('password')
        full_name = request.get('full_name')
        
        if not email or not password or not full_name:
            return {
                "success": False,
                "error": "Email, password, and full name are required"
            }
        
        print(f"[BACKEND SIGNUP] Creating user: {email}")
        
        # Create user using admin API (service role) - RESTORE PROPER AUTH
        try:
            print(f"[BACKEND SIGNUP] 🔧 Attempting to fix Supabase auth issue...")
            
            # Since existing users work, let's try a different approach
            # First, let's check if there are any database maintenance modes or limits
            
            user_response = supabase.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,  # Auto-confirm email
                "user_metadata": {
                    "full_name": full_name
                }
            })
            
            if user_response.user:
                print(f"[BACKEND SIGNUP] ✅ User created: {user_response.user.id}")
                
                # Create profile manually
                profile_data = {
                    'user_id': user_response.user.id,
                    'company_id': str(uuid.uuid4()),
                    'email': email,
                    'full_name': full_name,
                    'role': 'user'
                }
                
                profile_result = supabase.table('profiles').insert(profile_data).execute()
                print(f"[BACKEND SIGNUP] ✅ Profile created")
                
                # Trigger GHL registration
                try:
                    print(f"[BACKEND SIGNUP] 🚀 Starting GHL registration...")
                    ghl_payload = {
                        'full_name': full_name,
                        'email': email
                    }
                    
                    # Call our own GHL endpoint
                    import httpx
                    async with httpx.AsyncClient() as client:
                        ghl_response = await client.post(
                            'http://0.0.0.0:8000/api/ghl/create-subaccount-and-user-registration',
                            json=ghl_payload,
                            timeout=30.0
                        )
                        print(f"[BACKEND SIGNUP] GHL Response: {ghl_response.status_code}")
                
                except Exception as ghl_error:
                    print(f"[BACKEND SIGNUP] ⚠️ GHL registration failed: {ghl_error}")
                    # Don't fail the whole signup if GHL fails
                
                return {
                    "success": True,
                    "message": "Account created successfully!",
                    "user": {
                        "id": user_response.user.id,
                        "email": email,
                        "full_name": full_name
                    }
                }
            else:
                raise Exception("Failed to create user")
                
        except Exception as auth_error:
            print(f"[BACKEND SIGNUP] ❌ Auth error: {auth_error}")
            
            # DETAILED ERROR INVESTIGATION
            print(f"[BACKEND SIGNUP] 🔍 Investigating auth error...")
            print(f"[BACKEND SIGNUP]    Error type: {type(auth_error).__name__}")
            print(f"[BACKEND SIGNUP]    Error message: {str(auth_error)}")
            
            # Check if it's a specific database constraint issue
            if "Database error creating new user" in str(auth_error):
                # This might be a corrupted trigger or constraint
                # Let's try to identify what specifically is failing
                
                # Check current user count and limits
                try:
                    current_users = supabase.auth.admin.list_users()
                    print(f"[BACKEND SIGNUP] 📊 Current user count: {len(current_users)}")
                    
                    # Try to see if there are any specific patterns in recent successful users
                    if current_users:
                        latest_user = current_users[0]  # Most recent
                        print(f"[BACKEND SIGNUP] 📅 Latest successful user: {latest_user.email} at {latest_user.created_at}")
                        
                except Exception as count_error:
                    print(f"[BACKEND SIGNUP] ❌ Cannot check user count: {count_error}")
                
            return {
                "success": False,
                "error": f"Supabase authentication system error. Please contact support with error: {str(auth_error)}",
                "technical_details": {
                    "error_type": type(auth_error).__name__,
                    "error_message": str(auth_error),
                    "suggested_action": "Check Supabase dashboard for auth service status"
                }
            }
            
    except Exception as e:
        print(f"[BACKEND SIGNUP] ❌ General error: {e}")
        return {
            "success": False,
            "error": f"Signup failed: {str(e)}"
        }

@app.post("/api/auth/confirm-signup")
async def confirm_signup_api(request: dict):
    """Backend API endpoint to confirm user signup - called by frontend"""
    try:
        user_id = request.get('user_id')
        token = request.get('token')
        
        # If we have a token, try to get user_id from it
        if token and not user_id:
            try:
                response = supabase.auth.verify_otp({'token': token, 'type': 'email'})
                if response.user:
                    user_id = response.user.id
            except:
                pass
        
        if not user_id:
            return {"success": False, "error": "user_id required"}
        
        # Update email_confirmed to True
        supabase.table('profiles').update({'email_confirmed': True}).eq('user_id', user_id).execute()
        
        return {"success": True, "message": "Email confirmed successfully!"}
        
    except Exception as e:
        logger.error(f"Confirm signup error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/auth/confirm-email")
async def confirm_email_endpoint(request: dict):
    """Confirm user email address and update profile"""
    try:
        # Extract parameters - support both token-based and direct user_id confirmation
        token = request.get('token')
        user_id = request.get('user_id')
        email = request.get('email')
        
        logger.info(f"Email confirmation request: token={bool(token)}, user_id={user_id}, email={email}")
        
        # Method 1: Token-based confirmation (when user clicks email link)
        if token:
            try:
                # Verify the token with Supabase Auth
                response = supabase.auth.verify_otp({
                    'token': token,
                    'type': 'email'
                })
                
                if response.user:
                    user_id = response.user.id
                    email = response.user.email
                    logger.info(f"Token verified successfully for user: {user_id}, email: {email}")
                else:
                    return {
                        "success": False,
                        "error": "Invalid or expired confirmation token"
                    }
                    
            except Exception as token_error:
                logger.error(f"Token verification error: {str(token_error)}")
                return {
                    "success": False,
                    "error": "Invalid or expired confirmation token",
                    "details": str(token_error)
                }
        
        # Method 2: Direct confirmation (when user_id is provided)
        elif user_id:
            logger.info(f"Direct confirmation for user_id: {user_id}")
        else:
            return {
                "success": False,
                "error": "Either token or user_id is required for email confirmation"
            }
        
        # Update the profiles table to mark email as confirmed
        try:
            logger.info(f"Updating email_confirmed=true for user_id: {user_id}")
            
            update_result = supabase.table('profiles')\
                .update({
                    'email_confirmed': True,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })\
                .eq('user_id', user_id)\
                .execute()
            
            if update_result.data:
                logger.info(f"✅ Email confirmed successfully for user: {user_id}")
                
                # Get updated profile info
                profile_result = supabase.table('profiles')\
                    .select('email, full_name, email_confirmed')\
                    .eq('user_id', user_id)\
                    .single()\
                    .execute()
                
                profile_data = profile_result.data if profile_result.data else {}
                
                return {
                    "success": True,
                    "message": "Email confirmed successfully! You can now access all features.",
                    "user_id": user_id,
                    "email": profile_data.get('email', email),
                    "full_name": profile_data.get('full_name'),
                    "email_confirmed": True
                }
            else:
                logger.warning(f"No profile found for user_id: {user_id}")
                return {
                    "success": False,
                    "error": "User profile not found",
                    "user_id": user_id
                }
                
        except Exception as db_error:
            logger.error(f"Database update error for user {user_id}: {str(db_error)}")
            return {
                "success": False,
                "error": "Failed to update email confirmation status",
                "details": str(db_error)
            }
    
    except Exception as e:
        logger.error(f"Email confirmation endpoint error: {str(e)}")
        return {
            "success": False,
            "error": "Failed to process email confirmation",
            "details": str(e)
        }

@app.get("/api/auth/confirm-email")
async def confirm_email_get_endpoint(token: str = None, user_id: str = None):
    """Handle email confirmation via GET request (for email links)"""
    try:
        logger.info(f"GET email confirmation: token={bool(token)}, user_id={user_id}")
        
        # Call the POST endpoint logic
        request_data = {}
        if token:
            request_data['token'] = token
        if user_id:
            request_data['user_id'] = user_id
            
        result = await confirm_email_endpoint(request_data)
        
        # For GET requests, we might want to redirect or return HTML
        if result.get('success'):
            return {
                "success": True,
                "message": "Email confirmed successfully! You can now close this window and return to the application.",
                "data": result
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"GET email confirmation error: {str(e)}")
        return {
            "success": False,
            "error": "Failed to process email confirmation",
            "details": str(e)
        }

@app.get("/confirm-email", response_class=HTMLResponse)
async def email_confirmation_page():
    """Serve email confirmation HTML page"""
    try:
        # Read the HTML file
        html_file_path = os.path.join(os.path.dirname(__file__), "email_confirmation_page.html")
        
        if os.path.exists(html_file_path):
            with open(html_file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            return HTMLResponse(content=html_content, status_code=200)
        else:
            # Fallback HTML if file doesn't exist
            fallback_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Email Confirmation - Squidgy</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .container { max-width: 500px; margin: 0 auto; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🦑 Squidgy Email Confirmation</h1>
                    <p>Confirming your email address...</p>
                    <script>
                        const urlParams = new URLSearchParams(window.location.search);
                        const token = urlParams.get('token');
                        const userId = urlParams.get('user_id');
                        
                        if (token || userId) {
                            fetch('/api/auth/confirm-email', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ token: token, user_id: userId })
                            })
                            .then(response => response.json())
                            .then(result => {
                                if (result.success) {
                                    document.body.innerHTML = '<div class="container"><h1>✅ Email Confirmed!</h1><p>Thank you! You can now close this window.</p></div>';
                                } else {
                                    document.body.innerHTML = '<div class="container"><h1>❌ Confirmation Failed</h1><p>' + (result.error || 'Unknown error') + '</p></div>';
                                }
                            })
                            .catch(error => {
                                document.body.innerHTML = '<div class="container"><h1>❌ Error</h1><p>Unable to confirm email. Please try again.</p></div>';
                            });
                        } else {
                            document.body.innerHTML = '<div class="container"><h1>❌ Invalid Link</h1><p>This confirmation link is invalid.</p></div>';
                        }
                    </script>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=fallback_html, status_code=200)
            
    except Exception as e:
        logger.error(f"Error serving email confirmation page: {str(e)}")
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error - Squidgy</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>❌ Error</h1>
            <p>Unable to load email confirmation page.</p>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)

# =============================================================================
# TOOL ENDPOINTS - Organized Tools Integration
# =============================================================================

# Solar endpoints removed - tools_connector dependency removed

@app.get("/api/website/screenshot")
async def website_screenshot_endpoint(url: str, session_id: str = None):
    """Capture website screenshot"""
    try:
        result = await capture_website_screenshot(url, session_id)
        return result
    except Exception as e:
        logger.error(f"Error in website screenshot endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/website/favicon")
async def website_favicon_endpoint(url: str, session_id: str = None):
    """Get website favicon"""
    try:
        result = await get_website_favicon_async(url, session_id)
        return result
    except Exception as e:
        logger.error(f"Error in website favicon endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/website/analysis")
async def website_analysis_endpoint(request: WebsiteAnalysisRequest):
    """
    Analyze website and upsert into website_analysis table
    Performs upsert based on firm_user_id and website_url
    """
    try:
        # Initialize web analysis client
        web_client = WebAnalysisClient()
        
        # Get website analysis from external endpoint
        analysis_result = web_client.analyze_website(request.url)
        
        if not analysis_result['success']:
            return {
                "status": "error",
                "message": f"Website analysis failed: {analysis_result.get('error', 'Unknown error')}"
            }
        
        # Parse the analysis response text
        analysis_data = analysis_result.get('data', {})
        response_text = analysis_data.get('response_text', '')
        
        # Extract key information from the response
        company_name = None
        company_description = response_text  # Store the full analysis as company description
        business_domain = None
        
        # Simple extraction from the first page title
        if 'TITLE:' in response_text:
            title_start = response_text.find('TITLE:') + 6
            title_end = response_text.find('\n', title_start)
            if title_end > title_start:
                company_name = response_text[title_start:title_end].strip()
        
        # Extract domain from URL
        from urllib.parse import urlparse
        parsed_url = urlparse(request.url)
        business_domain = parsed_url.netloc
        
        # Get user profile to retrieve firm_id (required)
        if not request.firm_id:
            try:
                user_profile = supabase.table('profiles')\
                    .select('company_id')\
                    .eq('user_id', request.firm_user_id)\
                    .execute()
                
                if user_profile.data and len(user_profile.data) > 0:
                    request.firm_id = user_profile.data[0].get('company_id')
                    logger.info(f"Fetched firm_id: {request.firm_id} for user: {request.firm_user_id}")
                else:
                    return {
                        "status": "error",
                        "message": f"User profile not found for firm_user_id: {request.firm_user_id}"
                    }
                    
                if not request.firm_id:
                    return {
                        "status": "error",
                        "message": f"No company_id found in user profile for firm_user_id: {request.firm_user_id}"
                    }
                    
            except Exception as profile_error:
                logger.error(f"Could not fetch user profile: {profile_error}")
                return {
                    "status": "error",
                    "message": f"Failed to fetch user profile: {str(profile_error)}"
                }
        
        # Get GHL subaccount data if not provided
        ghl_location_id = request.ghl_location_id
        ghl_user_id = request.ghl_user_id
        
        if not ghl_location_id or not ghl_user_id:
            try:
                ghl_subaccount = supabase.table('ghl_subaccounts')\
                    .select('ghl_location_id, soma_ghl_user_id')\
                    .eq('firm_user_id', request.firm_user_id)\
                    .eq('agent_id', request.agent_id or 'web_analysis')\
                    .execute()
                
                if ghl_subaccount.data and len(ghl_subaccount.data) > 0:
                    subaccount = ghl_subaccount.data[0]
                    ghl_location_id = ghl_location_id or subaccount.get('ghl_location_id')
                    ghl_user_id = ghl_user_id or subaccount.get('soma_ghl_user_id')
                    logger.info(f"Found GHL subaccount data: location_id={ghl_location_id}, user_id={ghl_user_id}")
            except Exception as ghl_error:
                logger.warning(f"Could not fetch GHL subaccount data: {ghl_error}")
        
        # Prepare upsert data
        upsert_data = {
            'firm_user_id': request.firm_user_id,
            'agent_id': request.agent_id or 'web_analysis',
            'firm_id': request.firm_id,
            'website_url': request.url,
            'company_name': company_name,
            'company_description': company_description,
            'business_domain': business_domain,
            'analysis_status': 'completed',
            'last_updated_timestamp': datetime.now(timezone.utc).isoformat(),
            'ghl_location_id': ghl_location_id,
            'ghl_user_id': ghl_user_id
        }
        
        # Remove None values and clean the data
        upsert_data = {k: v for k, v in upsert_data.items() if v is not None}
        
        # Debug: log the upsert data
        logger.info(f"Upsert data: {upsert_data}")
        
        # Manual upsert: check if record exists, then update or insert
        existing = supabase.table('website_analysis')\
            .select('id')\
            .eq('firm_user_id', request.firm_user_id)\
            .eq('agent_id', request.agent_id or 'web_analysis')\
            .eq('firm_id', request.firm_id)\
            .execute()
        
        if existing.data and len(existing.data) > 0:
            # Update existing record
            record_id = existing.data[0]['id']
            result = supabase.table('website_analysis')\
                .update(upsert_data)\
                .eq('id', record_id)\
                .execute()
        else:
            # Insert new record
            result = supabase.table('website_analysis')\
                .insert(upsert_data)\
                .execute()
        
        # Return the exact same response as the external scraping service (raw text)
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=response_text, media_type="text/plain")
        
    except Exception as e:
        logger.error(f"Error in website analysis endpoint: {str(e)}")
        return {
            "status": "error",
            "message": f"Website analysis failed: {str(e)}"
        }

# GHL contact endpoints removed - tools_connector dependency removed

# =============================================================================
# WEBSITE ANALYSIS COMPLETE ENDPOINT (with background screenshot/favicon)
# =============================================================================

async def capture_screenshot_independent(
    url: str,
    firm_user_id: str,
    agent_id: str,
    firm_id: str
):
    """
    INDEPENDENT task to capture ONLY screenshot - runs completely async.
    Updates website_analysis table with screenshot_url.
    Fire-and-forget - doesn't block the API response.
    """
    try:
        # Wait 2 seconds to ensure the API response is sent to user first
        await asyncio.sleep(2)

        logger.info(f"[ASYNC SCREENSHOT] Starting independent screenshot capture for {url}")

        # Capture screenshot
        screenshot_result = await capture_website_screenshot(url, firm_user_id)

        # Update database if successful
        if isinstance(screenshot_result, dict) and screenshot_result.get('status') == 'success':
            screenshot_url = screenshot_result.get('public_url')
            normalized_url = normalize_url(url)

            # Update the website_analysis record
            supabase.table('website_analysis')\
                .update({
                    'screenshot_url': screenshot_url,
                    'last_updated_timestamp': datetime.now(timezone.utc).isoformat()
                })\
                .eq('firm_user_id', firm_user_id)\
                .eq('agent_id', agent_id)\
                .eq('firm_id', firm_id)\
                .execute()

            logger.info(f"[ASYNC SCREENSHOT] ✓ Screenshot saved: {screenshot_url}")
        else:
            logger.warning(f"[ASYNC SCREENSHOT] ✗ Screenshot capture failed: {screenshot_result}")

    except Exception as e:
        logger.error(f"[ASYNC SCREENSHOT] Error: {str(e)}")


async def capture_favicon_independent(
    url: str,
    firm_user_id: str,
    agent_id: str,
    firm_id: str
):
    """
    INDEPENDENT task to capture ONLY favicon - runs completely async.
    Updates website_analysis table with favicon_url.
    Fire-and-forget - doesn't block the API response.
    """
    try:
        # Wait 3 seconds (slightly offset from screenshot to avoid resource contention)
        await asyncio.sleep(3)

        logger.info(f"[ASYNC FAVICON] Starting independent favicon capture for {url}")

        # Capture favicon
        favicon_result = await get_website_favicon_async(url, firm_user_id)

        # Update database if successful
        if isinstance(favicon_result, dict) and favicon_result.get('status') == 'success':
            favicon_url = favicon_result.get('public_url')
            normalized_url = normalize_url(url)

            # Update the website_analysis record
            supabase.table('website_analysis')\
                .update({
                    'favicon_url': favicon_url,
                    'last_updated_timestamp': datetime.now(timezone.utc).isoformat()
                })\
                .eq('firm_user_id', firm_user_id)\
                .eq('agent_id', agent_id)\
                .eq('firm_id', firm_id)\
                .execute()

            logger.info(f"[ASYNC FAVICON] ✓ Favicon saved: {favicon_url}")
        else:
            logger.warning(f"[ASYNC FAVICON] ✗ Favicon capture failed: {favicon_result}")

    except Exception as e:
        logger.error(f"[ASYNC FAVICON] Error: {str(e)}")


async def capture_brand_colors_independent(
    url: str,
    firm_user_id: str,
    agent_id: str,
    firm_id: str
):
    """
    INDEPENDENT task to extract brand colors - runs completely async.
    Updates website_analysis table with brand_colors.
    Fire-and-forget - doesn't block the API response.
    """
    try:
        # Wait 1 second before starting (less than screenshot/favicon as it's lighter)
        await asyncio.sleep(1)

        logger.info(f"[ASYNC COLORS] Starting independent brand color extraction for {url}")

        # Extract colors in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        brand_colors = await loop.run_in_executor(None, extract_colors_from_website, url)

        # Update database if we got colors
        if brand_colors and len(brand_colors) > 0:
            normalized_url = normalize_url(url)

            # Update the website_analysis record
            supabase.table('website_analysis')\
                .update({
                    'brand_colors': brand_colors,
                    'last_updated_timestamp': datetime.now(timezone.utc).isoformat()
                })\
                .eq('firm_user_id', firm_user_id)\
                .eq('agent_id', agent_id)\
                .eq('firm_id', firm_id)\
                .execute()

            logger.info(f"[ASYNC COLORS] ✓ Extracted and saved {len(brand_colors)} brand colors")
        else:
            logger.warning(f"[ASYNC COLORS] ✗ No brand colors extracted from {url}")

    except Exception as e:
        logger.error(f"[ASYNC COLORS] Error: {str(e)}")


async def capture_screenshot_and_favicon_independent(
    url: str,
    firm_user_id: str,
    agent_id: str,
    firm_id: str
):
    """
    DEPRECATED: Use capture_screenshot_independent() and capture_favicon_independent() separately.

    INDEPENDENT task to capture screenshot and favicon - runs completely async.
    This is fire-and-forget - doesn't block the API response.
    Waits 2 seconds before starting to ensure response is sent first.
    """
    try:
        # Wait 2 seconds to ensure the API response is sent to user first
        await asyncio.sleep(2)

        logger.info(f"[ASYNC CAPTURE] Starting independent capture for {url}")

        # Run screenshot and favicon capture in parallel
        screenshot_task = capture_website_screenshot(url, firm_user_id)
        favicon_task = get_website_favicon_async(url, firm_user_id)

        screenshot_result, favicon_result = await asyncio.gather(
            screenshot_task,
            favicon_task,
            return_exceptions=True
        )

        # Prepare update data
        update_data = {
            'last_updated_timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Add screenshot URL if successful
        if isinstance(screenshot_result, dict) and screenshot_result.get('status') == 'success':
            update_data['screenshot_url'] = screenshot_result.get('public_url')
            logger.info(f"[ASYNC CAPTURE] Screenshot captured: {update_data['screenshot_url']}")
        else:
            logger.warning(f"[ASYNC CAPTURE] Screenshot capture failed: {screenshot_result}")

        # Add favicon URL if successful
        if isinstance(favicon_result, dict) and favicon_result.get('status') == 'success':
            update_data['favicon_url'] = favicon_result.get('public_url')
            logger.info(f"[ASYNC CAPTURE] Favicon captured: {update_data['favicon_url']}")
        else:
            logger.warning(f"[ASYNC CAPTURE] Favicon capture failed: {favicon_result}")

        # Update the website_analysis record
        if 'screenshot_url' in update_data or 'favicon_url' in update_data:
            normalized_url = normalize_url(url)
            supabase.table('website_analysis')\
                .update(update_data)\
                .eq('firm_user_id', firm_user_id)\
                .eq('agent_id', agent_id)\
                .eq('firm_id', firm_id)\
                .execute()
            logger.info(f"[ASYNC CAPTURE] Completed and database updated for {url}")

    except Exception as e:
        logger.error(f"[ASYNC CAPTURE] Error in independent capture: {str(e)}")


async def capture_screenshot_and_favicon_background(
    url: str,
    firm_user_id: str,
    agent_id: str,
    firm_id: str
):
    """
    DEPRECATED: Use capture_screenshot_and_favicon_independent() instead.
    Background task to capture screenshot and favicon, then update website_analysis table.
    Runs after analysis response is returned to user.
    """
    try:
        logger.info(f"Starting background capture for {url} (firm_user_id: {firm_user_id})")

        # Run screenshot and favicon capture in parallel
        screenshot_task = capture_website_screenshot(url, firm_user_id)
        favicon_task = get_website_favicon_async(url, firm_user_id)

        screenshot_result, favicon_result = await asyncio.gather(
            screenshot_task,
            favicon_task,
            return_exceptions=True
        )

        # Prepare update data
        update_data = {
            'last_updated_timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Add screenshot URL if successful
        if isinstance(screenshot_result, dict) and screenshot_result.get('status') == 'success':
            update_data['screenshot_url'] = screenshot_result.get('public_url')
            logger.info(f"Screenshot captured: {update_data['screenshot_url']}")
        else:
            logger.warning(f"Screenshot capture failed: {screenshot_result}")

        # Add favicon URL if successful
        if isinstance(favicon_result, dict) and favicon_result.get('status') == 'success':
            update_data['favicon_url'] = favicon_result.get('public_url')
            logger.info(f"Favicon captured: {update_data['favicon_url']}")
        else:
            logger.warning(f"Favicon capture failed: {favicon_result}")

        # Update the website_analysis record
        if 'screenshot_url' in update_data or 'favicon_url' in update_data:
            normalized_url = normalize_url(url)
            supabase.table('website_analysis')\
                .update(update_data)\
                .eq('firm_user_id', firm_user_id)\
                .eq('agent_id', agent_id)\
                .eq('firm_id', firm_id)\
                .execute()
            logger.info(f"Background capture completed and database updated for {url}")

    except Exception as e:
        logger.error(f"Error in background screenshot/favicon capture: {str(e)}")


async def analyze_website_content_with_ai(scraped_content: str, url: str) -> dict:
    """
    Use AI to analyze scraped website content and extract structured fields.

    Args:
        scraped_content: The raw scraped content from the website
        url: The website URL for context

    Returns:
        dict with extracted fields: company_name, value_proposition, business_niche, tags
    """
    logger.info(f"🤖 analyze_website_content_with_ai() CALLED for {url}")
    print(f"\n🤖 analyze_website_content_with_ai() CALLED for {url}", flush=True)

    # Check if API key is set
    if not OPENROUTER_API_KEY:
        logger.error(f"❌ OPENROUTER_API_KEY is not set!")
        print(f"❌ OPENROUTER_API_KEY is not set!", flush=True)
        return {
            "company_name": None,
            "value_proposition": None,
            "business_niche": None,
            "tags": None
        }

    logger.info(f"✓ API key is set (length: {len(OPENROUTER_API_KEY)})")
    print(f"✓ API key is set (length: {len(OPENROUTER_API_KEY)})", flush=True)

    try:
        from openai import AsyncOpenAI
        logger.info("✓ Imported AsyncOpenAI")
        print("✓ Imported AsyncOpenAI", flush=True)

        # Use OpenRouter API (compatible with OpenAI SDK)
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        logger.info("✓ Created OpenRouter client")
        print(f"✓ Created OpenRouter client", flush=True)

        # Strip out filler text to check actual content size
        filler_patterns = [
            "="*80,
            "WEBSITE SCRAPING RESULTS",
            "END OF SCRAPING RESULTS",
            "-"*80,
            "Total pages scraped:",
            "URL:",
            "Depth Level:",
            "Status:",
            "TITLE:",
        ]

        actual_content = scraped_content
        for pattern in filler_patterns:
            actual_content = actual_content.replace(pattern, "")

        # Remove extra whitespace and newlines
        actual_content = "\n".join(line.strip() for line in actual_content.split("\n") if line.strip())

        # Calculate actual content size in bytes
        actual_content_bytes = len(actual_content.encode('utf-8'))

        logger.info(f"📊 Content size: {len(scraped_content)} bytes total, {actual_content_bytes} bytes actual content")
        print(f"📊 Content size: {len(scraped_content)} bytes total, {actual_content_bytes} bytes actual content", flush=True)

        # If actual content is less than 500 bytes, use OpenRouter Web Search fallback
        if actual_content_bytes < 500:
            logger.warning(f"⚠️ Minimal content ({actual_content_bytes} < 500), triggering OpenRouter fallback")
            print(f"⚠️ Minimal content ({actual_content_bytes} < 500), triggering OpenRouter fallback", flush=True)
            logger.warning(f"Minimal actual content detected ({actual_content_bytes} bytes < 500 bytes threshold) for {url}, using OpenRouter Web Search")
            from Website.web_analysis import openrouter_web_search_fallback

            # Use OpenRouter to get better content
            fallback_result = openrouter_web_search_fallback(url)
            if fallback_result.get('status') != 'error' and fallback_result.get('content'):
                scraped_content = fallback_result.get('content')
                logger.info(f"✓ Using OpenRouter Web Search content for analysis")
                print(f"✓ Using OpenRouter Web Search content for analysis", flush=True)
            else:
                logger.warning(f"⚠️ OpenRouter fallback also failed, proceeding with minimal content")
                print(f"⚠️ OpenRouter fallback also failed, proceeding with minimal content", flush=True)

        # Create AI prompt to extract structured information
        logger.info(f"📄 Content preview (first 300 chars): {scraped_content[:300]}...")
        print(f"📄 Content preview (first 300 chars): {scraped_content[:300]}...", flush=True)

        prompt = f"""Analyze the following website content and extract key business information.

Website URL: {url}
Website Content:
{scraped_content}

Extract and provide the following information in JSON format:
{{
  "company_name": "The company or product name",
  "value_proposition": "A concise statement (1-2 sentences) explaining the unique value or benefit this company/product offers",
  "business_niche": "The specific industry, market segment, or business category (e.g., 'Fitness & Wellness', 'SaaS Project Management', 'E-commerce Fashion')",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"] // 3-5 relevant keywords or categories
}}

Guidelines:
- If the company name is not clearly stated, extract it from the title or domain
- Value proposition should focus on WHAT they offer and WHY it matters to customers
- Business niche should be specific (2-4 words describing their market)
- Tags should be relevant keywords for categorization (lowercase, no special characters)
- If any field cannot be determined from the content, use null

Provide ONLY the JSON response, no additional text."""

        # Call OpenRouter API
        logger.info(f"🌐 Calling OpenRouter API with model: deepseek/deepseek-chat")
        print(f"🌐 Calling OpenRouter API with model: deepseek/deepseek-chat", flush=True)

        response = await client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://app.squidgy.ai",
                "X-Title": "Squidgy AI Website Analyzer"
            },
            model="deepseek/deepseek-chat",  # Cost-effective model good for structured extraction
            messages=[
                {"role": "system", "content": "You are a business analyst expert at extracting key information from website content. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )

        logger.info(f"✓ OpenRouter API call completed")
        print(f"✓ OpenRouter API call completed", flush=True)

        # Parse the AI response
        ai_response = response.choices[0].message.content.strip()
        logger.info(f"📝 AI response (first 200 chars): {ai_response[:200]}...")
        print(f"📝 AI response (first 200 chars): {ai_response[:200]}...", flush=True)

        # Extract JSON from response (handle cases where AI adds markdown code blocks)
        import json
        import re

        # Try to find JSON in the response
        logger.info(f"🔍 Extracting JSON from AI response")
        print(f"🔍 Extracting JSON from AI response", flush=True)

        json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            logger.info(f"✓ Found JSON in markdown code block")
            print(f"✓ Found JSON in markdown code block", flush=True)
        else:
            # Try to find JSON without code blocks
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                logger.info(f"✓ Found JSON without code block")
                print(f"✓ Found JSON without code block", flush=True)
            else:
                json_str = ai_response
                logger.info(f"⚠️ No JSON pattern found, using raw response")
                print(f"⚠️ No JSON pattern found, using raw response", flush=True)

        # Parse JSON
        logger.info(f"📦 Parsing JSON string (length: {len(json_str)} chars)")
        print(f"📦 Parsing JSON string (length: {len(json_str)} chars)", flush=True)
        extracted_data = json.loads(json_str)

        logger.info(f"✅ Successfully extracted data: {extracted_data}")
        print(f"✅ Successfully extracted data: {extracted_data}", flush=True)
        return extracted_data

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"❌ Error in AI analysis: {str(e)}")
        logger.error(f"❌ Full traceback:\n{error_details}")
        print(f"\n❌ ERROR in AI analysis: {str(e)}", flush=True)
        print(f"❌ Full traceback:\n{error_details}", flush=True)
        # Return empty structure on error
        return {
            "company_name": None,
            "value_proposition": None,
            "business_niche": None,
            "tags": None
        }


@app.post("/api/website/analysis_complete")
async def website_analysis_complete_endpoint(
    request: WebsiteAnalysisCompleteRequest,
    background_tasks: BackgroundTasks
):
    """
    Complete website analysis endpoint:
    1. Check if record exists for firm_user_id + website_url (normalized)
    2. If exists with data -> return cached values
    3. If not -> run analysis, return response, then capture screenshot/favicon in background
    """
    try:
        # Normalize the URL for consistent comparison
        normalized_url = normalize_url(request.url)
        logger.info(f"Processing analysis_complete for URL: {normalized_url} (original: {request.url})")

        # Get firm_id from profiles table
        user_profile = supabase.table('profiles')\
            .select('company_id')\
            .eq('user_id', request.firm_user_id)\
            .execute()

        if not user_profile.data or len(user_profile.data) == 0:
            return {
                "status": "error",
                "message": f"User profile not found for firm_user_id: {request.firm_user_id}"
            }

        firm_id = user_profile.data[0].get('company_id')
        if not firm_id:
            return {
                "status": "error",
                "message": f"No company_id found in user profile for firm_user_id: {request.firm_user_id}"
            }

        logger.info(f"Found firm_id: {firm_id} for user: {request.firm_user_id}")

        # Check if exact record exists for (firm_user_id, agent_id, firm_id, website_url)
        existing_record = supabase.table('website_analysis')\
            .select('*')\
            .eq('firm_user_id', request.firm_user_id)\
            .eq('agent_id', request.agent_id)\
            .eq('firm_id', firm_id)\
            .eq('website_url', normalized_url)\
            .order('last_updated_timestamp', desc=True)\
            .limit(1)\
            .execute()

        # CASE 1: Exact match (including URL) exists -> return cached record
        if existing_record.data and len(existing_record.data) > 0:
            cached_record = existing_record.data[0]
            logger.info(f"Cache hit: exact match found for (firm_user_id={request.firm_user_id}, agent_id={request.agent_id}, url={normalized_url})")

            # Get cached brand colors from database (or empty if not yet extracted)
            brand_colors = cached_record.get('brand_colors', [])

            # If no cached brand colors, fire async task to extract them in background
            if not brand_colors or len(brand_colors) == 0:
                logger.info(f"No cached brand colors - firing async extraction")
                asyncio.create_task(
                    capture_brand_colors_independent(
                        request.url,
                        request.firm_user_id,
                        request.agent_id,
                        firm_id
                    )
                )

            return {
                "status": "success",
                "cached": True,
                "data": {
                    "company_name": cached_record.get('company_name'),
                    "company_description": cached_record.get('company_description'),
                    "value_proposition": cached_record.get('value_proposition'),
                    "business_niche": cached_record.get('business_niche'),
                    "business_domain": cached_record.get('business_domain'),
                    "tags": cached_record.get('tags'),
                    "screenshot_url": cached_record.get('screenshot_url'),
                    "favicon_url": cached_record.get('favicon_url'),
                    "website_url": cached_record.get('website_url'),
                    "brand_colors": brand_colors  # Cached colors or empty (will be populated async)
                },
                "message": "Analysis retrieved from cache"
            }

        # CASE 2: No exact match -> run fresh analysis and INSERT new record
        logger.info(f"🔍 CASE 2: Running fresh analysis for {normalized_url}")
        print(f"\n🔍 CASE 2: Running fresh analysis for {normalized_url}", flush=True)

        # ========== TRY 1: Direct web scraping with httpx + BeautifulSoup (fast, accurate) ==========
        # Try to scrape the website directly first - more accurate than web search
        # Falls back to OpenRouter web search if: 403 error, timeout, or insufficient content
        use_fallback = False
        ai_extracted = None
        response_text = None

        try:
            logger.info(f"📡 Attempting direct web scraping for {request.url}")
            print(f"📡 Attempting direct web scraping for {request.url}", flush=True)

            from bs4 import BeautifulSoup

            # Fetch website with httpx (timeout: 15s)
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as http_client:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                }
                fetch_response = await http_client.get(request.url, headers=headers)

                # Check for error status codes
                if fetch_response.status_code == 403:
                    logger.warning(f"⚠️ 403 Forbidden - falling back to web search")
                    print(f"⚠️ 403 Forbidden - falling back to web search", flush=True)
                    use_fallback = True
                elif fetch_response.status_code >= 400:
                    logger.warning(f"⚠️ HTTP {fetch_response.status_code} - falling back to web search")
                    print(f"⚠️ HTTP {fetch_response.status_code} - falling back to web search", flush=True)
                    use_fallback = True
                else:
                    # Parse HTML content
                    soup = BeautifulSoup(fetch_response.text, 'html.parser')

                    # Remove unwanted elements
                    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                        element.decompose()

                    # Extract text content
                    text_content = soup.get_text(separator='\n', strip=True)

                    # Clean up whitespace
                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    cleaned_content = '\n'.join(lines)

                    content_length = len(cleaned_content)
                    logger.info(f"✓ Scraped {content_length} characters of text")
                    print(f"✓ Scraped {content_length} characters of text", flush=True)

                    # Check if we have sufficient content (at least 200 chars of meaningful text)
                    if content_length < 200:
                        logger.warning(f"⚠️ Insufficient content ({content_length} < 200 chars) - falling back to web search")
                        print(f"⚠️ Insufficient content ({content_length} < 200 chars) - falling back to web search", flush=True)
                        use_fallback = True
                    else:
                        # We have good content! Truncate to 8000 chars to avoid token limits
                        response_text = cleaned_content[:8000]

                        logger.info(f"✓ Direct scraping successful - using actual website content")
                        print(f"✓ Direct scraping successful - using actual website content", flush=True)

                        # Analyze the scraped content with AI
                        logger.info(f"🤖 Analyzing scraped content with AI")
                        print(f"🤖 Analyzing scraped content with AI", flush=True)

                        ai_extracted = await analyze_website_content_with_ai(response_text, request.url)
                        logger.info(f"✓ AI analysis completed from scraped content")
                        print(f"✓ AI analysis completed from scraped content", flush=True)

        except httpx.TimeoutException:
            logger.warning(f"⚠️ Scraping timeout - falling back to web search")
            print(f"⚠️ Scraping timeout - falling back to web search", flush=True)
            use_fallback = True
        except Exception as scrape_error:
            logger.warning(f"⚠️ Scraping error: {str(scrape_error)} - falling back to web search")
            print(f"⚠️ Scraping error: {str(scrape_error)} - falling back to web search", flush=True)
            use_fallback = True

        # ========== FALLBACK: Use OpenRouter Web Search API if scraping failed ==========
        if use_fallback or not ai_extracted:
            logger.info(f"🌐 Using OpenRouter Web Search API fallback for {request.url}")
            print(f"🌐 Using OpenRouter Web Search API fallback for {request.url}", flush=True)

            # Analysis prompt template (used for both free and paid models)
            # Define this BEFORE the try block so it's available in the fallback
            import json
            import re

            analysis_prompt = f"""Visit the website {request.url} directly and analyze its actual content.

IMPORTANT: You must actually visit and read the website content at {request.url}.
Do not make assumptions based on the domain name or search for similar companies.
Analyze the ACTUAL website content you find.

Please provide in JSON format:
{{
  "company_name": "The company or product name",
  "company_description": "A comprehensive 8-10 sentence description covering: what the company does, their main products/services, who they serve, what makes them notable or unique in their space, their key features, target audience, competitive advantages, and business model",
  "value_proposition": "A concise statement (1-2 sentences) explaining the unique value or benefit this company/product offers",
  "business_niche": "The specific industry or market segment (e.g., 'E-commerce Platform', 'SaaS Analytics', 'Fintech')",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Guidelines:
- company_description should be detailed (8-10 complete sentences)
- Focus on WHAT they offer and WHY it matters
- Be specific about their market/industry
- Use 3-5 relevant keywords as tags
- If any field cannot be determined, use null

Provide ONLY valid JSON, no additional text."""

            try:
                # Use PAID model directly (FREE model too slow/unreliable - takes 60+ seconds, causes timeouts)
                # PAID model: deepseek/deepseek-chat - Only $0.14/1M tokens (basically free)
                # Completes in ~13 seconds (well under Heroku's 30s timeout)
                # See: https://openrouter.ai/docs/guides/features/plugins/web-search
                async with httpx.AsyncClient() as http_client:
                    response = await http_client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://app.squidgy.ai",
                            "X-Title": "Squidgy AI Website Analyzer"
                        },
                        json={
                            "model": "deepseek/deepseek-chat",  # PAID but cheap ($0.14/1M tokens), fast & reliable
                            "plugins": [{"id": "web", "engine": "native", "max_results": 5}],
                            "messages": [{
                                "role": "user",
                                "content": analysis_prompt
                            }],
                            "temperature": 0.3,
                            "max_tokens": 1500
                        },
                        timeout=20.0  # Reduced to 20s to allow time for fallback before Heroku's 30s timeout
                    )

                    response.raise_for_status()
                    data = response.json()

                logger.info(f"✓ OpenRouter API returned 200 OK")
                print(f"✓ OpenRouter API returned 200 OK", flush=True)

                # Check if response has expected structure
                if 'choices' not in data or len(data['choices']) == 0:
                    raise Exception(f"Invalid API response structure: {data}")

                ai_response = data['choices'][0]['message']['content'].strip()
                response_length = len(ai_response)
                logger.info(f"✓ OpenRouter Web Search completed (PAID model: deepseek-chat), response length: {response_length}")
                print(f"✓ OpenRouter Web Search completed (PAID model: deepseek-chat), response length: {response_length}", flush=True)

                # Check response size - if too large, might cause issues
                if response_length > 10000:
                    logger.warning(f"⚠️ Response very large ({response_length} chars), truncating to 8000")
                    ai_response = ai_response[:8000]

                # Parse JSON from response with timeout protection
                logger.info(f"🔍 Parsing JSON from response...")
                print(f"🔍 Parsing JSON from response...", flush=True)

                json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = ai_response

                logger.info(f"🔍 Found JSON string, length: {len(json_str)}")
                print(f"🔍 Found JSON string, length: {len(json_str)}, attempting to parse...", flush=True)

                ai_extracted = json.loads(json_str)
                logger.info(f"✓ AI analysis completed: {ai_extracted}")
                print(f"✓ AI analysis completed: {ai_extracted}", flush=True)

                # Set response_text for company_description
                response_text = ai_extracted.get('company_description', f"AI-analyzed content for {request.url}")

            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"❌ Primary request failed: {str(e)}")
                print(f"❌ Primary request failed: {str(e)}, retrying with fresh request...", flush=True)

                # RETRY: Try again with fresh httpx connection
                try:
                    logger.info(f"🔄 Retrying with fresh connection (deepseek/deepseek-chat)")
                    print(f"🔄 Retrying with fresh connection (deepseek/deepseek-chat)", flush=True)

                    # Call OpenRouter API with PAID model using httpx
                    async with httpx.AsyncClient() as http_client:
                        fallback_response = await http_client.post(
                            "https://openrouter.ai/api/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                                "Content-Type": "application/json",
                                "HTTP-Referer": "https://app.squidgy.ai",
                                "X-Title": "Squidgy AI Website Analyzer"
                            },
                            json={
                                "model": "deepseek/deepseek-chat",  # Paid but cheap ($0.14/1M tokens)
                                "plugins": [{"id": "web", "engine": "native", "max_results": 5}],
                                "messages": [{
                                    "role": "user",
                                    "content": analysis_prompt
                                }],
                                "temperature": 0.3,
                                "max_tokens": 1500
                            },
                            timeout=20.0
                        )

                        fallback_response.raise_for_status()
                        fallback_data = fallback_response.json()

                    logger.info(f"✓ Fallback API returned 200 OK")
                    print(f"✓ Fallback API returned 200 OK", flush=True)

                    # Check response structure
                    if 'choices' not in fallback_data or len(fallback_data['choices']) == 0:
                        raise Exception(f"Invalid retry response structure: {fallback_data}")

                    ai_response = fallback_data['choices'][0]['message']['content'].strip()
                    response_length = len(ai_response)
                    logger.info(f"✓ OpenRouter Web Search completed (retry attempt), response length: {response_length}")
                    print(f"✓ OpenRouter Web Search completed (retry attempt), response length: {response_length}", flush=True)

                    # Check response size
                    if response_length > 10000:
                        logger.warning(f"⚠️ Retry response very large ({response_length} chars), truncating to 8000")
                        ai_response = ai_response[:8000]

                    # Parse JSON from response
                    logger.info(f"🔍 Parsing JSON from retry response...")
                    print(f"🔍 Parsing JSON from retry response...", flush=True)

                    json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(0)
                        else:
                            json_str = ai_response

                    logger.info(f"🔍 Found JSON string from retry, length: {len(json_str)}")
                    print(f"🔍 Found JSON string from retry, length: {len(json_str)}, attempting to parse...", flush=True)

                    ai_extracted = json.loads(json_str)
                    logger.info(f"✓ AI analysis completed with retry: {ai_extracted}")
                    print(f"✓ AI analysis completed with retry: {ai_extracted}", flush=True)

                    # Set response_text for company_description
                    response_text = ai_extracted.get('company_description', f"AI-analyzed content for {request.url}")

                except Exception as retry_error:
                    import traceback
                    retry_details = traceback.format_exc()
                    logger.error(f"❌ Retry also failed: {str(retry_error)}")
                    logger.error(f"❌ Retry Traceback:\n{retry_details}")
                    print(f"❌ Both attempts failed: {str(retry_error)}", flush=True)
                    return {
                        "status": "error",
                        "message": f"Website analysis failed after retry: {str(retry_error)}"
                    }
        # ========== END FALLBACK SECTION ==========

        # Final check: Make sure we got results from either scraping or fallback
        if not ai_extracted:
            logger.error(f"❌ Both direct scraping and OpenRouter fallback failed for {request.url}")
            print(f"❌ Both direct scraping and OpenRouter fallback failed for {request.url}", flush=True)
            return {
                "status": "error",
                "message": "Website analysis failed: could not extract information from website"
            }

        # Get extracted values from AI
        company_name = ai_extracted.get('company_name')
        value_proposition = ai_extracted.get('value_proposition')
        business_niche = ai_extracted.get('business_niche')
        tags = ai_extracted.get('tags')

        # Set response_text if not already set (needed for company_description field)
        if not response_text:
            response_text = ai_extracted.get('company_description', f"AI-analyzed content for {request.url}")

        # Fallback: Extract company name from domain if AI didn't find it
        if not company_name:
            from urllib.parse import urlparse
            parsed_url = urlparse(request.url)
            domain_parts = parsed_url.netloc.split('.')
            # Get the main domain part (e.g., "tesla" from "www.tesla.com")
            company_name = domain_parts[-2] if len(domain_parts) >= 2 else domain_parts[0]
            company_name = company_name.capitalize()

        # Extract domain from URL
        from urllib.parse import urlparse
        parsed_url = urlparse(request.url)
        business_domain = parsed_url.netloc

        # Get GHL subaccount data
        ghl_location_id = None
        ghl_user_id = None
        try:
            ghl_subaccount = supabase.table('ghl_subaccounts')\
                .select('ghl_location_id, soma_ghl_user_id')\
                .eq('firm_user_id', request.firm_user_id)\
                .eq('agent_id', request.agent_id)\
                .execute()

            if ghl_subaccount.data and len(ghl_subaccount.data) > 0:
                subaccount = ghl_subaccount.data[0]
                ghl_location_id = subaccount.get('ghl_location_id')
                ghl_user_id = subaccount.get('soma_ghl_user_id')
        except Exception as ghl_error:
            logger.warning(f"Could not fetch GHL subaccount data: {ghl_error}")

        # Prepare upsert data
        upsert_data = {
            'firm_user_id': request.firm_user_id,
            'agent_id': request.agent_id,
            'firm_id': firm_id,
            'website_url': normalized_url,
            'company_name': company_name,
            'company_description': response_text,
            'value_proposition': value_proposition,
            'business_niche': business_niche,
            'tags': tags,
            'business_domain': business_domain,
            'analysis_status': 'completed',
            'last_updated_timestamp': datetime.now(timezone.utc).isoformat(),
            'ghl_location_id': ghl_location_id,
            'ghl_user_id': ghl_user_id
        }

        # Remove None values
        upsert_data = {k: v for k, v in upsert_data.items() if v is not None}

        # INSERT new record (unique constraint now includes website_url)
        supabase.table('website_analysis')\
            .insert(upsert_data)\
            .execute()
        logger.info(f"Inserted new record for firm_user_id: {request.firm_user_id}, agent_id: {request.agent_id}, url: {normalized_url}")

        # Fetch the latest record by timestamp to return
        latest_record = supabase.table('website_analysis')\
            .select('*')\
            .eq('firm_user_id', request.firm_user_id)\
            .eq('agent_id', request.agent_id)\
            .eq('firm_id', firm_id)\
            .order('last_updated_timestamp', desc=True)\
            .limit(1)\
            .execute()

        logger.info(f"Analysis saved to database for {normalized_url}")

        # ========== SAVE EXTRACTED CONTENT TO KNOWLEDGE BASE ==========
        # Use shared save_content_to_knowledge_base function (same as file upload)
        kb_document = f"""Website Analysis: {normalized_url}

Company Name: {company_name or 'Unknown'}

Company Description:
{response_text or 'No description available'}

Value Proposition:
{value_proposition or 'Not specified'}

Business Niche: {business_niche or 'Not specified'}

Business Domain: {business_domain or 'Not specified'}

Tags: {', '.join(tags) if tags else 'None'}
"""
        
        kb_saved = await save_content_to_knowledge_base(
            user_id=request.firm_user_id,
            agent_id=request.agent_id,
            content=kb_document,
            source='website_analysis',
            file_name=f"Website: {company_name or business_domain}",
            file_url=normalized_url
        )
        # ========== END KNOWLEDGE BASE SAVE ==========

        # Fire THREE COMPLETELY SEPARATE independent async tasks
        # They run independently from each other - one failure won't affect the other
        # Uses asyncio.create_task() to run without blocking response
        # Colors start after 1s, screenshot after 2s, favicon after 3s (slightly offset)

        # Task 1: Brand color extraction
        asyncio.create_task(
            capture_brand_colors_independent(
                request.url,
                request.firm_user_id,
                request.agent_id,
                firm_id
            )
        )

        # Task 2: Screenshot capture
        asyncio.create_task(
            capture_screenshot_independent(
                request.url,
                request.firm_user_id,
                request.agent_id,
                firm_id
            )
        )

        # Task 3: Favicon capture
        asyncio.create_task(
            capture_favicon_independent(
                request.url,
                request.firm_user_id,
                request.agent_id,
                firm_id
            )
        )

        logger.info(f"Screenshot, favicon, and brand colors fired as 3 independent tasks - not blocking response")

        # Return the latest record data (assets are being processed in background)
        if latest_record.data and len(latest_record.data) > 0:
            record = latest_record.data[0]
            return {
                "status": "success",
                "cached": False,
                "data": {
                    "company_name": record.get('company_name'),
                    "company_description": record.get('company_description'),
                    "value_proposition": record.get('value_proposition'),
                    "business_niche": record.get('business_niche'),
                    "business_domain": record.get('business_domain'),
                    "tags": record.get('tags'),
                    "screenshot_url": record.get('screenshot_url'),
                    "favicon_url": record.get('favicon_url'),
                    "website_url": record.get('website_url'),
                    "brand_colors": []  # Will be populated by background task
                },
                "processing_assets": True,
                "saved_to_kb": kb_saved,
                "message": "Analysis completed. Screenshot, favicon, and brand colors are being captured in background."
            }
        else:
            # Fallback if fetch failed (shouldn't happen)
            return {
                "status": "success",
                "cached": False,
                "data": {
                    "company_name": company_name,
                    "company_description": response_text,
                    "business_domain": business_domain,
                    "website_url": normalized_url,
                    "screenshot_url": None,
                    "favicon_url": None,
                    "brand_colors": []  # Will be populated by background task
                },
                "processing_assets": True,
                "saved_to_kb": kb_saved,
                "message": "Analysis completed. Screenshot, favicon, and brand colors are being captured in background."
            }

    except Exception as e:
        logger.error(f"Error in website_analysis_complete endpoint: {str(e)}")
        return {
            "status": "error",
            "message": f"Website analysis failed: {str(e)}"
        }

# =============================================================================
# AGENT BUSINESS SETUP ENDPOINTS
# =============================================================================

class AgentSetupRequest(BaseModel):
    user_id: str
    agent_id: str
    agent_name: str
    setup_data: Dict[str, Any]
    is_enabled: bool = True
    setup_type: str = "agent_config"  # agent_config, SolarSetup, CalendarSetup, NotificationSetup, SOLAgent
    session_id: Optional[str] = None


# =============================================================================

# GHL Sub-account and User Creation Endpoints
class GHLSubAccountRequest(BaseModel):
    company_id: str
    snapshot_id: str
    agency_token: str
    user_id: Optional[str] = None  # Add user_id for Facebook automation
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    timezone: Optional[str] = None
    website: Optional[str] = None
    prospect_first_name: Optional[str] = None
    prospect_last_name: Optional[str] = None
    prospect_email: Optional[str] = None
    allow_duplicate_contact: bool = False
    allow_duplicate_opportunity: bool = False
    allow_facebook_name_merge: bool = False
    disable_contact_timezone: bool = False
    subaccount_name: Optional[str] = None

class GHLRegistrationRequest(BaseModel):
    """Request model for GHL subaccount creation during user registration"""
    
    # Required from registration form
    full_name: str
    email: str
    
    # Optional - will use defaults if not provided
    phone: Optional[str] = "+17166044029"
    address: Optional[str] = "456 Solar Demo Avenue" 
    city: Optional[str] = "Buffalo"
    state: Optional[str] = "NY"
    country: Optional[str] = "US"
    postal_code: Optional[str] = "14201"
    timezone: Optional[str] = None  # Auto-detected from country
    website: Optional[str] = None   # Will generate default
    
    # Internal fields (populated automatically)
    user_id: Optional[str] = None   # Looked up from profiles table
    company_id: Optional[str] = None # Looked up from profiles table

class SecureGHLSubAccountRequest(BaseModel):
    subaccount_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    timezone: Optional[str] = None
    website: Optional[str] = None
    business_email: Optional[str] = None
    prospect_email: Optional[str] = None
    prospect_first_name: Optional[str] = None
    prospect_last_name: Optional[str] = None
    allow_duplicate_contact: Optional[bool] = False
    allow_duplicate_opportunity: Optional[bool] = False
    allow_facebook_name_merge: Optional[bool] = False
    disable_contact_timezone: Optional[bool] = False
    
class GHLUserCreationRequest(BaseModel):
    company_id: str
    location_id: str
    agency_token: str
    # All fields below are optional with defaults
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    phone: Optional[str] = None
    account_type: Optional[str] = "account"
    role: Optional[str] = "admin"
    custom_permissions: Optional[Dict[str, Any]] = None

# Global variable to store location_id after subaccount creation
last_created_location_id = None

@app.post("/api/ghl/create-subaccount")
async def create_ghl_subaccount(request: SecureGHLSubAccountRequest):
    """Create a GoHighLevel sub-account with solar snapshot"""
    global last_created_location_id
    
    try:
        # Generate unique name with timestamp
        timestamp = datetime.now().strftime("%H%M%S")
        subaccount_name = request.subaccount_name or f"SolarSetup_Clone_{timestamp}"

        # Get GoHighLevel API credentials from environment variables or constants
        try:
            # First try environment variables
            company_id = os.getenv("GHL_COMPANY_ID")
            agency_token = os.getenv("GHL_AGENCY_TOKEN")
            snapshot_id = os.getenv("GHL_SNAPSHOT_ID")
            
            if not all([company_id, agency_token, snapshot_id]):
                # Fall back to constants if env vars not set
                from GHL.environment.constant import Constant
                constants = Constant()
                company_id = company_id or constants.Company_Id
                agency_token = agency_token or constants.Agency_Access_Key
                snapshot_id = snapshot_id or "bInwX5BtZM6oEepAsUwo"  # SOL - Solar Assistant
                logger.info(f"Using constants for missing environment variables")
            else:
                logger.info(f"Using environment variables for GHL authentication")
        except ImportError:
            # Final fallback if both env vars and constants fail
            company_id = os.getenv("GHL_COMPANY_ID", "lp2p1q27DrdGta1qGDJd")
            agency_token = os.getenv("GHL_AGENCY_TOKEN", "pit-e3d8d384-00cb-4744-8213-b1ab06ae71fe")
            snapshot_id = os.getenv("GHL_SNAPSHOT_ID", "bInwX5BtZM6oEepAsUwo")
            logger.info(f"Using environment variables with defaults")
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {agency_token}",
            "Version": "2021-07-28",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }


        # Set default values for missing fields
        phone = request.phone or "+17166044029"
        address = request.address or "456 Solar Demo Avenue"
        city = request.city or "Buffalo"
        state = request.state or "NY"
        country = request.country or "US"
        postal_code = request.postal_code or "14201"
        website = request.website if hasattr(request, 'website') and request.website else f"https://solar-{timestamp}.com"

        # Determine timezone based on country if not provided
        if not request.timezone:
            try:
                # Import the consolidated timezone utility
                from ghl_timezone_utils import get_timezone_for_ghl
                country_code = country
                # Get timezone based on country and validate it
                timezone = get_timezone_for_ghl(country_code)
                logger.info(f"Automatically selected timezone '{timezone}' based on country '{country_code}'")
            except Exception as e:
                # Fallback to default timezone if there's an error
                timezone = "America/New_York"
                logger.warning(f"Error selecting timezone by country: {str(e)}. Using default: {timezone}")
        else:
            timezone = request.timezone

        # Set prospect info with defaults or provided values
        prospect_first_name = request.prospect_first_name or "Solar"
        prospect_last_name = request.prospect_last_name or "Customer"
        prospect_email = request.prospect_email or f"admin+{timestamp}@solar-setup.com"

        # Use business email if provided, otherwise use prospect email
        business_email = request.business_email if hasattr(request, 'business_email') and request.business_email else prospect_email
        
        # Validate country code - GHL expects 2-letter country codes
        # Based on GHL API documentation - using common valid country codes
        valid_country_codes = {
            "AF", "AL", "DZ", "AD", "AO", "AG", "AR", "AM", "AU", "AT", "AZ", "BS", "BH", "BD", "BB", "BY", 
            "BE", "BZ", "BJ", "BT", "BO", "BA", "BW", "BR", "BN", "BG", "BF", "BI", "KH", "CM", "CA", "CV", 
            "CF", "TD", "CL", "CN", "CO", "KM", "CG", "CD", "CK", "CR", "CI", "HR", "CU", "CY", "CZ", "DK", 
            "DJ", "DM", "DO", "EC", "EG", "SV", "GQ", "ER", "EE", "ET", "FJ", "FI", "FR", "GA", "GM", "GE", 
            "DE", "GH", "GR", "GD", "GT", "GN", "GW", "GY", "HT", "HN", "HK", "HU", "IS", "IN", "ID", "IR", 
            "IQ", "IE", "IL", "IT", "JM", "JP", "JO", "KZ", "KE", "KI", "KP", "KR", "XK", "KW", "KG", "LA", 
            "LV", "LB", "LS", "LR", "LY", "LI", "LT", "LU", "MK", "MG", "MW", "MY", "MV", "ML", "MT", "MR", 
            "MU", "MX", "FM", "MD", "MC", "MN", "ME", "MA", "MZ", "MM", "NA", "NR", "NP", "NL", "NZ", "NI", 
            "NE", "NG", "NO", "OM", "PK", "PW", "PS", "PA", "PG", "PY", "PE", "PH", "PL", "PT", "QA", "RO", 
            "RU", "RW", "KN", "LC", "VC", "WS", "SM", "ST", "SA", "SN", "RS", "SC", "SL", "SG", "SK", "SI", 
            "SB", "SO", "ZA", "ES", "LK", "SD", "SR", "SZ", "SE", "CH", "SY", "TW", "TJ", "TZ", "TH", "TL", 
            "TG", "TO", "TT", "TN", "TR", "TM", "TV", "UG", "GB", "UA", "AE", "US", "UY", "UZ", "VU", "VE", 
            "VN", "YE", "ZM", "ZW"
        }
        
        # Ensure country code is valid, default to "US" if not  
        country_code = request.country.upper() if request.country and request.country.upper() in valid_country_codes else "US"
        
        # Prepare payload
        payload = {
            "name": subaccount_name,  # Use subaccount_name as the business name
            "phone": phone,
            "email": business_email,  # Include email at the top level for business email
            "companyId": company_id,
            "address": address,
            "city": city,
            "state": state,
            "country": country,
            "postalCode": postal_code,
            "website": website,
            "timezone": timezone,
            "prospectInfo": {
                "firstName": prospect_first_name,
                "lastName": prospect_last_name,
                "email": prospect_email
            },
            "settings": {
                "allowDuplicateContact": request.allow_duplicate_contact,
                "allowDuplicateOpportunity": request.allow_duplicate_opportunity,
                "allowFacebookNameMerge": request.allow_facebook_name_merge,
                "disableContactTimezone": request.disable_contact_timezone
            },
            "snapshotId": snapshot_id
        }

        logger.info(f"Creating GHL sub-account: {subaccount_name}")
        logger.info(f"Using API credentials - Company ID: {company_id}, Snapshot ID: {snapshot_id}")
        logger.info(f"API Token (first 20 chars): {agency_token[:20]}...")
        logger.info(f"Payload: {payload}")
        
        logger.info(f"Creating GHL sub-account: {subaccount_name} with country: {country_code}")
        
        # Make the API call
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://services.leadconnectorhq.com/locations/",
                headers=headers,
                json=payload
            )

            # Log response details for debugging
            logger.info(f"GHL API Response Status: {response.status_code}")
            logger.info(f"GHL API Response Headers: {dict(response.headers)}")
            try:
                response_json = response.json()
                logger.info(f"GHL API Response Body: {response_json}")
            except:
                logger.info(f"GHL API Response Text: {response.text}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            location_id = data.get('id')
            last_created_location_id = location_id  # Store for user creation
            
            logger.info(f"Successfully created sub-account with ID: {location_id}")
            
            return {
                "status": "success",
                "message": "Sub-account created successfully",
                "location_id": location_id,
                "subaccount_name": subaccount_name,
                "details": data
            }
        else:
            # logger.error(f"Failed to create sub-account: {response.status_code} - {response.text}")
            # Get detailed error information
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json
            except:
                pass

            logger.error(f"Failed to create sub-account: {response.status_code} - {error_detail}")

            # Provide more helpful error messages based on status code
            if response.status_code == 401:
                error_msg = "Authentication failed - Invalid API token"
            elif response.status_code == 403:
                error_msg = "Access forbidden - Check API permissions"
            elif response.status_code == 400:
                error_msg = f"Bad request - Invalid payload: {error_detail}"
            elif response.status_code == 500:
                error_msg = f"GoHighLevel server error: {error_detail}"
            else:
                error_msg = f"Failed to create sub-account: {error_detail}"
            raise HTTPException(
                status_code=response.status_code,
                detail=error_msg
            )
            
    except httpx.TimeoutException:
        logger.error("Timeout while creating sub-account")
        raise HTTPException(status_code=504, detail="Timeout while creating sub-account")
    except Exception as e:
        logger.error(f"Error creating sub-account: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ghl/create-user")
async def create_ghl_user(request: GHLUserCreationRequest):
    """Create a GoHighLevel user (OVI user only, not admin)"""
    try:
        # Full permissions for the user
         # Set default values for missing fields
        timestamp = datetime.now().strftime("%H%M%S")
        first_name = request.first_name or "Ovi"
        last_name = request.last_name or "Colton"
        password = request.password or "Dummy@123"
        phone = request.phone or "+17166044029"

        # Generate unique email to avoid conflicts if not provided
        email = request.email or f"ovi+{timestamp}@test-solar.com"

        # Use custom permissions if provided, otherwise use default permissions
        permissions = request.custom_permissions if request.custom_permissions else {
            "campaignsEnabled": True,
            "campaignsReadOnly": False,
            "contactsEnabled": True,
            "workflowsEnabled": True,
            "workflowsReadOnly": False,
            "triggersEnabled": True,
            "funnelsEnabled": True,
            "websitesEnabled": True,
            "opportunitiesEnabled": True,
            "dashboardStatsEnabled": True,
            "bulkRequestsEnabled": True,
            "appointmentsEnabled": True,
            "reviewsEnabled": True,
            "onlineListingsEnabled": True,
            "phoneCallEnabled": True,
            "conversationsEnabled": True,
            "assignedDataOnly": False,
            "adwordsReportingEnabled": True,
            "membershipEnabled": True,
            "facebookAdsReportingEnabled": True,
            "attributionsReportingEnabled": True,
            "settingsEnabled": True,
            "tagsEnabled": True,
            "leadValueEnabled": True,
            "marketingEnabled": True,
            "agentReportingEnabled": True,
            "botService": True,
            "socialPlanner": True,
            "bloggingEnabled": True,
            "invoiceEnabled": True,
            "affiliateManagerEnabled": True,
            "contentAiEnabled": True,
            "refundsEnabled": True,
            "recordPaymentEnabled": True,
            "cancelSubscriptionEnabled": True,
            "paymentsEnabled": True,
            "communitiesEnabled": True,
            "exportPaymentsEnabled": True
        }
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {request.agency_token}",
            "Version": "2021-07-28",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Use the actual user email for downstream Facebook integration
        # This ensures the same credentials are used throughout the flow
        
        # Prepare payload for Soma's user account
        payload = {
            "companyId": request.company_id,
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "password": password,
            "phone": phone,
            "type": request.account_type,
            "role": request.role,
            "locationIds": [request.location_id],
            "permissions": permissions
        }
        
    
        # Make the API call
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://services.leadconnectorhq.com/users/",
                headers=headers,
                json=payload
            )
        
        if response.status_code in [200, 201]:
            data = response.json()
            user_id = data.get('id')
            
            logger.info(f"✅ User created successfully: {user_id}")
            
            return {
                "status": "success",
                "user_id": user_id,
                "message": "GoHighLevel user created successfully!",
                "details": {
                    "name": f"{request.first_name} {request.last_name}",
                    "email": email,
                    "role": request.role,
                    "location_id": request.location_id,
                    "created_at": datetime.now().isoformat()
                }
            }
        else:
            logger.error(f"Failed to create user: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to create user: {response.text}"
            )
            
    except httpx.TimeoutException:
        logger.error("Timeout while creating user")
        raise HTTPException(status_code=504, detail="Timeout while creating user")
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def create_agency_user(
    company_id: str,
    location_id: str,
    agency_token: str,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    phone: str,
    role: str = "admin",
    permissions: dict = None,
    scopes: list = None
):
    """Create user using agency-level API (like Ovi Colton pattern)"""
    
    # Build minimal payload (like successful test)
    payload = {
        "companyId": company_id,
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "password": password,
        "phone": phone,
        "type": "account",
        "role": role,
        "locationIds": [location_id]  # Assign to specific location
    }
    
    # Only add permissions and scopes if provided - exactly like old working backend
    if permissions:
        payload["permissions"] = permissions
    if scopes:
        payload["scopes"] = scopes
        payload["scopesAssignedToOnly"] = []
    
    headers = {
        "Authorization": f"Bearer {agency_token}",
        "Version": "2021-07-28",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        # Log the exact payload being sent for debugging
        logger.info(f"Creating user with payload: {json.dumps(payload, indent=2)}")
        logger.info(f"Using agency token: {agency_token[:20]}...")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://services.leadconnectorhq.com/users/",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 201:
                user_data = response.json()
                return {
                    "status": "success",
                    "message": "User created successfully via agency API",
                    "user_id": user_data.get("id"),
                    "details": {
                        "name": f"{first_name} {last_name}",
                        "email": email,
                        "role": role,
                        "location_ids": [location_id]
                    },
                    "raw_response": user_data
                }
            else:
                error_text = response.text
                logger.error(f"Failed to create user via agency API: {response.status_code} - {error_text}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create user: {response.status_code} - {error_text}"
                )
                
    except Exception as e:
        logger.error(f"Exception in agency user creation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}")

async def wait_for_location_availability(location_id: str, agency_token: str, max_retries: int = 10, delay_seconds: float = 2) -> bool:
    """Wait for newly created location to become available for user creation"""
    
    headers = {
        "Authorization": f"Bearer {agency_token}",
        "Version": "2021-07-28",
        "Accept": "application/json"
    }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Checking location availability: attempt {attempt + 1}/{max_retries}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://services.leadconnectorhq.com/locations/search",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    locations = data.get('locations', [])
                    
                    # Check if our location_id is in the list
                    for location in locations:
                        if location.get('id') == location_id:
                            logger.info(f"✅ Location {location_id} is now available!")
                            return True
                    
                    logger.info(f"Location {location_id} not yet available (attempt {attempt + 1})")
                else:
                    logger.warning(f"Failed to check locations: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error checking location availability: {e}")
        
        if attempt < max_retries - 1:  # Don't sleep on the last attempt
            await asyncio.sleep(delay_seconds)
    
    logger.error(f"❌ Location {location_id} never became available after {max_retries} attempts")
    return False

# Pydantic models for website extraction
class WebsiteExtractionRequest(BaseModel):
    website_url: str
    user_id: str

class WebsiteExtractionResponse(BaseModel):
    success: bool
    message: str
    extracted_data: dict = None
    ghl_response: dict = None

# @app.post("/api/ghl/extract-and-create-account", response_model=WebsiteExtractionResponse)
# async def extract_website_info_and_create_account(request: WebsiteExtractionRequest, background_tasks: BackgroundTasks):
#     """Extract business info from website using LLM and create GHL account in background"""
#     try:
#         # Add to background tasks for processing
#         background_tasks.add_task(process_website_extraction, request.website_url, request.user_id)
        
#         return WebsiteExtractionResponse(
#             success=True,
#             message="Website extraction started in background. GHL account will be created automatically.",
#             extracted_data=None,
#             ghl_response=None
#         )
        
#     except Exception as e:
#         logger.error(f"Error starting website extraction: {e}")
#         return WebsiteExtractionResponse(
#             success=False,
#             message=f"Failed to start website extraction: {str(e)}",
#             extracted_data=None,
#             ghl_response=None
#         )

async def process_website_extraction(website_url: str, user_id: str):
    """Background task to extract website info and create GHL account"""
    try:
        logger.info(f"🔍 Starting website extraction for: {website_url}")
        
        # Step 1: Extract website content using LLM
        extracted_data = await extract_business_info_from_website(website_url)
        
        if not extracted_data:
            logger.error(f"❌ Failed to extract data from website: {website_url}")
            return
        
        logger.info(f"✅ Extracted business data: {extracted_data}")
        
        # Step 2: Create GHL sub-account using extracted data
        ghl_payload = create_ghl_payload_from_extracted_data(extracted_data, user_id)
        
        # Step 3: Call the existing GHL creation endpoint
        ghl_request = GHLSubAccountRequest(**ghl_payload)
        ghl_response = await create_subaccount_and_user(ghl_request)
        
        logger.info(f"✅ GHL account creation completed for {extracted_data.get('business_name', 'Unknown')}")
        
    except Exception as e:
        logger.error(f"❌ Error in background website extraction: {e}")

async def extract_business_info_from_website(website_url: str) -> dict:
    """Use LLM to extract business information from website"""
    try:
        import httpx
        import json
        
        # Fetch website content
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(website_url)
            website_content = response.text[:5000]  # Limit content size
        
        # Prepare prompt for LLM
        prompt = f"""
        Analyze the following website content and extract business information. 
        Return ONLY a valid JSON object with these exact fields:
        
        {{
            "business_name": "extracted business name or 'Not Sure'",
            "business_email": "contact email or 'Not Sure'", 
            "phone": "phone number in format +1-xxx-xxx-xxxx or 'Not Sure'",
            "website": "{website_url}",
            "address": "street address or 'Not Sure'",
            "city": "city name or 'Not Sure'",
            "state": "state/province code or 'Not Sure'",
            "country": "country code (US/CA/etc) or 'Not Sure'",
            "postal_code": "zip/postal code or 'Not Sure'",
            "first_name": "owner/contact first name or 'Not Sure'",
            "last_name": "owner/contact last name or 'Not Sure'"
        }}
        
        Website content:
        {website_content}
        
        Return only the JSON object, no other text.
        """
        
        # Call Perplexity API (OpenAI fallback disabled)
        llm_response = await call_llm_api(prompt)
        
        # Parse JSON response
        try:
            extracted_data = json.loads(llm_response)
            return extracted_data
        except json.JSONDecodeError:
            # Try to extract JSON from response if it has extra text
            import re
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())
                return extracted_data
            else:
                logger.error(f"Invalid JSON response from LLM: {llm_response}")
                return None
                
    except Exception as e:
        logger.error(f"Error extracting website info: {e}")
        return None

async def call_llm_api(prompt: str) -> str:
    """Call LLM API (Perplexity only, OpenAI fallback disabled)"""
    try:
        import httpx
        import os
        
        # Try Perplexity first
        perplexity_key = os.getenv('PERPLEXITY_API_KEY')
        if perplexity_key:
            headers = {
                'Authorization': f'Bearer {perplexity_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': 'llama-3.1-sonar-small-128k-online',
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 1000,
                'temperature': 0.1
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    'https://api.perplexity.ai/chat/completions',
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']
        
        # Fallback to OpenAI - COMMENTED OUT TO REDUCE DEPENDENCIES
        # openai_key = os.getenv('OPENAI_API_KEY')
        # if openai_key:
        #     headers = {
        #         'Authorization': f'Bearer {openai_key}',
        #         'Content-Type': 'application/json'
        #     }
        #     
        #     payload = {
        #         'model': 'gpt-3.5-turbo',
        #         'messages': [
        #             {'role': 'user', 'content': prompt}
        #         ],
        #         'max_tokens': 1000,
        #         'temperature': 0.1
        #     }
        #     
        #     async with httpx.AsyncClient(timeout=60.0) as client:
        #         response = await client.post(
        #             'https://api.openai.com/v1/chat/completions',
        #             headers=headers,
        #             json=payload
        #         )
        #         
        #         if response.status_code == 200:
        #             result = response.json()
        #             return result['choices'][0]['message']['content']
        
        # If no API keys available, return default
        logger.warning("No LLM API keys available, using default extraction")
        return '{"business_name": "Not Sure", "business_email": "Not Sure", "phone": "Not Sure", "website": "Not Sure", "address": "Not Sure", "city": "Not Sure", "state": "Not Sure", "country": "Not Sure", "postal_code": "Not Sure", "first_name": "Not Sure", "last_name": "Not Sure"}'
        
    except Exception as e:
        logger.error(f"Error calling LLM API: {e}")
        return '{"business_name": "Not Sure", "business_email": "Not Sure", "phone": "Not Sure", "website": "Not Sure", "address": "Not Sure", "city": "Not Sure", "state": "Not Sure", "country": "Not Sure", "postal_code": "Not Sure", "first_name": "Not Sure", "last_name": "Not Sure"}'

def create_ghl_payload_from_extracted_data(extracted_data: dict, user_id: str) -> dict:
    """Convert extracted data to GHL payload format"""
    import random
    
    random_num = random.randint(1000, 9999)
    business_name = extracted_data.get('business_name', 'Not Sure')
    
    # If business_name is "Not Sure", use demo name
    if business_name == "Not Sure":
        business_name = f"ExtractedBusiness_{random_num}"
    
    # Format phone number
    phone = extracted_data.get('phone', '+1-555-0000')
    if phone == "Not Sure":
        phone = f"+1-555-{random_num}"
    
    # Format email
    email = extracted_data.get('business_email', f'extracted+{random_num}@example.com')
    if email == "Not Sure":
        email = f'extracted+{random_num}@example.com'
    
    return {
        "company_id": "lp2p1q27DrdGta1qGDJd",
        "snapshot_id": "bInwX5BtZM6oEepAsUwo", 
        "agency_token": "pit-e3d8d384-00cb-4744-8213-b1ab06ae71fe",
        "user_id": user_id,
        "subaccount_name": business_name,
        "prospect_email": email,
        "prospect_first_name": extracted_data.get('first_name', business_name.split(' ')[0] if business_name != "Not Sure" else 'Extracted'),
        "prospect_last_name": extracted_data.get('last_name', ' '.join(business_name.split(' ')[1:]) if business_name != "Not Sure" and len(business_name.split(' ')) > 1 else 'Business'),
        "phone": phone,
        "website": extracted_data.get('website', 'https://extracted-business.com'),
        "address": extracted_data.get('address', 'Not Sure') if extracted_data.get('address') != "Not Sure" else "123 Extracted Business Ave",
        "city": extracted_data.get('city', 'Not Sure') if extracted_data.get('city') != "Not Sure" else "Business City",
        "state": extracted_data.get('state', 'Not Sure') if extracted_data.get('state') != "Not Sure" else "CA",
        "country": extracted_data.get('country', 'Not Sure') if extracted_data.get('country') != "Not Sure" else "US",
        "postal_code": extracted_data.get('postal_code', 'Not Sure') if extracted_data.get('postal_code') != "Not Sure" else "90210",
        "timezone": 'America/Los_Angeles',
        "allow_duplicate_contact": False,
        "allow_duplicate_opportunity": False,
        "allow_facebook_name_merge": True,
        "disable_contact_timezone": False
    }

@app.post("/api/ghl/create-subaccount-and-user")
async def create_subaccount_and_user(request: GHLSubAccountRequest):
    """Create both sub-account and user in one call - triggered after Solar setup completion"""
    try:
        # First create the sub-account
        secure_request = SecureGHLSubAccountRequest(
            subaccount_name=request.subaccount_name,
            phone=request.phone,
            address=request.address,
            city=request.city,
            state=request.state,
            country=request.country,
            postal_code=request.postal_code,
            timezone=request.timezone,
            website=request.website if hasattr(request, 'website') else None,
            prospect_email=request.prospect_email,
            prospect_first_name=request.prospect_first_name,
            prospect_last_name=request.prospect_last_name,
            allow_duplicate_contact=request.allow_duplicate_contact,
            allow_duplicate_opportunity=request.allow_duplicate_opportunity,
            allow_facebook_name_merge=request.allow_facebook_name_merge,
            disable_contact_timezone=request.disable_contact_timezone
        )

        subaccount_response = await create_ghl_subaccount(secure_request)
        
        if subaccount_response["status"] != "success":
            return subaccount_response
        
        location_id = subaccount_response["location_id"]
        
        # Create TWO users: 1) Business Owner 2) Soma Addakula
        
        # First user: Business Owner with form data
        # business_user_request = GHLUserCreationRequest(
        #     company_id=request.company_id,
        #     location_id=location_id,
        #     agency_token=request.agency_token,
        #     first_name=request.prospect_first_name,
        #     last_name=request.prospect_last_name,
        #     email=request.prospect_email,
        #     password="Dummy@123",  # Standard password as requested
        #     phone=request.phone
        # )
        
        # Create users using proper agency-level API with full permissions
        
        # Use full permissions from working Ovi Colton pattern
        full_permissions = {
            "campaignsEnabled": True,
            "campaignsReadOnly": False,
            "contactsEnabled": True,
            "workflowsEnabled": True,
            "workflowsReadOnly": False,
            "triggersEnabled": True,
            "funnelsEnabled": True,
            "websitesEnabled": True,
            "opportunitiesEnabled": True,
            "dashboardStatsEnabled": True,
            "bulkRequestsEnabled": True,
            "appointmentsEnabled": True,
            "reviewsEnabled": True,
            "onlineListingsEnabled": True,
            "phoneCallEnabled": True,
            "conversationsEnabled": True,
            "assignedDataOnly": False,
            "adwordsReportingEnabled": True,
            "membershipEnabled": True,
            "facebookAdsReportingEnabled": True,
            "attributionsReportingEnabled": True,
            "settingsEnabled": True,
            "tagsEnabled": True,
            "leadValueEnabled": True,
            "marketingEnabled": True,
            "agentReportingEnabled": True,
            "botService": True,
            "socialPlanner": True,
            "bloggingEnabled": True,
            "invoiceEnabled": True,
            "affiliateManagerEnabled": True,
            "contentAiEnabled": True,
            "refundsEnabled": True,
            "recordPaymentEnabled": True,
            "cancelSubscriptionEnabled": True,
            "paymentsEnabled": True,
            "communitiesEnabled": True,
            "exportPaymentsEnabled": True
        }
        
        # Use EXACT working scopes from the old successful backend
        location_scopes = [
            "adPublishing.readonly",
            "adPublishing.write",
            "blogs.write",
            "calendars.readonly",
            "calendars.write",
            "calendars/events.write",
            "calendars/groups.write",
            "campaigns.write",
            "certificates.readonly",
            "certificates.write",
            "communities.write",
            "contacts.write",
            "contacts/bulkActions.write",
            "contentAI.write",
            "conversations.readonly",
            "conversations.write",
            "conversations/message.readonly",
            "conversations/message.write",
            "custom-menu-link.write",
            "dashboard/stats.readonly",
            "forms.write",
            "funnels.write",
            "gokollab.write",
            "invoices.readonly",
            "invoices.write",
            "invoices/schedule.readonly",
            "invoices/schedule.write",
            "invoices/template.readonly",
            "invoices/template.write",
            "locations/tags.readonly",
            "locations/tags.write",
            "marketing.write",
            "marketing/affiliate.write",
            "medias.readonly",
            "medias.write",
            "membership.write",
            "native-integrations.readonly",
            "native-integrations.write",
            "opportunities.write",
            "opportunities/bulkActions.write",
            "opportunities/leadValue.readonly",
            "prospecting.readonly",
            "prospecting.write",
            "prospecting/auditReport.write",
            "prospecting/reports.readonly",
            "qrcodes.write",
            "quizzes.write",
            "reporting/adwords.readonly",
            "reporting/agent.readonly",
            "reporting/attributions.readonly",
            "reporting/facebookAds.readonly",
            "reporting/phone.readonly",
            "reporting/reports.readonly",
            "reporting/reports.write",
            "reputation/listing.write",
            "reputation/review.write",
            "settings.write",
            "socialplanner/account.readonly",
            "socialplanner/account.write",
            "socialplanner/category.readonly",
            "socialplanner/category.write",
            "socialplanner/csv.readonly",
            "socialplanner/csv.write",
            "socialplanner/facebook.readonly",
            "socialplanner/filters.readonly",
            "socialplanner/group.write",
            "socialplanner/hashtag.readonly",
            "socialplanner/hashtag.write",
            "socialplanner/linkedin.readonly",
            "socialplanner/medias.readonly",
            "socialplanner/medias.write",
            "socialplanner/metatag.readonly",
            "socialplanner/notification.readonly",
            "socialplanner/notification.write",
            "socialplanner/oauth.readonly",
            "socialplanner/oauth.write",
            "socialplanner/post.readonly",
            "socialplanner/post.write",
            "socialplanner/recurring.readonly",
            "socialplanner/recurring.write",
            "socialplanner/review.readonly",
            "socialplanner/review.write",
            "socialplanner/rss.readonly",
            "socialplanner/rss.write",
            "socialplanner/search.readonly",
            "socialplanner/setting.readonly",
            "socialplanner/setting.write",
            "socialplanner/snapshot.readonly",
            "socialplanner/snapshot.write",
            "socialplanner/stat.readonly",
            "socialplanner/tag.readonly",
            "socialplanner/tag.write",
            "socialplanner/twitter.readonly",
            "socialplanner/watermarks.readonly",
            "socialplanner/watermarks.write",
            "surveys.write",
            "triggers.write",
            "voice-ai-agent-goals.readonly",
            "voice-ai-agent-goals.write",
            "voice-ai-agents.write",
            "voice-ai-dashboard.readonly",
            "websites.write",
            "wordpress.read",
            "wordpress.write"
        ]
        
        # SKIP business user creation to avoid "user already exists" errors
        # Create business user using agency API with full permissions
        # business_user_response = await create_agency_user(
        #     company_id=request.company_id,
        #     location_id=location_id,
        #     agency_token=request.agency_token,
        #     first_name=request.prospect_first_name,
        #     last_name=request.prospect_last_name,
        #     email=request.prospect_email,
        #     password="Dummy@123",
        #     phone=request.phone,
        #     role="user",
        #     permissions=full_permissions,
        #     scopes=location_scopes
        # )
        
        # Create mock business user response since we're skipping creation
        business_user_response = {
            "status": "skipped",
            "message": "Business user creation skipped to avoid conflicts",
            "user_id": location_id,
            "details": {
                "name": f"{request.prospect_first_name} {request.prospect_last_name}",
                "email": request.prospect_email,
                "role": "admin",
                "location_ids": [location_id]
            }
        }
        
        # Second user: Soma Addakula with location-specific email
        # Use location-specific email to avoid conflicts
        # soma_email = f"info@squidgy.net"
        
        # soma_user_request = GHLUserCreationRequest(
        #     company_id=request.company_id,
        #     location_id=location_id,
        #     agency_token=request.agency_token,
        #     first_name="Soma",
        #     last_name="Addakula",
        #     email=soma_email,  # Use unique email per location
        #     password="Dummy@123",
        #     phone=request.phone or "+17166044029"  # Use business phone or default
        # )
        
        # Create Soma user with UNIQUE email per location to avoid conflicts
        # Use location-specific email to ensure uniqueness
        soma_unique_email = f"somashekhar34+{location_id[:8]}@gmail.com"
        
        # Add delay to ensure location is propagated in production
        logger.info(f"Waiting 5 seconds for location {location_id} to propagate...")
        await asyncio.sleep(5)

        soma_user_response = await create_agency_user(
            company_id=request.company_id,
            location_id=location_id,
            agency_token=request.agency_token,
            first_name="Soma",
            last_name="Addakula",
            email=soma_unique_email,  # Use unique email per location
            password="Dummy@123",
            phone="+17166044029",
            role="admin",
            permissions=full_permissions,
            scopes=location_scopes
        )
        
        # Save business information to database for automation
        business_id = str(uuid.uuid4())
        
        print(f"[GHL AUTOMATION] 💾 Saving business data to database for automation...")
        print(f"[GHL AUTOMATION] Business: {request.subaccount_name}")
        print(f"[GHL AUTOMATION] Location ID: {location_id}")
        print(f"[GHL AUTOMATION] Automation Email: {soma_unique_email}")
        
        try:
            # Get the actual user_id to use as firm_user_id
            actual_user_id = request.user_id
            if not actual_user_id:
                print(f"[GHL AUTOMATION] ⚠️ No user_id provided, automation cannot be triggered")
                print(f"[GHL AUTOMATION] Frontend needs to send user_id in the request")
                raise Exception("user_id is required for automation - frontend must provide current user's ID")
            
            print(f"[GHL AUTOMATION] 👤 Using user_id as firm_user_id: {actual_user_id}")
            
            # Lookup company_id from profiles table based on user_id
            print(f"[GHL AUTOMATION] 🔍 Looking up company_id from profiles table...")
            user_profile = supabase.table('profiles')\
                .select('company_id')\
                .eq('user_id', actual_user_id)\
                .single()\
                .execute()
            
            if not user_profile.data or not user_profile.data.get('company_id'):
                print(f"[GHL AUTOMATION] ❌ No company_id found for user_id: {actual_user_id}")
                raise Exception(f"User profile missing company_id for user: {actual_user_id}")
            
            firm_id = user_profile.data['company_id']
            print(f"[GHL AUTOMATION] ✅ Found company_id to use as firm_id: {firm_id}")
            
            # Upsert business data for Facebook automation (handle duplicates)
            # Note: firm_user_id = user_id, and we store company_id for reference
            supabase.table('squidgy_business_information').upsert({
                'id': business_id,
                'firm_user_id': actual_user_id,  # user_id as firm_user_id (always)
                'agent_id': 'SOLAgent',
                'business_name': request.subaccount_name,
                'business_address': request.address,
                'city': request.city,
                'state': request.state,
                'country': request.country,
                'postal_code': request.postal_code,
                'ghl_location_id': location_id,
                'ghl_user_email': soma_unique_email,
                'ghl_user_password': "Dummy@123",
                'ghl_user_id': soma_user_response.get("user_id") if soma_user_response.get("status") == "success" else None,
                'setup_status': 'user_created',
                'updated_at': datetime.now().isoformat()
            }, on_conflict='firm_user_id,agent_id').execute()
            
            print(f"[GHL AUTOMATION] 📋 Database mapping:")
            print(f"[GHL AUTOMATION]   user_id → firm_user_id: {actual_user_id}")
            print(f"[GHL AUTOMATION]   company_id (firm_id): {firm_id}")
            print(f"[GHL AUTOMATION]   ghl_location_id: {location_id}")
            
            print(f"[GHL AUTOMATION] ✅ Business data saved successfully!")
            print(f"[GHL AUTOMATION] Business ID: {business_id}")
            
            # Trigger Facebook automation asynchronously
            print(f"[GHL AUTOMATION] 🚀 Triggering Facebook PIT creation automation...")
            print(f"[GHL AUTOMATION] This will run in background - check logs for PIT creation progress")
            
            # Extract Soma user ID for automation
            soma_ghl_user_id = soma_user_response.get("user_id") if soma_user_response.get("status") == "success" else None
            print(f"[GHL AUTOMATION] 👤 Soma GHL User ID: {soma_ghl_user_id}")
            
            # Use asyncio to run automation in background (non-blocking)
            asyncio.create_task(run_facebook_automation_for_business(
                business_id=business_id,
                location_id=location_id,
                email=soma_unique_email,
                password="Dummy@123",
                firm_user_id=actual_user_id,
                ghl_user_id=soma_ghl_user_id
            ))
            
        except Exception as db_error:
            print(f"[GHL AUTOMATION] ⚠️ Database save failed: {db_error}")
            print(f"[GHL AUTOMATION] Account created but automation won't trigger")

        # Return combined response with SOMA's credentials for downstream Facebook integration
        return {
            "status": "success",
            "message": "GoHighLevel sub-account and Soma user created successfully!",
            "subaccount": subaccount_response,
            "business_user": business_user_response,  # Skipped business user with mock response
            "soma_user": soma_user_response,
            "user": soma_user_response,  # Main user field points to Soma for Facebook integration
            "facebook_integration_credentials": {
                "email": soma_unique_email,  # Soma's unique email for Facebook
                "password": "Dummy@123",  # Soma's credentials  
                "phone": "+17166044029",  # Soma's credentials
                "location_id": location_id,
                "user_id": soma_user_response.get("user_id") if soma_user_response.get("status") == "success" else None,
                "ready_for_facebook": True
            },
            "details": {
                "name": "Soma Addakula",
                "email": soma_unique_email,
                "role": "Admin User"
            },
            "business_id": business_id,  # Include business_id for tracking
            "automation_triggered": True,  # Indicate automation was started
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in combined creation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_ghl_creation_background(
    ghl_record_id: str, 
    user_id: str, 
    company_id: str,
    subaccount_name: str,
    phone: str,
    address: str,
    city: str,
    state: str,
    country: str,
    postal_code: str,
    timezone: str,
    website: str,
    prospect_first_name: str,
    prospect_last_name: str,
    prospect_email: str
):
    """Background task for GHL subaccount and user creation during registration"""
    try:
        print(f"[GHL BACKGROUND] 🚀 Starting background GHL creation for record: {ghl_record_id}")
        
        # Update status to running
        supabase.table('ghl_subaccounts').update({
            'creation_status': 'creating',
            'updated_at': datetime.now().isoformat()
        }).eq('id', ghl_record_id).execute()
        
        # Step 1: Create the sub-account using existing function
        secure_request = SecureGHLSubAccountRequest(
            subaccount_name=subaccount_name,
            phone=phone,
            address=address,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            timezone=timezone or "America/New_York",
            website=website,
            prospect_email=prospect_email,
            prospect_first_name=prospect_first_name,
            prospect_last_name=prospect_last_name,
            allow_duplicate_contact=False,
            allow_duplicate_opportunity=False,
            allow_facebook_name_merge=False,
            disable_contact_timezone=False
        )
        
        print(f"[GHL BACKGROUND] 📍 Creating GHL subaccount...")
        subaccount_response = await create_ghl_subaccount(secure_request)
        
        if subaccount_response["status"] != "success":
            raise Exception(f"Subaccount creation failed: {subaccount_response}")
        
        location_id = subaccount_response["location_id"]
        print(f"[GHL BACKGROUND] ✅ Subaccount created with location_id: {location_id}")
        
        # Update database with subaccount creation success
        supabase.table('ghl_subaccounts').update({
            'ghl_location_id': location_id,
            'ghl_company_id': subaccount_response.get("company_id"),
            'ghl_snapshot_id': subaccount_response.get("snapshot_id"),
            'subaccount_created_at': datetime.now().isoformat(),
            'creation_status': 'subaccount_created',
            'updated_at': datetime.now().isoformat()
        }).eq('id', ghl_record_id).execute()
        
        # Step 2: Create Soma user
        print(f"[GHL BACKGROUND] 👤 Creating Soma user...")
        
        # Generate unique email for Soma
        soma_unique_email = f"somashekhar34+{location_id[:8]}@gmail.com"
        
        # Get GHL credentials
        company_id_ghl = os.getenv("GHL_COMPANY_ID", "lp2p1q27DrdGta1qGDJd")
        agency_token = os.getenv("GHL_AGENCY_TOKEN", "pit-e3d8d384-00cb-4744-8213-b1ab06ae71fe")
        
        # Use the same permissions and scopes from the original function
        full_permissions = {
            "campaignsEnabled": True,
            "campaignsReadOnly": False,
            "contactsEnabled": True,
            "workflowsEnabled": True,
            "workflowsReadOnly": False,
            "triggersEnabled": True,
            "funnelsEnabled": True,
            "websitesEnabled": True,
            "opportunitiesEnabled": True,
            "dashboardStatsEnabled": True,
            "bulkRequestsEnabled": True,
            "appointmentsEnabled": True,
            "reviewsEnabled": True,
            "onlineListingsEnabled": True,
            "phoneCallEnabled": True,
            "conversationsEnabled": True,
            "assignedDataOnly": False,
            "adwordsReportingEnabled": True,
            "membershipEnabled": True,
            "facebookAdsReportingEnabled": True,
            "attributionsReportingEnabled": True,
            "settingsEnabled": True,
            "tagsEnabled": True,
            "leadValueEnabled": True,
            "marketingEnabled": True,
            "agentReportingEnabled": True,
            "botService": True,
            "socialPlanner": True,
            "bloggingEnabled": True,
            "invoiceEnabled": True,
            "affiliateManagerEnabled": True,
            "contentAiEnabled": True,
            "refundsEnabled": True,
            "recordPaymentEnabled": True,
            "cancelSubscriptionEnabled": True,
            "paymentsEnabled": True,
            "communitiesEnabled": True,
            "exportPaymentsEnabled": True
        }
        
        # Use EXACT working scopes from the old successful backend
        location_scopes = [
            "adPublishing.readonly",
            "adPublishing.write",
            "blogs.write",
            "calendars.readonly",
            "calendars.write",
            "calendars/events.write",
            "calendars/groups.write",
            "campaigns.write",
            "certificates.readonly",
            "certificates.write",
            "communities.write",
            "contacts.write",
            "contacts/bulkActions.write",
            "contentAI.write",
            "conversations.readonly",
            "conversations.write",
            "conversations/message.readonly",
            "conversations/message.write",
            "custom-menu-link.write",
            "dashboard/stats.readonly",
            "forms.write",
            "funnels.write",
            "gokollab.write",
            "invoices.readonly",
            "invoices.write",
            "invoices/schedule.readonly",
            "invoices/schedule.write",
            "invoices/template.readonly",
            "invoices/template.write",
            "locations/tags.readonly",
            "locations/tags.write",
            "marketing.write",
            "marketing/affiliate.write",
            "medias.readonly",
            "medias.write",
            "membership.write",
            "native-integrations.readonly",
            "native-integrations.write",
            "opportunities.write",
            "opportunities/bulkActions.write",
            "opportunities/leadValue.readonly",
            "prospecting.readonly",
            "prospecting.write",
            "prospecting/auditReport.write",
            "prospecting/reports.readonly",
            "qrcodes.write",
            "quizzes.write",
            "reporting/adwords.readonly",
            "reporting/agent.readonly",
            "reporting/attributions.readonly",
            "reporting/facebookAds.readonly",
            "reporting/phone.readonly",
            "reporting/reports.readonly",
            "reporting/reports.write",
            "reputation/listing.write",
            "reputation/review.write",
            "settings.write",
            "socialplanner/account.readonly",
            "socialplanner/account.write",
            "socialplanner/category.readonly",
            "socialplanner/category.write",
            "socialplanner/csv.readonly",
            "socialplanner/csv.write",
            "socialplanner/facebook.readonly",
            "socialplanner/filters.readonly",
            "socialplanner/group.write",
            "socialplanner/hashtag.readonly",
            "socialplanner/hashtag.write",
            "socialplanner/linkedin.readonly",
            "socialplanner/medias.readonly",
            "socialplanner/medias.write",
            "socialplanner/metatag.readonly",
            "socialplanner/notification.readonly",
            "socialplanner/notification.write",
            "socialplanner/oauth.readonly",
            "socialplanner/oauth.write",
            "socialplanner/post.readonly",
            "socialplanner/post.write",
            "socialplanner/recurring.readonly",
            "socialplanner/recurring.write",
            "socialplanner/review.readonly",
            "socialplanner/review.write",
            "socialplanner/rss.readonly",
            "socialplanner/rss.write",
            "socialplanner/search.readonly",
            "socialplanner/setting.readonly",
            "socialplanner/setting.write",
            "socialplanner/snapshot.readonly",
            "socialplanner/snapshot.write",
            "socialplanner/stat.readonly",
            "socialplanner/tag.readonly",
            "socialplanner/tag.write",
            "socialplanner/twitter.readonly",
            "socialplanner/watermarks.readonly",
            "socialplanner/watermarks.write",
            "surveys.write",
            "triggers.write",
            "voice-ai-agent-goals.readonly",
            "voice-ai-agent-goals.write",
            "voice-ai-agents.write",
            "voice-ai-dashboard.readonly",
            "websites.write",
            "wordpress.read",
            "wordpress.write"
        ]
        
        # Add delay for location propagation
        await asyncio.sleep(5)
        
        soma_user_response = await create_agency_user(
            company_id=company_id_ghl,
            location_id=location_id,
            agency_token=agency_token,
            first_name="Soma",
            last_name="Addakula",
            email=soma_unique_email,
            password="Dummy@123",
            phone="+17166044029",
            role="admin",
            permissions=full_permissions,
            scopes=location_scopes
        )
        
        if soma_user_response.get("status") != "success":
            raise Exception(f"Soma user creation failed: {soma_user_response}")
        
        soma_user_id = soma_user_response.get("user_id")
        print(f"[GHL BACKGROUND] ✅ Soma user created with ID: {soma_user_id}")

        # Update database with soma user creation (tokens will be captured by browser automation)
        supabase.table('ghl_subaccounts').update({
            'soma_ghl_user_id': soma_user_id,
            'soma_ghl_email': soma_unique_email,
            'soma_ghl_password': "Dummy@123",
            'soma_user_created_at': datetime.now().isoformat(),
            'creation_status': 'created',
            'automation_status': 'pending_token_capture',
            'updated_at': datetime.now().isoformat()
        }).eq('id', ghl_record_id).execute()

        # Step 3: Trigger browser automation to capture firebase_token
        # NOTE: GHL /users/authenticate API doesn't exist (returns 404)
        # So we MUST use browser automation to login and intercept firebase_token from network requests
        print(f"[GHL BACKGROUND] 🌐 Triggering BackgroundAutomationUser1 to capture firebase_token via browser...")

        try:
            automation_service_url = os.getenv('AUTOMATION_USER1_SERVICE_URL', 'https://backgroundautomationuser1-1644057ede7b.herokuapp.com')

            async with httpx.AsyncClient(timeout=300.0) as client:
                automation_response = await client.post(
                    f"{automation_service_url}/ghl/complete-automation",
                    json={
                        "location_id": location_id,
                        "email": soma_unique_email,
                        "password": "Dummy@123",
                        "firm_user_id": user_id,
                        "ghl_user_id": soma_user_id
                    }
                )

                if automation_response.status_code == 200:
                    print(f"[GHL BACKGROUND] ✅ Browser automation triggered successfully!")
                else:
                    print(f"[GHL BACKGROUND] ⚠️ Browser automation trigger failed: {automation_response.status_code}")
                    # Set status to show manual token refresh needed
                    supabase.table('ghl_subaccounts').update({
                        'automation_status': 'token_capture_failed',
                        'automation_error': f"Browser automation failed: {automation_response.text}",
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', ghl_record_id).execute()

        except Exception as automation_error:
            print(f"[GHL BACKGROUND] ⚠️ Could not trigger browser automation: {automation_error}")
            supabase.table('ghl_subaccounts').update({
                'automation_status': 'token_capture_failed',
                'automation_error': str(automation_error),
                'updated_at': datetime.now().isoformat()
            }).eq('id', ghl_record_id).execute()
        
        # Step 4: Create Facebook integration record
        facebook_record_id = str(uuid.uuid4())
        
        print(f"[GHL BACKGROUND] 📱 Creating Facebook integration record...")
        supabase.table('facebook_integrations').insert({
            'id': facebook_record_id,
            'firm_user_id': user_id,
            'firm_id': company_id,
            'ghl_subaccount_id': ghl_record_id,
            'ghl_location_id': location_id,
            'facebook_email': soma_unique_email,
            'facebook_password': "Dummy@123",
            'soma_ghl_user_id': soma_user_id,
            'automation_status': 'ready'
        }).execute()
        
        # Step 5: Start Facebook automation background task
        print(f"[GHL BACKGROUND] 🚀 Starting Facebook automation...")
        asyncio.create_task(run_facebook_automation_registration(
            facebook_record_id=facebook_record_id,
            ghl_record_id=ghl_record_id,
            location_id=location_id,
            email=soma_unique_email,
            password="Dummy@123",
            firm_user_id=user_id,
            ghl_user_id=soma_user_id
        ))
        
        print(f"[GHL BACKGROUND] ✅ GHL creation completed successfully!")
        print(f"[GHL BACKGROUND] 🎯 Location ID: {location_id}")
        print(f"[GHL BACKGROUND] 👤 Soma User ID: {soma_user_id}")
        print(f"[GHL BACKGROUND] 🔑 PIT Token automation started")
        print(f"[GHL BACKGROUND] 📱 Facebook automation started")
        
    except Exception as e:
        error_msg = str(e)
        print(f"[GHL BACKGROUND] ❌ Background creation failed: {error_msg}")
        
        # Update database with error
        supabase.table('ghl_subaccounts').update({
            'creation_status': 'failed',
            'creation_error': error_msg,
            'updated_at': datetime.now().isoformat()
        }).eq('id', ghl_record_id).execute()

async def run_pit_token_automation(
    ghl_record_id: str,
    location_id: str,
    email: str,
    password: str,
    firm_user_id: str,
    ghl_user_id: str = None
):
    """Run PIT Token automation by calling BackgroundAutomationUser1 service"""
    try:
        print(f"[PIT AUTOMATION] 🔑 Starting PIT Token automation")
        print(f"[PIT AUTOMATION] GHL Record ID: {ghl_record_id}")
        print(f"[PIT AUTOMATION] Location ID: {location_id}")
        print(f"[PIT AUTOMATION] Firm User ID: {firm_user_id}")
        
        # Update status to running
        supabase.table('ghl_subaccounts').update({
            'automation_status': 'pit_running',
            'updated_at': datetime.now().isoformat()
        }).eq('id', ghl_record_id).execute()
        
        print(f"[PIT AUTOMATION] ✅ Updated automation status to 'pit_running'")
        
        # Call BackgroundAutomationUser1 service
        automation_service_url = os.getenv('AUTOMATION_USER1_SERVICE_URL', 'https://backgroundautomationuser1-1644057ede7b.herokuapp.com')
        
        print(f"[PIT AUTOMATION] 📞 Calling BackgroundAutomationUser1 service at: {automation_service_url}")
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{automation_service_url}/ghl/complete-automation",
                json={
                    "location_id": location_id,
                    "firm_user_id": firm_user_id,
                    "email": email,
                    "password": password,
                    "ghl_user_id": ghl_user_id
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"[PIT AUTOMATION] ✅ Automation service responded: {result.get('message')}")
                print(f"[PIT AUTOMATION] 🎯 Task ID: {result.get('task_id')}")
                print(f"[PIT AUTOMATION] 🚀 Automation is running on remote service")
                print(f"[PIT AUTOMATION] 💾 Database will be updated automatically by the service")
            else:
                error_msg = f"Service returned {response.status_code}: {response.text}"
                print(f"[PIT AUTOMATION] ❌ Automation service error: {error_msg}")
                
                # Update status to failed
                supabase.table('ghl_subaccounts').update({
                    'automation_status': 'pit_failed',
                    'automation_error': error_msg,
                    'updated_at': datetime.now().isoformat()
                }).eq('id', ghl_record_id).execute()
            
    except Exception as e:
        error_msg = f"PIT automation task failed: {str(e)}"
        print(f"[PIT AUTOMATION] ❌ TASK ERROR: {error_msg}")
        
        try:
            supabase.table('ghl_subaccounts').update({
                'automation_status': 'pit_failed',
                'automation_error': error_msg,
                'updated_at': datetime.now().isoformat()
            }).eq('id', ghl_record_id).execute()
        except:
            pass

async def run_facebook_automation_registration(
    facebook_record_id: str,
    ghl_record_id: str, 
    location_id: str, 
    email: str, 
    password: str, 
    firm_user_id: str, 
    ghl_user_id: str = None
):
    """Run Facebook automation for registration-created GHL accounts by calling BackgroundAutomationUser1 service"""
    try:
        print(f"[FACEBOOK REG] 🚀 Starting Facebook automation for registration")
        print(f"[FACEBOOK REG] Facebook Record ID: {facebook_record_id}")
        print(f"[FACEBOOK REG] GHL Record ID: {ghl_record_id}")
        print(f"[FACEBOOK REG] Location ID: {location_id}")
        print(f"[FACEBOOK REG] Firm User ID: {firm_user_id}")
        
        # Update status to running
        supabase.table('facebook_integrations').update({
            'automation_status': 'running',
            'automation_step': 'starting',
            'automation_started_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }).eq('id', facebook_record_id).execute()
        
        # Also update ghl_subaccounts automation status
        supabase.table('ghl_subaccounts').update({
            'automation_status': 'running',
            'updated_at': datetime.now().isoformat()
        }).eq('id', ghl_record_id).execute()
        
        print(f"[FACEBOOK REG] ✅ Updated automation status to 'running'")
        
        # Call BackgroundAutomationUser1 service
        automation_service_url = os.getenv('AUTOMATION_USER1_SERVICE_URL', 'https://backgroundautomationuser1-1644057ede7b.herokuapp.com')
        
        print(f"[FACEBOOK REG] 📞 Calling BackgroundAutomationUser1 service at: {automation_service_url}")
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{automation_service_url}/ghl/complete-automation",
                json={
                    "location_id": location_id,
                    "firm_user_id": firm_user_id,
                    "email": email,
                    "password": password,
                    "ghl_user_id": ghl_user_id
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"[FACEBOOK REG] ✅ Automation service responded: {result.get('message')}")
                print(f"[FACEBOOK REG] 🎯 Task ID: {result.get('task_id')}")
                print(f"[FACEBOOK REG] 🚀 Automation is running on remote service")
                print(f"[FACEBOOK REG] 💾 Database will be updated automatically by the service")
            else:
                error_msg = f"Service returned {response.status_code}: {response.text}"
                print(f"[FACEBOOK REG] ❌ Automation service error: {error_msg}")
                
                # Update status to failed
                supabase.table('facebook_integrations').update({
                    'automation_status': 'failed',
                    'automation_step': 'service_error',
                    'automation_completed_at': datetime.now().isoformat(),
                    'automation_error': error_msg,
                    'updated_at': datetime.now().isoformat()
                }).eq('id', facebook_record_id).execute()
                
                supabase.table('ghl_subaccounts').update({
                    'automation_status': 'failed',
                    'automation_error': error_msg,
                    'updated_at': datetime.now().isoformat()
                }).eq('id', ghl_record_id).execute()
            
    except Exception as e:
        error_msg = f"Background Facebook automation failed: {e}"
        print(f"[FACEBOOK REG] ❌ BACKGROUND ERROR: {error_msg}")
        
        # Update with error
        try:
            supabase.table('facebook_integrations').update({
                'automation_status': 'failed',
                'automation_step': 'background_error',
                'automation_completed_at': datetime.now().isoformat(),
                'automation_error': error_msg,
                'updated_at': datetime.now().isoformat()
            }).eq('id', facebook_record_id).execute()
        except:
            print(f"[FACEBOOK REG] ❌ Could not update database with error status")

@app.post("/api/ghl/create-subaccount-and-user-registration")
async def create_subaccount_and_user_registration(request: GHLRegistrationRequest):
    """Create GHL sub-account and user during user registration - runs as async job"""
    try:
        print(f"🚀 BACKEND_GHL: ===== GHL REGISTRATION ENDPOINT CALLED =====")
        print(f"📥 BACKEND_GHL: Request received at {datetime.now().isoformat()}")
        print(f"👤 BACKEND_GHL: Full Name: {request.full_name}")
        print(f"📧 BACKEND_GHL: Email: {request.email}")
        print(f"📱 BACKEND_GHL: Phone: {getattr(request, 'phone', 'Not provided')}")
        print(f"🌍 BACKEND_GHL: Address: {getattr(request, 'address', 'Not provided')}")
        print(f"🌐 BACKEND_GHL: Website: {getattr(request, 'website', 'Not provided')}")
        
        # Step 1: Lookup user_id and company_id from profiles table
        print(f"🔍 BACKEND_GHL: Step 1 - Looking up user profile by email: {request.email}")
        start_profile_lookup = time.time()
        
        user_profile = supabase.table('profiles')\
            .select('user_id, company_id')\
            .eq('email', request.email)\
            .single()\
            .execute()
        
        end_profile_lookup = time.time()
        print(f"⏱️ BACKEND_GHL: Profile lookup completed in {(end_profile_lookup - start_profile_lookup) * 1000:.0f}ms")
        
        if not user_profile.data:
            print(f"❌ BACKEND_GHL: User profile not found for email: {request.email}")
            raise HTTPException(status_code=404, detail=f"User profile not found for email: {request.email}")
        
        user_id = user_profile.data['user_id']
        company_id = user_profile.data['company_id']
        
        print(f"✅ BACKEND_GHL: Found user profile successfully:")
        print(f"🆔 BACKEND_GHL:   user_id (firm_user_id): {user_id}")
        print(f"🏢 BACKEND_GHL:   company_id (firm_id): {company_id}")
        print(f"📊 BACKEND_GHL:   profile_data: {user_profile.data}")
        
        # Step 2: Parse full name into first and last name
        print(f"📝 BACKEND_GHL: Step 2 - Parsing full name...")
        name_parts = request.full_name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else "Client"
        print(f"👤 BACKEND_GHL: Parsed name - First: '{first_name}', Last: '{last_name}'")
        
        # Step 3: Generate subaccount name and website
        print(f"🏗️ BACKEND_GHL: Step 3 - Generating subaccount details...")
        timestamp = datetime.now().strftime("%H%M%S")
        subaccount_name = f"{request.full_name} @Client_{request.email}"
        website = request.website or f"https://client-{timestamp}.com"
        
        print(f"📝 BACKEND_GHL: Generated values:")
        print(f"🏢 BACKEND_GHL:   subaccount_name: {subaccount_name}")
        print(f"👤 BACKEND_GHL:   prospect_first_name: {first_name}")
        print(f"👤 BACKEND_GHL:   prospect_last_name: {last_name}")
        print(f"🌐 BACKEND_GHL:   website: {website}")
        print(f"⏰ BACKEND_GHL:   timestamp: {timestamp}")
        
        # Step 4: Create entry in ghl_subaccounts table (pending status)
        print(f"💾 BACKEND_GHL: Step 4 - Creating database record...")
        ghl_record_id = str(uuid.uuid4())
        print(f"🆔 BACKEND_GHL: Generated GHL record ID: {ghl_record_id}")
        
        start_db_insert = time.time()
        supabase.table('ghl_subaccounts').insert({
            'id': ghl_record_id,
            'firm_user_id': user_id,
            'firm_id': company_id,
            'agent_id': 'SOL',
            'subaccount_name': subaccount_name,
            'business_phone': request.phone,
            'business_address': request.address,
            'business_city': request.city,
            'business_state': request.state,
            'business_country': request.country,
            'business_postal_code': request.postal_code,
            'business_timezone': request.timezone or "America/New_York",
            'business_website': website,
            'prospect_first_name': first_name,
            'prospect_last_name': last_name,
            'prospect_email': request.email,
            'creation_status': 'pending',
            'automation_status': 'not_started'
        }).execute()
        
        end_db_insert = time.time()
        print(f"⏱️ BACKEND_GHL: Database insert completed in {(end_db_insert - start_db_insert) * 1000:.0f}ms")
        print(f"✅ BACKEND_GHL: Database record created successfully: {ghl_record_id}")
        
        # Step 5: Run GHL creation as async background task
        print(f"🚀 BACKEND_GHL: Step 5 - Starting background GHL creation task...")
        print(f"🔧 BACKEND_GHL: Background task parameters:")
        print(f"🆔 BACKEND_GHL:   ghl_record_id: {ghl_record_id}")
        print(f"👤 BACKEND_GHL:   user_id: {user_id}")
        print(f"🏢 BACKEND_GHL:   company_id: {company_id}")
        print(f"📧 BACKEND_GHL:   prospect_email: {request.email}")
        
        background_task_start = time.time()
        asyncio.create_task(run_ghl_creation_background(
            ghl_record_id=ghl_record_id,
            user_id=user_id,
            company_id=company_id,
            subaccount_name=subaccount_name,
            phone=request.phone,
            address=request.address,
            city=request.city,
            state=request.state,
            country=request.country,
            postal_code=request.postal_code,
            timezone=request.timezone,
            website=website,
            prospect_first_name=first_name,
            prospect_last_name=last_name,
            prospect_email=request.email
        ))
        
        background_task_end = time.time()
        print(f"⏱️ BACKEND_GHL: Background task creation completed in {(background_task_end - background_task_start) * 1000:.0f}ms")
        print(f"✅ BACKEND_GHL: Background task started successfully")
        
        # Step 6: Return immediate response while background task runs
        print(f"📤 BACKEND_GHL: Step 6 - Preparing response...")
        
        response_data = {
            "status": "accepted",
            "message": "GHL account creation started successfully",
            "ghl_record_id": ghl_record_id,
            "user_id": user_id,
            "company_id": company_id,
            "subaccount_name": subaccount_name,
            "background_task_started": True,
            "check_status_endpoint": f"/api/ghl/status/{ghl_record_id}",
            "created_at": datetime.now().isoformat()
        }
        
        print(f"📋 BACKEND_GHL: Response prepared:")
        print(f"✅ BACKEND_GHL:   status: {response_data['status']}")
        print(f"🆔 BACKEND_GHL:   ghl_record_id: {response_data['ghl_record_id']}")
        print(f"👤 BACKEND_GHL:   user_id: {response_data['user_id']}")
        print(f"🕒 BACKEND_GHL:   created_at: {response_data['created_at']}")
        print(f"🎯 BACKEND_GHL: ===== GHL REGISTRATION ENDPOINT COMPLETED =====")
        
        return response_data
        
    except Exception as e:
        print(f"❌ BACKEND_GHL: CRITICAL ERROR in registration GHL creation:")
        print(f"❌ BACKEND_GHL: Error type: {type(e).__name__}")
        print(f"❌ BACKEND_GHL: Error message: {str(e)}")
        print(f"❌ BACKEND_GHL: Error occurred at: {datetime.now().isoformat()}")
        logger.error(f"Error in registration GHL creation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ghl/trigger-pit-automation/{ghl_record_id}")
async def trigger_pit_automation(ghl_record_id: str):
    """Manually trigger PIT token automation for an existing GHL subaccount"""
    try:
        print(f"[MANUAL PIT] 🔑 Manual PIT automation trigger for: {ghl_record_id}")
        
        # Get GHL subaccount details
        ghl_result = supabase.table('ghl_subaccounts')\
            .select('*')\
            .eq('id', ghl_record_id)\
            .single()\
            .execute()
        
        if not ghl_result.data:
            raise HTTPException(status_code=404, detail=f"GHL record not found: {ghl_record_id}")
        
        ghl_data = ghl_result.data
        
        # Validate required fields
        if not ghl_data.get('ghl_location_id'):
            raise HTTPException(status_code=400, detail="Location ID not found in record")
        if not ghl_data.get('soma_ghl_email'):
            raise HTTPException(status_code=400, detail="Soma email not found in record")
        if not ghl_data.get('soma_ghl_password'):
            raise HTTPException(status_code=400, detail="Soma password not found in record")
        
        # PIT automation - COMMENTED OUT (NOT NEEDED)
        # We removed authorization header from all social media API calls
        # Only firebase_token is needed, which is already captured during user creation
        print(f"[MANUAL PIT] ⏭️  PIT automation no longer needed (using firebase_token only)")
        # asyncio.create_task(run_pit_token_automation(
        #     ghl_record_id=ghl_record_id,
        #     location_id=ghl_data['ghl_location_id'],
        #     email=ghl_data['soma_ghl_email'],
        #     password=ghl_data['soma_ghl_password'],
        #     firm_user_id=ghl_data['firm_user_id'],
        #     ghl_user_id=ghl_data.get('soma_ghl_user_id')
        # ))

        print(f"[MANUAL PIT] ℹ️  firebase_token is already available from user creation")

        return {
            "status": "skipped",
            "message": "PIT token automation no longer needed - using firebase_token only",
            "ghl_record_id": ghl_record_id,
            "location_id": ghl_data['ghl_location_id'],
            "check_status_endpoint": f"/api/ghl/status/{ghl_record_id}",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering PIT automation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ghl/retry-automation")
async def retry_ghl_automation(request: dict):
    """
    Retry GHL automation for a failed setup.
    This will retry soma_ghl_user creation if needed, then trigger browser automation.
    """
    try:
        firm_user_id = request.get('firm_user_id')
        
        if not firm_user_id:
            raise HTTPException(status_code=400, detail="firm_user_id is required")
        
        # Get GHL subaccount details
        ghl_result = supabase.table('ghl_subaccounts')\
            .select('*')\
            .eq('firm_user_id', firm_user_id)\
            .single()\
            .execute()
        
        if not ghl_result.data:
            raise HTTPException(status_code=404, detail=f"GHL record not found for user: {firm_user_id}")
        
        ghl_data = ghl_result.data
        ghl_record_id = ghl_data['id']
        location_id = ghl_data.get('ghl_location_id')
        
        if not location_id:
            raise HTTPException(status_code=400, detail="Location ID not found - subaccount may not have been created")
        
        # Check if soma_ghl_user needs to be created
        soma_user_id = ghl_data.get('soma_ghl_user_id')
        soma_email = ghl_data.get('soma_ghl_email')
        
        if not soma_user_id:
            # Generate unique email for Soma (same format as original)
            soma_email = f"somashekhar34+{location_id[:8]}@gmail.com"
            
            # Get GHL credentials
            agency_token = os.getenv("GHL_AGENCY_TOKEN", "pit-e3d8d384-00cb-4744-8213-b1ab06ae71fe")
            company_id = os.getenv("GHL_COMPANY_ID", "lp2p1q27DrdGta1qGDJd")
            
            # Full permissions (same as original)
            full_permissions = {
                "campaignsEnabled": True,
                "campaignsReadOnly": False,
                "contactsEnabled": True,
                "workflowsEnabled": True,
                "triggersEnabled": True,
                "funnelsEnabled": True,
                "websitesEnabled": True,
                "opportunitiesEnabled": True,
                "dashboardStatsEnabled": True,
                "bulkRequestsEnabled": True,
                "appointmentsEnabled": True,
                "reviewsEnabled": True,
                "onlineListingsEnabled": True,
                "phoneCallEnabled": True,
                "conversationsEnabled": True,
                "assignedDataOnly": False,
                "adwordsReportingEnabled": True,
                "membershipEnabled": True,
                "facebookAdsReportingEnabled": True,
                "attributionsReportingEnabled": True,
                "settingsEnabled": True,
                "tagsEnabled": True,
                "leadValueEnabled": True,
                "marketingEnabled": True,
                "agentReportingEnabled": True,
                "botService": True,
                "socialPlanner": True,
                "bloggingEnabled": True,
                "invoiceEnabled": True,
                "affiliateManagerEnabled": True,
                "contentAiEnabled": True,
                "refundsEnabled": True,
                "recordPaymentEnabled": True,
                "cancelSubscriptionEnabled": True,
                "paymentsEnabled": True,
                "communitiesEnabled": True,
                "exportPaymentsEnabled": True
            }
            
            # Create soma user using the existing helper function
            try:
                soma_user_response = await create_agency_user(
                    company_id=company_id,
                    location_id=location_id,
                    agency_token=agency_token,
                    first_name="Soma",
                    last_name="Addakula",
                    email=soma_email,
                    password="Dummy@123",
                    phone="+17166044029",
                    role="admin",
                    permissions=full_permissions
                )
                
                if soma_user_response.get("status") == "success":
                    soma_user_id = soma_user_response.get("user_id")
                    
                    # Update database
                    supabase.table('ghl_subaccounts').update({
                        'soma_ghl_user_id': soma_user_id,
                        'soma_ghl_email': soma_email,
                        'soma_ghl_password': "Dummy@123",
                        'soma_user_created_at': datetime.now().isoformat(),
                        'creation_status': 'created',
                        'creation_error': None,
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', ghl_record_id).execute()
                else:
                    error_msg = f"Failed to create soma user: {soma_user_response}"
                    
                    supabase.table('ghl_subaccounts').update({
                        'creation_status': 'failed',
                        'creation_error': error_msg,
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', ghl_record_id).execute()
                    
                    raise HTTPException(status_code=500, detail=error_msg)
                    
            except Exception as e:
                error_msg = f"Error creating soma user: {str(e)}"
                raise HTTPException(status_code=500, detail=error_msg)
        else:
            soma_email = ghl_data.get('soma_ghl_email')
        
        # Trigger browser automation to capture firebase_token
        automation_service_url = os.getenv('AUTOMATION_USER1_SERVICE_URL', 'https://backgroundautomationuser1-1644057ede7b.herokuapp.com')
        
        # Update status
        supabase.table('ghl_subaccounts').update({
            'automation_status': 'running',
            'automation_error': None,
            'updated_at': datetime.now().isoformat()
        }).eq('id', ghl_record_id).execute()
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{automation_service_url}/ghl/complete-automation",
                json={
                    "location_id": location_id,
                    "email": soma_email or ghl_data.get('soma_ghl_email'),
                    "password": "Dummy@123",
                    "firm_user_id": firm_user_id,
                    "ghl_user_id": soma_user_id
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                
                return {
                    "success": True,
                    "message": "GHL automation retry started",
                    "firm_user_id": firm_user_id,
                    "location_id": location_id,
                    "soma_user_id": soma_user_id,
                    "status": "running"
                }
            else:
                error_msg = f"Automation service error: {response.status_code} - {response.text}"
                
                supabase.table('ghl_subaccounts').update({
                    'automation_status': 'failed',
                    'automation_error': error_msg,
                    'updated_at': datetime.now().isoformat()
                }).eq('id', ghl_record_id).execute()
                
                raise HTTPException(status_code=500, detail=error_msg)
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ghl/refresh-tokens/{firm_user_id}")
async def refresh_ghl_tokens(firm_user_id: str, agent_id: str = "SOL"):
    """
    Manually refresh firebase_token for existing users
    This triggers the BackgroundAutomationUser1 service to capture tokens via browser automation
    """
    try:
        print(f"[TOKEN REFRESH] 🔄 Starting token refresh for user: {firm_user_id}")

        # Get GHL subaccount details
        ghl_result = supabase.table('ghl_subaccounts')\
            .select('*')\
            .eq('firm_user_id', firm_user_id)\
            .eq('agent_id', agent_id)\
            .single()\
            .execute()

        if not ghl_result.data:
            raise HTTPException(status_code=404, detail="GHL subaccount not found")

        ghl_data = ghl_result.data
        location_id = ghl_data.get('ghl_location_id')
        soma_email = ghl_data.get('soma_ghl_email')
        soma_password = ghl_data.get('soma_ghl_password')
        soma_user_id = ghl_data.get('soma_ghl_user_id')

        if not all([location_id, soma_email, soma_password]):
            raise HTTPException(status_code=400, detail="Missing GHL credentials")

        # Update status to indicate refresh is running
        supabase.table('ghl_subaccounts').update({
            'automation_status': 'token_refresh_running',
            'updated_at': datetime.now().isoformat()
        }).eq('firm_user_id', firm_user_id).eq('agent_id', agent_id).execute()

        # Call BackgroundAutomationUser1 service to capture tokens
        print(f"[TOKEN REFRESH] 📞 Calling BackgroundAutomationUser1 service...")

        automation_service_url = os.getenv('AUTOMATION_USER1_SERVICE_URL', 'https://backgroundautomationuser1-1644057ede7b.herokuapp.com')

        async with httpx.AsyncClient(timeout=300.0) as client:
            automation_response = await client.post(
                f"{automation_service_url}/ghl/complete-automation",
                json={
                    "location_id": location_id,
                    "email": soma_email,
                    "password": soma_password,
                    "firm_user_id": firm_user_id,
                    "ghl_user_id": soma_user_id
                }
            )

            if automation_response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Automation service error: {automation_response.text}"
                )

        print(f"[TOKEN REFRESH] ✅ Token refresh started successfully")

        return {
            "success": True,
            "message": "Token refresh started. Tokens will be captured via browser automation.",
            "status": "running",
            "firm_user_id": firm_user_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TOKEN REFRESH] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ghl/user/{user_id}/integrations")
async def get_user_ghl_integrations(user_id: str):
    """Get all GHL integrations for a user by firm_user_id"""
    try:
        print(f"[GHL INTEGRATIONS] 📊 Fetching integrations for user: {user_id}")

        # Get all GHL subaccounts for this user using firm_user_id
        ghl_result = supabase.table('ghl_subaccounts')\
            .select('*')\
            .eq('firm_user_id', user_id)\
            .execute()

        if not ghl_result.data:
            return {"integrations": [], "message": "No GHL integrations found for this user"}

        return {
            "integrations": ghl_result.data,
            "count": len(ghl_result.data)
        }
        
    except Exception as e:
        logger.error(f"Error fetching GHL integrations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ghl/status/{ghl_record_id}")
async def get_ghl_status(ghl_record_id: str):
    """Get status of GHL subaccount creation and Facebook automation"""
    try:
        print(f"[GHL STATUS] 📊 Checking status for record: {ghl_record_id}")
        
        # Get GHL subaccount status
        ghl_result = supabase.table('ghl_subaccounts')\
            .select('*')\
            .eq('id', ghl_record_id)\
            .single()\
            .execute()
        
        if not ghl_result.data:
            raise HTTPException(status_code=404, detail=f"GHL record not found: {ghl_record_id}")
        
        ghl_data = ghl_result.data
        
        # Get Facebook integration status if available
        facebook_result = supabase.table('facebook_integrations')\
            .select('*')\
            .eq('ghl_subaccount_id', ghl_record_id)\
            .execute()
        
        facebook_data = facebook_result.data[0] if facebook_result.data else None
        
        # Build response
        response = {
            "ghl_record_id": ghl_record_id,
            "ghl_status": {
                "creation_status": ghl_data['creation_status'],
                "automation_status": ghl_data['automation_status'],
                "location_id": ghl_data.get('ghl_location_id'),
                "soma_user_id": ghl_data.get('soma_ghl_user_id'),
                "subaccount_name": ghl_data['subaccount_name'],
                "created_at": ghl_data['created_at'],
                "subaccount_created_at": ghl_data.get('subaccount_created_at'),
                "soma_user_created_at": ghl_data.get('soma_user_created_at'),
                "creation_error": ghl_data.get('creation_error'),
                "automation_error": ghl_data.get('automation_error'),
                "pit_token_available": bool(ghl_data.get('pit_token')),
                "pit_token_preview": ghl_data.get('pit_token')[:30] + "..." if ghl_data.get('pit_token') else None
            },
            "facebook_status": None,
            "overall_status": ghl_data['creation_status'],
            "timestamp": datetime.now().isoformat()
        }
        
        # Add Facebook status if available
        if facebook_data:
            response["facebook_status"] = {
                "automation_status": facebook_data['automation_status'],
                "automation_step": facebook_data.get('automation_step'),
                "pit_token_available": bool(facebook_data.get('pit_token')),
                "access_token_available": bool(facebook_data.get('access_token')),
                "firebase_token_available": bool(facebook_data.get('firebase_token')),
                "automation_started_at": facebook_data.get('automation_started_at'),
                "automation_completed_at": facebook_data.get('automation_completed_at'),
                "automation_error": facebook_data.get('automation_error'),
                "retry_count": facebook_data.get('retry_count', 0),
                "automation_result": facebook_data.get('automation_result')
            }
            
            # Update overall status based on both GHL and Facebook
            if ghl_data['creation_status'] == 'created' and facebook_data['automation_status'] == 'completed':
                response["overall_status"] = 'fully_completed'
            elif ghl_data['creation_status'] == 'created' and facebook_data['automation_status'] in ['running', 'ready']:
                response["overall_status"] = 'facebook_in_progress'
            elif ghl_data['creation_status'] == 'failed' or facebook_data['automation_status'] == 'failed':
                response["overall_status"] = 'failed'
        
        print(f"[GHL STATUS] ✅ Status retrieved successfully")
        print(f"[GHL STATUS] Overall Status: {response['overall_status']}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving GHL status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Facebook OAuth Integration Endpoints
# =============================================================================

class FacebookOAuthRequest(BaseModel):
    locationId: str
    userId: str

class FacebookOAuthExtractor:
    """Facebook OAuth parameter extraction utility for GHL integration"""
    
    @staticmethod
    async def extract_params(location_id: str, user_id: str) -> dict:
        """Extract OAuth parameters from GHL Facebook service"""
        try:
            ghl_url = f"https://services.leadconnectorhq.com/social-media-posting/oauth/facebook/start?locationId={location_id}&userId={user_id}"
            
            async with httpx.AsyncClient(follow_redirects=False) as client:
                response = await client.get(ghl_url)
                
                if response.status_code not in [301, 302]:
                    raise ValueError(f"Expected redirect from GHL service, got {response.status_code}")
                
                redirect_url = response.headers.get('location', '')
                if not redirect_url or 'facebook.com' not in redirect_url:
                    raise ValueError(f"Invalid redirect URL: {redirect_url}")
                
                params = {}
                
                if 'facebook.com/privacy/consent/gdp' in redirect_url:
                    # Extract from GDPR consent page (URL encoded)
                    import re
                    import urllib.parse
                    patterns = {
                        'app_id': r'params%5Bapp_id%5D=(\d+)',
                        'redirect_uri': r'params%5Bredirect_uri%5D=%22([^%]+(?:%[^%]+)*)',
                        'scope': r'params%5Bscope%5D=(%5B[^%]+(?:%[^%]+)*%5D)',
                        'state': r'params%5Bstate%5D=%22([^%]+(?:%[^%]+)*)',
                        'logger_id': r'params%5Blogger_id%5D=%22([^%]+)'
                    }
                    
                    for param, pattern in patterns.items():
                        match = re.search(pattern, redirect_url)
                        if match:
                            value = match.group(1)
                            
                            if param == 'app_id':
                                params['app_id'] = value
                                params['client_id'] = value
                            elif param == 'redirect_uri':
                                params['redirect_uri'] = urllib.parse.unquote(value.replace('\\%2F', '/').replace('\\', ''))
                            elif param == 'scope':
                                try:
                                    scope_str = urllib.parse.unquote(value)
                                    scope_array = json.loads(scope_str.replace('\\', ''))
                                    params['scope'] = ','.join(scope_array)
                                except:
                                    params['scope'] = 'email,pages_show_list,pages_read_engagement'
                            elif param == 'state':
                                params['state'] = urllib.parse.unquote(value.replace('\\', ''))
                            elif param == 'logger_id':
                                params['logger_id'] = value
                    
                    params['response_type'] = 'code'
                    
                elif 'facebook.com/dialog/oauth' in redirect_url:
                    # Extract from direct OAuth URL
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(redirect_url)
                    query_params = parse_qs(parsed.query)
                    
                    for key, value in query_params.items():
                        params[key] = value[0] if value else None
                
                return {
                    'success': True,
                    'params': params,
                    'redirect_url': redirect_url,
                    'extracted_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Facebook OAuth extraction error: {str(e)}")
            raise

@app.post("/api/facebook/extract-oauth-params")
async def extract_facebook_oauth_params(request: FacebookOAuthRequest):
    """
    Extract Facebook OAuth parameters from GHL service for Squidgy chat integration

    This endpoint is used by the chat window in the frontend to generate
    Facebook OAuth URLs for solar sales specialists to connect their Facebook accounts.

    Note: The userId passed here should be firm_user_id, and we'll look up the ghl_location_id and soma_ghl_user_id from the database.
    For Facebook OAuth start URL: locationId uses ghl_location_id, userId uses soma_ghl_user_id (created during subaccount setup).
    For Facebook accounts API: Uses agency_user_id (extracted from Firebase token during automation).
    """
    try:
        logger.info(f"🔍 Extracting Facebook OAuth params for location: {request.locationId}, firm_user_id: {request.userId}")

        # Look up the ghl_location_id and soma_ghl_user_id from the ghl_subaccounts table
        ghl_result = supabase.table('ghl_subaccounts').select(
            'ghl_location_id, soma_ghl_user_id'
        ).eq('firm_user_id', request.userId).execute()

        if not ghl_result.data or not ghl_result.data[0].get('ghl_location_id'):
            logger.error(f"❌ No GHL location found for firm_user_id: {request.userId}")
            raise HTTPException(status_code=404, detail="GHL location not found. Please complete GHL setup first.")

        ghl_location_id = ghl_result.data[0]['ghl_location_id']
        soma_ghl_user_id = ghl_result.data[0].get('soma_ghl_user_id')

        if not soma_ghl_user_id:
            logger.error(f"❌ No soma_ghl_user_id found for firm_user_id: {request.userId}")
            raise HTTPException(status_code=404, detail="GHL user not created. Please complete GHL setup first.")

        logger.info(f"✅ Found ghl_location_id: {ghl_location_id} for firm_user_id: {request.userId}")
        logger.info(f"✅ Using soma_ghl_user_id: {soma_ghl_user_id} for OAuth userId parameter")

        # Use ghl_location_id for locationId and soma_ghl_user_id for userId
        # NOTE: agency_user_id is used for Facebook accounts API endpoint, NOT OAuth start URL
        result = await FacebookOAuthExtractor.extract_params(ghl_location_id, soma_ghl_user_id)
        
        logger.info(f"✅ Successfully extracted Facebook OAuth parameters")
        logger.info(f"   Client ID: {result['params'].get('client_id', 'NOT_FOUND')}")
        logger.info(f"   Redirect URI: {result['params'].get('redirect_uri', 'NOT_FOUND')}")
        
        return result
        
    except ValueError as e:
        logger.error(f"❌ Facebook OAuth extraction error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"💥 Unexpected error in Facebook OAuth extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/facebook/start-oauth-with-interception")
async def start_oauth_with_interception(request: dict, background_tasks: BackgroundTasks):
    """
    Start OAuth flow with browser automation token interception
    This launches a visible browser that intercepts tokens during the OAuth flow
    """
    try:
        firm_user_id = request.get('firm_user_id')
        if not firm_user_id:
            raise HTTPException(status_code=400, detail="firm_user_id is required")
        
        print(f"[OAUTH INTERCEPTION] 🚀 Starting OAuth with token interception for user: {firm_user_id}")

        # Get GHL location ID and soma_ghl_user_id
        ghl_result = supabase.table('ghl_subaccounts').select(
            'ghl_location_id, soma_ghl_user_id'
        ).eq('firm_user_id', firm_user_id).execute()

        if not ghl_result.data or not ghl_result.data[0].get('ghl_location_id'):
            raise HTTPException(status_code=404, detail="GHL location not found. Please complete GHL setup first.")

        ghl_location_id = ghl_result.data[0]['ghl_location_id']
        soma_ghl_user_id = ghl_result.data[0].get('soma_ghl_user_id')

        if not soma_ghl_user_id:
            raise HTTPException(status_code=404, detail="GHL user not created. Please complete GHL setup first.")

        print(f"[OAUTH INTERCEPTION] ✅ Found location_id: {ghl_location_id}")
        print(f"[OAUTH INTERCEPTION] ✅ Using soma_ghl_user_id: {soma_ghl_user_id} for OAuth start URL")

        # Generate OAuth URL with soma_ghl_user_id (NOT agency_user_id)
        # NOTE: agency_user_id is used for Facebook accounts API endpoint, NOT OAuth start URL
        result = await FacebookOAuthExtractor.extract_params(ghl_location_id, soma_ghl_user_id)
        
        if not result.get('success') or not result.get('params'):
            raise HTTPException(status_code=500, detail="Failed to generate OAuth URL")
        
        # Build OAuth URL
        enhancedScope = 'email,pages_show_list,pages_read_engagement,pages_manage_metadata,pages_manage_posts,pages_manage_engagement,pages_read_user_content,business_management,public_profile,read_insights,pages_manage_ads,leads_retrieval,ads_read,pages_messaging,ads_management,instagram_basic,instagram_manage_messages,instagram_manage_comments,catalog_management'
        
        from urllib.parse import urlencode
        oauth_params = {
            'response_type': result['params'].get('response_type', 'code'),
            'client_id': result['params']['client_id'],
            'redirect_uri': 'https://services.leadconnectorhq.com/integrations/oauth/finish',
            'scope': enhancedScope,
            'state': json.dumps({
                'locationId': ghl_location_id,
                'userId': ghl_location_id,
                'type': 'facebook',
                'source': 'squidgy_intercepted'
            }),
            'logger_id': result['params'].get('logger_id', str(uuid.uuid4()))
        }
        
        oauth_url = f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(oauth_params)}"
        
        print(f"[OAUTH INTERCEPTION] 🔗 OAuth URL generated: {oauth_url[:80]}...")
        
        # Import and create interceptor instance (dynamic import like other automations)
        try:
            print(f"[OAUTH INTERCEPTION] 📦 Loading Facebook OAuth interceptor module...")
            from facebook_oauth_interceptor import FacebookOAuthInterceptor
            interceptor = FacebookOAuthInterceptor()
        except ImportError as import_error:
            error_msg = f"Could not import FacebookOAuthInterceptor: {import_error}"
            print(f"[OAUTH INTERCEPTION] ❌ IMPORT ERROR: {error_msg}")
            raise HTTPException(
                status_code=503,
                detail="Facebook OAuth interception is not available on this server. Playwright browser automation is required."
            )
        
        # Initialize browser and interception BEFORE returning OAuth URL
        print(f"[OAUTH INTERCEPTION] ⏳ Initializing browser interception...")
        init_result = await interceptor.initialize_interception()
        
        if not init_result.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize interception: {init_result.get('error', 'Unknown error')}"
            )
        
        print(f"[OAUTH INTERCEPTION] ✅ Interception ready, browser is listening for tokens")
        
        # Store session
        session_id = str(uuid.uuid4())
        oauth_interceptor_sessions[session_id] = {
            'interceptor': interceptor,
            'firm_user_id': firm_user_id,
            'ghl_location_id': ghl_location_id,
            'started_at': datetime.now().isoformat()
        }
        
        # Monitor for tokens in background
        async def monitor_for_tokens():
            try:
                # Start session and open OAuth URL
                await interceptor.start_session(oauth_url)
                
                # Wait for completion (5 minutes timeout)
                result = await interceptor.wait_for_completion(timeout_seconds=300)
                
                if result.get('success'):
                    tokens = await interceptor.get_captured_tokens()
                    
                    print(f"[OAUTH INTERCEPTION] ✅ Tokens captured!")
                    print(f"[OAUTH INTERCEPTION] Access Token: {'✅' if tokens['access_token'] else '❌'}")
                    print(f"[OAUTH INTERCEPTION] Firebase Token: {'✅' if tokens['firebase_token'] else '❌'}")
                    print(f"[OAUTH INTERCEPTION] PIT Token: {'✅' if tokens['pit_token'] else '❌'}")
                    
                    # Save tokens to database
                    if tokens['access_token'] or tokens['firebase_token']:
                        # Check if facebook_integrations record exists
                        fb_result = supabase.table('facebook_integrations').select('id').eq('firm_user_id', firm_user_id).execute()
                        
                        update_data = {
                            'updated_at': datetime.now().isoformat()
                        }
                        
                        if tokens['access_token']:
                            update_data['access_token'] = tokens['access_token']
                        if tokens['firebase_token']:
                            update_data['firebase_token'] = tokens['firebase_token']
                        if tokens['pit_token']:
                            update_data['pit_token'] = tokens['pit_token']
                        
                        if fb_result.data and len(fb_result.data) > 0:
                            # Update existing record
                            supabase.table('facebook_integrations').update(update_data).eq('firm_user_id', firm_user_id).execute()
                            print(f"[OAUTH INTERCEPTION] ✅ Updated facebook_integrations table")
                        else:
                            # Create new record
                            update_data['id'] = str(uuid.uuid4())
                            update_data['firm_user_id'] = firm_user_id
                            update_data['ghl_location_id'] = ghl_location_id
                            update_data['automation_status'] = 'tokens_captured'
                            supabase.table('facebook_integrations').insert(update_data).execute()
                            print(f"[OAUTH INTERCEPTION] ✅ Created facebook_integrations record")
                
                # Cleanup
                await interceptor.cleanup()
                
                # Remove from sessions
                if session_id in oauth_interceptor_sessions:
                    del oauth_interceptor_sessions[session_id]
                
            except Exception as e:
                print(f"[OAUTH INTERCEPTION] ❌ Error in background task: {e}")
                await interceptor.cleanup()
        
        # Start background task
        background_tasks.add_task(run_interception)
        
        return {
            'success': True,
            'message': 'OAuth browser opened with token interception. Please complete the login in the browser window.',
            'session_id': session_id,
            'oauth_url': oauth_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[OAUTH INTERCEPTION] ❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/facebook/oauth-interception-status/{session_id}")
async def get_oauth_interception_status(session_id: str):
    """Check status of OAuth interception session"""
    try:
        if session_id not in oauth_interceptor_sessions:
            return {
                'success': False,
                'message': 'Session not found or expired'
            }
        
        session = oauth_interceptor_sessions[session_id]
        interceptor = session['interceptor']
        
        tokens = await interceptor.get_captured_tokens()
        
        return {
            'success': True,
            'session_active': interceptor.session_active,
            'tokens_captured': tokens['tokens_captured'],
            'started_at': session['started_at']
        }
        
    except Exception as e:
        print(f"[OAUTH INTERCEPTION] ❌ Status check error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@app.get("/api/facebook/oauth-health")
async def facebook_oauth_health():
    """Health check for Facebook OAuth service"""
    return {
        "service": "facebook_oauth",
        "status": "healthy",
        "endpoints": [
            "/api/facebook/extract-oauth-params",
            "/api/facebook/start-oauth-with-interception",
            "/api/facebook/oauth-interception-status/{session_id}",
            "/api/facebook/integrate",
            "/api/facebook/integration-status/{location_id}",
            "/api/facebook/connect-page"
        ],
        "timestamp": datetime.now().isoformat()
    }

# =============================================================================
# FACEBOOK INTEGRATION WITH BROWSER AUTOMATION
# =============================================================================

# In-memory storage for integration status (in production, use Redis or database)
integration_status = {}

# In-memory storage for OAuth interceptor sessions
oauth_interceptor_sessions = {}

@app.post("/api/facebook/integrate")
async def integrate_facebook(request: dict, background_tasks: BackgroundTasks):
    """Start Facebook integration with browser automation"""
    
    # Use dynamic location_id from request
    location_id = request.get('location_id')
    if not location_id:
        raise HTTPException(status_code=400, detail="location_id required")
    
    # Initialize status
    integration_status[location_id] = {
        "status": "processing",
        "current_step": "Starting browser automation...",
        "started_at": datetime.now().isoformat()
    }
    
    # Start background task
    background_tasks.add_task(run_facebook_integration, request)
    
    return {
        "status": "processing",
        "message": "Facebook integration started. Browser automation in progress...",
        "location_id": location_id,
        "status_check_url": f"/api/facebook/integration-status/{location_id}",
        "note": "Use the returned location_id for status checks"
    }

async def run_facebook_integration(request: dict):
    """Run the actual Facebook integration with browser automation using dynamic credentials"""
    
    # Use dynamic values from request
    location_id = request.get('location_id')
    if not location_id:
        raise HTTPException(status_code=400, detail="location_id required")
    
    try:
        # Update status 
        integration_status[location_id]["current_step"] = "Starting Facebook integration with Gmail 2FA..."
        
        # NOTE: Facebook OAuth is handled as part of the main GHL automation flow
        # The ghl_automation_complete_playwright.py handles Facebook integration
        # during the initial user registration process
        
        # For now, return a message indicating OAuth should be done during registration
        integration_status[location_id] = {
            "status": "completed",
            "message": "Facebook OAuth is handled during the initial GHL registration process. Check if Facebook integration was completed during account setup.",
            "completed_at": datetime.now().isoformat()
        }
            
    except Exception as e:
        integration_status[location_id] = {
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        }

@app.get("/api/facebook/integration-status")
async def get_integration_status_default():
    """Get integration status - requires location_id parameter"""
    raise HTTPException(status_code=400, detail="location_id parameter required. Use /api/facebook/integration-status/{location_id}")

@app.post("/api/facebook/integration-status/reset/{location_id}")
async def reset_integration_status(location_id: str):
    """Reset/clear stuck integration status for specific location"""
    if location_id in integration_status:
        del integration_status[location_id]
    return {"status": "reset", "message": f"Integration status cleared for location {location_id}"}


@app.get("/api/facebook/integration-status/{location_id}")
async def get_integration_status(location_id: str):
    """Get the current integration status for the specified location_id"""
    
    # Check if status exists for the requested location_id
    if location_id in integration_status:
        status_data = integration_status[location_id].copy()
        status_data["location_id"] = location_id
        return status_data
    
    # If no status found, return not_found
    return {
        "status": "not_found", 
        "message": "No integration found for this location",
        "location_id": location_id
    }


@app.post("/api/facebook/check-accounts-after-oauth")
async def check_facebook_accounts_after_oauth(request: dict):
    """
    Check for newly created Facebook accounts after OAuth completion
    This is called when user clicks 'I Completed Facebook OAuth'
    """
    try:
        user_id = request.get('user_id')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        print(f"📱 [OAUTH CHECK] Checking for Facebook accounts after OAuth for user: {user_id}")
        
        # Convert user_id to UUID format for database query
        try:
            firm_user_uuid = str(uuid.UUID(user_id))  # Validates and formats UUID
        except ValueError:
            firm_user_uuid = user_id  # Keep as string if not valid UUID
        
        # Get setup data
        setup_result = supabase.table('squidgy_agent_business_setup').select(
            'highlevel_tokens, ghl_location_id, facebook_account_id'
        ).eq('firm_user_id', firm_user_uuid).eq('agent_id', 'SOLAgent').eq('setup_type', 'GHLSetup').single().execute()
        
        if not setup_result.data:
            return {
                "success": False,
                "message": "No GHL setup found",
                "facebook_account_id": None
            }
        
        setup_data = setup_result.data
        tokens = setup_data.get('highlevel_tokens', {})
        target_location_id = setup_data.get('ghl_location_id')
        existing_account_id = setup_data.get('facebook_account_id')
        
        # If we already have an account ID, return it
        if existing_account_id:
            print(f"📱 [OAUTH CHECK] Found existing account ID: {existing_account_id}")
            return {
                "success": True,
                "message": "Facebook account already registered",
                "facebook_account_id": existing_account_id
            }
        
        # Check for PIT token
        pit_token = None
        if isinstance(tokens, dict):
            pit_token = tokens.get('tokens', {}).get('private_integration_token')
        
        if not pit_token or not target_location_id:
            return {
                "success": False,
                "message": "Missing PIT token or location ID",
                "facebook_account_id": None
            }
        
        print(f"📱 [OAUTH CHECK] Checking for new Facebook accounts with PIT token...")
        
        # Check for Facebook accounts using PIT token
        import httpx
        headers = {
            "Authorization": f"Bearer {pit_token}",
            "Version": "2021-07-28",
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            accounts_url = f"https://services.leadconnectorhq.com/social-media-posting/{target_location_id}/accounts"
            response = await client.get(accounts_url, headers=headers)
            
            if response.status_code == 200:
                accounts_data = response.json()
                facebook_accounts = []
                
                if 'results' in accounts_data and 'accounts' in accounts_data['results']:
                    facebook_accounts = [acc for acc in accounts_data['results']['accounts'] if acc.get('platform') == 'facebook']
                
                if facebook_accounts:
                    # Found Facebook account(s)! Store the first one
                    facebook_account_id = facebook_accounts[0].get('_id') or facebook_accounts[0].get('id')
                    
                    print(f"📱 [OAUTH CHECK] ✅ Found new Facebook account: {facebook_account_id}")
                    
                    # Store the account ID in database
                    supabase.table('squidgy_agent_business_setup').update({
                        'facebook_account_id': facebook_account_id,
                        'updated_at': 'now()'
                    }).eq('firm_user_id', firm_user_uuid).eq('agent_id', 'SOLAgent').eq('setup_type', 'GHLSetup').execute()
                    
                    return {
                        "success": True,
                        "message": f"Facebook account registered successfully",
                        "facebook_account_id": facebook_account_id,
                        "total_accounts": len(facebook_accounts)
                    }
                else:
                    print(f"📱 [OAUTH CHECK] No Facebook accounts found yet")
                    return {
                        "success": False,
                        "message": "No Facebook accounts found. OAuth may still be processing.",
                        "facebook_account_id": None
                    }
            else:
                print(f"📱 [OAUTH CHECK] ❌ API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "message": f"API error: {response.status_code}",
                    "facebook_account_id": None
                }
                
    except Exception as e:
        print(f"📱 [OAUTH CHECK] ❌ Error: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "facebook_account_id": None
        }


# =============================================================================
# NEW FACEBOOK ENDPOINTS USING facebook_integrations TABLE
# =============================================================================

@app.post("/api/ghl/get-location-id")
async def get_ghl_location_id(request: dict):
    """
    Get GHL location ID from ghl_subaccounts table for a user
    """
    try:
        firm_user_id = request.get('firm_user_id')
        if not firm_user_id:
            return {"success": False, "error": "User ID not provided"}
        
        print(f"[GHL LOCATION] Getting location ID for user: {firm_user_id}")
        
        # Check ghl_subaccounts table
        result = supabase.table('ghl_subaccounts').select(
            'ghl_location_id, agent_id, subaccount_name'
        ).eq('firm_user_id', firm_user_id).execute()
        
        if not result.data or len(result.data) == 0:
            print(f"[GHL LOCATION] No GHL subaccount found for user: {firm_user_id}")
            return {
                "success": False,
                "error": "No GHL account found"
            }
        
        # Get the most recent subaccount
        subaccount = result.data[0]
        location_id = subaccount.get('ghl_location_id')
        
        print(f"[GHL LOCATION] Found location ID: {location_id}")
        
        return {
            "success": True,
            "location_id": location_id,
            "agent_id": subaccount.get('agent_id'),
            "subaccount_name": subaccount.get('subaccount_name')
        }
        
    except Exception as e:
        print(f"[GHL LOCATION] Error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/facebook/check-integration-status")
async def check_facebook_integration_status(request: dict):
    """
    Check if facebook_integrations record exists for a user and has tokens
    """
    try:
        firm_user_id = request.get('firm_user_id')
        if not firm_user_id:
            # Try to get from profiles table using email
            email = request.get('email')
            if email:
                profile_result = supabase.table('profiles').select('user_id').eq('email', email).single().execute()
                if profile_result.data:
                    firm_user_id = profile_result.data['user_id']
        
        if not firm_user_id:
            return {
                "exists": False,
                "has_tokens": False,
                "message": "User ID not provided"
            }
        
        print(f"[FB CHECK] Checking integration status for user: {firm_user_id}")
        
        # Check facebook_integrations table
        result = supabase.table('facebook_integrations').select(
            'id, firm_user_id, ghl_location_id, pit_token, '
            'access_token, firebase_token, automation_status, automation_completed_at, '
            'facebook_business_id, facebook_page_id'
        ).eq('firm_user_id', firm_user_id).execute()
        
        if not result.data or len(result.data) == 0:
            print(f"[FB CHECK] No integration found for user: {firm_user_id}")
            return {
                "exists": False,
                "has_tokens": False,
                "message": "No Facebook integration found"
            }
        
        # Get the most recent integration
        integration = result.data[0]
        has_pit = bool(integration.get('pit_token'))
        has_access = bool(integration.get('access_token'))
        has_firebase = bool(integration.get('firebase_token'))
        
        print(f"[FB CHECK] Found integration - PIT: {has_pit}, Access: {has_access}, Firebase: {has_firebase}")
        
        return {
            "exists": True,
            "has_tokens": has_pit,
            "has_pit_token": has_pit,
            "has_access_token": has_access,
            "has_firebase_token": has_firebase,
            "automation_status": integration.get('automation_status'),
            "automation_completed_at": integration.get('automation_completed_at'),
            "facebook_business_id": integration.get('facebook_business_id'),
            "facebook_page_id": integration.get('facebook_page_id'),
            "ghl_location_id": integration.get('ghl_location_id'),
            "message": "Integration found with tokens" if has_pit else "Integration found but missing tokens"
        }
        
    except Exception as e:
        print(f"[FB CHECK] Error checking integration status: {e}")
        return {
            "exists": False,
            "has_tokens": False,
            "error": str(e),
            "message": f"Error checking integration: {str(e)}"
        }

# OLD ENDPOINT REMOVED - Using new simple endpoint below

@app.post("/api/facebook/save-selected-pages")
async def save_selected_facebook_pages(request: dict):
    """
    Save selected Facebook pages to facebook_integrations table
    """
    try:
        firm_user_id = request.get('firm_user_id')
        selected_page_ids = request.get('selected_page_ids', [])
        
        if not firm_user_id:
            raise HTTPException(status_code=400, detail="firm_user_id is required")
        
        if not selected_page_ids:
            raise HTTPException(status_code=400, detail="No pages selected")
        
        print(f"[FB SAVE] Saving {len(selected_page_ids)} pages for user: {firm_user_id}")
        
        # Store selected pages in automation_result
        selected_pages_data = {
            "selected_page_ids": selected_page_ids,
            "connected_at": datetime.now().isoformat(),
            "status": "connected"
        }
        
        # Update facebook_integrations record
        update_result = supabase.table('facebook_integrations').update({
            'automation_result': selected_pages_data,
            'facebook_page_id': selected_page_ids[0] if len(selected_page_ids) == 1 else None,
            'status': 'active',
            'updated_at': datetime.now().isoformat()
        }).eq('firm_user_id', firm_user_id).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=404, detail="Failed to update integration")
        
        print(f"[FB SAVE] Successfully saved {len(selected_page_ids)} pages")
        
        # Also connect pages in GHL if we have the tokens
        integration_result = supabase.table('facebook_integrations').select(
            'ghl_location_id, pit_token, firebase_token'
        ).eq('firm_user_id', firm_user_id).single().execute()
        
        if integration_result.data:
            integration = integration_result.data
            pit_token = integration.get('pit_token')
            firebase_token = integration.get('firebase_token')
            location_id = integration.get('ghl_location_id')
            
            if pit_token and firebase_token and location_id:
                # Connect pages in GHL
                for page_id in selected_page_ids:
                    try:
                        ghl_api_url = f"https://services.leadconnectorhq.com/locations/{location_id}/integrations/facebook/pages/{page_id}/connect"
                        
                        headers = {
                            "Authorization": f"Bearer {pit_token}",
                            "token-id": firebase_token,
                            "Version": "2021-04-15",
                            "Content-Type": "application/json"
                        }
                        
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.post(ghl_api_url, headers=headers, json={})
                            print(f"[FB SAVE] Connected page {page_id} in GHL: {response.status_code}")
                    except Exception as e:
                        print(f"[FB SAVE] Error connecting page {page_id} in GHL: {e}")
        
        return {
            "success": True,
            "saved_pages": selected_page_ids,
            "message": f"Successfully saved {len(selected_page_ids)} pages"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[FB SAVE] Error saving pages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# SIMPLE FACEBOOK INTEGRATION ENDPOINTS
# =============================================================================

@app.post("/api/facebook/get-pages-from-integration")
async def get_pages_from_integration(request: dict):
    """
    Simple endpoint to get Facebook pages using stored tokens
    No browser automation - just API calls using pit_token and firebase_token
    """
    try:
        firm_user_id = request.get('firm_user_id')
        if not firm_user_id:
            raise HTTPException(status_code=400, detail="firm_user_id is required")
            
        print(f"[FB PAGES] Getting pages for user: {firm_user_id}")
        
        # Try to get integration record with stored pages
        integration_result = supabase.table('facebook_integrations').select(
            'ghl_location_id, pit_token, firebase_token, pages'
        ).eq('firm_user_id', firm_user_id).execute()
        
        pit_token = None
        firebase_token = None
        location_id = None
        stored_pages = None
        
        if integration_result.data and len(integration_result.data) > 0:
            integration = integration_result.data[0] 
            pit_token = integration.get('pit_token')
            firebase_token = integration.get('firebase_token')
            location_id = integration.get('ghl_location_id')
            stored_pages = integration.get('pages')
        
        # If no tokens in facebook_integrations, try to get from ghl_subaccounts as fallback
        if not pit_token or not location_id:
            print(f"[FB PAGES] No tokens in facebook_integrations, checking ghl_subaccounts...")
            ghl_result = supabase.table('ghl_subaccounts').select(
                'ghl_location_id, pit_token'
            ).eq('firm_user_id', firm_user_id).execute()

            if ghl_result.data and len(ghl_result.data) > 0:
                location_id = ghl_result.data[0].get('ghl_location_id')
                pit_token = ghl_result.data[0].get('pit_token')
                print(f"[FB PAGES] Using PIT token from ghl_subaccounts for location: {location_id}")
            else:
                raise HTTPException(status_code=404, detail="No GHL account found. Please complete GHL setup first.")
        
        # Check if we have the minimum required token
        if not pit_token:
            raise HTTPException(status_code=400, detail="Missing PIT token. Please complete GHL setup first.")
        
        # If we have tokens, first check if we have stored pages
        if stored_pages and isinstance(stored_pages, list) and len(stored_pages) > 0:
            print(f"[FB PAGES] Using stored pages: {len(stored_pages)} pages found")
            return {
                "success": True,
                "pages": stored_pages,
                "message": f"Found {len(stored_pages)} Facebook pages (from database)",
                "source": "database"
            }
        
        # If no stored pages but we have tokens, fetch from Facebook Graph API using access_token
        
        # Check if we have access_token from facebook_integrations
        access_token = None
        if integration_result.data and len(integration_result.data) > 0:
            access_token = integration_result.data[0].get('access_token')
        
        # Get Firebase token from ghl_subaccounts
        if not firebase_token:
            print(f"[FB PAGES] No firebase_token in facebook_integrations, checking ghl_subaccounts...")
            ghl_result = supabase.table('ghl_subaccounts').select(
                'firebase_token'
            ).eq('firm_user_id', firm_user_id).execute()

            if ghl_result.data and len(ghl_result.data) > 0:
                firebase_token = ghl_result.data[0].get('firebase_token')
                print(f"[FB PAGES] Using Firebase token from ghl_subaccounts")
        
        if not firebase_token:
            raise HTTPException(status_code=400, detail="Missing Firebase token. Please wait for token refresh to complete.")
        
        # Use GHL backend API to fetch Facebook pages
        print(f"[FB PAGES] Fetching pages from GHL backend API using Firebase token")
        
        ghl_backend_url = f"https://backend.leadconnectorhq.com/integrations/facebook/{location_id}/allPages"
        headers = {
            "authorization": f"Bearer {access_token or pit_token}",
            "token-id": firebase_token,
            "version": "2021-07-28",
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(ghl_backend_url, headers=headers, params={"limit": 100})
            
            if response.status_code == 200:
                ghl_pages_data = response.json()
                print(f"[FB PAGES] GHL Backend API Response: {ghl_pages_data}")
                
                facebook_pages = ghl_pages_data.get('pages', [])
                
                if not facebook_pages:
                    return {
                        "success": False,
                        "message": "No Facebook pages found. Please connect your Facebook pages in GoHighLevel first.",
                        "pages": [],
                        "source": "ghl_backend_empty"
                    }
                
                facebook_accounts_data = facebook_pages
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', response.text)
                raise HTTPException(status_code=response.status_code, detail=f"GHL Backend API error: {error_msg}")
        
        # Transform to our expected format for UI consistency
        transformed_pages = []
        for fb_account in facebook_accounts_data:
            transformed_page = {
                "id": fb_account.get("id", ""),
                "name": fb_account.get("name", ""),
                "facebookPageId": fb_account.get("id", ""),
                "facebookPageName": fb_account.get("name", ""),
                "type": fb_account.get("type", "facebook"),
                "locationId": fb_account.get("locationId", location_id)
            }
            transformed_pages.append(transformed_page)
        
        print(f"[FB PAGES] Successfully retrieved {len(transformed_pages)} pages")
        
        # Store the pages in database for future use
        try:
            supabase.table('facebook_integrations').update({
                'pages': transformed_pages,
                'updated_at': datetime.now().isoformat()
            }).eq('firm_user_id', firm_user_id).execute()
            print(f"[FB PAGES] Stored {len(transformed_pages)} pages in database")
        except Exception as e:
            print(f"[FB PAGES] Warning: Could not store pages in database: {e}")
        
        # Determine source for response message
        source = "facebook_api" if access_token else "ghl_api"
        
        return {
            "success": True,
            "pages": transformed_pages,
            "message": f"Found {len(transformed_pages)} Facebook pages",
            "source": source
        }
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"[FB PAGES] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/facebook/connect-selected-pages")
async def connect_selected_pages(request: dict):
    """
    Simple endpoint to connect selected Facebook pages
    Stores selected pages in database and connects them in GHL
    """
    try:
        firm_user_id = request.get('firm_user_id') 
        selected_page_ids = request.get('selected_page_ids', [])
        
        if not firm_user_id:
            raise HTTPException(status_code=400, detail="firm_user_id is required")
        if not selected_page_ids:
            raise HTTPException(status_code=400, detail="selected_page_ids is required")
            
        print(f"[FB CONNECT] Connecting {len(selected_page_ids)} pages for user: {firm_user_id}")
        
        # Get integration record with stored pages
        integration_result = supabase.table('facebook_integrations').select(
            'ghl_location_id, pit_token, firebase_token, pages'
        ).eq('firm_user_id', firm_user_id).execute()
        
        if not integration_result.data:
            raise HTTPException(status_code=404, detail="No Facebook integration found")
        
        integration = integration_result.data[0]
        pit_token = integration.get('pit_token')
        firebase_token = integration.get('firebase_token') 
        location_id = integration.get('ghl_location_id')
        stored_pages = integration.get('pages', [])
        
        # Get full page data for the selected page IDs
        selected_pages_data = []
        for page_id in selected_page_ids:
            # Find the page data from stored pages
            page_data = None
            for stored_page in stored_pages:
                if (stored_page.get('id') == page_id or 
                    stored_page.get('facebookPageId') == page_id):
                    page_data = stored_page
                    break
            
            if page_data:
                selected_pages_data.append(page_data)
            else:
                # If page data not found, create basic structure
                selected_pages_data.append({
                    "id": page_id,
                    "facebookPageId": page_id,
                    "name": f"Page {page_id}",
                    "facebookPageName": f"Page {page_id}",
                    "selected_at": datetime.now().isoformat()
                })
        
        # Store selected pages with full data in automation_result
        automation_result = {
            "selected_page_ids": selected_page_ids,
            "selected_pages_data": selected_pages_data,
            "connected_at": datetime.now().isoformat(),
            "status": "connected",
            "total_pages": len(selected_page_ids)
        }
        
        # Update facebook_integrations record with connected_pages data
        update_result = supabase.table('facebook_integrations').update({
            'automation_result': automation_result,
            'connected_pages': selected_pages_data,  # Store connected pages in new column
            'automation_status': 'completed',
            'automation_completed_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }).eq('firm_user_id', firm_user_id).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to save selected pages")
        
        # Connect pages in GHL if we have tokens
        connected_pages = []
        failed_pages = []
        
        if pit_token and firebase_token and location_id:
            try:
                # Use the correct GHL API endpoint for connecting pages
                ghl_api_url = f"https://backend.leadconnectorhq.com/integrations/facebook/{location_id}/pages"
                
                headers = {
                    "token-id": firebase_token,
                    "channel": "APP",
                    "source": "WEB_USER",
                    "version": "2021-07-28",
                    "accept": "application/json, text/plain, */*",
                    "content-type": "application/json"
                }
                
                # Prepare pages payload - send all selected pages at once
                pages_payload = {
                    "pages": selected_pages_data
                }
                
                print(f"[FB CONNECT] Connecting {len(selected_pages_data)} pages to GHL...")
                print(f"[FB CONNECT] API URL: {ghl_api_url}")
                print(f"[FB CONNECT] Payload: {pages_payload}")
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(ghl_api_url, headers=headers, json=pages_payload)
                    
                    if response.status_code in [200, 201]:
                        connected_pages = selected_page_ids
                        print(f"[FB CONNECT] Successfully connected {len(selected_page_ids)} pages")
                        print(f"[FB CONNECT] GHL Response: {response.json()}")
                    else:
                        failed_pages = selected_page_ids
                        print(f"[FB CONNECT] Failed to connect pages: {response.status_code}")
                        print(f"[FB CONNECT] Error: {response.text}")
                        
            except Exception as e:
                failed_pages = selected_page_ids
                print(f"[FB CONNECT] Error connecting pages: {e}")
        
        return {
            "success": True,
            "connected_pages": connected_pages,
            "failed_pages": failed_pages,
            "total_selected": len(selected_page_ids),
            "message": f"Connected {len(connected_pages)} of {len(selected_page_ids)} pages"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[FB CONNECT] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/facebook/get-connection-status")
async def get_facebook_connection_status(firm_user_id: str):
    """
    Check if user has connected Facebook pages
    Returns connection status for UI step marking
    """
    try:
        if not firm_user_id:
            raise HTTPException(status_code=400, detail="firm_user_id is required")
        
        # Check if user has connected pages
        integration_result = supabase.table('facebook_integrations').select(
            'connected_pages, automation_status, automation_completed_at'
        ).eq('firm_user_id', firm_user_id).execute()
        
        if not integration_result.data:
            return {
                "success": True,
                "is_connected": False,
                "connected_pages": [],
                "total_connected": 0,
                "message": "No Facebook integration found"
            }
        
        integration = integration_result.data[0]
        connected_pages = integration.get('connected_pages', [])
        automation_status = integration.get('automation_status')
        
        # Consider connected if there are connected_pages and status is completed
        is_connected = (
            len(connected_pages) > 0 and 
            automation_status == 'completed'
        )
        
        return {
            "success": True,
            "is_connected": is_connected,
            "connected_pages": connected_pages,
            "total_connected": len(connected_pages),
            "automation_status": automation_status,
            "message": f"Found {len(connected_pages)} connected pages" if is_connected else "No connected pages found"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[FB STATUS] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# BUSINESS PROFILE ENDPOINTS
# =============================================================================

class BusinessProfileRequest(BaseModel):
    firm_user_id: str
    business_name: str
    business_email: str
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "US"
    postal_code: Optional[str] = None
    logo_url: Optional[str] = None
    screenshot_url: Optional[str] = None
    favicon_url: Optional[str] = None

@app.post("/api/business/upload-logo")
async def upload_business_logo(
    logo: UploadFile = File(...),
    session_id: str = Form(default="")
):
    """
    Upload business logo to Supabase Storage
    """
    try:
        # Validate file type
        if not logo.content_type or not logo.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Validate file size (max 5MB)
        content = await logo.read()
        if len(content) > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(status_code=400, detail="File size must be less than 5MB")
        
        # Generate filename
        file_extension = logo.filename.split('.')[-1] if '.' in logo.filename else 'jpg'
        if session_id:
            filename = f"{session_id}_business_logo.{file_extension}"
        else:
            filename = f"business_logo_{int(time.time())}.{file_extension}"
        
        # Process image with PIL to ensure it's valid and convert to JPG
        try:
            # Save uploaded content to temp file
            with tempfile.NamedTemporaryFile(delete=False) as tmp_input:
                tmp_input.write(content)
                tmp_input_path = tmp_input.name
            
            # Open and process image
            img = Image.open(tmp_input_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save as JPG
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_output:
                img.save(tmp_output.name, 'JPEG', quality=85)
                tmp_output_path = tmp_output.name
            
            # Read processed content
            with open(tmp_output_path, 'rb') as f:
                processed_content = f.read()
            
            # Clean up
            os.unlink(tmp_input_path)
            os.unlink(tmp_output_path)
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Upload to Supabase Storage
        storage_path = f"business_logos/{filename}"
        
        # Remove existing file if present
        try:
            supabase.storage.from_('static').remove([storage_path])
        except:
            pass
        
        response = supabase.storage.from_('static').upload(
            storage_path,
            processed_content,
            {
                "content-type": "image/jpeg",
                "upsert": "true"
            }
        )
        
        # Handle response
        if hasattr(response, 'error') and response.error:
            if "already exists" in str(response.error):
                public_url = supabase.storage.from_('static').get_public_url(storage_path)
                return {
                    "status": "success",
                    "message": "Logo uploaded successfully",
                    "logo_url": public_url,
                    "storage_path": storage_path,
                    "filename": filename
                }
            else:
                raise HTTPException(status_code=500, detail=f"Upload error: {response.error}")
        else:
            public_url = supabase.storage.from_('static').get_public_url(storage_path)
            return {
                "status": "success",
                "message": "Logo uploaded successfully",
                "logo_url": public_url,
                "storage_path": storage_path,
                "filename": filename
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading business logo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/business/save-profile")
async def save_business_profile(request: BusinessProfileRequest):
    """
    Save business profile information to database
    """
    try:
        # Get user name, email, and company_id from profiles table
        user_profile = supabase.table('profiles')\
            .select('full_name, email, company_id')\
            .eq('user_id', request.firm_user_id)\
            .single()\
            .execute()
        
        if not user_profile.data:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        profile_data = user_profile.data
        
        # Ensure company_id exists for firm_id
        print(f"[BUSINESS PROFILE] User profile data: {profile_data}")
        
        if not profile_data.get('company_id'):
            print(f"[BUSINESS PROFILE] ❌ Missing company_id in profile for user: {request.firm_user_id}")
            raise HTTPException(status_code=400, detail="User profile missing company_id - required for business profile")
        
        print(f"[BUSINESS PROFILE] ✅ Using company_id as firm_id: {profile_data['company_id']}")
        
        # Prepare business profile data
        business_data = {
            'firm_user_id': request.firm_user_id,
            'firm_id': profile_data['company_id'],  # Use company_id from profiles as firm_id
            'business_name': request.business_name,
            'business_email': request.business_email,
            'phone': request.phone,
            'website': request.website,
            'address': request.address,
            'city': request.city,
            'state': request.state,
            'country': request.country,
            'postal_code': request.postal_code,
            'logo_url': request.logo_url,
            'screenshot_url': request.screenshot_url,
            'favicon_url': request.favicon_url,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert business profile
        try:
            result = supabase.table('business_profiles')\
                .upsert(business_data, on_conflict='firm_user_id')\
                .execute()
            
            print(f"[BUSINESS PROFILE] ✅ Successfully saved business profile")
            print(f"[BUSINESS PROFILE] Business: {request.business_name}")
            print(f"[BUSINESS PROFILE] Firm ID: {profile_data['company_id']}")
            
        except Exception as e:
            print(f"[BUSINESS PROFILE] ❌ Database error: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        return {
            "status": "success",
            "message": "Business profile saved successfully",
            "business_profile": business_data,
            "user_info": {
                "name": profile_data['full_name'],
                "email": profile_data['email']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving business profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/business/profile/{firm_user_id}")
async def get_business_profile(firm_user_id: str):
    """
    Get business profile by user ID
    """
    try:
        result = supabase.table('business_profiles')\
            .select('*')\
            .eq('firm_user_id', firm_user_id)\
            .single()\
            .execute()
        
        if not result.data:
            return {
                "status": "not_found",
                "message": "Business profile not found",
                "business_profile": None
            }
        
        return {
            "status": "success",
            "message": "Business profile found",
            "business_profile": result.data
        }
        
    except Exception as e:
        logger.error(f"Error getting business profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================

# CORS middleware
# ============================================================================
# BUSINESS SETUP WORKFLOW ENDPOINTS
# ============================================================================

import secrets
import string
from typing import Optional
from fastapi import BackgroundTasks

# Business Setup Models
class BusinessInformationRequest(BaseModel):
    firm_user_id: str
    agent_id: str
    business_name: str
    business_address: str
    city: str
    state: str
    country: str = "United States"
    postal_code: str
    business_logo_url: Optional[str] = None
    snapshot_id: str  # HighLevel snapshot ID for location creation

class BusinessSetupResponse(BaseModel):
    success: bool
    message: str
    business_id: Optional[str] = None
    status: str
    ghl_location_id: Optional[str] = None
    ghl_user_email: Optional[str] = None
    automation_started: bool = False

# Business Setup Utility Functions
def generate_secure_password(length: int = 12) -> str:
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_user_email(business_name: str, location_id: str) -> str:
    """Generate a unique email for the HighLevel user"""
    clean_name = ''.join(c.lower() for c in business_name if c.isalnum())[:10]
    return f"{clean_name}+{location_id}@squidgyai.com"

async def create_ghl_location_sim(snapshot_id: str, business_info: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate creating a HighLevel location (replace with real API call)"""
    try:
        print(f"[GHL API] Creating location with snapshot: {snapshot_id}")
        print(f"[GHL API] Business: {business_info['business_name']}")
        
        # Generate location ID (replace with actual API call)
        location_id = f"LOC_{uuid.uuid4().hex[:16].upper()}"
        
        return {
            "success": True,
            "location_id": location_id,
            "location_name": business_info['business_name'],
            "address": business_info['business_address']
        }
        
    except Exception as e:
        print(f"[ERROR] Location creation failed: {e}")
        return {"success": False, "error": str(e)}

async def create_ghl_user_sim(location_id: str, email: str, password: str, business_info: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate creating a HighLevel user (replace with real API call)"""
    try:
        print(f"[GHL API] Creating user for location: {location_id}")
        print(f"[GHL API] Email: {email}")
        
        # Generate user ID (replace with actual API call)
        user_id = f"USER_{uuid.uuid4().hex[:16].upper()}"
        
        return {
            "success": True,
            "user_id": user_id,
            "email": email,
            "location_id": location_id
        }
        
    except Exception as e:
        print(f"[ERROR] User creation failed: {e}")
        return {"success": False, "error": str(e)}


# Business Setup API Endpoints

@app.post("/api/facebook/retry-token-capture")
async def retry_facebook_token_capture(request: dict, background_tasks: BackgroundTasks):
    """
    Retry Facebook token capture using ghl_automation_for_retry.py
    Updates facebook_integrations table with access_token, firebase_token, and expires_at
    """
    try:
        firm_user_id = request.get('firm_user_id')
        
        if not firm_user_id:
            raise HTTPException(status_code=400, detail="firm_user_id is required")
        
        print(f"[RETRY] Starting token capture retry for firm_user_id: {firm_user_id}")
        
        # Check if facebook_integrations record exists
        integration_result = supabase.table('facebook_integrations').select(
            'id, firm_user_id, ghl_location_id, automation_status'
        ).eq('firm_user_id', firm_user_id).execute()
        
        if not integration_result.data:
            raise HTTPException(
                status_code=404, 
                detail="No Facebook integration record found. Please complete initial setup first."
            )
        
        integration = integration_result.data[0]
        location_id = integration.get('ghl_location_id')
        
        if not location_id:
            # Try to get location_id from ghl_subaccounts
            ghl_result = supabase.table('ghl_subaccounts').select(
                'ghl_location_id'
            ).eq('firm_user_id', firm_user_id).execute()
            
            if ghl_result.data:
                location_id = ghl_result.data[0].get('ghl_location_id')
            
            if not location_id:
                raise HTTPException(
                    status_code=400, 
                    detail="No GHL location ID found. Please complete business setup first."
                )
        
        # Update automation status to indicate retry in progress
        supabase.table('facebook_integrations').update({
            'automation_status': 'retry_in_progress',
            'automation_step': 'token_capture_retry',
            'updated_at': datetime.now().isoformat()
        }).eq('firm_user_id', firm_user_id).execute()
        
        # Start background task for retry automation
        background_tasks.add_task(
            run_facebook_retry_automation, 
            firm_user_id, 
            location_id
        )
        
        return {
            "success": True,
            "message": "Token capture retry started in background",
            "firm_user_id": firm_user_id,
            "location_id": location_id,
            "status": "retry_in_progress"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Retry token capture failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_facebook_retry_automation(firm_user_id: str, location_id: str):
    """Background task to run the retry automation script by calling BackgroundAutomationUser1 service"""
    try:
        print(f"[RETRY AUTOMATION] Starting for firm_user_id: {firm_user_id}, location_id: {location_id}")

        # OLD CODE - COMMENTED OUT (Now using BackgroundAutomationUser1 service)
        # # Import the retry automation class
        # from ghl_automation_for_retry import HighLevelRetryAutomation
        #
        # # Run the retry automation
        # automation = HighLevelRetryAutomation(headless=True)  # Headless for background execution
        # success = await automation.run_retry_automation("", "", location_id, firm_user_id)

        # NEW CODE - Call BackgroundAutomationUser1 service
        automation_service_url = os.getenv('AUTOMATION_USER1_SERVICE_URL', 'https://backgroundautomationuser1-1644057ede7b.herokuapp.com')

        print(f"[RETRY AUTOMATION] Calling BackgroundAutomationUser1 service at: {automation_service_url}")

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{automation_service_url}/ghl/retry-automation",
                json={
                    "location_id": location_id,
                    "firm_user_id": firm_user_id
                }
            )

            if response.status_code == 200:
                result = response.json()
                print(f"[RETRY AUTOMATION] ✅ Automation service responded: {result.get('message')}")
                print(f"[RETRY AUTOMATION] 🎯 Task ID: {result.get('task_id')}")
                print(f"[RETRY AUTOMATION] 🚀 Automation is running on remote service")
                print(f"[RETRY AUTOMATION] 💾 Database will be updated automatically by the service")

                # Note: Don't update database here - BackgroundAutomationUser1 service handles it
            else:
                error_msg = f"Service returned {response.status_code}: {response.text}"
                print(f"[RETRY AUTOMATION] ❌ Automation service error: {error_msg}")

                # Update status to failed
                supabase.table('facebook_integrations').update({
                    'automation_status': 'retry_failed',
                    'automation_step': 'service_error',
                    'automation_error': error_msg,
                    'updated_at': datetime.now().isoformat()
                }).eq('firm_user_id', firm_user_id).execute()

    except Exception as e:
        error_msg = f"Exception calling automation service: {e}"
        print(f"[RETRY AUTOMATION] ❌ {error_msg}")

        # Update status to indicate error
        try:
            supabase.table('facebook_integrations').update({
                'automation_status': 'retry_error',
                'automation_step': 'automation_exception',
                'automation_error': error_msg,
                'updated_at': datetime.now().isoformat()
            }).eq('firm_user_id', firm_user_id).execute()
        except Exception as db_error:
            print(f"[RETRY AUTOMATION] Failed to update error status in database: {db_error}")



# ============================================================================
# FIREBASE TOKEN REFRESH ENDPOINT
# ============================================================================

@app.post("/api/ghl/run-complete-automation")
async def run_complete_automation(request: dict, background_tasks: BackgroundTasks):
    """
    Run complete GHL automation including PIT creation
    Calls BackgroundAutomationUser1 service to handle Playwright automation
    Updates ghl_subaccounts table with PIT_Token, Firebase Token, and timestamps
    """
    try:
        firm_user_id = request.get('firm_user_id')
        location_id = request.get('location_id')
        
        if not firm_user_id or not location_id:
            raise HTTPException(status_code=400, detail="firm_user_id and location_id are required")
        
        print(f"[COMPLETE AUTOMATION] Starting for firm_user_id: {firm_user_id}, location: {location_id}")
        
        # Call BackgroundAutomationUser1 service
        automation_service_url = os.getenv('AUTOMATION_USER1_SERVICE_URL', 'https://backgroundautomationuser1-1644057ede7b.herokuapp.com')
        
        print(f"[COMPLETE AUTOMATION] Calling BackgroundAutomationUser1 service at: {automation_service_url}")
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{automation_service_url}/ghl/complete-automation",
                json={
                    "location_id": location_id,
                    "firm_user_id": firm_user_id
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"[COMPLETE AUTOMATION] Service responded: {result.get('message')}")
                print(f"[COMPLETE AUTOMATION] Task ID: {result.get('task_id')}")
                
                return {
                    "success": True,
                    "message": "Complete automation started in background",
                    "task_id": result.get('task_id'),
                    "status": "running"
                }
            else:
                print(f"[COMPLETE AUTOMATION] Service error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Automation service error: {response.text}"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"[COMPLETE AUTOMATION] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ghl/refresh-firebase-token")
async def refresh_firebase_token(request: dict, background_tasks: BackgroundTasks):
    """
    Check if Firebase token is older than 1 hour and refresh if needed
    Updates ghl_subaccounts table with new token and timestamp
    """
    try:
        firm_user_id = request.get('firm_user_id')
        
        if not firm_user_id:
            raise HTTPException(status_code=400, detail="firm_user_id is required")
        
        print(f"[TOKEN REFRESH] Checking token age for firm_user_id: {firm_user_id}")
        
        # Get current token and timestamp from ghl_subaccounts
        ghl_result = supabase.table('ghl_subaccounts').select(
            'id, ghl_location_id, soma_ghl_email, soma_ghl_password, firebase_token, firebase_token_time, automation_status'
        ).eq('firm_user_id', firm_user_id).execute()

        if not ghl_result.data:
            raise HTTPException(
                status_code=404,
                detail="No GHL subaccount found. Please complete setup first."
            )

        ghl_record = ghl_result.data[0]
        location_id = ghl_record.get('ghl_location_id')
        current_token = ghl_record.get('firebase_token')
        token_time = ghl_record.get('firebase_token_time')
        soma_email = ghl_record.get('soma_ghl_email')
        soma_password = ghl_record.get('soma_ghl_password')
        automation_status = ghl_record.get('automation_status')
        
        if not location_id:
            raise HTTPException(status_code=400, detail="GHL location_id not found")
        
        # Check if token needs refresh (older than 1 hour or doesn't exist)
        needs_refresh = True
        token_age = None
        if token_time and current_token:
            from datetime import datetime, timedelta
            token_age = datetime.now() - datetime.fromisoformat(str(token_time))
            if token_age < timedelta(hours=1):
                needs_refresh = False
                print(f"[TOKEN REFRESH] Token is fresh (age: {token_age}), no refresh needed")
        
        if not needs_refresh:
            return {
                "success": True,
                "message": "Token is still valid",
                "token_refreshed": False,
                "token_age_minutes": int(token_age.total_seconds() / 60) if token_age else None
            }
        
        print(f"[TOKEN REFRESH] Token needs refresh, starting automation...")
        
        # Start background task to refresh token
        background_tasks.add_task(
            run_firebase_token_refresh,
            firm_user_id,
            location_id,
            soma_email,
            soma_password
        )
        
        return {
            "success": True,
            "message": "Token refresh started in background",
            "token_refreshed": True,
            "status": "refreshing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TOKEN REFRESH] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_firebase_token_refresh(firm_user_id: str, location_id: str, email: str, password: str):
    """Background task to refresh Firebase token by calling BackgroundAutomationUser1 service"""
    try:
        print(f"[TOKEN REFRESH] Starting token refresh automation for: {firm_user_id}")
        
        # Set status to prevent duplicate runs
        supabase.table('ghl_subaccounts').update({
            'automation_status': 'token_refresh_running',
            'updated_at': datetime.now().isoformat()
        }).eq('firm_user_id', firm_user_id).execute()
        
        # Call BackgroundAutomationUser1 service
        automation_service_url = os.getenv('AUTOMATION_USER1_SERVICE_URL', 'https://backgroundautomationuser1-1644057ede7b.herokuapp.com')
        
        print(f"[TOKEN REFRESH] Calling BackgroundAutomationUser1 service at: {automation_service_url}")
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{automation_service_url}/ghl/retry-automation",
                json={
                    "location_id": location_id,
                    "firm_user_id": firm_user_id
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"[TOKEN REFRESH] Automation service responded: {result.get('message')}")
                print(f"[TOKEN REFRESH] Task ID: {result.get('task_id')}")
                print(f"[TOKEN REFRESH] Automation is running on remote service, database will be updated automatically")
            else:
                print(f"[TOKEN REFRESH] Automation service error: {response.status_code} - {response.text}")
                # Clear running status
                supabase.table('ghl_subaccounts').update({
                    'automation_status': 'token_refresh_failed',
                    'automation_error': f"Service returned {response.status_code}",
                    'updated_at': datetime.now().isoformat()
                }).eq('firm_user_id', firm_user_id).execute()
            
    except Exception as e:
        print(f"[TOKEN REFRESH] Exception calling automation service: {e}")
        # Clear running status on exception
        try:
            supabase.table('ghl_subaccounts').update({
                'automation_status': 'token_refresh_error',
                'automation_error': str(e),
                'updated_at': datetime.now().isoformat()
            }).eq('firm_user_id', firm_user_id).execute()
        except:
            pass


# ============================================================================
# END BUSINESS SETUP WORKFLOW
# ============================================================================

# ============================================================================
# FILE PROCESSING ENDPOINT - Simplified Approach
# ============================================================================

@app.post("/api/file/process")
async def process_file_from_url(
    background_tasks: BackgroundTasks,
    firm_user_id: str = Form(...),
    file_name: str = Form(...),
    file_url: str = Form(...),
    agent_id: str = Form(...),
    agent_name: str = Form(...)
):
    """
    Accept file storage URL from frontend and process in background
    
    Parameters:
    - firm_user_id: User ID from frontend
    - file_name: Original filename
    - file_url: Supabase storage URL (already uploaded by frontend)
    - agent_id: Agent ID from YAML config
    - agent_name: Agent name from YAML config
    
    Returns:
    - Immediate "thanks" response with file_id for tracking
    """
    try:
        logger.info(f"File processing request from user {firm_user_id}: {file_name}")
        
        # Validate required fields
        if not all([firm_user_id, file_name, file_url, agent_id, agent_name]):
            raise HTTPException(status_code=400, detail="All fields are required")
        
        # Create processing record
        result = await file_processing_service.create_processing_record(
            firm_user_id=firm_user_id,
            file_name=file_name,
            file_url=file_url,
            agent_id=agent_id,
            agent_name=agent_name
        )
        
        if not result["success"]:
            logger.error(f"Failed to create processing record: {result['error']}")
            raise HTTPException(status_code=500, detail=f"Failed to create record: {result['error']}")
        
        file_id = result["file_id"]
        logger.info(f"Created processing record: {file_id}")
        
        # Start background text extraction
        processor = get_background_processor()
        background_tasks.add_task(processor.process_file, file_id)
        
        # Return immediate success response
        return {
            "success": True,
            "message": "Thank you! Your file has been received and is being processed.",
            "data": {
                "file_id": file_id,
                "firm_user_id": firm_user_id,
                "file_name": file_name,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "status": "processing_started",
                "processing_url": f"/api/file/status/{file_id}"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in file processing endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

class FileExtractionRequest(BaseModel):
    file_url: str
    file_name: str
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    save_to_kb: Optional[Union[bool, str]] = False
    
    @validator('save_to_kb', pre=True)
    def parse_save_to_kb(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes')
        return False


@app.post("/api/file/extract-text")
async def extract_text_from_file(request: FileExtractionRequest):
    """
    Text extraction from a file URL with optional embedding generation and Neon KB save.
    Called by n8n workflow to extract text from PDF, DOCX, JSON, TXT, MD files.

    Parameters:
    - file_url: Supabase storage URL (or any public URL)
    - file_name: Original filename (used to detect file type by extension)
    - user_id: (Optional) User ID for saving to knowledge base
    - agent_id: (Optional) Agent ID for saving to knowledge base
    - save_to_kb: (Optional) If true, generates embeddings and saves to Neon KB

    Returns:
    - extracted_text: The extracted text content
    - chunks: Text split into embedding-safe chunks
    - kb_saved: Whether content was saved to knowledge base (if save_to_kb=true)
    """
    import asyncpg
    
    file_url = request.file_url
    file_name = request.file_name
    user_id = request.user_id
    agent_id = request.agent_id
    save_to_kb = request.save_to_kb
    
    # Log all received parameters for debugging
    logger.info(f"Extract-text received: file_name={file_name}, user_id={user_id}, agent_id={agent_id}, save_to_kb={save_to_kb} (type: {type(save_to_kb).__name__})")
    
    try:
        logger.info(f"Extract-text request: {file_name} from {file_url[:80]}...")

        processor = get_background_processor()
        if not processor:
            raise HTTPException(status_code=500, detail="Background processor not initialized")

        # Download file
        file_bytes = await processor.download_file(file_url)

        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty file downloaded")

        # Extract text
        extracted_text = await processor.extract_text(file_bytes, file_name)

        if not extracted_text or not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text content found in file")

        logger.info(f"Extracted {len(extracted_text)} chars from {file_name}")

        # Chunk the text for embedding-safe sizes
        chunks = processor.chunk_text(extracted_text, chunk_size=4000, chunk_overlap=400)

        logger.info(f"Split into {len(chunks)} chunks for {file_name}")

        # If save_to_kb is true and we have user_id + agent_id, use shared function to save to KB
        kb_saved = False
        
        if save_to_kb and user_id and agent_id:
            logger.info(f"Attempting to save to KB: user_id={user_id}, agent_id={agent_id}, file_name={file_name}")
            kb_saved = await save_content_to_knowledge_base(
                user_id=user_id,
                agent_id=agent_id,
                content=extracted_text,
                source='chat_file_upload',
                file_name=file_name,
                file_url=file_url
            )
            logger.info(f"KB save result: {kb_saved}")

        return {
            "success": True,
            "file_name": file_name,
            "extracted_text": extracted_text,
            "char_count": len(extracted_text),
            "kb_saved": kb_saved,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text extraction failed for {file_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@app.get("/api/file/status/{file_id}")
async def get_file_processing_status(file_id: str):
    """Get processing status for a file"""
    try:
        result = await file_processing_service.get_processing_record(file_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail="File not found")
        
        data = result["data"]
        
        return {
            "success": True,
            "data": {
                "file_id": data["file_id"],
                "file_name": data["file_name"],
                "agent_id": data["agent_id"],
                "agent_name": data["agent_name"],
                "status": data["processing_status"],
                "extracted_text": data.get("extracted_text"),
                "error_message": data.get("error_message"),
                "created_at": data["created_at"],
                "updated_at": data["updated_at"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/user/{firm_user_id}")
async def get_user_files(firm_user_id: str, agent_id: Optional[str] = None):
    """Get all processed files for a user"""
    try:
        result = await file_processing_service.get_user_files(firm_user_id, agent_id)
        
        return {
            "success": True,
            "data": result["data"],
            "count": result["count"]
        }
        
    except Exception as e:
        logger.error(f"Error getting user files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# END FILE PROCESSING
# ============================================================================

# ============================================================================
# KNOWLEDGE BASE ENDPOINTS
# ============================================================================

@app.post("/api/knowledge-base/text")
async def save_text_knowledge(
    firm_user_id: str = Form(...),
    agent_id: str = Form(...),
    agent_name: str = Form(...),
    text_content: str = Form(...)
):
    """
    Save text content (voice/manual input) to knowledge base
    
    Parameters:
    - firm_user_id: User ID
    - agent_id: Agent ID from YAML config
    - agent_name: Agent name from YAML config
    - text_content: User's text input (voice or manual)
    
    Returns:
    - Success response with record ID
    """
    try:
        logger.info(f"Saving text knowledge for user {firm_user_id}, agent {agent_id}")
        
        # Validate required fields
        if not all([firm_user_id, agent_id, agent_name, text_content.strip()]):
            raise HTTPException(status_code=400, detail="All fields are required and text cannot be empty")
        
        # Generate unique file_id for text entry
        file_id = f"text_{uuid.uuid4().hex[:12]}"
        
        # Insert into firm_users_knowledge_base table
        result = supabase.table("firm_users_knowledge_base").insert({
            "firm_user_id": firm_user_id,
            "file_id": file_id,
            "file_name": "User Input",
            "file_url": "",  # Empty for text input
            "agent_id": agent_id,
            "agent_name": agent_name,
            "extracted_text": text_content.strip(),
            "processing_status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to save text knowledge")
        
        logger.info(f"Text knowledge saved successfully: {file_id}")
        
        return {
            "success": True,
            "message": "Text knowledge saved successfully",
            "file_id": file_id,
            "processing_status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving text knowledge: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge-base/file")
async def save_file_knowledge(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    agent_id: str = Form(...),
    agent_name: str = Form(...)
):
    """
    Upload file to Supabase storage and save metadata to Neon database.
    Background task extracts text and updates the record.
    
    Parameters:
    - file: The uploaded file
    - user_id: User ID
    - agent_id: Agent ID from YAML config
    - agent_name: Agent name from YAML config
    
    Returns:
    - Immediate response with file_id for tracking
    """
    import asyncpg
    
    # Neon database configuration
    NEON_DB_HOST = os.getenv('NEON_DB_HOST')
    NEON_DB_PORT = os.getenv('NEON_DB_PORT', '5432')
    NEON_DB_USER = os.getenv('NEON_DB_USER')
    NEON_DB_PASSWORD = os.getenv('NEON_DB_PASSWORD')
    NEON_DB_NAME = os.getenv('NEON_DB_NAME', 'neondb')
    
    conn = None
    try:
        file_name = file.filename or f"file_{uuid.uuid4().hex[:8]}"
        logger.info(f"Uploading file for user {user_id}: {file_name}")
        
        # Validate required fields
        if not all([user_id, agent_id, agent_name]):
            raise HTTPException(status_code=400, detail="All fields are required")
        
        # Read file content
        file_content = await file.read()
        
        # Generate unique storage path
        unique_id = uuid.uuid4().hex[:12]
        storage_path = f"knowledge-base/{user_id}/{agent_id}/{unique_id}_{file_name}"
        
        # Upload to Supabase storage (agentkbs bucket)
        try:
            response = supabase.storage.from_('agentkbs').upload(
                storage_path,
                file_content,
                {
                    "content-type": file.content_type or "application/octet-stream",
                    "upsert": "false"
                }
            )
            
            # Check for upload errors
            if hasattr(response, 'error') and response.error:
                raise HTTPException(status_code=500, detail=f"Storage upload failed: {response.error}")
                
        except Exception as upload_error:
            if "already exists" not in str(upload_error):
                logger.error(f"Supabase upload error: {str(upload_error)}")
                raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(upload_error)}")
        
        # Get public URL
        file_url = supabase.storage.from_('agentkbs').get_public_url(storage_path)
        
        # Save metadata to Neon database (user_vector_knowledge_base table)
        if not all([NEON_DB_HOST, NEON_DB_USER, NEON_DB_PASSWORD]):
            raise HTTPException(status_code=500, detail="Neon database configuration missing")
        
        conn = await asyncpg.connect(
            host=NEON_DB_HOST,
            port=int(NEON_DB_PORT),
            user=NEON_DB_USER,
            password=NEON_DB_PASSWORD,
            database=NEON_DB_NAME,
            ssl='require'
        )
        
        query = """
            INSERT INTO user_vector_knowledge_base
            (user_id, agent_id, document, category, source, file_name, file_url, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """
        
        created_at = datetime.utcnow()
        
        result = await conn.fetchrow(
            query,
            user_id,
            agent_id,
            f"File uploaded: {file_name} (processing...)",  # Placeholder until extraction
            'documents',
            'file_upload',
            file_name,
            file_url,
            created_at,
            created_at
        )
        
        file_id = str(result['id'])
        logger.info(f"Created Neon knowledge base record: {file_id}")
        
        # Start background text extraction that will update the Neon record
        background_tasks.add_task(
            extract_and_update_neon_record,
            file_id,
            file_url,
            file_name,
            user_id,
            agent_id
        )
        
        # Initialize file status for SSE streaming
        update_file_status(file_id, "uploading", "File uploaded, starting processing...", 10)
        
        return {
            "success": True,
            "message": "File uploaded to knowledge base successfully",
            "file_id": file_id,
            "file_url": file_url,
            "processing_status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving file knowledge: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            await conn.close()


@app.get("/api/file/status-stream/{file_id}")
async def stream_file_status(file_id: str):
    """
    SSE endpoint to stream file processing status updates.
    Frontend subscribes to this after uploading a file.
    """
    async def event_generator():
        last_status = None
        timeout_counter = 0
        max_timeout = 300  # 5 minutes max
        
        while timeout_counter < max_timeout:
            with _file_status_lock:
                current_status = file_processing_status.get(file_id)
            
            if current_status and current_status != last_status:
                last_status = current_status
                yield f"data: {json.dumps(current_status)}\n\n"
                
                # If completed or failed, end the stream
                if current_status.get("status") in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(1)
            timeout_counter += 1
        
        # Send final timeout message if we hit the limit
        if timeout_counter >= max_timeout:
            yield f"data: {json.dumps({'status': 'timeout', 'message': 'Processing timeout', 'progress': 0})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# =============================================================================
# SHARED KB UTILITIES - Used by both file upload and website analysis
# =============================================================================

async def generate_embedding_for_kb(text: str) -> Optional[str]:
    """
    Generate embedding for text using OpenRouter API.
    Returns formatted string for PostgreSQL vector, or None if failed.
    
    Used by:
    - extract_and_update_neon_record (file uploads)
    - save_content_to_knowledge_base (website analysis)
    """
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set, skipping embedding generation")
        return None
    
    try:
        logger.info(f"Generating embedding for text ({len(text)} chars)...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://openrouter.ai/api/v1/embeddings',
                headers={
                    'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'openai/text-embedding-3-small',
                    'input': text[:8000]  # Limit input size
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                embedding = result.get('data', [{}])[0].get('embedding', [])
                if embedding and len(embedding) > 0:
                    # Format as PostgreSQL vector string: [0.1, 0.2, ...]
                    vector_str = '[' + ','.join(str(x) for x in embedding) + ']'
                    logger.info(f"Generated embedding with {len(embedding)} dimensions")
                    return vector_str
                else:
                    logger.error(f"OpenRouter returned empty embedding")
                    return None
            else:
                logger.error(f"OpenRouter embedding failed ({response.status_code}): {response.text}")
                return None
    except Exception as e:
        logger.error(f"Embedding generation error: {str(e)}")
        return None


async def save_content_to_knowledge_base(
    user_id: str,
    agent_id: str,
    content: str,
    source: str,
    file_name: str,
    file_url: str,
    chunk_size: int = 4000,
    chunk_overlap: int = 400
) -> bool:
    """
    Save content to user_vector_knowledge_base with chunking and embeddings.
    
    Used by:
    - Website analysis endpoint
    - Can be reused for other content types
    
    Args:
        user_id: User ID (firm_user_id)
        agent_id: Agent ID
        content: Text content to save
        source: Source identifier (e.g., 'website_analysis', 'file_upload')
        file_name: Display name for the content
        file_url: URL or identifier for the content
        chunk_size: Size of each chunk (default 4000)
        chunk_overlap: Overlap between chunks (default 400)
    
    Returns:
        True if saved successfully, False otherwise
    """
    import asyncpg
    
    NEON_DB_HOST = os.getenv('NEON_DB_HOST')
    NEON_DB_PORT = os.getenv('NEON_DB_PORT', '5432')
    NEON_DB_USER = os.getenv('NEON_DB_USER')
    NEON_DB_PASSWORD = os.getenv('NEON_DB_PASSWORD')
    NEON_DB_NAME = os.getenv('NEON_DB_NAME', 'neondb')
    
    if not all([NEON_DB_HOST, NEON_DB_USER, NEON_DB_PASSWORD]):
        logger.warning("Neon DB config missing - cannot save to KB")
        return False
    
    conn = None
    try:
        # Chunk the content using same logic as file upload
        processor = get_background_processor()
        if processor:
            chunks = processor.chunk_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        else:
            # Fallback: simple chunking if processor not available
            chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size - chunk_overlap)]
            if not chunks:
                chunks = [content]
        
        logger.info(f"Chunked content into {len(chunks)} chunks for KB save")
        
        conn = await asyncpg.connect(
            host=NEON_DB_HOST,
            port=int(NEON_DB_PORT),
            user=NEON_DB_USER,
            password=NEON_DB_PASSWORD,
            database=NEON_DB_NAME,
            ssl='require'
        )
        
        total_chunks = len(chunks)
        created_at = datetime.utcnow()
        
        for i, chunk in enumerate(chunks, start=1):
            if not chunk.strip():
                continue
            
            # Format document like file upload: "Source: {name} [Part X/Y]\n\n{chunk}"
            formatted_doc = f"{file_name} [Part {i}/{total_chunks}]\n\n{chunk}"
            
            # Generate embedding
            embedding = await generate_embedding_for_kb(chunk)
            
            if embedding:
                insert_query = """
                    INSERT INTO user_vector_knowledge_base
                    (user_id, agent_id, document, embedding, category, source, file_name, file_url, created_at, updated_at)
                    VALUES ($1, $2, $3, $4::vector, $5, $6, $7, $8, $9, $10)
                """
                await conn.execute(
                    insert_query,
                    user_id,
                    agent_id,
                    formatted_doc,
                    embedding,
                    'documents',
                    source,
                    file_name,
                    file_url,
                    created_at,
                    created_at
                )
            else:
                insert_query = """
                    INSERT INTO user_vector_knowledge_base
                    (user_id, agent_id, document, category, source, file_name, file_url, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """
                await conn.execute(
                    insert_query,
                    user_id,
                    agent_id,
                    formatted_doc,
                    'documents',
                    source,
                    file_name,
                    file_url,
                    created_at,
                    created_at
                )
            
            logger.info(f"Saved chunk {i}/{total_chunks} to KB for {file_name}")
        
        logger.info(f"✓ Successfully saved {total_chunks} chunks to KB for user {user_id}, agent {agent_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save content to KB: {str(e)}")
        return False
    finally:
        if conn:
            await conn.close()


async def extract_and_update_neon_record(
    file_id: str,
    file_url: str,
    file_name: str,
    user_id: str,
    agent_id: str
):
    """
    Background task to:
    1. Extract text from file using /api/file/extract-text endpoint
    2. Generate embeddings using OpenRouter API
    3. Save text and embeddings to user_vector_knowledge_base in Neon
    """
    import asyncpg
    import httpx
    
    NEON_DB_HOST = os.getenv('NEON_DB_HOST')
    NEON_DB_PORT = os.getenv('NEON_DB_PORT', '5432')
    NEON_DB_USER = os.getenv('NEON_DB_USER')
    NEON_DB_PASSWORD = os.getenv('NEON_DB_PASSWORD')
    NEON_DB_NAME = os.getenv('NEON_DB_NAME', 'neondb')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    
    conn = None
    try:
        logger.info(f"Starting text extraction for file {file_id}: {file_name}")
        update_file_status(file_id, "extracting", "Extracting text from file...", 20)
        
        extracted_text = ""
        chunks = []
        
        # Step 1: Extract text directly using BackgroundTextProcessor (avoid localhost HTTP call)
        processor = get_background_processor()
        if not processor:
            raise Exception("Background processor not initialized")
        
        # Download file
        file_bytes = await processor.download_file(file_url)
        if not file_bytes:
            raise Exception("Empty file downloaded")
        
        # Extract text
        extracted_text = await processor.extract_text(file_bytes, file_name)
        
        if not extracted_text or not extracted_text.strip():
            raise Exception("No text content found in file")
        
        # Chunk the text
        chunks = processor.chunk_text(extracted_text, chunk_size=4000, chunk_overlap=400)
        logger.info(f"Extracted {len(extracted_text)} chars, {len(chunks)} chunks from {file_name}")
        update_file_status(file_id, "extracted", f"Extracted {len(chunks)} chunks from file", 40)
        
        # Step 2: Connect to Neon database (using shared generate_embedding_for_kb function)
        conn = await asyncpg.connect(
            host=NEON_DB_HOST,
            port=int(NEON_DB_PORT),
            user=NEON_DB_USER,
            password=NEON_DB_PASSWORD,
            database=NEON_DB_NAME,
            ssl='require'
        )
        
        # Step 4: Update original record with first chunk and embedding
        total_chunks = len(chunks)
        if chunks:
            update_file_status(file_id, "embedding", f"Generating embeddings for {total_chunks} chunks...", 50)
            
            # Format document like n8n: "File: {fileName} [Part X/Y]\n\n{chunk}"
            first_chunk_text = chunks[0] if chunks[0].strip() else ""
            formatted_doc = f"File: {file_name} [Part 1/{total_chunks}]\n\n{first_chunk_text}"
            
            embedding = await generate_embedding_for_kb(first_chunk_text)
            
            if embedding:
                # Update with text and embedding
                update_query = """
                    UPDATE user_vector_knowledge_base
                    SET document = $1, embedding = $2::vector, updated_at = $3
                    WHERE id = $4::uuid
                """
                await conn.execute(
                    update_query,
                    formatted_doc,
                    embedding,
                    datetime.utcnow(),
                    file_id
                )
                logger.info(f"Updated record {file_id} with embedding")
            else:
                # Update with text only (no embedding)
                update_query = """
                    UPDATE user_vector_knowledge_base
                    SET document = $1, updated_at = $2
                    WHERE id = $3::uuid
                """
                await conn.execute(
                    update_query,
                    formatted_doc,
                    datetime.utcnow(),
                    file_id
                )
                logger.warning(f"Updated record {file_id} WITHOUT embedding (generation failed)")
            
            logger.info(f"Updated original record {file_id} with chunk 1/{total_chunks}")
            
            # Step 5: Insert additional chunks as new records
            if len(chunks) > 1:
                for i, chunk in enumerate(chunks[1:], start=2):
                    if not chunk.strip():
                        continue
                    
                    # Format document like n8n
                    formatted_chunk = f"File: {file_name} [Part {i}/{total_chunks}]\n\n{chunk}"
                    chunk_embedding = await generate_embedding_for_kb(chunk)
                    
                    if chunk_embedding:
                        insert_query = """
                            INSERT INTO user_vector_knowledge_base
                            (user_id, agent_id, document, embedding, category, source, file_name, file_url, created_at, updated_at)
                            VALUES ($1, $2, $3, $4::vector, $5, $6, $7, $8, $9, $10)
                        """
                        await conn.execute(
                            insert_query,
                            user_id,
                            agent_id,
                            formatted_chunk,
                            chunk_embedding,
                            'documents',
                            'file_upload',
                            file_name,
                            file_url,
                            datetime.utcnow(),
                            datetime.utcnow()
                        )
                    else:
                        insert_query = """
                            INSERT INTO user_vector_knowledge_base
                            (user_id, agent_id, document, category, source, file_name, file_url, created_at, updated_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """
                        await conn.execute(
                            insert_query,
                            user_id,
                            agent_id,
                            formatted_chunk,
                            'documents',
                            'file_upload',
                            file_name,
                            file_url,
                            datetime.utcnow(),
                            datetime.utcnow()
                        )
                    
                    logger.info(f"Inserted chunk {i}/{total_chunks} for file {file_id}")
                    # Update progress for each chunk
                    progress = 50 + int((i / total_chunks) * 40)
                    update_file_status(file_id, "saving", f"Saving chunk {i}/{total_chunks}...", progress)
        
        logger.info(f"Successfully processed file {file_id}: {len(chunks)} chunks with embeddings")
        update_file_status(file_id, "completed", f"Successfully processed {total_chunks} chunks", 100)
        
    except Exception as e:
        logger.error(f"Background extraction failed for {file_id}: {str(e)}")
        update_file_status(file_id, "failed", f"Processing failed: {str(e)}", 0)
        # Try to update record with error message
        try:
            if not conn:
                conn = await asyncpg.connect(
                    host=NEON_DB_HOST,
                    port=int(NEON_DB_PORT),
                    user=NEON_DB_USER,
                    password=NEON_DB_PASSWORD,
                    database=NEON_DB_NAME,
                    ssl='require'
                )
            await conn.execute(
                """UPDATE user_vector_knowledge_base SET document = $1, updated_at = $2 WHERE id = $3::uuid""",
                f"[Extraction failed: {str(e)}]",
                datetime.utcnow(),
                file_id
            )
        except:
            pass
    finally:
        if conn:
            await conn.close()

@app.get("/api/knowledge-base/{agent_id}")
async def get_agent_knowledge(agent_id: str, firm_user_id: Optional[str] = None):
    """Get all knowledge base entries for an agent"""
    try:
        query = supabase.table("firm_users_knowledge_base").select("*").eq("agent_id", agent_id)
        
        if firm_user_id:
            query = query.eq("firm_user_id", firm_user_id)
        
        result = query.order("created_at", desc=True).execute()
        
        return {
            "success": True,
            "data": result.data,
            "count": len(result.data)
        }
        
    except Exception as e:
        logger.error(f"Error getting agent knowledge: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# END KNOWLEDGE BASE ENDPOINTS
# ============================================================================

# ============================================================================
# WEB SCRAPING ENDPOINTS
# ============================================================================

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel
import httpx
import time
import logging

class WebScraper:
    def __init__(self, max_depth=1, delay=0, max_pages=10):
        self.max_depth = max_depth
        self.delay = delay
        self.max_pages = max_pages
        self.visited = set()
        self.session = httpx.Client(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
            timeout=10.0
        )
    
    def is_valid_url(self, url, base_domain):
        """Check if URL is valid and belongs to the same domain"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_parsed = urlparse(base_domain)
            return (parsed.netloc == base_parsed.netloc and 
                    parsed.scheme in ['http', 'https'])
        except:
            return False
    
    def extract_text_content(self, soup):
        """Extract meaningful text content from HTML"""
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        text_parts = []
        
        title = soup.find('title')
        if title:
            text_parts.append(f"TITLE: {title.get_text().strip()}")
        
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        if main_content:
            headings = main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            for heading in headings:
                text_parts.append(f"\n{heading.name.upper()}: {heading.get_text().strip()}")
            
            paragraphs = main_content.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if text:
                    text_parts.append(text)
            
            lists = main_content.find_all(['ul', 'ol'])
            for lst in lists:
                items = lst.find_all('li')
                for item in items:
                    text = item.get_text().strip()
                    if text:
                        text_parts.append(f"• {text}")
        
        return '\n'.join(text_parts)
    
    def get_links(self, soup, base_url):
        """Extract all valid links from the page"""
        from urllib.parse import urljoin
        links = set()
        for link in soup.find_all('a', href=True):
            url = urljoin(base_url, link['href'])
            url = url.split('#')[0]
            if self.is_valid_url(url, base_url):
                links.add(url)
        return links
    
    def fetch_page(self, url, depth):
        """Fetch and parse a single page"""
        start_time = time.time()
        try:
            if self.delay > 0:
                time.sleep(self.delay)
            
            fetch_start = time.time()
            response = self.session.get(url)
            response.raise_for_status()
            fetch_time = time.time() - fetch_start
            
            parse_start = time.time()
            soup = BeautifulSoup(response.content, 'html.parser')
            text_content = self.extract_text_content(soup)
            links = self.get_links(soup, url) if depth < self.max_depth else set()
            parse_time = time.time() - parse_start
            
            total_time = time.time() - start_time
            logger.info(f"Fetched {url} | Depth: {depth} | Fetch: {fetch_time:.2f}s | Parse: {parse_time:.2f}s | Total: {total_time:.2f}s | Links: {len(links)}")
            
            return {
                'url': url,
                'depth': depth,
                'content': text_content,
                'status': response.status_code,
                'links': links
            }
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return {
                'url': url,
                'depth': depth,
                'content': '',
                'status': 'error',
                'error': str(e),
                'links': set()
            }
    
    def scrape(self, start_url):
        """Scrape website with concurrent requests up to max_depth"""
        scrape_start = time.time()
        logger.info(f"Starting scrape of {start_url} | Max depth: {self.max_depth} | Max pages: {self.max_pages}")
        
        results = {}
        to_scrape = [(start_url, 0)]
        self.visited.add(start_url)
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            while to_scrape and len(results) < self.max_pages:
                current_batch = to_scrape[:min(5, self.max_pages - len(results))]
                to_scrape = to_scrape[len(current_batch):]
                
                futures = {executor.submit(self.fetch_page, url, depth): (url, depth) 
                          for url, depth in current_batch}
                
                for future in as_completed(futures):
                    result = future.result()
                    url = result['url']
                    depth = result['depth']
                    
                    results[url] = {
                        'depth': depth,
                        'content': result['content'],
                        'status': result['status']
                    }
                    if result.get('error'):
                        results[url]['error'] = result['error']
                    
                    if depth < self.max_depth and len(results) < self.max_pages:
                        for link in result.get('links', []):
                            if link not in self.visited and len(self.visited) < self.max_pages:
                                self.visited.add(link)
                                to_scrape.append((link, depth + 1))
        
        total_time = time.time() - scrape_start
        logger.info(f"Scrape complete | Pages: {len(results)} | Total time: {total_time:.2f}s | Avg per page: {total_time/max(len(results), 1):.2f}s")
        return results

def format_scrape_as_text(results):
    """Format scraping results as plain text for AI analysis"""
    output = []
    output.append("=" * 80)
    output.append("WEBSITE SCRAPING RESULTS")
    output.append("=" * 80)
    output.append(f"\nTotal pages scraped: {len(results)}\n")
    
    for url, data in results.items():
        output.append("\n" + "=" * 80)
        output.append(f"URL: {url}")
        output.append(f"Depth Level: {data['depth']}")
        output.append(f"Status: {data['status']}")
        output.append("-" * 80)
        
        if data.get('error'):
            output.append(f"ERROR: {data['error']}")
        elif data['content']:
            output.append(data['content'])
        else:
            output.append("(No content extracted)")
        
        output.append("")
    
    output.append("\n" + "=" * 80)
    output.append("END OF SCRAPING RESULTS")
    output.append("=" * 80)
    
    return '\n'.join(output)

class WebScrapeRequest(BaseModel):
    url: str
    max_depth: Optional[int] = 1
    max_pages: Optional[int] = 10
    format: Optional[str] = "text"

@app.post("/api/scrape")
async def scrape_website_endpoint(request: WebScrapeRequest):
    """
    Scrape a website and extract text content
    
    Parameters:
    - url: The URL to scrape (required)
    - max_depth: Maximum depth to crawl (default: 1)
    - max_pages: Maximum pages to scrape (default: 10)
    - format: Output format - "json" or "text" (default: "text")
    """
    request_start = time.time()
    
    url = request.url
    max_depth = request.max_depth
    max_pages = request.max_pages
    output_format = request.format
    
    logger.info(f"Scrape request received | URL: {url} | Depth: {max_depth} | Max pages: {max_pages} | Format: {output_format}")
    
    if not url.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
    
    try:
        scraper = WebScraper(max_depth=max_depth, max_pages=max_pages)
        results = scraper.scrape(url)
        
        request_time = time.time() - request_start
        logger.info(f"Request complete | Total time: {request_time:.2f}s | Pages: {len(results)}")
        
        if output_format == 'text':
            text_output = format_scrape_as_text(results)
            return {
                "success": True,
                "pages_scraped": len(results),
                "content": text_output,
                "format": "text"
            }
        else:
            return {
                "success": True,
                "pages_scraped": len(results),
                "results": results,
                "format": "json"
            }
    
    except Exception as e:
        logger.error(f"Scrape failed | Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# END WEB SCRAPING ENDPOINTS
# ============================================================================

# ============================================================================
# SUPABASE QUERY ENDPOINT
# ============================================================================

@app.post("/api/supabase/query")
async def supabase_query(request: Request):
    """
    Generic Supabase query endpoint

    Request body:
    {
        "table": "table_name",
        "filters": [
            {
                "column": "column_name",
                "operator": "eq" | "neq" | "gt" | "gte" | "lt" | "lte" | "like" | "ilike" | "in",
                "value": "value"
            }
        ],
        "select": "*" (optional),
        "limit": 100 (optional),
        "order": {"column": "created_at", "ascending": false} (optional)
    }
    """
    try:
        body = await request.json()
        table_name = body.get('table')
        filters = body.get('filters', [])
        select_fields = body.get('select', '*')
        limit = body.get('limit')
        order = body.get('order')

        if not table_name:
            raise HTTPException(status_code=400, detail="table is required")

        # Build query
        query = supabase.table(table_name).select(select_fields)

        # Apply filters
        for filter_item in filters:
            column = filter_item.get('column')
            operator = filter_item.get('operator', 'eq')
            value = filter_item.get('value')

            if not column:
                continue

            if operator == 'eq':
                query = query.eq(column, value)
            elif operator == 'neq':
                query = query.neq(column, value)
            elif operator == 'gt':
                query = query.gt(column, value)
            elif operator == 'gte':
                query = query.gte(column, value)
            elif operator == 'lt':
                query = query.lt(column, value)
            elif operator == 'lte':
                query = query.lte(column, value)
            elif operator == 'like':
                query = query.like(column, value)
            elif operator == 'ilike':
                query = query.ilike(column, value)
            elif operator == 'in':
                query = query.in_(column, value)

        # Apply order
        if order:
            order_column = order.get('column', 'created_at')
            ascending = order.get('ascending', False)
            query = query.order(order_column, desc=not ascending)

        # Apply limit
        if limit:
            query = query.limit(limit)

        # Execute query
        result = query.execute()

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Supabase query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SOCIAL MEDIA OAUTH ENDPOINTS
# Note: Facebook/Instagram OAuth endpoints are handled by routers:
# - GHL_Marketing/social_facebook.py - /api/social/facebook/*
# - GHL_Marketing/social_instagram.py - /api/social/instagram/*
# These routers are mounted below in the "Social Media Routes" section
# ============================================================================

# ============================================================================
# GHL MEDIA ROUTES
# ============================================================================
try:
    from routes.ghl_media import router as ghl_media_router
    app.include_router(ghl_media_router)
    logger.info("GHL Media routes loaded successfully")
except ImportError as e:
    logger.warning(f"GHL Media routes not available: {e}")
except Exception as e:
    logger.error(f"Error loading GHL Media routes: {e}")

# ============================================================================
# KNOWLEDGE BASE ROUTES
# ============================================================================
try:
    from routes.knowledge_base import router as knowledge_base_router
    app.include_router(knowledge_base_router)
    logger.info("Knowledge Base routes loaded successfully")
except ImportError as e:
    logger.warning(f"Knowledge Base routes not available: {e}")
except Exception as e:
    logger.error(f"Error loading Knowledge Base routes: {e}")

# ============================================================================
# SOCIAL MEDIA ROUTES - FACEBOOK
# ============================================================================
try:
    from GHL_Marketing.social_facebook import router as social_facebook_router
    app.include_router(social_facebook_router)
    logger.info("Social Media Facebook routes loaded successfully")
except ImportError as e:
    logger.warning(f"Social Media Facebook routes not available: {e}")
except Exception as e:
    logger.error(f"Error loading Social Media Facebook routes: {e}")

# ============================================================================
# SOCIAL MEDIA ROUTES - INSTAGRAM
# ============================================================================
try:
    from GHL_Marketing.social_instagram import router as social_instagram_router
    app.include_router(social_instagram_router)
    logger.info("Social Media Instagram routes loaded successfully")
except ImportError as e:
    logger.warning(f"Social Media Instagram routes not available: {e}")
except Exception as e:
    logger.error(f"Error loading Social Media Instagram routes: {e}")

# ============================================================================
# SOCIAL MEDIA ROUTES - SLACK
# ============================================================================
try:
    from GHL_Marketing.social_slack import router as social_slack_router
    app.include_router(social_slack_router)
    logger.info("Social Media Slack routes loaded successfully")
except ImportError as e:
    logger.warning(f"Social Media Slack routes not available: {e}")
except Exception as e:
    logger.error(f"Error loading Social Media Slack routes: {e}")

# ============================================================================
# SOCIAL MEDIA ROUTES - SCHEDULED POSTS
# ============================================================================
try:
    from GHL_Marketing.social_scheduled_posts import router as social_scheduled_posts_router
    app.include_router(social_scheduled_posts_router)
    logger.info("Social Media Scheduled Posts routes loaded successfully")
except ImportError as e:
    logger.warning(f"Social Media Scheduled Posts routes not available: {e}")
except Exception as e:
    logger.error(f"Error loading Social Media Scheduled Posts routes: {e}")

# ============================================================================
# MCP (Model Context Protocol) INTEGRATION
# ============================================================================

# Import MCP components
try:
    from mcp.server import MCPGateway
    
    # Initialize MCP Gateway
    mcp_gateway = MCPGateway(supabase)
    
    # Add MCP routes
    app.include_router(mcp_gateway.router, prefix="/api/v1/mcp", tags=["MCP"])
    
    # Initialize MCP system (will be called manually after app startup)
    async def initialize_mcp():
        """Initialize MCP system"""
        try:
            await mcp_gateway.initialize()
            logger.info("MCP system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MCP system: {e}")
    
    # Schedule MCP initialization
    async def setup_mcp():
        await initialize_mcp()
    
    logger.info("MCP integration loaded successfully")
    
except ImportError as e:
    logger.warning(f"MCP integration not available: {e}")
except Exception as e:
    logger.error(f"Error loading MCP integration: {e}")

# ============================================================================
# END MCP INTEGRATION
# ============================================================================

# ============================================================================
# TEMPLATED.IO ROUTES
# ============================================================================
try:
    from routes.templated_io import router as templated_router
    app.include_router(templated_router)
    logger.info("Templated.io routes loaded successfully")
except ImportError as e:
    logger.warning(f"Templated.io routes not available: {e}")
except Exception as e:
    logger.error(f"Error loading Templated.io routes: {e}")

# ============================================================================
# POSTHOG ANALYTICS ROUTES
# ============================================================================
try:
    from routes.analytics import router as analytics_router
    app.include_router(analytics_router)
    logger.info("PostHog Analytics routes loaded successfully")
except ImportError as e:
    logger.warning(f"PostHog Analytics routes not available: {e}")
except Exception as e:
    logger.error(f"Error loading PostHog Analytics routes: {e}")

# ============================================================================
# ADMIN ROUTES
# ============================================================================
try:
    from routes.admin import router as admin_router
    app.include_router(admin_router)
    logger.info("Admin routes loaded successfully")
except ImportError as e:
    logger.warning(f"Admin routes not available: {e}")
except Exception as e:
    logger.error(f"Error loading Admin routes: {e}")

# ============================================================================
# TWILIO SMS WEBHOOK
# ============================================================================

@app.post("/api/webhooks/twilio/sms")
async def receive_twilio_sms(request: Request):
    """
    Twilio SMS Webhook Endpoint
    Receives incoming SMS messages from Twilio and returns a TwiML response.
    Configure this URL in your Twilio phone number settings.
    """
    try:
        form_data = await request.form()
        from_number = form_data.get("From")
        to_number = form_data.get("To")
        body = form_data.get("Body")
        message_sid = form_data.get("MessageSid")
        
        logger.info(f"Received SMS from {from_number} to {to_number}: {body}")
        print(f"📱 New SMS from {from_number}: {body}")
        
        # Create TwiML response
        resp = TwilioMessagingResponse()
        resp.message("Message received 👍")
        
        return Response(content=str(resp), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error processing Twilio SMS webhook: {str(e)}")
        # Return empty TwiML response on error
        resp = TwilioMessagingResponse()
        return Response(content=str(resp), media_type="application/xml")

# ============================================================================
# END TWILIO SMS WEBHOOK
# ============================================================================

# ============================================================================
# AGENT ENABLEMENT NOTIFICATION ENDPOINT
# ============================================================================

class AgentEnablementNotification(BaseModel):
    user_id: str
    agent_id: str
    agent_name: Optional[str] = None
    action: str = "enabled"  # enabled, disabled, updated

@app.post("/api/agents/notify-enablement")
async def notify_agent_enablement(request: AgentEnablementNotification):
    """
    Endpoint for n8n to call after enabling an agent.
    Broadcasts via Supabase Realtime to force frontend sidebar refresh.
    """
    try:
        user_id = request.user_id
        agent_id = request.agent_id
        agent_name = request.agent_name or agent_id
        action = request.action
        
        logger.info(f"🔔 Agent enablement notification: user={user_id}, agent={agent_id}, action={action}")
        print(f"🔔 Agent enablement notification: user={user_id}, agent={agent_id}, action={action}")
        
        # Verify the agent was actually enabled in the database
        result = supabase.table('assistant_personalizations')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('assistant_id', agent_id)\
            .execute()
        
        if result.data:
            agent_record = result.data[0]
            is_enabled = agent_record.get('is_enabled', False)
            
            # Broadcast refresh signal via Supabase Realtime
            # Frontend listens to channel: agent-refresh-{user_id}
            try:
                import httpx
                supabase_url = os.getenv('SUPABASE_URL') or os.getenv('VITE_SUPABASE_URL')
                supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY') or os.getenv('VITE_SUPABASE_ANON_KEY')
                
                if supabase_url and supabase_key:
                    # Use Supabase Realtime broadcast via REST API
                    broadcast_url = f"{supabase_url}/realtime/v1/api/broadcast"
                    async with httpx.AsyncClient() as client:
                        broadcast_response = await client.post(
                            broadcast_url,
                            headers={
                                'apikey': supabase_key,
                                'Authorization': f'Bearer {supabase_key}',
                                'Content-Type': 'application/json'
                            },
                            json={
                                'messages': [{
                                    'topic': f'agent-refresh-{user_id}',
                                    'event': 'refresh_sidebar',
                                    'payload': {
                                        'user_id': user_id,
                                        'agent_id': agent_id,
                                        'action': action,
                                        'timestamp': datetime.now(timezone.utc).isoformat()
                                    }
                                }]
                            },
                            timeout=10.0
                        )
                        logger.info(f"📡 Broadcast sent: status={broadcast_response.status_code}")
            except Exception as broadcast_error:
                logger.warning(f"⚠️ Broadcast failed (non-critical): {broadcast_error}")
            
            return {
                "success": True,
                "message": f"Agent {agent_name} {action} successfully",
                "user_id": user_id,
                "agent_id": agent_id,
                "is_enabled": is_enabled,
                "notification_sent": True
            }
        else:
            return {
                "success": False,
                "message": f"Agent {agent_id} not found in database for user {user_id}",
                "user_id": user_id,
                "agent_id": agent_id,
                "notification_sent": False
            }
            
    except Exception as e:
        logger.error(f"❌ Error in agent enablement notification: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "notification_sent": False
        }

# ============================================================================
# END AGENT ENABLEMENT NOTIFICATION
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
