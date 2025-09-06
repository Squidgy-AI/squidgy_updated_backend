"""
Invitation handler that creates profiles before invitations
Ensures no foreign key constraint violations
"""

from typing import Dict, Optional
import logging
from supabase import Client
import json

logger = logging.getLogger(__name__)

class InvitationHandler:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    async def create_invitation(
        self, 
        sender_id: str, 
        recipient_email: str, 
        sender_company_id: str,
        group_id: Optional[str] = None,
        token: Optional[str] = None
    ) -> Dict:
        """
        Create an invitation with automatic profile creation
        This prevents foreign key constraint errors
        """
        try:
            logger.info(f"Creating invitation from {sender_id} to {recipient_email}")
            
            # Call the database function that handles profile creation
            result = self.supabase.rpc(
                'create_invitation_with_profile',
                {
                    'p_sender_id': sender_id,
                    'p_recipient_email': recipient_email.lower().strip(),
                    'p_sender_company_id': sender_company_id,
                    'p_group_id': group_id,
                    'p_token': token
                }
            ).execute()
            
            if result.data and isinstance(result.data, dict):
                return result.data
            elif result.data and isinstance(result.data, list) and len(result.data) > 0:
                return result.data[0]
            else:
                return {
                    'success': False,
                    'error': 'Unexpected response format',
                    'details': str(result)
                }
                
        except Exception as e:
            logger.error(f"Error creating invitation: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to create invitation',
                'details': str(e)
            }
    
    async def handle_invitation_request(
        self,
        sender_email: str,
        recipient_email: str,
        token: str,
        invite_url: str
    ) -> Dict:
        """
        Handle the complete invitation flow:
        1. Get sender details
        2. Create profile for recipient if needed
        3. Create invitation
        4. Send invitation email
        """
        try:
            # Get sender details
            sender_result = self.supabase.from_('profiles').select(
                'user_id, company_id, full_name'
            ).eq('email', sender_email.lower()).single().execute()
            
            if not sender_result.data:
                return {
                    'success': False,
                    'error': 'Sender not found',
                    'details': f'No profile found for {sender_email}'
                }
            
            sender = sender_result.data
            
            # Create invitation (which will also create profile if needed)
            invitation_result = await self.create_invitation(
                sender_id=sender['user_id'],
                recipient_email=recipient_email,
                sender_company_id=sender['company_id'],
                token=token
            )
            
            if not invitation_result.get('success'):
                return invitation_result
            
            # Send invitation email using Supabase Auth
            try:
                # Use admin.invite_user_by_email for proper email template
                self.supabase.auth.admin.invite_user_by_email(
                    recipient_email.lower(),
                    {
                        "redirect_to": invite_url,
                        "data": {
                            "invitation_token": token,
                            "sender_name": sender.get('full_name', sender_email)
                        }
                    }
                )
                
                return {
                    'success': True,
                    'message': 'Invitation created and email sent successfully',
                    'invitation_id': invitation_result.get('invitation_id'),
                    'recipient_id': invitation_result.get('recipient_id'),
                    'token': token
                }
                
            except Exception as email_error:
                logger.error(f"Failed to send invitation email: {str(email_error)}")
                # Invitation created but email failed
                return {
                    'success': True,
                    'message': 'Invitation created but email sending failed',
                    'invitation_id': invitation_result.get('invitation_id'),
                    'recipient_id': invitation_result.get('recipient_id'),
                    'token': token,
                    'email_error': str(email_error),
                    'fallback_url': invite_url
                }
                
        except Exception as e:
            logger.error(f"Error in invitation flow: {str(e)}")
            return {
                'success': False,
                'error': 'Invitation flow failed',
                'details': str(e)
            }

# Integration with FastAPI endpoint
async def create_invitation_endpoint(
    request: Dict,
    supabase_client: Client
) -> Dict:
    """
    FastAPI endpoint handler for creating invitations
    """
    handler = InvitationHandler(supabase_client)
    
    # Extract required fields
    sender_email = request.get('sender_email')
    recipient_email = request.get('recipient_email')
    token = request.get('token')
    invite_url = request.get('invite_url')
    
    # Validate inputs
    if not all([sender_email, recipient_email, token, invite_url]):
        return {
            'success': False,
            'error': 'Missing required fields',
            'required': ['sender_email', 'recipient_email', 'token', 'invite_url']
        }
    
    # Process invitation
    return await handler.handle_invitation_request(
        sender_email=sender_email,
        recipient_email=recipient_email,
        token=token,
        invite_url=invite_url
    )