"""Neo4j graph database store for production deployment"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
from neo4j import GraphDatabase, AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable, TransientError

from src.core.models import MemoryAtom, AtomType, Provenance, GraphType


class Neo4jConfig:
    """Neo4j connection configuration"""
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
        database: str = "neo4j",
        max_connection_lifetime: int = 3600,
        max_connection_pool_size: int = 50,
        connection_acquisition_timeout: int = 60
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.max_connection_lifetime = max_connection_lifetime
        self.max_connection_pool_size = max_connection_pool_size
        self.connection_acquisition_timeout = connection_acquisition_timeout


class Neo4jGraphStore:
    """
    Production-grade graph database store using Neo4j.
    
    Features:
    - Native graph queries (faster than SQLite)
    - Scalable to millions of nodes
    - ACID transactions
    - Relationship indexing
    - Multi-tenant support via labels
    """
    
    def __init__(self, config: Neo4jConfig):
        """
        Initialize Neo4j connection.
        
        Args:
            config: Neo4j configuration
        """
        self.config = config
        self.driver = GraphDatabase.driver(
            config.uri,
            auth=(config.user, config.password),
            max_connection_lifetime=config.max_connection_lifetime,
            max_connection_pool_size=config.max_connection_pool_size,
            connection_acquisition_timeout=config.connection_acquisition_timeout
        )
        
        # Create indexes on startup
        self._create_indexes()
        
        logger.info(f"Neo4j store initialized: {config.uri}")
    
    def _create_indexes(self):
        """Create indexes for performance"""
        with self.driver.session(database=self.config.database) as session:
            # Index on atom ID
            session.run(
                "CREATE INDEX atom_id_index IF NOT EXISTS "
                "FOR (a:Atom) ON (a.id)"
            )
            
            # Index on subject
            session.run(
                "CREATE INDEX atom_subject_index IF NOT EXISTS "
                "FOR (a:Atom) ON (a.subject)"
            )
            
            # Index on predicate
            session.run(
                "CREATE INDEX atom_predicate_index IF NOT EXISTS "
                "FOR (a:Atom) ON (a.predicate)"
            )
            
            # Index on graph type
            session.run(
                "CREATE INDEX atom_graph_index IF NOT EXISTS "
                "FOR (a:Atom) ON (a.graph)"
            )
            
            # Composite index for triple queries
            session.run(
                "CREATE INDEX atom_triple_index IF NOT EXISTS "
                "FOR (a:Atom) ON (a.subject, a.predicate)"
            )
            
            logger.info("Neo4j indexes created")
    
    async def insert_atom(self, atom: MemoryAtom) -> None:
        """
        Insert atom into Neo4j graph.
        
        Args:
            atom: Memory atom to insert
        """
        query = """
        CREATE (a:Atom {
            id: $id,
            subject: $subject,
            predicate: $predicate,
            object: $object,
            atom_type: $atom_type,
            provenance: $provenance,
            confidence: $confidence,
            graph: $graph,
            first_observed: $first_observed,
            last_accessed: $last_accessed,
            assertion_count: $assertion_count,
            contexts: $contexts,
            tenant_id: $tenant_id
        })
        """
        
        with self.driver.session(database=self.config.database) as session:
            session.run(
                query,
                id=atom.id,
                subject=atom.subject,
                predicate=atom.predicate,
                object=atom.object,
                atom_type=atom.atom_type.value,
                provenance=atom.provenance.value,
                confidence=atom.confidence,
                graph=atom.graph.value,
                first_observed=atom.first_observed.isoformat(),
                last_accessed=atom.last_accessed.isoformat(),
                assertion_count=atom.assertion_count,
                contexts=atom.contexts or [],
                tenant_id=getattr(atom, 'tenant_id', 'default')
            )
        
        logger.debug(f"Inserted atom {atom.id} into Neo4j")
    
    async def get_atom(self, atom_id: str) -> Optional[MemoryAtom]:
        """
        Retrieve atom by ID.
        
        Args:
            atom_id: Atom identifier
            
        Returns:
            MemoryAtom if found, None otherwise
        """
        query = """
        MATCH (a:Atom {id: $id})
        RETURN a
        """
        
        with self.driver.session(database=self.config.database) as session:
            result = session.run(query, id=atom_id)
            record = result.single()
            
            if not record:
                return None
            
            return self._record_to_atom(record['a'])
    
    async def find_by_triple(
        self,
        subject: str,
        predicate: Optional[str] = None,
        object_value: Optional[str] = None,
        exclude_historical: bool = True
    ) -> List[MemoryAtom]:
        """
        Find atoms matching triple pattern.
        
        Args:
            subject: Subject to match
            predicate: Optional predicate to match
            object_value: Optional object to match
            exclude_historical: If True, exclude historical graph
            
        Returns:
            List of matching atoms
        """
        conditions = ["a.subject = $subject"]
        params = {"subject": subject}
        
        if predicate:
            conditions.append("a.predicate = $predicate")
            params["predicate"] = predicate
        
        if object_value:
            conditions.append("a.object = $object")
            params["object"] = object_value
        
        if exclude_historical:
            conditions.append("a.graph <> 'historical'")
        
        query = f"""
        MATCH (a:Atom)
        WHERE {' AND '.join(conditions)}
        RETURN a
        ORDER BY a.confidence DESC
        """
        
        with self.driver.session(database=self.config.database) as session:
            result = session.run(query, **params)
            return [self._record_to_atom(record['a']) for record in result]
    
    async def get_substantiated_atoms(
        self,
        subject: str,
        tenant_id: str = 'default'
    ) -> List[MemoryAtom]:
        """
        Get all substantiated atoms for subject.
        
        Args:
            subject: Subject identifier
            tenant_id: Tenant identifier for multi-tenancy
            
        Returns:
            List of substantiated atoms
        """
        query = """
        MATCH (a:Atom)
        WHERE a.subject = $subject 
          AND a.graph = 'substantiated'
          AND a.tenant_id = $tenant_id
        RETURN a
        ORDER BY a.confidence DESC
        """
        
        with self.driver.session(database=self.config.database) as session:
            result = session.run(query, subject=subject, tenant_id=tenant_id)
            return [self._record_to_atom(record['a']) for record in result]
    
    async def get_atoms_by_graph(
        self,
        graph: GraphType,
        subject: Optional[str] = None,
        tenant_id: str = 'default'
    ) -> List[MemoryAtom]:
        """
        Get atoms by graph type.
        
        Args:
            graph: Graph type to filter by
            subject: Optional subject filter
            tenant_id: Tenant identifier
            
        Returns:
            List of atoms in specified graph
        """
        conditions = ["a.graph = $graph", "a.tenant_id = $tenant_id"]
        params = {"graph": graph.value, "tenant_id": tenant_id}
        
        if subject:
            conditions.append("a.subject = $subject")
            params["subject"] = subject
        
        query = f"""
        MATCH (a:Atom)
        WHERE {' AND '.join(conditions)}
        RETURN a
        """
        
        with self.driver.session(database=self.config.database) as session:
            result = session.run(query, **params)
            return [self._record_to_atom(record['a']) for record in result]
    
    async def update_atom(self, atom: MemoryAtom) -> None:
        """
        Update existing atom.
        
        Args:
            atom: Atom with updated values
        """
        query = """
        MATCH (a:Atom {id: $id})
        SET a.confidence = $confidence,
            a.last_accessed = $last_accessed,
            a.assertion_count = $assertion_count,
            a.graph = $graph,
            a.contexts = $contexts
        """
        
        with self.driver.session(database=self.config.database) as session:
            session.run(
                query,
                id=atom.id,
                confidence=atom.confidence,
                last_accessed=atom.last_accessed.isoformat(),
                assertion_count=atom.assertion_count,
                graph=atom.graph.value,
                contexts=atom.contexts or []
            )
        
        logger.debug(f"Updated atom {atom.id}")
    
    async def delete_atom(self, atom_id: str) -> None:
        """
        Delete atom from graph.
        
        Args:
            atom_id: Atom identifier
        """
        query = """
        MATCH (a:Atom {id: $id})
        DELETE a
        """
        
        with self.driver.session(database=self.config.database) as session:
            session.run(query, id=atom_id)
        
        logger.debug(f"Deleted atom {atom_id}")
    
    async def get_all_atoms(
        self,
        subject: Optional[str] = None,
        tenant_id: str = 'default'
    ) -> List[MemoryAtom]:
        """
        Get all atoms (optionally filtered by subject).
        
        Args:
            subject: Optional subject filter
            tenant_id: Tenant identifier
            
        Returns:
            List of all atoms
        """
        if subject:
            query = """
            MATCH (a:Atom)
            WHERE a.subject = $subject AND a.tenant_id = $tenant_id
            RETURN a
            """
            params = {"subject": subject, "tenant_id": tenant_id}
        else:
            query = """
            MATCH (a:Atom)
            WHERE a.tenant_id = $tenant_id
            RETURN a
            """
            params = {"tenant_id": tenant_id}
        
        with self.driver.session(database=self.config.database) as session:
            result = session.run(query, **params)
            return [self._record_to_atom(record['a']) for record in result]
    
    async def count_atoms(
        self,
        graph: Optional[GraphType] = None,
        tenant_id: str = 'default'
    ) -> int:
        """
        Count atoms in database.
        
        Args:
            graph: Optional graph filter
            tenant_id: Tenant identifier
            
        Returns:
            Number of atoms
        """
        if graph:
            query = """
            MATCH (a:Atom)
            WHERE a.graph = $graph AND a.tenant_id = $tenant_id
            RETURN count(a) as count
            """
            params = {"graph": graph.value, "tenant_id": tenant_id}
        else:
            query = """
            MATCH (a:Atom)
            WHERE a.tenant_id = $tenant_id
            RETURN count(a) as count
            """
            params = {"tenant_id": tenant_id}
        
        with self.driver.session(database=self.config.database) as session:
            result = session.run(query, **params)
            record = result.single()
            return record['count'] if record else 0
    
    def _record_to_atom(self, node: Dict[str, Any]) -> MemoryAtom:
        """Convert Neo4j node to MemoryAtom"""
        return MemoryAtom(
            id=node['id'],
            subject=node['subject'],
            predicate=node['predicate'],
            object=node['object'],
            atom_type=AtomType(node['atom_type']),
            provenance=Provenance(node['provenance']),
            confidence=node['confidence'],
            graph=GraphType(node['graph']),
            first_observed=datetime.fromisoformat(node['first_observed']),
            last_accessed=datetime.fromisoformat(node['last_accessed']),
            assertion_count=node['assertion_count'],
            contexts=node.get('contexts', [])
        )
    
    def close(self):
        """Close Neo4j driver"""
        self.driver.close()
        logger.info("Neo4j driver closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
