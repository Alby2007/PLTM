"""Unit tests for vector embedding store"""

import pytest
import asyncpg
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from src.storage.vector_store import VectorEmbeddingStore
from src.core.models import MemoryAtom, AtomType, Provenance, GraphType


@pytest.fixture
async def mock_db_pool():
    """Mock asyncpg connection pool"""
    pool = AsyncMock()
    conn = AsyncMock()
    
    # Mock acquire context manager
    pool.acquire.return_value.__aenter__.return_value = conn
    pool.acquire.return_value.__aexit__.return_value = None
    
    return pool, conn


@pytest.fixture
def vector_store():
    """Create vector store instance (without DB connection)"""
    store = VectorEmbeddingStore("postgresql://localhost/test")
    return store


@pytest.fixture
def sample_atom():
    """Create sample memory atom"""
    return MemoryAtom(
        id="atom_123",
        subject="user",
        predicate="works_at",
        object="Google",
        atom_type=AtomType.RELATION,
        provenance=Provenance.USER_STATED,
        confidence=0.9,
        graph=GraphType.SUBSTANTIATED,
    )


class TestVectorEmbedding:
    """Test embedding generation"""
    
    def test_embed_generates_correct_dimensions(self, vector_store):
        """Test that embeddings have correct dimensions"""
        text = "I work at Google"
        embedding = vector_store.embed(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)  # all-MiniLM-L6-v2 dimension
    
    def test_embed_deterministic(self, vector_store):
        """Test that same text produces same embedding"""
        text = "I love Python programming"
        
        emb1 = vector_store.embed(text)
        emb2 = vector_store.embed(text)
        
        np.testing.assert_array_almost_equal(emb1, emb2)
    
    def test_embed_different_texts(self, vector_store):
        """Test that different texts produce different embeddings"""
        emb1 = vector_store.embed("I love Python")
        emb2 = vector_store.embed("I hate Java")
        
        # Embeddings should be different
        assert not np.array_equal(emb1, emb2)


class TestSemanticSimilarity:
    """Test semantic similarity calculations"""
    
    @pytest.mark.asyncio
    async def test_identical_texts_high_similarity(self, vector_store):
        """Identical texts should have similarity ~1.0"""
        text = "I work at Google"
        similarity = await vector_store.get_semantic_similarity(text, text)
        
        assert similarity > 0.99
    
    @pytest.mark.asyncio
    async def test_similar_texts_high_similarity(self, vector_store):
        """Semantically similar texts should have high similarity"""
        text1 = "I work at Google"
        text2 = "I am employed by Google"
        
        similarity = await vector_store.get_semantic_similarity(text1, text2)
        
        # Should be high similarity (>0.7)
        assert similarity > 0.7
    
    @pytest.mark.asyncio
    async def test_different_texts_low_similarity(self, vector_store):
        """Semantically different texts should have low similarity"""
        text1 = "I work at Google"
        text2 = "I love pizza"
        
        similarity = await vector_store.get_semantic_similarity(text1, text2)
        
        # Should be low similarity (<0.3)
        assert similarity < 0.3
    
    @pytest.mark.asyncio
    async def test_opposite_companies_low_similarity(self, vector_store):
        """Different companies should have low similarity"""
        text1 = "Google"
        text2 = "Anthropic"
        
        similarity = await vector_store.get_semantic_similarity(text1, text2)
        
        # Should be low similarity (this is what string matching missed!)
        assert similarity < 0.5


