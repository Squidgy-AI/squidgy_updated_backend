"""
Test script for file content extraction
Extracts text from any file (PDF, DOCX, TXT, JSON, images) and saves to .txt
Uses the exact same extraction functions from backend (background_text_processor.py)
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the actual backend extractor classes
from background_text_processor import TextExtractor, BackgroundTextProcessor

try:
    import httpx
except ImportError:
    httpx = None
    print("⚠️  httpx not installed - URL downloads won't work")

# OpenRouter API key for image OCR
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')


async def download_file(url: str) -> bytes:
    """Download file from URL"""
    if not httpx:
        raise ImportError("httpx not installed. Run: pip install httpx")

    print(f"  🔄 Downloading from URL...")
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        print(f"  ✅ Downloaded {len(response.content)} bytes")
        return response.content


async def extract_text(file_bytes: bytes, file_name: str) -> str:
    """
    Extract text using the backend's TextExtractor class.
    This is the exact same logic used by the backend.
    """
    file_ext = Path(file_name).suffix.lower()

    # Handle image files - extract text using OpenRouter vision model
    if file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
        return await TextExtractor.extract_from_image(file_bytes, file_name)

    if file_ext == '.pdf':
        return TextExtractor.extract_from_pdf(file_bytes)
    elif file_ext in ['.txt', '.md', '.markdown']:
        return TextExtractor.extract_from_txt(file_bytes)
    elif file_ext in ['.json']:
        return TextExtractor.extract_from_json(file_bytes)
    elif file_ext in ['.docx', '.doc']:
        return TextExtractor.extract_from_docx(file_bytes)
    else:
        # Fallback: try to read as plain text
        try:
            return TextExtractor.extract_from_txt(file_bytes)
        except Exception:
            raise Exception(f"Unsupported file type: {file_ext}")


async def extract_and_save(input_path: str, output_path: str = None):
    """
    Extract text from file and save to .txt

    Args:
        input_path: Local file path or URL
        output_path: Output .txt file path (optional, auto-generated if not provided)
    """
    print("=" * 60)
    print("File Content Extractor")
    print("=" * 60)
    print(f"\nInput: {input_path}")

    # Determine if input is URL or local file
    is_url = input_path.startswith('http://') or input_path.startswith('https://')

    if is_url:
        file_bytes = await download_file(input_path)
        # Extract filename from URL
        file_name = input_path.split('/')[-1].split('?')[0]
        if not file_name:
            file_name = "downloaded_file"
    else:
        # Local file
        if not os.path.exists(input_path):
            print(f"\n❌ File not found: {input_path}")
            return

        file_name = os.path.basename(input_path)
        print(f"  📄 Reading local file...")
        with open(input_path, 'rb') as f:
            file_bytes = f.read()
        print(f"  ✅ Read {len(file_bytes)} bytes")

    # Extract text
    file_ext = Path(file_name).suffix.lower()
    print(f"\nFile: {file_name}")
    print(f"Type: {file_ext}")
    print(f"Size: {len(file_bytes):,} bytes")

    print(f"\n🔄 Extracting text using backend's TextExtractor...")

    try:
        extracted_text = await extract_text(file_bytes, file_name)

        if not extracted_text or not extracted_text.strip():
            print("\n❌ No text content found in file")
            return

        print(f"✅ Extracted {len(extracted_text):,} characters")

        # Chunk the text using the same logic as backend
        chunks = BackgroundTextProcessor.chunk_text(extracted_text, chunk_size=4000, chunk_overlap=400)
        print(f"✅ Split into {len(chunks)} chunks (4000 chars each, 400 overlap)")

        # Generate output path if not provided
        if not output_path:
            base_name = Path(file_name).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"extracted_{base_name}_{timestamp}.txt"

        # Save to file with chunk separations (same format as saved to Neon)
        total_chunks = len(chunks)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Extracted from: {file_name}\n")
            f.write(f"# Date: {datetime.now().isoformat()}\n")
            f.write(f"# Original size: {len(file_bytes):,} bytes\n")
            f.write(f"# Extracted characters: {len(extracted_text):,}\n")
            f.write(f"# Total chunks: {total_chunks}\n")
            f.write("=" * 60 + "\n\n")
            
            for i, chunk in enumerate(chunks, 1):
                # Format exactly like backend saves to Neon
                f.write(f"{'='*60}\n")
                f.write(f"File: {file_name} [Part {i}/{total_chunks}]\n")
                f.write(f"{'='*60}\n\n")
                f.write(chunk)
                f.write("\n\n")

        print(f"\n✅ Saved to: {output_path}")

        # Show preview
        print(f"\n{'-' * 60}")
        print("Preview (first 500 characters):")
        print(f"{'-' * 60}")
        preview = extracted_text[:500]
        if len(extracted_text) > 500:
            preview += "..."
        print(preview)
        print(f"{'-' * 60}")

        return extracted_text

    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def interactive_mode():
    """Interactive mode - prompts for file path"""
    print("\n" + "=" * 60)
    print("File Content Extractor - Interactive Mode")
    print("=" * 60)
    print("\nSupported file types:")
    print("  📄 PDF (.pdf)")
    print("  📝 Text (.txt, .md, .markdown)")
    print("  📋 Word (.docx)")
    print("  📊 JSON (.json)")
    print("  🖼️  Images (.png, .jpg, .jpeg, .gif, .bmp, .webp) - OCR via OpenRouter")
    print("\nYou can provide:")
    print("  - Local file path (e.g., C:\\docs\\file.pdf)")
    print("  - URL (e.g., https://example.com/file.pdf)")
    print("\nType 'exit' or 'quit' to exit")
    print("=" * 60)

    if not OPENROUTER_API_KEY:
        print("\n⚠️  OPENROUTER_API_KEY not set - image OCR won't work")

    while True:
        print("\n")
        try:
            input_path = input("📁 Enter file path or URL: ").strip().strip('"').strip("'")
        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting...")
            break

        if not input_path:
            continue

        if input_path.lower() in ('exit', 'quit', 'q'):
            print("Exiting...")
            break

        # Optional: ask for output path
        output_path = input("💾 Output file (press Enter for auto): ").strip()
        if not output_path:
            output_path = None

        await extract_and_save(input_path, output_path)


if __name__ == "__main__":
    # Check if file path provided as argument
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        asyncio.run(extract_and_save(input_file, output_file))
    else:
        # Interactive mode
        asyncio.run(interactive_mode())
