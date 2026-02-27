"""
Simple File Processing Service
Handles file processing records with background text extraction
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from supabase import Client

logger = logging.getLogger(__name__)

class FileProcessingService:
    """Service class for file_processing database operations"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    def generate_file_id(self) -> str:
        """Generate unique file ID"""
        return f"file_{uuid.uuid4().hex[:12]}"
    
    def extract_storage_path_from_url(self, file_url: str) -> Optional[str]:
        """
        Extract storage path from Supabase public URL
        
        Example URL: https://[project].supabase.co/storage/v1/object/public/newsletter/user123_1234567890_document.pdf
        Returns: user123_1234567890_document.pdf
        """
        try:
            if not file_url or file_url == "":
                return None
            
            # Split by '/newsletter/' to get the path after bucket name
            if '/newsletter/' in file_url:
                return file_url.split('/newsletter/')[-1]
            
            return None
        except Exception as e:
            logger.error(f"Error extracting storage path from URL: {str(e)}")
            return None
    
    async def delete_old_storage_file(self, file_url: str) -> bool:
        """
        Delete old file from Supabase storage
        
        Args:
            file_url: Supabase storage public URL
            
        Returns:
            True if deleted successfully or file doesn't exist, False on error
        """
        try:
            if not file_url or file_url == "":
                return True  # No file to delete
            
            storage_path = self.extract_storage_path_from_url(file_url)
            if not storage_path:
                logger.warning(f"Could not extract storage path from URL: {file_url}")
                return True  # Don't fail the operation
            
            # Delete from Supabase storage
            response = self.supabase.storage.from_('newsletter').remove([storage_path])
            
            logger.info(f"Deleted old storage file: {storage_path}")
            return True
            
        except Exception as e:
            # Log error but don't fail the operation - orphaned files are not critical
            logger.warning(f"Failed to delete old storage file (non-critical): {str(e)}")
            return True
    
    async def create_processing_record(
        self,
        firm_user_id: str,
        file_name: str,
        file_url: str,
        agent_id: str,
        agent_name: str
    ) -> Dict[str, Any]:
        """
        Create or update a file processing record using upsert logic.
        
        If a file with the same firm_user_id and file_name exists, it will be updated
        and the old storage file will be deleted to prevent orphans.
        This matches the database constraint: UNIQUE (firm_user_id, file_name)
        
        Args:
            firm_user_id: User ID from frontend
            file_name: Original filename
            file_url: Supabase storage URL
            agent_id: Agent ID from YAML config
            agent_name: Agent name from YAML config
            
        Returns:
            Dictionary with record data or error information
        """
        try:
            # Check if record already exists for this user and filename
            existing_response = self.supabase.table("firm_users_knowledge_base").select("file_url").eq(
                "firm_user_id", firm_user_id
            ).eq("file_name", file_name).execute()
            
            # If record exists and has a file_url, delete the old storage file
            if existing_response.data and len(existing_response.data) > 0:
                old_file_url = existing_response.data[0].get("file_url")
                if old_file_url and old_file_url != file_url:
                    logger.info(f"Deleting old storage file for {file_name} before update")
                    await self.delete_old_storage_file(old_file_url)
            
            file_id = self.generate_file_id()
            
            record_data = {
                "firm_user_id": firm_user_id,
                "file_id": file_id,
                "file_name": file_name,
                "file_url": file_url,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "processing_status": "pending",
                "extracted_text": None,
                "error_message": None
            }
            
            # Use upsert to handle ON CONFLICT (firm_user_id, file_name)
            # This will update existing records or insert new ones
            response = self.supabase.table("firm_users_knowledge_base").upsert(
                record_data,
                on_conflict="firm_user_id,file_name"
            ).execute()
            
            if response.data:
                returned_file_id = response.data[0].get("file_id", file_id)
                logger.info(f"Upserted file processing record: {returned_file_id} (firm_user_id: {firm_user_id}, file_name: {file_name})")
                return {
                    "success": True,
                    "data": response.data[0],
                    "file_id": returned_file_id,
                    "message": "File processing record created/updated"
                }
            else:
                logger.error("Failed to upsert file processing record: No data returned")
                return {
                    "success": False,
                    "error": "Failed to create/update record - no data returned",
                    "data": None
                }
                
        except Exception as e:
            logger.error(f"Error upserting file processing record: {str(e)}")
            return {
                "success": False,
                "error": f"Database error: {str(e)}",
                "data": None
            }
    
    async def update_processing_status(
        self,
        file_id: str,
        status: str,
        extracted_text: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update processing status and results
        
        Args:
            file_id: Unique file identifier
            status: New status (pending, processing, completed, failed)
            extracted_text: Extracted text content (optional)
            error_message: Error message if failed (optional)
            
        Returns:
            Dictionary with success status
        """
        try:
            update_data = {
                "processing_status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if extracted_text is not None:
                update_data["extracted_text"] = extracted_text
            
            if error_message is not None:
                update_data["error_message"] = error_message
            
            response = self.supabase.table("firm_users_knowledge_base").update(update_data).eq("file_id", file_id).execute()
            
            if response.data:
                logger.info(f"Updated processing status for {file_id}: {status}")
                return {"success": True, "message": "Status updated"}
            else:
                logger.error(f"Failed to update status for {file_id}")
                return {"success": False, "error": "Update failed"}
                
        except Exception as e:
            logger.error(f"Error updating processing status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_processing_record(self, file_id: str) -> Dict[str, Any]:
        """Get processing record by file_id"""
        try:
            response = self.supabase.table("firm_users_knowledge_base").select("*").eq("file_id", file_id).execute()
            
            if response.data and len(response.data) > 0:
                return {
                    "success": True,
                    "data": response.data[0]
                }
            else:
                return {
                    "success": False,
                    "error": "Record not found"
                }
                
        except Exception as e:
            logger.error(f"Error retrieving processing record: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_user_files(
        self, 
        firm_user_id: str, 
        agent_id: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get files for a user, optionally filtered by agent"""
        try:
            query = self.supabase.table("firm_users_knowledge_base").select("*").eq("firm_user_id", firm_user_id)
            
            if agent_id:
                query = query.eq("agent_id", agent_id)
            
            response = query.order("created_at", desc=True).limit(limit).execute()
            
            return {
                "success": True,
                "data": response.data,
                "count": len(response.data)
            }
                
        except Exception as e:
            logger.error(f"Error retrieving user files: {str(e)}")
            return {"success": False, "error": str(e), "data": []}