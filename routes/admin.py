# routes/admin.py - Admin API routes for user management

import os
import logging
import asyncpg
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Neon database configuration
NEON_DB_HOST = os.getenv('NEON_DB_HOST')
NEON_DB_PORT = os.getenv('NEON_DB_PORT', '5432')
NEON_DB_USER = os.getenv('NEON_DB_USER')
NEON_DB_PASSWORD = os.getenv('NEON_DB_PASSWORD')
NEON_DB_NAME = os.getenv('NEON_DB_NAME', 'neondb')

router = APIRouter(prefix="/admin", tags=["admin"])

# Initialize Supabase client with service role key for admin operations
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def get_admin_supabase() -> Client:
    """Get Supabase client with service role key for admin operations"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=500, detail="Supabase admin credentials not configured")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class DeleteUserRequest(BaseModel):
    user_id: str
    admin_user_id: str


@router.post("/delete-user")
async def delete_user(request: DeleteUserRequest):
    """
    Hard delete a user from the system:
    - Delete from auth.users (Supabase Auth)
    - Delete from profiles table
    - Delete from related tables (business_profiles, chat_history, etc.)
    - Delete user's storage files
    """
    try:
        supabase = get_admin_supabase()
        user_id = request.user_id
        admin_user_id = request.admin_user_id
        
        logger.info(f"Admin {admin_user_id} deleting user {user_id}")
        
        # First, get the user's profile to find their auth id and other related data
        profile_result = supabase.table('profiles').select('*').eq('user_id', user_id).execute()
        
        if not profile_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        profile = profile_result.data[0]
        auth_id = profile.get('id')  # The id in profiles matches auth.users.id
        firm_user_id = profile.get('user_id')
        company_id = profile.get('company_id')
        
        deleted_items = []
        errors = []
        
        # 1. Delete from chat_history
        try:
            supabase.table('chat_history').delete().eq('user_id', user_id).execute()
            deleted_items.append('chat_history')
        except Exception as e:
            errors.append(f"chat_history: {str(e)}")
        
        # 2. Delete from squidgy_agent_business_setup
        try:
            supabase.table('squidgy_agent_business_setup').delete().eq('firm_user_id', firm_user_id).execute()
            deleted_items.append('squidgy_agent_business_setup')
        except Exception as e:
            errors.append(f"squidgy_agent_business_setup: {str(e)}")
        
        # 3. Delete from business_profiles
        try:
            supabase.table('business_profiles').delete().eq('firm_user_id', firm_user_id).execute()
            deleted_items.append('business_profiles')
        except Exception as e:
            errors.append(f"business_profiles: {str(e)}")
        
        # 4. Delete from newsletters
        try:
            supabase.table('newsletters').delete().eq('user_id', user_id).execute()
            deleted_items.append('newsletters')
        except Exception as e:
            errors.append(f"newsletters: {str(e)}")
        
        # 5. Delete from content_repurposer
        try:
            supabase.table('content_repurposer').delete().eq('user_id', user_id).execute()
            deleted_items.append('content_repurposer')
        except Exception as e:
            errors.append(f"content_repurposer: {str(e)}")
        
        # 6. Delete from invitations (as sender or recipient)
        try:
            supabase.table('invitations').delete().eq('sender_id', user_id).execute()
            supabase.table('invitations').delete().eq('recipient_id', user_id).execute()
            deleted_items.append('invitations')
        except Exception as e:
            errors.append(f"invitations: {str(e)}")
        
        # 7. Delete from admin_audit_logs
        try:
            supabase.table('admin_audit_logs').delete().eq('target_user_id', user_id).execute()
            deleted_items.append('admin_audit_logs')
        except Exception as e:
            errors.append(f"admin_audit_logs: {str(e)}")
        
        # 8. Delete user's storage files
        try:
            # List and delete files in user's storage bucket folder
            storage_paths = [
                f"avatars/{user_id}",
                f"uploads/{user_id}",
                f"knowledge-base/{user_id}"
            ]
            for path in storage_paths:
                try:
                    files = supabase.storage.from_('user-files').list(path)
                    if files:
                        file_paths = [f"{path}/{f['name']}" for f in files]
                        if file_paths:
                            supabase.storage.from_('user-files').remove(file_paths)
                except:
                    pass  # Storage bucket might not exist
            deleted_items.append('storage')
        except Exception as e:
            errors.append(f"storage: {str(e)}")
        
        # 9. Delete from Neon database (user_vector_knowledge_base table)
        try:
            if all([NEON_DB_HOST, NEON_DB_USER, NEON_DB_PASSWORD]):
                conn = await asyncpg.connect(
                    host=NEON_DB_HOST,
                    port=int(NEON_DB_PORT),
                    user=NEON_DB_USER,
                    password=NEON_DB_PASSWORD,
                    database=NEON_DB_NAME,
                    ssl='require'
                )
                try:
                    # Delete all knowledge base entries for this user
                    await conn.execute(
                        "DELETE FROM user_vector_knowledge_base WHERE user_id = $1",
                        user_id
                    )
                    deleted_items.append('neon_knowledge_base')
                finally:
                    await conn.close()
            else:
                errors.append("neon: Database configuration missing")
        except Exception as e:
            errors.append(f"neon_knowledge_base: {str(e)}")
        
        # 10. Delete from profiles table
        try:
            supabase.table('profiles').delete().eq('user_id', user_id).execute()
            deleted_items.append('profiles')
        except Exception as e:
            errors.append(f"profiles: {str(e)}")
        
        # 11. Delete from auth.users (using admin API)
        if auth_id:
            try:
                supabase.auth.admin.delete_user(auth_id)
                deleted_items.append('auth.users')
            except Exception as e:
                errors.append(f"auth.users: {str(e)}")
        
        # Log the admin action
        try:
            supabase.table('admin_audit_logs').insert({
                'admin_user_id': admin_user_id,
                'action': 'hard_delete_user',
                'target_user_id': user_id,
                'details': {
                    'deleted_items': deleted_items,
                    'errors': errors,
                    'user_email': profile.get('email')
                }
            }).execute()
        except:
            pass  # Don't fail if audit log fails
        
        return {
            "success": True,
            "message": f"User {user_id} deleted successfully",
            "deleted_items": deleted_items,
            "errors": errors if errors else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
