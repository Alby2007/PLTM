"""API key management system"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class APIKeyScope(str, Enum):
    """API key permission scopes"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    DECAY = "decay"
    ANALYTICS = "analytics"


@dataclass
class APIKey:
    """API key model"""
    key_id: str
    user_id: str
    tenant_id: str
    key_hash: str
    name: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    usage_limit: Optional[int] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class APIKeyManager:
    """
    API key management system.
    
    Features:
    - Generate API keys
    - Validate API keys
    - Key rotation
    - Usage tracking
    - Scoped permissions
    - Expiration dates
    - Usage quotas
    """
    
    def __init__(self):
        """Initialize API key manager"""
        # In production, store in database
        self.keys: Dict[str, APIKey] = {}
        logger.info("API key manager initialized")
    
    # ========================================================================
    # KEY GENERATION
    # ========================================================================
    
    def generate_api_key(
        self,
        user_id: str,
        tenant_id: str,
        name: str,
        scopes: List[str],
        expires_in_days: Optional[int] = None,
        usage_limit: Optional[int] = None,
        metadata: Dict[str, Any] = None
    ) -> tuple[str, APIKey]:
        """
        Generate new API key.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            name: Descriptive name for key
            scopes: List of permission scopes
            expires_in_days: Optional expiration in days
            usage_limit: Optional usage quota
            metadata: Optional metadata
            
        Returns:
            Tuple of (plain_key, api_key_object)
        """
        # Generate random key
        plain_key = f"lltm_{secrets.token_urlsafe(32)}"
        
        # Hash key for storage
        key_hash = self._hash_key(plain_key)
        
        # Generate key ID
        key_id = f"key_{secrets.token_hex(8)}"
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create API key object
        api_key = APIKey(
            key_id=key_id,
            user_id=user_id,
            tenant_id=tenant_id,
            key_hash=key_hash,
            name=name,
            scopes=scopes,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            usage_limit=usage_limit,
            metadata=metadata or {}
        )
        
        # Store key
        self.keys[key_hash] = api_key
        
        logger.info(
            f"Generated API key {key_id} for user {user_id} "
            f"with scopes {scopes}"
        )
        
        return plain_key, api_key
    
    def _hash_key(self, plain_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(plain_key.encode()).hexdigest()
    
    # ========================================================================
    # KEY VALIDATION
    # ========================================================================
    
    def validate_key(self, plain_key: str) -> Optional[APIKey]:
        """
        Validate API key.
        
        Args:
            plain_key: Plain text API key
            
        Returns:
            APIKey object if valid, None otherwise
        """
        key_hash = self._hash_key(plain_key)
        api_key = self.keys.get(key_hash)
        
        if not api_key:
            logger.warning("Invalid API key")
            return None
        
        # Check if active
        if not api_key.is_active:
            logger.warning(f"Inactive API key: {api_key.key_id}")
            return None
        
        # Check expiration
        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            logger.warning(f"Expired API key: {api_key.key_id}")
            return None
        
        # Check usage limit
        if api_key.usage_limit and api_key.usage_count >= api_key.usage_limit:
            logger.warning(f"Usage limit exceeded: {api_key.key_id}")
            return None
        
        # Update usage
        api_key.last_used = datetime.utcnow()
        api_key.usage_count += 1
        
        logger.debug(f"Validated API key {api_key.key_id}")
        return api_key
    
    def has_scope(self, api_key: APIKey, required_scope: str) -> bool:
        """
        Check if API key has required scope.
        
        Args:
            api_key: API key object
            required_scope: Required permission scope
            
        Returns:
            True if key has scope
        """
        # Admin scope has all permissions
        if APIKeyScope.ADMIN in api_key.scopes:
            return True
        
        return required_scope in api_key.scopes
    
    # ========================================================================
    # KEY MANAGEMENT
    # ========================================================================
    
    def list_keys(
        self,
        user_id: str,
        tenant_id: str,
        include_inactive: bool = False
    ) -> List[APIKey]:
        """
        List API keys for user.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            include_inactive: Include inactive keys
            
        Returns:
            List of API keys
        """
        keys = []
        
        for api_key in self.keys.values():
            if api_key.user_id != user_id or api_key.tenant_id != tenant_id:
                continue
            
            if not include_inactive and not api_key.is_active:
                continue
            
            keys.append(api_key)
        
        return sorted(keys, key=lambda k: k.created_at, reverse=True)
    
    def get_key_by_id(self, key_id: str) -> Optional[APIKey]:
        """
        Get API key by ID.
        
        Args:
            key_id: Key identifier
            
        Returns:
            APIKey object if found
        """
        for api_key in self.keys.values():
            if api_key.key_id == key_id:
                return api_key
        return None
    
    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke API key.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if revoked successfully
        """
        api_key = self.get_key_by_id(key_id)
        
        if not api_key:
            logger.warning(f"Key not found: {key_id}")
            return False
        
        api_key.is_active = False
        logger.info(f"Revoked API key {key_id}")
        return True
    
    def delete_key(self, key_id: str) -> bool:
        """
        Delete API key permanently.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if deleted successfully
        """
        for key_hash, api_key in list(self.keys.items()):
            if api_key.key_id == key_id:
                del self.keys[key_hash]
                logger.info(f"Deleted API key {key_id}")
                return True
        
        logger.warning(f"Key not found: {key_id}")
        return False
    
    def rotate_key(
        self,
        key_id: str,
        new_name: Optional[str] = None
    ) -> Optional[tuple[str, APIKey]]:
        """
        Rotate API key (create new, revoke old).
        
        Args:
            key_id: Key identifier to rotate
            new_name: Optional new name
            
        Returns:
            Tuple of (new_plain_key, new_api_key) if successful
        """
        old_key = self.get_key_by_id(key_id)
        
        if not old_key:
            logger.warning(f"Key not found: {key_id}")
            return None
        
        # Create new key with same settings
        new_plain_key, new_api_key = self.generate_api_key(
            user_id=old_key.user_id,
            tenant_id=old_key.tenant_id,
            name=new_name or f"{old_key.name} (rotated)",
            scopes=old_key.scopes,
            expires_in_days=(
                (old_key.expires_at - datetime.utcnow()).days
                if old_key.expires_at else None
            ),
            usage_limit=old_key.usage_limit,
            metadata=old_key.metadata
        )
        
        # Revoke old key
        self.revoke_key(key_id)
        
        logger.info(f"Rotated API key {key_id} -> {new_api_key.key_id}")
        return new_plain_key, new_api_key
    
    def update_key(
        self,
        key_id: str,
        name: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        usage_limit: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update API key settings.
        
        Args:
            key_id: Key identifier
            name: Optional new name
            scopes: Optional new scopes
            usage_limit: Optional new usage limit
            metadata: Optional new metadata
            
        Returns:
            True if updated successfully
        """
        api_key = self.get_key_by_id(key_id)
        
        if not api_key:
            logger.warning(f"Key not found: {key_id}")
            return False
        
        if name:
            api_key.name = name
        if scopes:
            api_key.scopes = scopes
        if usage_limit is not None:
            api_key.usage_limit = usage_limit
        if metadata:
            api_key.metadata.update(metadata)
        
        logger.info(f"Updated API key {key_id}")
        return True
    
    # ========================================================================
    # USAGE TRACKING
    # ========================================================================
    
    def get_usage_stats(self, key_id: str) -> Optional[Dict[str, Any]]:
        """
        Get usage statistics for API key.
        
        Args:
            key_id: Key identifier
            
        Returns:
            Usage statistics dict
        """
        api_key = self.get_key_by_id(key_id)
        
        if not api_key:
            return None
        
        return {
            "key_id": api_key.key_id,
            "name": api_key.name,
            "usage_count": api_key.usage_count,
            "usage_limit": api_key.usage_limit,
            "usage_percentage": (
                (api_key.usage_count / api_key.usage_limit * 100)
                if api_key.usage_limit else None
            ),
            "last_used": api_key.last_used.isoformat() if api_key.last_used else None,
            "created_at": api_key.created_at.isoformat(),
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "is_active": api_key.is_active,
        }
    
    def reset_usage(self, key_id: str) -> bool:
        """
        Reset usage counter for API key.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if reset successfully
        """
        api_key = self.get_key_by_id(key_id)
        
        if not api_key:
            logger.warning(f"Key not found: {key_id}")
            return False
        
        api_key.usage_count = 0
        logger.info(f"Reset usage for API key {key_id}")
        return True
    
    # ========================================================================
    # CLEANUP
    # ========================================================================
    
    def cleanup_expired_keys(self) -> int:
        """
        Remove expired keys.
        
        Returns:
            Number of keys removed
        """
        now = datetime.utcnow()
        removed = 0
        
        for key_hash, api_key in list(self.keys.items()):
            if api_key.expires_at and now > api_key.expires_at:
                del self.keys[key_hash]
                removed += 1
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} expired API keys")
        
        return removed
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_stats(self) -> dict:
        """Get API key manager statistics"""
        active_keys = sum(1 for k in self.keys.values() if k.is_active)
        expired_keys = sum(
            1 for k in self.keys.values()
            if k.expires_at and datetime.utcnow() > k.expires_at
        )
        
        return {
            "total_keys": len(self.keys),
            "active_keys": active_keys,
            "inactive_keys": len(self.keys) - active_keys,
            "expired_keys": expired_keys,
        }


# Global API key manager instance
api_key_manager = APIKeyManager()
