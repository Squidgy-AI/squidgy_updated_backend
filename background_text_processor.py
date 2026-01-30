"""
Background Text Processor
Handles downloading files from URLs and extracting text content
"""

import asyncio
import json
import logging
import tempfile
import os
import re
from typing import Optional, Dict, Any, List
import httpx
from pathlib import Path

# Text extraction libraries
try:
    import PyPDF2
    from io import BytesIO
except ImportError:
    PyPDF2 = None

try:
    from docx import Document
except ImportError:
    Document = None

logger = logging.getLogger(__name__)

class TextExtractor:
    """Handles text extraction from different file types"""
    
    @staticmethod
    def extract_from_pdf(file_bytes: bytes) -> str:
        """Extract text from PDF bytes"""
        if not PyPDF2:
            raise ImportError("PyPDF2 not installed")
        
        try:
            pdf_file = BytesIO(file_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_content = []
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())
            
            return '\n'.join(text_content).strip()
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    @staticmethod
    def extract_from_txt(file_bytes: bytes) -> str:
        """Extract text from TXT bytes with multiple encoding support"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                return file_bytes.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
        
        raise Exception("Failed to decode text file with supported encodings")
    
    @staticmethod
    def extract_from_json(file_bytes: bytes) -> str:
        """Extract text from JSON bytes - pretty-print the structured data"""
        encodings = ['utf-8', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                raw = file_bytes.decode(encoding)
                parsed = json.loads(raw)
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

        raise Exception("Failed to parse JSON file")

    @staticmethod
    def extract_from_docx(file_bytes: bytes) -> str:
        """Extract text from DOCX bytes"""
        if not Document:
            raise ImportError("python-docx not installed")
        
        try:
            # Save bytes to temporary file for docx processing
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                temp_file.write(file_bytes)
                temp_file_path = temp_file.name
            
            try:
                doc = Document(temp_file_path)
                text_content = []
                
                # Extract paragraphs
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        text_content.append(paragraph.text.strip())
                
                # Extract table content
                for table in doc.tables:
                    for row in table.rows:
                        row_text = []
                        for cell in row.cells:
                            if cell.text.strip():
                                row_text.append(cell.text.strip())
                        if row_text:
                            text_content.append(' | '.join(row_text))
                
                return '\n'.join(text_content).strip()
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            raise Exception(f"Failed to extract text from DOCX: {str(e)}")


class BackgroundTextProcessor:
    """Handles background processing of file text extraction"""

    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.text_extractor = TextExtractor()
    
    async def download_file(self, file_url: str) -> bytes:
        """Download file from URL and return bytes"""
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(file_url)
                response.raise_for_status()
                return response.content
        except httpx.TimeoutException:
            raise Exception("File download timeout")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to download file: HTTP {e.response.status_code}")
        except Exception as e:
            raise Exception(f"File download error: {str(e)}")
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1500, chunk_overlap: int = 200) -> List[str]:
        """Split text into chunks with overlap, breaking at sentence/paragraph boundaries."""
        if not text or not text.strip():
            return []

        # If text fits in one chunk, return as-is
        if len(text) <= chunk_size:
            return [text.strip()]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # If this is the last chunk, take the rest
            if end >= len(text):
                chunk = text[start:].strip()
                if chunk:
                    chunks.append(chunk)
                break

            # Try to break at paragraph boundary (double newline)
            segment = text[start:end]
            break_pos = segment.rfind('\n\n')

            # Fallback: break at single newline
            if break_pos == -1 or break_pos < chunk_size * 0.3:
                break_pos = segment.rfind('\n')

            # Fallback: break at sentence end (. ! ?)
            if break_pos == -1 or break_pos < chunk_size * 0.3:
                sentence_match = None
                for m in re.finditer(r'[.!?]\s', segment):
                    if m.start() >= chunk_size * 0.3:
                        sentence_match = m
                if sentence_match:
                    break_pos = sentence_match.end()

            # Fallback: break at space
            if break_pos == -1 or break_pos < chunk_size * 0.3:
                break_pos = segment.rfind(' ')

            # Last resort: hard cut
            if break_pos == -1 or break_pos < chunk_size * 0.3:
                break_pos = chunk_size

            chunk = text[start:start + break_pos].strip()
            if chunk:
                chunks.append(chunk)

            # Move start forward, accounting for overlap
            start = start + break_pos - chunk_overlap
            if start < 0:
                start = 0

        return chunks

    def extract_text(self, file_bytes: bytes, file_name: str) -> str:
        """Extract text based on file extension"""
        file_ext = Path(file_name).suffix.lower()

        # Handle image files - no text extraction needed, Claude can process images directly
        if file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
            return f"[Image file: {file_name}]"

        if file_ext == '.pdf':
            return self.text_extractor.extract_from_pdf(file_bytes)
        elif file_ext in ['.txt', '.md', '.markdown']:
            return self.text_extractor.extract_from_txt(file_bytes)
        elif file_ext in ['.json']:
            return self.text_extractor.extract_from_json(file_bytes)
        elif file_ext in ['.docx', '.doc']:
            return self.text_extractor.extract_from_docx(file_bytes)
        else:
            # Fallback: try to read as plain text
            try:
                return self.text_extractor.extract_from_txt(file_bytes)
            except Exception:
                raise Exception(f"Unsupported file type: {file_ext}")
    
    async def update_processing_status(
        self, 
        file_id: str, 
        status: str, 
        extracted_text: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update file processing status in database"""
        try:
            update_data = {
                "processing_status": status,
                "updated_at": "now()"
            }
            
            if extracted_text is not None:
                update_data["extracted_text"] = extracted_text
            
            if error_message is not None:
                update_data["error_message"] = error_message
            
            result = self.supabase.table("firm_users_knowledge_base").update(
                update_data
            ).eq("file_id", file_id).execute()
            
            if not result.data:
                logger.error(f"Failed to update status for file_id: {file_id}")
                
        except Exception as e:
            logger.error(f"Database update error for {file_id}: {e}")
    
    async def process_file(self, file_id: str):
        """Main processing function for a file"""
        try:
            # Get file record from database
            result = self.supabase.table("firm_users_knowledge_base").select(
                "file_id, file_name, file_url, processing_status, firm_user_id, agent_id"
            ).eq("file_id", file_id).execute()

            if not result.data:
                logger.error(f"File record not found: {file_id}")
                return

            file_record = result.data[0]

            # Skip if already processed
            if file_record["processing_status"] in ["completed", "failed"]:
                logger.info(f"File {file_id} already processed with status: {file_record['processing_status']}")
                return

            # Update status to processing
            await self.update_processing_status(file_id, "processing")

            # Download file
            logger.info(f"Downloading file: {file_record['file_url']}")
            file_bytes = await self.download_file(file_record["file_url"])

            # Extract text
            logger.info(f"Extracting text from: {file_record['file_name']}")
            extracted_text = self.extract_text(file_bytes, file_record["file_name"])

            if not extracted_text.strip():
                raise Exception("No text content found in file")

            # Update with success
            await self.update_processing_status(
                file_id,
                "completed",
                extracted_text=extracted_text
            )

            logger.info(f"Successfully processed file {file_id}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Processing failed for {file_id}: {error_msg}")

            # Update with failure
            await self.update_processing_status(
                file_id,
                "failed",
                error_message=error_msg
            )


# Global processor instance
_background_processor = None

def get_background_processor():
    """Get the global background processor instance"""
    global _background_processor
    return _background_processor

def initialize_background_processor(supabase_client):
    """Initialize the global background processor"""
    global _background_processor
    _background_processor = BackgroundTextProcessor(supabase_client)
    return _background_processor