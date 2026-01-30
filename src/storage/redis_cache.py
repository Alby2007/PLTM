"""Redis caching layer for performance optimization"""

import json
import pickle
from typing import Optional, List, Any
from datetime import timedelta
from loguru import logger
import redis.asyncio as redis

from src.core.models import MemoryAtom


class RedisConfig:
    """Redis connection configuration"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        decode_responses: bool = False  # False for binary data (pickle)
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.decode_responses = decode_responses


class RedisCache:
    """
    Redis caching layer for LTM system.
    
    Features:
    - Cache frequently accessed atoms
    - Session storage
    - Rate limiting counters
    - Distributed locks
    - Multi-tenant support via key prefixes
    """
    
    # Cache TTLs (in seconds)
    TTL_USER_ATOMS = 300  # 5 minutes
    TTL_CONFLICT_CHECK = 60  # 1 minute
    TTL_STABILITY_SCORE = 600  # 10 minutes
    TTL_SESSION = 3600  # 1 hour
    TTL_RATE_LIMIT = 3600  # 1 hour
    
    def __init__(self, config: RedisConfig):
        """
        Initialize Redis connection.
        
        Args:
            config: Redis configuration
        """
        self.config = config
        self.pool = redis.ConnectionPool(
            host=config.host,
            port=config.port,
            db=config.db,
            password=config.password,
            max_connections=config.max_connections,
            socket_timeout=config.socket_timeout,
            socket_connect_timeout=config.socket_connect_timeout,
            decode_responses=config.decode_responses
        )
        self.client = redis.Redis(connection_pool=self.pool)
        
        logger.info(f"Redis cache initialized: {config.host}:{config.port}")
    
    # ========================================================================
    # ATOM CACHING
    # ========================================================================
    
    async def cache_atom(
        self,
        atom: MemoryAtom,
        ttl: int = TTL_USER_ATOMS,
        tenant_id: str = 'default'
    ) -> None:
        """
        Cache a memory atom.
        
        Args:
            atom: Memory atom to cache
            ttl: Time to live in seconds
            tenant_id: Tenant identifier
        """
        key = self._atom_key(atom.id, tenant_id)
        value = pickle.dumps(atom)
        
        await self.client.setex(key, ttl, value)
        logger.debug(f"Cached atom {atom.id} (TTL: {ttl}s)")
    
    async def get_cached_atom(
        self,
        atom_id: str,
        tenant_id: str = 'default'
    ) -> Optional[MemoryAtom]:
        """
        Retrieve cached atom.
        
        Args:
            atom_id: Atom identifier
            tenant_id: Tenant identifier
            
        Returns:
            MemoryAtom if cached, None otherwise
        """
        key = self._atom_key(atom_id, tenant_id)
        value = await self.client.get(key)
        
        if value:
            logger.debug(f"Cache hit: atom {atom_id}")
            return pickle.loads(value)
        
        logger.debug(f"Cache miss: atom {atom_id}")
        return None
    
    async def cache_user_atoms(
        self,
        user_id: str,
        atoms: List[MemoryAtom],
        ttl: int = TTL_USER_ATOMS,
        tenant_id: str = 'default'
    ) -> None:
        """
        Cache all atoms for a user.
        
        Args:
            user_id: User identifier
            atoms: List of atoms to cache
            ttl: Time to live in seconds
            tenant_id: Tenant identifier
        """
        key = self._user_atoms_key(user_id, tenant_id)
        value = pickle.dumps(atoms)
        
        await self.client.setex(key, ttl, value)
        logger.debug(f"Cached {len(atoms)} atoms for user {user_id}")
    
    async def get_cached_user_atoms(
        self,
        user_id: str,
        tenant_id: str = 'default'
    ) -> Optional[List[MemoryAtom]]:
        """
        Retrieve cached user atoms.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            
        Returns:
            List of atoms if cached, None otherwise
        """
        key = self._user_atoms_key(user_id, tenant_id)
        value = await self.client.get(key)
        
        if value:
            logger.debug(f"Cache hit: user atoms {user_id}")
            return pickle.loads(value)
        
        logger.debug(f"Cache miss: user atoms {user_id}")
        return None
    
    async def invalidate_atom(
        self,
        atom_id: str,
        tenant_id: str = 'default'
    ) -> None:
        """
        Invalidate cached atom.
        
        Args:
            atom_id: Atom identifier
            tenant_id: Tenant identifier
        """
        key = self._atom_key(atom_id, tenant_id)
        await self.client.delete(key)
        logger.debug(f"Invalidated cache: atom {atom_id}")
    
    async def invalidate_user_atoms(
        self,
        user_id: str,
        tenant_id: str = 'default'
    ) -> None:
        """
        Invalidate cached user atoms.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
        """
        key = self._user_atoms_key(user_id, tenant_id)
        await self.client.delete(key)
        logger.debug(f"Invalidated cache: user atoms {user_id}")
    
    # ========================================================================
    # STABILITY SCORE CACHING
    # ========================================================================
    
    async def cache_stability(
        self,
        atom_id: str,
        stability: float,
        ttl: int = TTL_STABILITY_SCORE,
        tenant_id: str = 'default'
    ) -> None:
        """
        Cache stability score.
        
        Args:
            atom_id: Atom identifier
            stability: Stability score (0.0-1.0)
            ttl: Time to live in seconds
            tenant_id: Tenant identifier
        """
        key = self._stability_key(atom_id, tenant_id)
        await self.client.setex(key, ttl, str(stability))
        logger.debug(f"Cached stability for {atom_id}: {stability:.3f}")
    
    async def get_cached_stability(
        self,
        atom_id: str,
        tenant_id: str = 'default'
    ) -> Optional[float]:
        """
        Retrieve cached stability score.
        
        Args:
            atom_id: Atom identifier
            tenant_id: Tenant identifier
            
        Returns:
            Stability score if cached, None otherwise
        """
        key = self._stability_key(atom_id, tenant_id)
        value = await self.client.get(key)
        
        if value:
            return float(value)
        return None
    
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    async def create_session(
        self,
        session_id: str,
        user_id: str,
        data: dict,
        ttl: int = TTL_SESSION
    ) -> None:
        """
        Create user session.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            data: Session data
            ttl: Time to live in seconds
        """
        key = self._session_key(session_id)
        value = json.dumps({
            "user_id": user_id,
            "data": data
        })
        
        await self.client.setex(key, ttl, value)
        logger.debug(f"Created session {session_id} for user {user_id}")
    
    async def get_session(
        self,
        session_id: str
    ) -> Optional[dict]:
        """
        Retrieve session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data if exists, None otherwise
        """
        key = self._session_key(session_id)
        value = await self.client.get(key)
        
        if value:
            return json.loads(value)
        return None
    
    async def delete_session(
        self,
        session_id: str
    ) -> None:
        """
        Delete session.
        
        Args:
            session_id: Session identifier
        """
        key = self._session_key(session_id)
        await self.client.delete(key)
        logger.debug(f"Deleted session {session_id}")
    
    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int = 3600,
        tenant_id: str = 'default'
    ) -> tuple[bool, int]:
        """
        Check rate limit using sliding window.
        
        Args:
            identifier: User ID or API key
            limit: Maximum requests allowed
            window: Time window in seconds
            tenant_id: Tenant identifier
            
        Returns:
            Tuple of (allowed, remaining_requests)
        """
        key = self._rate_limit_key(identifier, tenant_id)
        
        # Increment counter
        count = await self.client.incr(key)
        
        # Set expiry on first request
        if count == 1:
            await self.client.expire(key, window)
        
        allowed = count <= limit
        remaining = max(0, limit - count)
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {identifier}: "
                f"{count}/{limit} in {window}s"
            )
        
        return allowed, remaining
    
    async def reset_rate_limit(
        self,
        identifier: str,
        tenant_id: str = 'default'
    ) -> None:
        """
        Reset rate limit counter.
        
        Args:
            identifier: User ID or API key
            tenant_id: Tenant identifier
        """
        key = self._rate_limit_key(identifier, tenant_id)
        await self.client.delete(key)
        logger.debug(f"Reset rate limit for {identifier}")
    
    # ========================================================================
    # DISTRIBUTED LOCKS
    # ========================================================================
    
    async def acquire_lock(
        self,
        lock_name: str,
        timeout: int = 10,
        tenant_id: str = 'default'
    ) -> bool:
        """
        Acquire distributed lock.
        
        Args:
            lock_name: Lock identifier
            timeout: Lock timeout in seconds
            tenant_id: Tenant identifier
            
        Returns:
            True if lock acquired, False otherwise
        """
        key = self._lock_key(lock_name, tenant_id)
        
        # Try to set lock with NX (only if not exists)
        acquired = await self.client.set(
            key,
            "1",
            ex=timeout,
            nx=True
        )
        
        if acquired:
            logger.debug(f"Acquired lock: {lock_name}")
        else:
            logger.debug(f"Failed to acquire lock: {lock_name}")
        
        return bool(acquired)
    
    async def release_lock(
        self,
        lock_name: str,
        tenant_id: str = 'default'
    ) -> None:
        """
        Release distributed lock.
        
        Args:
            lock_name: Lock identifier
            tenant_id: Tenant identifier
        """
        key = self._lock_key(lock_name, tenant_id)
        await self.client.delete(key)
        logger.debug(f"Released lock: {lock_name}")
    
    # ========================================================================
    # CACHE STATISTICS
    # ========================================================================
    
    async def get_cache_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache statistics
        """
        info = await self.client.info("stats")
        
        return {
            "total_connections": info.get("total_connections_received", 0),
            "total_commands": info.get("total_commands_processed", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": self._calculate_hit_rate(
                info.get("keyspace_hits", 0),
                info.get("keyspace_misses", 0)
            ),
            "used_memory": info.get("used_memory_human", "0"),
            "connected_clients": info.get("connected_clients", 0),
        }
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate"""
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0
    
    # ========================================================================
    # KEY GENERATION
    # ========================================================================
    
    def _atom_key(self, atom_id: str, tenant_id: str) -> str:
        """Generate key for atom cache"""
        return f"lltm:{tenant_id}:atom:{atom_id}"
    
    def _user_atoms_key(self, user_id: str, tenant_id: str) -> str:
        """Generate key for user atoms cache"""
        return f"lltm:{tenant_id}:user_atoms:{user_id}"
    
    def _stability_key(self, atom_id: str, tenant_id: str) -> str:
        """Generate key for stability cache"""
        return f"lltm:{tenant_id}:stability:{atom_id}"
    
    def _session_key(self, session_id: str) -> str:
        """Generate key for session"""
        return f"lltm:session:{session_id}"
    
    def _rate_limit_key(self, identifier: str, tenant_id: str) -> str:
        """Generate key for rate limiting"""
        return f"lltm:{tenant_id}:rate_limit:{identifier}"
    
    def _lock_key(self, lock_name: str, tenant_id: str) -> str:
        """Generate key for distributed lock"""
        return f"lltm:{tenant_id}:lock:{lock_name}"
    
    # ========================================================================
    # CLEANUP
    # ========================================================================
    
    async def flush_tenant(self, tenant_id: str) -> int:
        """
        Flush all keys for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Number of keys deleted
        """
        pattern = f"lltm:{tenant_id}:*"
        keys = []
        
        async for key in self.client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            deleted = await self.client.delete(*keys)
            logger.info(f"Flushed {deleted} keys for tenant {tenant_id}")
            return deleted
        
        return 0
    
    async def close(self):
        """Close Redis connection"""
        await self.client.close()
        await self.pool.disconnect()
        logger.info("Redis connection closed")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
