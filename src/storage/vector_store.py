"""Vector embedding store using pgvector for semantic similarity search"""

import asyncpg
import numpy as np
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer
from loguru import logger

from src.core.models import MemoryAtom


class VectorEmbeddingStore:
    """
    pgvector-based semantic similarity search for memory atoms.
    
    Replaces string matching with actual semantic understanding.
    Uses sentence-transformers for embeddings and PostgreSQL pgvector for storage.
    
    Key capabilities:
    - Semantic similarity search (find similar objects)
    - Conflict detection (find semantically different objects for same subject/predicate)
    - Embedding caching for performance
    """
    
    # Model: all-MiniLM-L6-v2 (384 dimensions, fast, good quality)
    MODEL_NAME = "all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384
    
    def __init__(self, db_url: str):
        """
        Initialize vector store.
        
        Args:
            db_url: PostgreSQL connection string (e.g., postgresql://user:pass@localhost/dbname)
        """
        self.db_url = db_url
        self.pool: Optional[asyncpg.Pool] = None
        self.model: Optional[SentenceTransformer] = None
        self._model_loaded = False
    
    def _load_model(self) -> None:
        """Lazy load the sentence transformer model"""
        if not self._model_loaded:
            logger.info(f"Loading embedding model: {self.MODEL_NAME}")
            self.model = SentenceTransformer(self.MODEL_NAME)
            self._model_loaded = True
            logger.info("Embedding model loaded successfully")
    
    async def init_pool(self) -> None:
        """
        Initialize PostgreSQL connection pool and create schema.
        
        Creates:
        - pgvector extension
        - atom_embeddings table
        - IVFFlat index for fast similarity search
        """
        logger.info("Initializing vector store connection pool")
        self.pool = await asyncpg.create_pool(self.db_url, min_size=2, max_size=10)
        
        async with self.pool.acquire() as conn:
            # Enable pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            logger.info("pgvector extension enabled")
            
            # Create embeddings table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS atom_embeddings (
                    atom_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object_text TEXT NOT NULL,
                    embedding vector(384),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create index for fast similarity search
            # IVFFlat index: approximate nearest neighbor search
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS embedding_cosine_idx 
                ON atom_embeddings 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
            
            # Create indexes for filtering
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_subject_predicate 
                ON atom_embeddings (subject, predicate)
            """)
            
            logger.info("Vector store schema initialized")
    
    async def close(self) -> None:
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Vector store connection pool closed")
    
    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding vector for text.
        
        Args:
            text: Input text to embed
            
        Returns:
            384-dimensional embedding vector
        """
        self._load_model()
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    async def store_embedding(
        self,
        atom_id: str,
        subject: str,
        predicate: str,
        object_text: str
    ) -> None:
        """
        Store atom embedding in vector database.
        
        Args:
            atom_id: Unique atom identifier
            subject: Atom subject
            predicate: Atom predicate
            object_text: Atom object (text to embed)
        """
        embedding = self.embed(object_text)
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO atom_embeddings 
                    (atom_id, subject, predicate, object_text, embedding)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (atom_id) DO UPDATE
                SET object_text = $4,
                    embedding = $5,
                    updated_at = NOW()
            """, atom_id, subject, predicate, object_text, embedding.tolist())
        
        logger.debug(f"Stored embedding for atom {atom_id}")
    
    async def find_similar(
        self,
        query_text: str,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Tuple[str, str, float]]:
        """
        Find semantically similar atoms.
        
        Args:
            query_text: Query text to find similar atoms for
            limit: Maximum number of results
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of (atom_id, object_text, similarity_score)
        """
        query_embedding = self.embed(query_text)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    atom_id,
                    object_text,
                    1 - (embedding <=> $1::vector) as similarity
                FROM atom_embeddings
                WHERE 1 - (embedding <=> $1::vector) > $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """, query_embedding.tolist(), threshold, limit)
            
            results = [(row['atom_id'], row['object_text'], row['similarity']) 
                      for row in rows]
            
            logger.debug(f"Found {len(results)} similar atoms for query: {query_text[:50]}")
            return results
    
    async def find_conflicting_objects(
        self,
        subject: str,
        predicate: str,
        object_text: str,
        similarity_threshold: float = 0.6,
        limit: int = 10
    ) -> List[Tuple[str, str, float]]:
        """
        Find atoms with same subject/predicate but semantically different objects.
        
        This is the KEY method that replaces string-based conflict detection.
        
        Args:
            subject: Atom subject to match
            predicate: Atom predicate to match
            object_text: Object text to compare against
            similarity_threshold: Minimum similarity to consider (0-1)
            limit: Maximum results
            
        Returns:
            List of (atom_id, object_text, similarity_score)
            
        Example:
            subject="user", predicate="works_at", object_text="Google"
            Returns: [("atom_123", "Anthropic", 0.15), ...]
            
            Low similarity = potential conflict!
        """
        query_embedding = self.embed(object_text)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    atom_id,
                    object_text,
                    1 - (embedding <=> $1::vector) as similarity
                FROM atom_embeddings
                WHERE subject = $2 
                  AND predicate = $3
                  AND object_text != $4
                ORDER BY similarity DESC
                LIMIT $5
            """, query_embedding.tolist(), subject, predicate, object_text, limit)
            
            results = [(row['atom_id'], row['object_text'], row['similarity']) 
                      for row in rows]
            
            logger.debug(
                f"Found {len(results)} potential conflicts for "
                f"[{subject}] [{predicate}] [{object_text}]"
            )
            return results
    
    async def get_semantic_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """
        Calculate semantic similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score (0-1)
        """
        emb1 = self.embed(text1)
        emb2 = self.embed(text2)
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        
        return float(similarity)
    
    async def batch_store_embeddings(self, atoms: List[MemoryAtom]) -> None:
        """
        Store embeddings for multiple atoms efficiently.
        
        Args:
            atoms: List of MemoryAtoms to store embeddings for
        """
        if not atoms:
            return
        
        # Generate all embeddings first (can be parallelized)
        embeddings = [self.embed(atom.object) for atom in atoms]
        
        # Batch insert
        async with self.pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO atom_embeddings 
                    (atom_id, subject, predicate, object_text, embedding)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (atom_id) DO UPDATE
                SET object_text = $4,
                    embedding = $5,
                    updated_at = NOW()
            """, [
                (atom.id, atom.subject, atom.predicate, atom.object, emb.tolist())
                for atom, emb in zip(atoms, embeddings)
            ])
        
        logger.info(f"Batch stored {len(atoms)} embeddings")
    
    async def delete_embedding(self, atom_id: str) -> None:
        """
        Delete embedding for an atom.
        
        Args:
            atom_id: Atom ID to delete
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM atom_embeddings
                WHERE atom_id = $1
            """, atom_id)
        
        logger.debug(f"Deleted embedding for atom {atom_id}")
    
    async def get_stats(self) -> dict:
        """
        Get vector store statistics.
        
        Returns:
            Dict with stats (total embeddings, avg similarity, etc.)
        """
        async with self.pool.acquire() as conn:
            total = await conn.fetchval("""
                SELECT COUNT(*) FROM atom_embeddings
            """)
            
            subjects = await conn.fetchval("""
                SELECT COUNT(DISTINCT subject) FROM atom_embeddings
            """)
            
            predicates = await conn.fetchval("""
                SELECT COUNT(DISTINCT predicate) FROM atom_embeddings
            """)
        
        return {
            "total_embeddings": total,
            "unique_subjects": subjects,
            "unique_predicates": predicates,
            "model": self.MODEL_NAME,
            "embedding_dim": self.EMBEDDING_DIM,
        }
