"""Setup script for PostgreSQL + pgvector database"""

import asyncio
import asyncpg
from loguru import logger


async def setup_vector_database(db_url: str = "postgresql://localhost:5432/lltm_vectors"):
    """
    Setup PostgreSQL database with pgvector extension.
    
    Steps:
    1. Create database if it doesn't exist
    2. Enable pgvector extension
    3. Create atom_embeddings table
    4. Create indexes for fast similarity search
    
    Args:
        db_url: PostgreSQL connection URL
    """
    logger.info("Setting up vector database...")
    
    # Parse connection URL to get database name
    # Format: postgresql://user:pass@host:port/dbname
    parts = db_url.split("/")
    db_name = parts[-1]
    base_url = "/".join(parts[:-1])
    
    try:
        # Connect to postgres database to create our database
        logger.info(f"Connecting to PostgreSQL server...")
        conn = await asyncpg.connect(f"{base_url}/postgres")
        
        # Check if database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            db_name
        )
        
        if not exists:
            logger.info(f"Creating database: {db_name}")
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"Database {db_name} created successfully")
        else:
            logger.info(f"Database {db_name} already exists")
        
        await conn.close()
        
        # Connect to our database
        logger.info(f"Connecting to {db_name}...")
        conn = await asyncpg.connect(db_url)
        
        # Enable pgvector extension
        logger.info("Enabling pgvector extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        logger.info("pgvector extension enabled")
        
        # Create atom_embeddings table
        logger.info("Creating atom_embeddings table...")
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
        logger.info("atom_embeddings table created")
        
        # Create indexes
        logger.info("Creating indexes...")
        
        # IVFFlat index for fast similarity search
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS embedding_cosine_idx 
            ON atom_embeddings 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        logger.info("Created IVFFlat index for similarity search")
        
        # Index for filtering by subject/predicate
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_subject_predicate 
            ON atom_embeddings (subject, predicate)
        """)
        logger.info("Created subject/predicate index")
        
        # Index for created_at
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON atom_embeddings (created_at DESC)
        """)
        logger.info("Created created_at index")
        
        await conn.close()
        
        logger.info("✅ Vector database setup complete!")
        logger.info(f"Database URL: {db_url}")
        logger.info("You can now use the VectorEmbeddingStore")
        
        return True
        
    except asyncpg.PostgresError as e:
        logger.error(f"PostgreSQL error: {e}")
        logger.error("Make sure PostgreSQL is running and you have the correct credentials")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


async def test_vector_database(db_url: str = "postgresql://localhost:5432/lltm_vectors"):
    """
    Test vector database connection and operations.
    
    Args:
        db_url: PostgreSQL connection URL
    """
    logger.info("Testing vector database...")
    
    try:
        conn = await asyncpg.connect(db_url)
        
        # Test pgvector extension
        result = await conn.fetchval(
            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        )
        
        if result == "vector":
            logger.info("✅ pgvector extension is installed")
        else:
            logger.error("❌ pgvector extension not found")
            return False
        
        # Test table exists
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'atom_embeddings'
            )
        """)
        
        if result:
            logger.info("✅ atom_embeddings table exists")
        else:
            logger.error("❌ atom_embeddings table not found")
            return False
        
        # Test insert and query
        logger.info("Testing insert and query...")
        
        # Insert test embedding
        test_embedding = [0.1] * 384  # Dummy embedding
        await conn.execute("""
            INSERT INTO atom_embeddings 
                (atom_id, subject, predicate, object_text, embedding)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (atom_id) DO NOTHING
        """, "test_atom", "test_user", "test_pred", "test object", test_embedding)
        
        # Query test embedding
        result = await conn.fetchrow("""
            SELECT atom_id, subject, predicate, object_text
            FROM atom_embeddings
            WHERE atom_id = $1
        """, "test_atom")
        
        if result and result['atom_id'] == "test_atom":
            logger.info("✅ Insert and query working")
        else:
            logger.error("❌ Insert/query failed")
            return False
        
        # Clean up test data
        await conn.execute("DELETE FROM atom_embeddings WHERE atom_id = 'test_atom'")
        
        await conn.close()
        
        logger.info("✅ All vector database tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False


async def drop_vector_database(db_url: str = "postgresql://localhost:5432/lltm_vectors"):
    """
    Drop vector database (use with caution!).
    
    Args:
        db_url: PostgreSQL connection URL
    """
    parts = db_url.split("/")
    db_name = parts[-1]
    base_url = "/".join(parts[:-1])
    
    logger.warning(f"⚠️  Dropping database: {db_name}")
    
    try:
        conn = await asyncpg.connect(f"{base_url}/postgres")
        
        # Terminate existing connections
        await conn.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_name}'
              AND pid <> pg_backend_pid()
        """)
        
        # Drop database
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        
        await conn.close()
        
        logger.info(f"✅ Database {db_name} dropped successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to drop database: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    # Default database URL
    db_url = "postgresql://localhost:5432/lltm_vectors"
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if len(sys.argv) > 2:
            db_url = sys.argv[2]
        
        if command == "setup":
            asyncio.run(setup_vector_database(db_url))
        elif command == "test":
            asyncio.run(test_vector_database(db_url))
        elif command == "drop":
            confirm = input(f"Are you sure you want to drop {db_url}? (yes/no): ")
            if confirm.lower() == "yes":
                asyncio.run(drop_vector_database(db_url))
            else:
                print("Cancelled")
        else:
            print("Unknown command. Use: setup, test, or drop")
    else:
        # Default: setup and test
        print("Setting up vector database...")
        success = asyncio.run(setup_vector_database(db_url))
        
        if success:
            print("\nTesting vector database...")
            asyncio.run(test_vector_database(db_url))
