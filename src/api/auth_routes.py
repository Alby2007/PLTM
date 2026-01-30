"""Authentication API routes"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from loguru import logger

from src.auth.jwt_auth import jwt_auth
from src.auth.api_keys import api_key_manager, APIKeyScope
from src.middleware.rate_limiter import rate_limiter, RateLimitTier

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class UserRegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    tenant_id: str = "default"


class UserLoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class APIKeyCreateRequest(BaseModel):
    """API key creation request"""
    name: str
    scopes: list[str] = ["read", "write"]
    expires_in_days: Optional[int] = None
    usage_limit: Optional[int] = None


class APIKeyResponse(BaseModel):
    """API key response"""
    key_id: str
    api_key: str
    name: str
    scopes: list[str]
    created_at: str
    expires_at: Optional[str] = None


class UserInfo(BaseModel):
    """User information"""
    user_id: str
    email: str
    tenant_id: str
    scopes: list[str]


# ============================================================================
# TEMPORARY USER STORE (In production, use database)
# ============================================================================

class User:
    """User model"""
    def __init__(self, user_id: str, email: str, password_hash: str, full_name: str, tenant_id: str):
        self.user_id = user_id
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.tenant_id = tenant_id
        self.created_at = datetime.utcnow()
        self.is_active = True


# Temporary in-memory user store
users_db = {}  # email -> User


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserInfo:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        UserInfo object
        
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    user = jwt_auth.get_user_from_token(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return UserInfo(**user)


async def get_current_user_from_api_key(
    x_api_key: str = Header(None)
) -> UserInfo:
    """
    Get current user from API key.
    
    Args:
        x_api_key: API key from header
        
    Returns:
        UserInfo object
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    
    api_key = api_key_manager.validate_key(x_api_key)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    return UserInfo(
        user_id=api_key.user_id,
        email="",  # API keys don't have email
        tenant_id=api_key.tenant_id,
        scopes=api_key.scopes
    )


def require_scope(required_scope: str):
    """
    Dependency to require specific scope.
    
    Args:
        required_scope: Required permission scope
        
    Returns:
        Dependency function
    """
    async def scope_checker(user: UserInfo = Depends(get_current_user)):
        if required_scope not in user.scopes and "admin" not in user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {required_scope}"
            )
        return user
    return scope_checker


# ============================================================================
# REGISTRATION & LOGIN
# ============================================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest):
    """
    Register new user.
    
    Args:
        request: User registration data
        
    Returns:
        JWT token pair
    """
    # Check if user exists
    if request.email in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    password_hash = jwt_auth.hash_password(request.password)
    
    # Create user
    user_id = f"user_{len(users_db) + 1}"
    user = User(
        user_id=user_id,
        email=request.email,
        password_hash=password_hash,
        full_name=request.full_name,
        tenant_id=request.tenant_id
    )
    
    users_db[request.email] = user
    
    # Generate tokens
    tokens = jwt_auth.create_token_pair(
        user_id=user.user_id,
        email=user.email,
        tenant_id=user.tenant_id,
        scopes=["read", "write"]
    )
    
    logger.info(f"User registered: {user.email}")
    
    return TokenResponse(**tokens)


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest):
    """
    Login user.
    
    Args:
        request: Login credentials
        
    Returns:
        JWT token pair
    """
    # Check rate limit
    allowed, rate_info = await rate_limiter.check_rate_limit(
        identifier=request.email,
        tier=RateLimitTier.FREE
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": "3600"}
        )
    
    # Get user
    user = users_db.get(request.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not jwt_auth.verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Generate tokens
    tokens = jwt_auth.create_token_pair(
        user_id=user.user_id,
        email=user.email,
        tenant_id=user.tenant_id,
        scopes=["read", "write"]
    )
    
    logger.info(f"User logged in: {user.email}")
    
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token.
    
    Args:
        request: Refresh token
        
    Returns:
        New JWT token pair
    """
    tokens = jwt_auth.refresh_access_token(request.refresh_token)
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    logger.info("Token refreshed")
    
    return TokenResponse(**tokens)


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Logout user (revoke token).
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        Success message
    """
    token = credentials.credentials
    jwt_auth.revoke_token(token)
    
    logger.info("User logged out")
    
    return {"message": "Successfully logged out"}


# ============================================================================
# USER INFO
# ============================================================================

@router.get("/me", response_model=UserInfo)
async def get_me(user: UserInfo = Depends(get_current_user)):
    """
    Get current user information.
    
    Args:
        user: Current authenticated user
        
    Returns:
        User information
    """
    return user


# ============================================================================
# API KEY MANAGEMENT
# ============================================================================

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    user: UserInfo = Depends(get_current_user)
):
    """
    Create new API key.
    
    Args:
        request: API key creation data
        user: Current authenticated user
        
    Returns:
        API key details
    """
    # Generate API key
    plain_key, api_key = api_key_manager.generate_api_key(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        name=request.name,
        scopes=request.scopes,
        expires_in_days=request.expires_in_days,
        usage_limit=request.usage_limit
    )
    
    logger.info(f"API key created: {api_key.key_id} for user {user.user_id}")
    
    return APIKeyResponse(
        key_id=api_key.key_id,
        api_key=plain_key,  # Only returned once!
        name=api_key.name,
        scopes=api_key.scopes,
        created_at=api_key.created_at.isoformat(),
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None
    )


@router.get("/api-keys")
async def list_api_keys(user: UserInfo = Depends(get_current_user)):
    """
    List user's API keys.
    
    Args:
        user: Current authenticated user
        
    Returns:
        List of API keys (without plain keys)
    """
    keys = api_key_manager.list_keys(user.user_id, user.tenant_id)
    
    return [
        {
            "key_id": k.key_id,
            "name": k.name,
            "scopes": k.scopes,
            "created_at": k.created_at.isoformat(),
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "last_used": k.last_used.isoformat() if k.last_used else None,
            "usage_count": k.usage_count,
            "usage_limit": k.usage_limit,
            "is_active": k.is_active,
        }
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    user: UserInfo = Depends(get_current_user)
):
    """
    Revoke API key.
    
    Args:
        key_id: API key identifier
        user: Current authenticated user
        
    Returns:
        Success message
    """
    # Verify key belongs to user
    api_key = api_key_manager.get_key_by_id(key_id)
    
    if not api_key or api_key.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Revoke key
    api_key_manager.revoke_key(key_id)
    
    logger.info(f"API key revoked: {key_id}")
    
    return {"message": "API key revoked successfully"}


@router.get("/api-keys/{key_id}/usage")
async def get_api_key_usage(
    key_id: str,
    user: UserInfo = Depends(get_current_user)
):
    """
    Get API key usage statistics.
    
    Args:
        key_id: API key identifier
        user: Current authenticated user
        
    Returns:
        Usage statistics
    """
    # Verify key belongs to user
    api_key = api_key_manager.get_key_by_id(key_id)
    
    if not api_key or api_key.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return api_key_manager.get_usage_stats(key_id)


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.get("/admin/stats", dependencies=[Depends(require_scope("admin"))])
async def get_auth_stats():
    """
    Get authentication statistics (admin only).
    
    Returns:
        Authentication statistics
    """
    return {
        "jwt": jwt_auth.get_stats(),
        "api_keys": api_key_manager.get_stats(),
    }
