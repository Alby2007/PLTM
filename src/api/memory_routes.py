"""Memory management API routes"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from loguru import logger

from src.core.models import MemoryAtom, AtomType, Provenance, GraphType
from src.api.auth_routes import get_current_user, UserInfo, require_scope
from src.storage.sqlite_store import SQLiteGraphStore
from src.core.decay import DecayEngine
from src.core.retrieval import MemoryRetriever

# Create router
router = APIRouter(prefix="/api/v1/memory", tags=["memory"])

# Initialize components
store = SQLiteGraphStore()
decay_engine = DecayEngine()
retriever = MemoryRetriever(store, decay_engine)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AtomResponse(BaseModel):
    """Memory atom response"""
    id: str
    subject: str
    predicate: str
    object: str
    atom_type: str
    provenance: str
    confidence: float
    graph: str
    first_observed: str
    last_accessed: str
    assertion_count: int
    contexts: List[str] = []
    stability: Optional[float] = None


class CreateAtomRequest(BaseModel):
    """Create atom request"""
    subject: str
    predicate: str
    object: str
    atom_type: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.9)
    contexts: List[str] = []


class UpdateAtomRequest(BaseModel):
    """Update atom request"""
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    contexts: Optional[List[str]] = None


class ProcessMessageRequest(BaseModel):
    """Process message request"""
    message: str
    session_id: Optional[str] = None


class ProcessMessageResponse(BaseModel):
    """Process message response"""
    atoms_extracted: int
    atoms_approved: int
    atoms_rejected: int
    atoms_quarantined: int
    conflicts_detected: int
    processing_time_ms: float


class MemoryStatsResponse(BaseModel):
    """Memory statistics response"""
    total_atoms: int
    by_graph: dict
    by_type: dict
    by_stability: dict
    weak_memories: int
    at_risk_memories: int


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def atom_to_response(atom: MemoryAtom, include_stability: bool = False) -> AtomResponse:
    """Convert MemoryAtom to response model"""
    response = AtomResponse(
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
        contexts=atom.contexts or []
    )
    
    if include_stability:
        response.stability = decay_engine.calculate_stability(atom)
    
    return response


# ============================================================================
# MEMORY CRUD OPERATIONS
# ============================================================================

@router.get("/{user_id}", response_model=List[AtomResponse])
async def get_user_memories(
    user_id: str,
    graph: Optional[str] = Query(None, description="Filter by graph type"),
    atom_type: Optional[str] = Query(None, description="Filter by atom type"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    min_stability: Optional[float] = Query(None, ge=0.0, le=1.0),
    include_stability: bool = Query(False, description="Include stability scores"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get user's memory atoms.
    
    Args:
        user_id: User identifier
        graph: Optional graph filter (substantiated, unsubstantiated, historical)
        atom_type: Optional atom type filter
        min_confidence: Minimum confidence threshold
        min_stability: Minimum stability threshold
        include_stability: Include stability scores
        limit: Maximum number of results
        current_user: Authenticated user
        
    Returns:
        List of memory atoms
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get atoms
    if graph:
        atoms = await store.get_atoms_by_graph(
            GraphType(graph),
            subject=user_id
        )
    else:
        atoms = await store.get_all_atoms(subject=user_id)
    
    # Apply filters
    if atom_type:
        atoms = [a for a in atoms if a.atom_type.value == atom_type]
    
    if min_confidence:
        atoms = [a for a in atoms if a.confidence >= min_confidence]
    
    if min_stability:
        atoms = [
            a for a in atoms
            if decay_engine.calculate_stability(a) >= min_stability
        ]
    
    # Limit results
    atoms = atoms[:limit]
    
    # Convert to response
    return [atom_to_response(a, include_stability) for a in atoms]


@router.get("/{user_id}/{atom_id}", response_model=AtomResponse)
async def get_atom(
    user_id: str,
    atom_id: str,
    include_stability: bool = Query(True),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get specific memory atom.
    
    Args:
        user_id: User identifier
        atom_id: Atom identifier
        include_stability: Include stability score
        current_user: Authenticated user
        
    Returns:
        Memory atom
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get atom
    atom = await store.get_atom(atom_id)
    
    if not atom or atom.subject != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atom not found"
        )
    
    return atom_to_response(atom, include_stability)


@router.post("/{user_id}", response_model=AtomResponse, status_code=status.HTTP_201_CREATED)
async def create_atom(
    user_id: str,
    request: CreateAtomRequest,
    current_user: UserInfo = Depends(require_scope("write"))
):
    """
    Create new memory atom.
    
    Args:
        user_id: User identifier
        request: Atom creation data
        current_user: Authenticated user
        
    Returns:
        Created atom
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Create atom
    atom = MemoryAtom(
        id=f"atom_{datetime.utcnow().timestamp()}",
        subject=request.subject,
        predicate=request.predicate,
        object=request.object,
        atom_type=AtomType(request.atom_type),
        provenance=Provenance.USER_STATED,
        confidence=request.confidence,
        graph=GraphType.UNSUBSTANTIATED,
        contexts=request.contexts
    )
    
    # Insert atom
    await store.insert_atom(atom)
    
    logger.info(f"Created atom {atom.id} for user {user_id}")
    
    return atom_to_response(atom, include_stability=True)