class TestDatabaseOperations:
    """Test database operations (with mocked DB)"""
    
    @pytest.mark.asyncio
    async def test_store_embedding(self, vector_store, mock_db_pool, sample_atom):
        """Test storing embedding in database"""
        pool, conn = mock_db_pool
        vector_store.pool = pool
        
        await vector_store.store_embedding(
            sample_atom.id,
            sample_atom.subject,
            sample_atom.predicate,
            sample_atom.object
        )
        
        # Verify execute was called
        assert conn.execute.called
        
        # Verify correct SQL structure
        call_args = conn.execute.call_args[0]
        assert "INSERT INTO atom_embeddings" in call_args[0]
        assert sample_atom.id in call_args[1:]
    
    @pytest.mark.asyncio
    async def test_find_similar(self, vector_store, mock_db_pool):
        """Test finding similar atoms"""
        pool, conn = mock_db_pool
        vector_store.pool = pool
        
        # Mock database response
        mock_rows = [
            {"atom_id": "atom_1", "object_text": "Google", "similarity": 0.95},
            {"atom_id": "atom_2", "object_text": "Alphabet", "similarity": 0.85},
        ]
        conn.fetch.return_value = mock_rows
        
        results = await vector_store.find_similar("Google", limit=10, threshold=0.7)
        
        assert len(results) == 2
        assert results[0][0] == "atom_1"
        assert results[0][2] == 0.95
    
    @pytest.mark.asyncio
    async def test_find_conflicting_objects(self, vector_store, mock_db_pool):
        """Test finding conflicting objects"""
        pool, conn = mock_db_pool
        vector_store.pool = pool
        
        # Mock database response
        mock_rows = [
            {"atom_id": "atom_old", "object_text": "Anthropic", "similarity": 0.15},
        ]
        conn.fetch.return_value = mock_rows
        
        results = await vector_store.find_conflicting_objects(
            subject="user",
            predicate="works_at",
            object_text="Google"
        )
        
        assert len(results) == 1
        assert results[0][1] == "Anthropic"
        assert results[0][2] < 0.3  # Low similarity = conflict
    
    @pytest.mark.asyncio
    async def test_batch_store_embeddings(self, vector_store, mock_db_pool):
        """Test batch storing embeddings"""
        pool, conn = mock_db_pool
        vector_store.pool = pool
        
        atoms = [
            MemoryAtom(
                id=f"atom_{i}",
                subject="user",
                predicate="likes",
                object=f"thing_{i}",
                atom_type=AtomType.RELATION,
                provenance=Provenance.USER_STATED,
                confidence=0.9,
                graph=GraphType.SUBSTANTIATED,
            )
            for i in range(3)
        ]
        
        await vector_store.batch_store_embeddings(atoms)
        
        # Verify executemany was called
        assert conn.executemany.called
        
        # Verify correct number of atoms
        call_args = conn.executemany.call_args[0]
        assert len(call_args[1]) == 3


class TestConflictDetection:
    """Test conflict detection scenarios"""
    
    @pytest.mark.asyncio
    async def test_detects_company_change(self, vector_store):
        """Should detect company change as low similarity"""
        similarity = await vector_store.get_semantic_similarity(
            "Google",
            "Anthropic"
        )
        
        # Different companies should have low similarity
        assert similarity < 0.5
    
    @pytest.mark.asyncio
    async def test_detects_synonym_as_similar(self, vector_store):
        """Should detect synonyms as high similarity"""
        similarity = await vector_store.get_semantic_similarity(
            "automobile",
            "car"
        )
        
        # Synonyms should have high similarity
        assert similarity > 0.7
    
    @pytest.mark.asyncio
    async def test_detects_paraphrase_as_similar(self, vector_store):
        """Should detect paraphrases as high similarity"""
        similarity = await vector_store.get_semantic_similarity(
            "I love Python programming",
            "Python is my favorite programming language"
        )
        
        # Paraphrases should have high similarity
        assert similarity > 0.6


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_embed_empty_string(self, vector_store):
        """Test embedding empty string"""
        embedding = vector_store.embed("")
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
    
    def test_embed_very_long_text(self, vector_store):
        """Test embedding very long text"""
        long_text = "word " * 1000  # 1000 words
        embedding = vector_store.embed(long_text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
    
    @pytest.mark.asyncio
    async def test_batch_store_empty_list(self, vector_store, mock_db_pool):
        """Test batch storing empty list"""
        pool, conn = mock_db_pool
        vector_store.pool = pool
        
        await vector_store.batch_store_embeddings([])
        
        # Should not call database
        assert not conn.executemany.called


class TestStats:
    """Test statistics gathering"""
    
    @pytest.mark.asyncio
    async def test_get_stats(self, vector_store, mock_db_pool):
        """Test getting vector store statistics"""
        pool, conn = mock_db_pool
        vector_store.pool = pool
        
        # Mock database responses
        conn.fetchval.side_effect = [100, 10, 5]  # total, subjects, predicates
        
        stats = await vector_store.get_stats()
        
        assert stats["total_embeddings"] == 100
        assert stats["unique_subjects"] == 10
        assert stats["unique_predicates"] == 5
        assert stats["model"] == "all-MiniLM-L6-v2"
        assert stats["embedding_dim"] == 384
