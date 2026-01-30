"""Configuration for vector embedding store"""

from pydantic_settings import BaseSettings
from typing import Optional


class VectorStoreConfig(BaseSettings):
    """
    Configuration for vector embedding store.
    
    Environment variables:
    - VECTOR_DB_URL: PostgreSQL connection URL for pgvector
    - VECTOR_ENABLED: Enable/disable vector embeddings (default: True)
    - VECTOR_MODEL: Sentence transformer model name
    - VECTOR_SIMILARITY_THRESHOLD: Default similarity threshold
    """
    
    # PostgreSQL connection for pgvector
    vector_db_url: str = "postgresql://localhost:5432/lltm_vectors"
    
    # Enable/disable vector embeddings
    vector_enabled: bool = True
    
    # Sentence transformer model
    vector_model: str = "all-MiniLM-L6-v2"
    vector_dim: int = 384
    
    # Similarity thresholds
    similarity_threshold: float = 0.6  # General similarity
    duplicate_threshold: float = 0.9   # Consider as duplicate
    conflict_threshold: float = 0.3    # Low similarity = potential conflict
    
    # Performance settings
    batch_size: int = 32  # Batch size for embedding generation
    cache_embeddings: bool = True  # Cache embeddings in memory
    
    class Config:
        env_prefix = "VECTOR_"
        case_sensitive = False


# Global config instance
vector_config = VectorStoreConfig()