@router.put("/{user_id}/{atom_id}", response_model=AtomResponse)
async def update_atom(
    user_id: str,
    atom_id: str,
    request: UpdateAtomRequest,
    current_user: UserInfo = Depends(require_scope("write"))
):
    """
    Update memory atom.
    
    Args:
        user_id: User identifier
        atom_id: Atom identifier
        request: Update data
        current_user: Authenticated user
        
    Returns:
        Updated atom
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get atom
    atom = await store.get_atom(atom_id)
    
    if not atom or atom.subject != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atom not found"
        )
    
    # Update fields
    if request.confidence is not None:
        atom.confidence = request.confidence
    
    if request.contexts is not None:
        atom.contexts = request.contexts
    
    # Save changes
    await store.update_atom(atom)
    
    logger.info(f"Updated atom {atom_id}")
    
    return atom_to_response(atom, include_stability=True)


@router.delete("/{user_id}/{atom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_atom(
    user_id: str,
    atom_id: str,
    current_user: UserInfo = Depends(require_scope("write"))
):
    """
    Delete memory atom.
    
    Args:
        user_id: User identifier
        atom_id: Atom identifier
        current_user: Authenticated user
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get atom
    atom = await store.get_atom(atom_id)
    
    if not atom or atom.subject != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atom not found"
        )
    
    # Delete atom
    await store.delete_atom(atom_id)
    
    logger.info(f"Deleted atom {atom_id}")


# ============================================================================
# MESSAGE PROCESSING
# ============================================================================

