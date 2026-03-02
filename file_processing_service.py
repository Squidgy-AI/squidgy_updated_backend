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
    
    def extract_storage_path_from_url(self, file_url: str) -> Optional[tuple[str, str]]:
        """
        Extract bucket name and storage path from Supabase public URL
        
        Example URL: https://[project].supabase.co/storage/v1/object/public/newsletter/user123_1234567890_document.pdf
        Returns: ('newsletter', 'user123_1234567890_document.pdf')
        """
        try:
            if not file_url or file_url == "":
                return None
            
            # Check for newsletter bucket
            if '/newsletter/' in file_url:
                return ('newsletter', file_url.split('/newsletter/')[-1])
            
            # Check for agentkbs bucket
            if '/agentkbs/' in file_url:
                return ('agentkbs', file_url.split('/agentkbs/')[-1])
            
            # Check for knowledge-base bucket (legacy)
            if '/knowledge-base/' in file_url:
                return ('knowledge-base', file_url.split('/knowledge-base/')[-1])
            
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
            
            result = self.extract_storage_path_from_url(file_url)
            if not result:
                logger.warning(f"Could not extract storage path from URL: {file_url}")
                return True  # Don't fail the operation
            
            bucket_name, storage_path = result
            
            # Delete from Supabase storage using the correct bucket
            response = self.supabase.storage.from_(bucket_name).remove([storage_path])
            
            logger.info(f"Deleted old storage file from {bucket_name}: {storage_path}")
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
        agent_name: str,
        source: str = "chat"
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
            source: Source of the file (e.g. chat, email)
            
        Returns:
            Dictionary with record data or error information
        """
        try:
            # Check if record already exists for this user and filename
            existing_response = self.supabase.table("firm_users_knowledge_base").select("*").eq(
                "firm_user_id", firm_user_id
            ).eq("file_name", file_name).execute()
            
            existing_record = None
            if existing_response.data and len(existing_response.data) > 0:
                existing_record = existing_response.data[0]
                old_file_url = existing_record.get("file_url")
                
                # Delete old storage file if it exists and is different
                if old_file_url and old_file_url != file_url:
                    logger.info(f"Deleting old storage file for {file_name} before update")
                    await self.delete_old_storage_file(old_file_url)
            
            # If record exists, update it; otherwise insert new record
            if existing_record:
                # UPDATE existing record - use the existing primary key 'id'
                record_id = str(existing_record.get("id"))
                old_neon_ids = existing_record.get("neon_record_ids", [])
                
                # Delete old Neon records if they exist
                if old_neon_ids and len(old_neon_ids) > 0:
                    await self.delete_neon_records(old_neon_ids, file_name, firm_user_id)
                
                update_data = {
                    "file_url": file_url,
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "neon_record_ids": [],  # Reset - will be populated after extraction
                    "source": source,
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                response = self.supabase.table("firm_users_knowledge_base").update(update_data).eq(
                    "firm_user_id", firm_user_id
                ).eq("file_name", file_name).execute()
                
                logger.info(f"Updated existing file record: {record_id} (firm_user_id: {firm_user_id}, file_name: {file_name})")
                
                if response.data:
                    return {
                        "success": True,
                        "data": response.data[0],
                        "id": record_id,
                        "message": "File processing record updated"
                    }
                else:
                    # Fetch the record after update if response data is empty
                    updated_response = self.supabase.table("firm_users_knowledge_base").select("*").eq(
                        "firm_user_id", firm_user_id
                    ).eq("file_name", file_name).execute()
                    if updated_response.data and len(updated_response.data) > 0:
                        return {
                            "success": True,
                            "data": updated_response.data[0],
                            "id": record_id,
                            "message": "File processing record updated"
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Failed to fetch updated record",
                            "data": None
                        }
            else:
                # INSERT new record - Supabase auto-generates 'id'
                record_data = {
                    "firm_user_id": firm_user_id,
                    "file_name": file_name,
                    "file_url": file_url,
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "neon_record_ids": [],  # Will be populated after extraction
                    "source": source
                }
                
                response = self.supabase.table("firm_users_knowledge_base").insert(record_data).execute()
                
                if response.data:
                    record_id = str(response.data[0].get("id"))
                    logger.info(f"Inserted new file record: {record_id} (firm_user_id: {firm_user_id}, file_name: {file_name})")
                    return {
                        "success": True,
                        "data": response.data[0],
                        "id": record_id,
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
            logger.error(f"Error upserting file processing record: {str(e)}")
            return {
                "success": False,
                "error": f"Database error: {str(e)}",
                "data": None
            }
    
    async def update_neon_record_ids(
        self,
        record_id: str,
        neon_record_ids: list
    ) -> Dict[str, Any]:
        """
        Update the neon_record_ids after text extraction and embedding
        
        Args:
            record_id: Primary key 'id' of the record
            neon_record_ids: List of Neon DB record IDs for this file's chunks
            
        Returns:
            Dictionary with success status
        """
        try:
            update_data = {
                "neon_record_ids": neon_record_ids,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table("firm_users_knowledge_base").update(update_data).eq("id", record_id).execute()
            
            if response.data:
                logger.info(f"Updated neon_record_ids for {record_id}: {len(neon_record_ids)} records")
                return {"success": True, "message": "Neon record IDs updated"}
            else:
                logger.error(f"Failed to update neon_record_ids for {record_id}")
                return {"success": False, "error": "Update failed"}
                
        except Exception as e:
            logger.error(f"Error updating neon_record_ids: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def delete_neon_records(self, neon_record_ids: list, file_name: str = None, firm_user_id: str = None) -> bool:
        """
        Delete Neon records by their IDs (called when replacing a file)
        
        Args:
            neon_record_ids: List of Neon DB record IDs to delete
            file_name: Optional file name for fallback deletion
            firm_user_id: Optional user ID for fallback deletion
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not neon_record_ids or len(neon_record_ids) == 0:
                return True
            
            # Import here to avoid circular imports
            import asyncpg
            import os
            
            NEON_DB_HOST = os.getenv("NEON_DB_HOST")
            NEON_DB_USER = os.getenv("NEON_DB_USER")
            NEON_DB_PASSWORD = os.getenv("NEON_DB_PASSWORD")
            NEON_DB_NAME = os.getenv("NEON_DB_NAME", "neondb")
            
            if not all([NEON_DB_HOST, NEON_DB_USER, NEON_DB_PASSWORD]):
                logger.warning("Neon DB credentials not configured, skipping record deletion")
                return True
            
            conn = await asyncpg.connect(
                host=NEON_DB_HOST,
                user=NEON_DB_USER,
                password=NEON_DB_PASSWORD,
                database=NEON_DB_NAME,
                ssl="require"
            )
            
            try:
                # Try to convert string IDs to integers (new format)
                try:
                    int_ids = [int(id) for id in neon_record_ids]
                    deleted = await conn.execute(
                        "DELETE FROM user_vector_knowledge_base WHERE id = ANY($1::int[])",
                        int_ids
                    )
                    logger.info(f"Deleted {len(int_ids)} Neon records by ID")
                except ValueError:
                    # IDs are UUIDs - can't delete by ID directly
                    # Fall back to deleting by file_name and user_id if provided
                    logger.warning(f"neon_record_ids are UUIDs, cannot delete by ID: {neon_record_ids[:3]}...")
                    
                    if file_name and firm_user_id:
                        query = """
                            DELETE FROM user_vector_knowledge_base 
                            WHERE file_name = $1 AND user_id = $2
                        """
                        deleted = await conn.execute(query, file_name, firm_user_id)
                        logger.info(f"Deleted Neon records by file_name '{file_name}' and user_id")
                    else:
                        logger.warning("Cannot delete UUID records without file_name and firm_user_id")
                
                return True
            finally:
                await conn.close()
                
        except Exception as e:
            logger.warning(f"Failed to delete Neon records (non-critical): {str(e)}")
            return True  # Don't fail the operation
    
    async def get_processing_record(self, record_id: str) -> Dict[str, Any]:
        """Get processing record by primary key 'id'"""
        try:
            logger.debug(f"Looking up record id: {record_id}")
            response = self.supabase.table("firm_users_knowledge_base").select("*").eq("id", record_id).execute()
            
            if response.data and len(response.data) > 0:
                logger.debug(f"Found record for {record_id}")
                return {
                    "success": True,
                    "data": response.data[0]
                }
            else:
                logger.warning(f"Record not found for id: {record_id}")
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
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get files for a user, optionally filtered by agent"""
        try:
            query = self.supabase.table("firm_users_knowledge_base").select("*").eq("firm_user_id", firm_user_id)
            
            if agent_id:
                query = query.eq("agent_id", agent_id)
            
            query = query.order("created_at", desc=True)
            
            # Only apply limit if specified
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            
            return {
                "success": True,
                "data": response.data,
                "count": len(response.data)
            }
                
        except Exception as e:
            logger.error(f"Error retrieving user files: {str(e)}")
            return {"success": False, "error": str(e), "data": []}