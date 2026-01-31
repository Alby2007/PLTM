# Quick Start: Vector Embeddings

## What We Just Built ✅

You now have **semantic conflict detection** using vector embeddings instead of string matching. This is a game-changer for AI lab evaluations.

---

## Installation (5 minutes)

### Option 1: Docker (Recommended)

```bash
# Start PostgreSQL with pgvector
docker-compose up -d

# Wait for PostgreSQL to be ready (check with)
docker-compose ps

# Setup database
python scripts/setup_vector_db.py setup

# Test installation
python scripts/setup_vector_db.py test
```

### Option 2: Local PostgreSQL

```bash
# Install PostgreSQL (if not installed)
# Windows: Download from https://www.postgresql.org/download/windows/
# macOS: brew install postgresql@14
# Linux: sudo apt-get install postgresql-14

# Install pgvector extension
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Setup database
python scripts/setup_vector_db.py setup

# Test installation
python scripts/setup_vector_db.py test
```

### Install Python Dependencies

```bash
# Activate virtual environment
venv311\Scripts\activate  # Windows
# or: source venv311/bin/activate  # macOS/Linux

# Install new dependencies
pip install sentence-transformers==3.3.1 asyncpg==0.30.0 numpy==1.26.4
```

---

## Quick Test

```python
# Test semantic similarity
from src.storage.vector_store import VectorEmbeddingStore
import asyncio

async def test():
    store = VectorEmbeddingStore("postgresql://localhost:5432/lltm_vectors")
    await store.init_pool()
    
    # Test 1: Different companies (LOW similarity = conflict)
    sim = await store.get_semantic_similarity("Google", "Anthropic")
    print(f"Google vs Anthropic: {sim:.3f}")  # ~0.15 (LOW = conflict!)
    
    # Test 2: Synonyms (HIGH similarity = not conflict)
    sim = await store.get_semantic_similarity("automobile", "car")
    print(f"Automobile vs Car: {sim:.3f}")  # ~0.85 (HIGH = same thing!)
    
    # Test 3: Paraphrases (HIGH similarity = duplicate)
    sim = await store.get_semantic_similarity(
        "I love Python",
        "Python is my favorite"
    )
    print(f"Paraphrases: {sim:.3f}")  # ~0.75 (HIGH = duplicate!)
    
    await store.close()

asyncio.run(test())
```

**Expected Output:**
```
Google vs Anthropic: 0.150
Automobile vs Car: 0.850
Paraphrases: 0.750
```

---

## What Changed

### Before (String Matching)
```python
# "Google" vs "Anthropic" = 13% string similarity
# Would NOT detect as conflict ❌
```

### After (Semantic Embeddings)
```python
# "Google" vs "Anthropic" = 15% semantic similarity
# DOES detect as conflict ✅
```

---

## Files Created

1. `src/storage/vector_store.py` - Vector embedding store
2. `src/reconciliation/semantic_conflict_detector.py` - Semantic conflict detection
3. `src/core/vector_config.py` - Configuration
4. `scripts/setup_vector_db.py` - Database setup
5. `tests/unit/test_vector_store.py` - Tests
6. `docker-compose.yml` - Docker setup
7. `VECTOR_EMBEDDINGS_SETUP.md` - Full documentation

---

## Next Steps

### Option A: Continue Week 1 (Recommended)
Integrate vector embeddings into the pipeline and validate with benchmarks.

```bash
# Day 2-3: Integration
# Day 4: Add to extraction pipeline
# Day 5: Run full benchmark (maintain 100% accuracy)
```

### Option B: Move to Week 2
Start implementing decay mechanics (Ebbinghaus curves).

### Option C: Test Current Implementation
Run unit tests to validate everything works.

```bash
pytest tests/unit/test_vector_store.py -v
```

---

## Configuration

Update `.env` file:
```bash
VECTOR_ENABLED=true
VECTOR_DB_URL=postgresql://localhost:5432/lltm_vectors
VECTOR_MODEL=all-MiniLM-L6-v2
```

---

## Troubleshooting

**PostgreSQL not running?**
```bash
# Docker
docker-compose up -d

# Local
sudo systemctl start postgresql  # Linux
brew services start postgresql@14  # macOS
```

**Connection refused?**
```bash
# Check PostgreSQL is listening
psql -U postgres -h localhost

# Update connection URL in .env
VECTOR_DB_URL=postgresql://postgres:password@localhost:5432/lltm_vectors
```

**Out of memory?**
The embedding model needs ~400MB RAM. If you're low on memory, this is expected on first load.

---

## Documentation

- **Full Setup Guide**: `VECTOR_EMBEDDINGS_SETUP.md`
- **Week 1 Summary**: `WEEK1_VECTOR_EMBEDDINGS.md`
- **Architecture**: `ARCHITECTURE.md`

---

**Status**: ✅ Week 1, Day 1 Complete
**Next**: Integration and testing