@router.post("/{user_id}/process", response_model=ProcessMessageResponse)
async def process_message(
    user_id: str,
    request: ProcessMessageRequest,
    current_user: UserInfo = Depends(require_scope("write"))
):
    """
    Process user message and extract memory atoms.
    
    Args:
        user_id: User identifier
        request: Message processing request
        current_user: Authenticated user
        
    Returns:
        Processing results
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    start_time = datetime.utcnow()
    
    # TODO: Implement full pipeline processing
    # For now, return mock response
    
    processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    return ProcessMessageResponse(
        atoms_extracted=0,
        atoms_approved=0,
        atoms_rejected=0,
        atoms_quarantined=0,
        conflicts_detected=0,
        processing_time_ms=processing_time
    )


# ============================================================================
# MEMORY STATISTICS
# ============================================================================

@router.get("/{user_id}/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    user_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get memory statistics for user.
    
    Args:
        user_id: User identifier
        current_user: Authenticated user
        
    Returns:
        Memory statistics
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get all atoms
    atoms = await store.get_all_atoms(subject=user_id)
    
    # Calculate statistics
    by_graph = {}
    by_type = {}
    by_stability = {
        "0.0-0.1": 0,
        "0.1-0.3": 0,
        "0.3-0.5": 0,
        "0.5-0.7": 0,
        "0.7-0.9": 0,
        "0.9-1.0": 0,
    }
    weak_memories = 0
    at_risk_memories = 0
    
    for atom in atoms:
        # By graph
        graph = atom.graph.value
        by_graph[graph] = by_graph.get(graph, 0) + 1
        
        # By type
        atom_type = atom.atom_type.value
        by_type[atom_type] = by_type.get(atom_type, 0) + 1
        
        # By stability
        stability = decay_engine.calculate_stability(atom)
        
        if stability < 0.1:
            by_stability["0.0-0.1"] += 1
            at_risk_memories += 1
        elif stability < 0.3:
            by_stability["0.1-0.3"] += 1
            at_risk_memories += 1
        elif stability < 0.5:
            by_stability["0.3-0.5"] += 1
            weak_memories += 1
        elif stability < 0.7:
            by_stability["0.5-0.7"] += 1
        elif stability < 0.9:
            by_stability["0.7-0.9"] += 1
        else:
            by_stability["0.9-1.0"] += 1
    
    return MemoryStatsResponse(
        total_atoms=len(atoms),
        by_graph=by_graph,
        by_type=by_type,
        by_stability=by_stability,
        weak_memories=weak_memories,
        at_risk_memories=at_risk_memories
    )


# ============================================================================
# WEAK & AT-RISK MEMORIES
# ============================================================================

@router.get("/{user_id}/weak", response_model=List[AtomResponse])
async def get_weak_memories(
    user_id: str,
    threshold: float = Query(0.5, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get weak memories (stability < threshold).
    
    Args:
        user_id: User identifier
        threshold: Stability threshold
        limit: Maximum results
        current_user: Authenticated user
        
    Returns:
        List of weak memories
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get weak memories
    weak = await retriever.get_weak_memories(user_id, threshold)
    
    # Limit results
    weak = weak[:limit]
    
    # Convert to response
    return [
        atom_to_response(atom, include_stability=True)
        for atom, stability in weak
    ]


@router.get("/{user_id}/at-risk", response_model=List[AtomResponse])
async def get_at_risk_memories(
    user_id: str,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get at-risk memories (near dissolution).
    
    Args:
        user_id: User identifier
        hours: Hours until dissolution
        limit: Maximum results
        current_user: Authenticated user
        
    Returns:
        List of at-risk memories
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get at-risk memories
    at_risk = await retriever.get_at_risk_memories(user_id, hours)
    
    # Limit results
    at_risk = at_risk[:limit]
    
    # Convert to response
    return [
        atom_to_response(atom, include_stability=True)
        for atom, hours_remaining in at_risk
    ]


# ============================================================================
# RECONSOLIDATION
# ============================================================================

@router.post("/{user_id}/reconsolidate", dependencies=[Depends(require_scope("write"))])
async def reconsolidate_memories(
    user_id: str,
    threshold: float = Query(0.5, ge=0.0, le=1.0),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Reconsolidate weak memories.
    
    Args:
        user_id: User identifier
        threshold: Stability threshold
        current_user: Authenticated user
        
    Returns:
        Number of memories reconsolidated
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Reconsolidate
    count = await retriever.reconsolidate_weak_memories(user_id, threshold)
    
    logger.info(f"Reconsolidated {count} memories for user {user_id}")
    
    return {
        "reconsolidated": count,
        "threshold": threshold
    }


@router.post("/{user_id}/{atom_id}/reconsolidate", dependencies=[Depends(require_scope("write"))])
async def reconsolidate_atom(
    user_id: str,
    atom_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Reconsolidate specific atom.
    
    Args:
        user_id: User identifier
        atom_id: Atom identifier
        current_user: Authenticated user
        
    Returns:
        Updated atom
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get atom
    atom = await store.get_atom(atom_id)
    
    if not atom or atom.subject != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atom not found"
        )
    
    # Reconsolidate
    decay_engine.reconsolidate(atom)
    await store.update_atom(atom)
    
    logger.info(f"Reconsolidated atom {atom_id}")
    
    return atom_to_response(atom, include_stability=True)
