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
    
    async def create_processing_record(
        self,
        firm_user_id: str,
        file_name: str,
        file_url: str,
        agent_id: str,
        agent_name: str
    ) -> Dict[str, Any]:
        """
        Create a new file processing record
        
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
            file_id = self.generate_file_id()
            
            record_data = {
                "firm_user_id": firm_user_id,
                "file_id": file_id,
                "file_name": file_name,
                "file_url": file_url,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "processing_status": "pending"
            }
            
            response = self.supabase.table("firm_users_knowledge_base").insert(record_data).execute()
            
            if response.data:
                logger.info(f"Created file processing record: {file_id}")
                return {
                    "success": True,
                    "data": response.data[0],
                    "file_id": file_id,
                    "message": "File processing record created"
                }
            else:
                logger.error("Failed to create file processing record: No data returned")
                return {
                    "success": False,
                    "error": "Failed to create record - no data returned",
                    "data": None
                }
                
        except Exception as e:
            logger.error(f"Error creating file processing record: {str(e)}")
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