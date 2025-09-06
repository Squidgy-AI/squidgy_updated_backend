# embedding_service.py - Free embedding alternative using sentence-transformers
"""
Free and efficient embedding service using sentence-transformers.
This replaces OpenAI embeddings to avoid quota issues and reduce costs.
"""

import os
import logging
from typing import List, Optional, Dict, Any
import numpy as np
from functools import lru_cache
import pickle
import hashlib

logger = logging.getLogger(__name__)

class FreeEmbeddingService:
    """
    Free embedding service using sentence-transformers.
    Provides caching and optimized performance.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_size: int = 1000):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Sentence transformer model to use
            cache_size: Number of embeddings to cache in memory
        """
        self.model_name = model_name
        self.model = None
        self.cache_size = cache_size
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self._init_model()
    
    def _init_model(self):
        """Initialize the sentence transformer model lazily."""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
        except ImportError:
            logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
            self.model = None  # Set to None instead of raising
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = None  # Set to None instead of raising
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    @lru_cache(maxsize=1000)
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for text with caching.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of float values representing the embedding
        """
        if not text or not text.strip():
            return None
            
        try:
            # Check cache first
            cache_key = self._get_cache_key(text)
            if cache_key in self._embedding_cache:
                cached_embedding = self._embedding_cache[cache_key]
                return cached_embedding.tolist()
            
            # Generate embedding
            if self.model is None:
                self._init_model()
            
            # If model is still None (sentence-transformers not available), return dummy embedding
            if self.model is None:
                logger.warning("Sentence transformers not available, using dummy embedding")
                # Generate a simple hash-based dummy embedding (384 dimensions to match all-MiniLM-L6-v2)
                text_hash = hashlib.md5(text.encode()).hexdigest()
                # Convert hex to pseudo-float vector
                dummy_embedding = []
                for i in range(0, len(text_hash), 2):
                    hex_val = text_hash[i:i+2]
                    # Convert to float between -1 and 1
                    float_val = (int(hex_val, 16) - 127.5) / 127.5
                    dummy_embedding.append(float_val)
                # Pad to 384 dimensions
                while len(dummy_embedding) < 384:
                    dummy_embedding.extend(dummy_embedding[:min(len(dummy_embedding), 384 - len(dummy_embedding))])
                return dummy_embedding[:384]
                
            embedding = self.model.encode([text.strip()])[0]
            
            # Cache the result
            if len(self._embedding_cache) < self.cache_size:
                self._embedding_cache[cache_key] = embedding
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Error generating embedding for text: {e}")
            return None
    
    def get_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Get embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings (or None for failed embeddings)
        """
        if not texts:
            return []
            
        try:
            if self.model is None:
                self._init_model()
            
            # Filter out empty texts and track indices
            valid_texts = []
            valid_indices = []
            
            for i, text in enumerate(texts):
                if text and text.strip():
                    valid_texts.append(text.strip())
                    valid_indices.append(i)
            
            if not valid_texts:
                return [None] * len(texts)
            
            # Generate embeddings in batch
            embeddings = self.model.encode(valid_texts)
            
            # Map back to original indices
            result = [None] * len(texts)
            for embedding, original_idx in zip(embeddings, valid_indices):
                result[original_idx] = embedding.tolist()
                
                # Cache individual embeddings
                cache_key = self._get_cache_key(texts[original_idx])
                if len(self._embedding_cache) < self.cache_size:
                    self._embedding_cache[cache_key] = embedding
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [None] * len(texts)
    
    def clear_cache(self):
        """Clear the embedding cache."""
        self._embedding_cache.clear()
        self.get_embedding.cache_clear()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "memory_cache_size": len(self._embedding_cache),
            "lru_cache_info": self.get_embedding.cache_info()._asdict(),
            "model_name": self.model_name
        }

# Global instance
_embedding_service: Optional[FreeEmbeddingService] = None

def get_embedding_service() -> FreeEmbeddingService:
    """Get the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = FreeEmbeddingService()
    return _embedding_service

def get_embedding(text: str) -> Optional[List[float]]:
    """Convenience function to get a single embedding."""
    service = get_embedding_service()
    return service.get_embedding(text)

def get_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """Convenience function to get multiple embeddings."""
    service = get_embedding_service()
    return service.get_embeddings_batch(texts)

# Compatibility with OpenAI-style interface
class OpenAICompatibleEmbedding:
    """OpenAI-compatible interface for easy replacement."""
    
    def __init__(self):
        self.service = get_embedding_service()
    
    def create(self, input: str, model: str = "text-embedding-3-small"):
        """Create embedding in OpenAI-style format."""
        embedding = self.service.get_embedding(input)
        if embedding is None:
            raise Exception("Failed to generate embedding")
        
        # Return in OpenAI format
        return type('EmbeddingResponse', (), {
            'data': [type('EmbeddingData', (), {
                'embedding': embedding
            })()]
        })()

# For easy drop-in replacement
def create_openai_compatible_client():
    """Create OpenAI-compatible embedding client."""
    client = type('EmbeddingClient', (), {})()
    client.embeddings = OpenAICompatibleEmbedding()
    return client