"""JWT-based authentication system"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from loguru import logger

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class JWTAuth:
    """
    JWT authentication manager.
    
    Features:
    - Token generation (access + refresh)
    - Token validation
    - Password hashing and verification
    - Token revocation support
    """
    
    def __init__(
        self,
        secret_key: str = SECRET_KEY,
        algorithm: str = ALGORITHM,
        access_token_expire_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days: int = REFRESH_TOKEN_EXPIRE_DAYS
    ):
        """
        Initialize JWT authentication.
        
        Args:
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Access token TTL
            refresh_token_expire_days: Refresh token TTL
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        
        # Revoked tokens (in production, use Redis)
        self.revoked_tokens = set()
        
        logger.info("JWT authentication initialized")
    
    # ========================================================================
    # PASSWORD HASHING
    # ========================================================================
    
    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    # ========================================================================
    # TOKEN GENERATION
    # ========================================================================
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        tenant_id: str = "default",
        scopes: list = None,
        additional_claims: Dict[str, Any] = None
    ) -> str:
        """
        Create JWT access token.
        
        Args:
            user_id: User identifier
            email: User email
            tenant_id: Tenant identifier
            scopes: List of permission scopes
            additional_claims: Additional JWT claims
            
        Returns:
            JWT access token
        """
        expires = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        claims = {
            "sub": user_id,
            "email": email,
            "tenant_id": tenant_id,
            "scopes": scopes or ["read", "write"],
            "type": "access",
            "exp": expires,
            "iat": datetime.utcnow(),
        }
        
        if additional_claims:
            claims.update(additional_claims)
        
        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(f"Created access token for user {user_id}")
        return token
    
    def create_refresh_token(
        self,
        user_id: str,
        email: str,
        tenant_id: str = "default"
    ) -> str:
        """
        Create JWT refresh token.
        
        Args:
            user_id: User identifier
            email: User email
            tenant_id: Tenant identifier
            
        Returns:
            JWT refresh token
        """
        expires = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        claims = {
            "sub": user_id,
            "email": email,
            "tenant_id": tenant_id,
            "type": "refresh",
            "exp": expires,
            "iat": datetime.utcnow(),
        }
        
        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(f"Created refresh token for user {user_id}")
        return token
    
    def create_token_pair(
        self,
        user_id: str,
        email: str,
        tenant_id: str = "default",
        scopes: list = None
    ) -> Dict[str, str]:
        """
        Create access and refresh token pair.
        
        Args:
            user_id: User identifier
            email: User email
            tenant_id: Tenant identifier
            scopes: List of permission scopes
            
        Returns:
            Dict with access_token and refresh_token
        """
        return {
            "access_token": self.create_access_token(user_id, email, tenant_id, scopes),
            "refresh_token": self.create_refresh_token(user_id, email, tenant_id),
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
        }
    
    # ========================================================================
    # TOKEN VALIDATION
    # ========================================================================
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            # Check if token is revoked
            if token in self.revoked_tokens:
                logger.warning("Attempted to use revoked token")
                return None
            
            # Decode token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            return payload
            
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            return None
    
    def validate_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate access token.
        
        Args:
            token: JWT access token
            
        Returns:
            Token payload if valid, None otherwise
        """
        payload = self.decode_token(token)
        
        if not payload:
            return None
        
        # Check token type
        if payload.get("type") != "access":
            logger.warning("Token is not an access token")
            return None
        
        return payload
    
    def validate_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate refresh token.
        
        Args:
            token: JWT refresh token
            
        Returns:
            Token payload if valid, None otherwise
        """
        payload = self.decode_token(token)
        
        if not payload:
            return None
        
        # Check token type
        if payload.get("type") != "refresh":
            logger.warning("Token is not a refresh token")
            return None
        
        return payload
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Generate new access token from refresh token.
        
        Args:
            refresh_token: JWT refresh token
            
        Returns:
            New token pair if valid, None otherwise
        """
        payload = self.validate_refresh_token(refresh_token)
        
        if not payload:
            return None
        
        # Create new token pair
        return self.create_token_pair(
            user_id=payload["sub"],
            email=payload["email"],
            tenant_id=payload.get("tenant_id", "default"),
            scopes=payload.get("scopes", ["read", "write"])
        )
    
    # ========================================================================
    # TOKEN REVOCATION
    # ========================================================================
    
    def revoke_token(self, token: str) -> None:
        """
        Revoke token (add to blacklist).
        
        Args:
            token: JWT token to revoke
        """
        self.revoked_tokens.add(token)
        logger.info("Token revoked")
    
    def is_token_revoked(self, token: str) -> bool:
        """
        Check if token is revoked.
        
        Args:
            token: JWT token
            
        Returns:
            True if token is revoked
        """
        return token in self.revoked_tokens
    
    # ========================================================================
    # USER EXTRACTION
    # ========================================================================
    
    def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Extract user information from token.
        
        Args:
            token: JWT access token
            
        Returns:
            User info dict if valid, None otherwise
        """
        payload = self.validate_access_token(token)
        
        if not payload:
            return None
        
        return {
            "user_id": payload["sub"],
            "email": payload["email"],
            "tenant_id": payload.get("tenant_id", "default"),
            "scopes": payload.get("scopes", []),
        }
    
    def has_scope(self, token: str, required_scope: str) -> bool:
        """
        Check if token has required scope.
        
        Args:
            token: JWT access token
            required_scope: Required permission scope
            
        Returns:
            True if token has scope
        """
        user = self.get_user_from_token(token)
        
        if not user:
            return False
        
        return required_scope in user.get("scopes", [])
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_stats(self) -> dict:
        """Get authentication statistics"""
        return {
            "revoked_tokens_count": len(self.revoked_tokens),
            "access_token_ttl_minutes": self.access_token_expire_minutes,
            "refresh_token_ttl_days": self.refresh_token_expire_days,
        }


# Global JWT auth instance
jwt_auth = JWTAuth()
