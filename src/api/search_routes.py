"""Advanced search API routes"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from loguru import logger

from src.core.models import MemoryAtom, AtomType, GraphType
from src.api.auth_routes import get_current_user, UserInfo
from src.storage.sqlite_store import SQLiteGraphStore
from src.storage.vector_store import VectorEmbeddingStore
from src.core.vector_config import VectorConfig
from src.core.decay import DecayEngine

# Create router
router = APIRouter(prefix="/api/v1/search", tags=["search"])

# Initialize components
store = SQLiteGraphStore()
vector_store = VectorEmbeddingStore(VectorConfig())
decay_engine = DecayEngine()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SearchRequest(BaseModel):
    """Search request"""
    query: str
    search_type: str = Field("full_text", description="full_text, semantic, or hybrid")
    filters: Optional[dict] = None
    limit: int = Field(20, ge=1, le=100)


class SearchResult(BaseModel):
    """Search result"""
    atom_id: str
    subject: str
    predicate: str
    object: str
    atom_type: str
    confidence: float
    graph: str
    score: float
    stability: Optional[float] = None
    highlights: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """Search response"""
    query: str
    total_results: int
    results: List[SearchResult]
    search_time_ms: float
    facets: Optional[dict] = None


class FacetedSearchRequest(BaseModel):
    """Faceted search request"""
    query: Optional[str] = None
    facets: dict = Field(
        default_factory=dict,
        description="Facets to filter by (atom_type, graph, predicate, etc.)"
    )
    limit: int = Field(20, ge=1, le=100)


# ============================================================================
# FULL-TEXT SEARCH
# ============================================================================

@router.get("/{user_id}/full-text", response_model=SearchResponse)
async def full_text_search(
    user_id: str,
    q: str = Query(..., description="Search query"),
    atom_type: Optional[str] = Query(None, description="Filter by atom type"),
    graph: Optional[str] = Query(None, description="Filter by graph"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Full-text search across memory atoms.
    
    Searches in subject, predicate, and object fields.
    
    Args:
        user_id: User identifier
        q: Search query
        atom_type: Optional atom type filter
        graph: Optional graph filter
        min_confidence: Minimum confidence threshold
        limit: Maximum results
        current_user: Authenticated user
        
    Returns:
        Search results
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    import time
    start_time = time.time()
    
    # Get all atoms for user
    atoms = await store.get_all_atoms(subject=user_id)
    
    # Apply filters
    if atom_type:
        atoms = [a for a in atoms if a.atom_type.value == atom_type]
    
    if graph:
        atoms = [a for a in atoms if a.graph.value == graph]
    
    if min_confidence:
        atoms = [a for a in atoms if a.confidence >= min_confidence]
    
    # Full-text search
    query_lower = q.lower()
    results = []
    
    for atom in atoms:
        score = 0.0
        highlights = []
        
        # Search in subject
        if query_lower in atom.subject.lower():
            score += 1.0
            highlights.append(f"subject: {atom.subject}")
        
        # Search in predicate
        if query_lower in atom.predicate.lower():
            score += 2.0  # Predicates are more important
            highlights.append(f"predicate: {atom.predicate}")
        
        # Search in object
        if query_lower in atom.object.lower():
            score += 1.5
            highlights.append(f"object: {atom.object}")
        
        if score > 0:
            stability = decay_engine.calculate_stability(atom)
            
            results.append(SearchResult(
                atom_id=atom.id,
                subject=atom.subject,
                predicate=atom.predicate,
                object=atom.object,
                atom_type=atom.atom_type.value,
                confidence=atom.confidence,
                graph=atom.graph.value,
                score=score,
                stability=stability,
                highlights=highlights
            ))
    
    # Sort by score (descending)
    results.sort(key=lambda r: r.score, reverse=True)
    
    # Limit results
    results = results[:limit]
    
    search_time = (time.time() - start_time) * 1000
    
    return SearchResponse(
        query=q,
        total_results=len(results),
        results=results,
        search_time_ms=search_time
    )


# ============================================================================
# SEMANTIC SEARCH
# ============================================================================

@router.get("/{user_id}/semantic", response_model=SearchResponse)
async def semantic_search(
    user_id: str,
    q: str = Query(..., description="Search query"),
    threshold: float = Query(0.6, ge=0.0, le=1.0, description="Similarity threshold"),
    atom_type: Optional[str] = Query(None),
    graph: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Semantic search using vector embeddings.
    
    Finds atoms semantically similar to query.
    
    Args:
        user_id: User identifier
        q: Search query
        threshold: Similarity threshold (0.0-1.0)
        atom_type: Optional atom type filter
        graph: Optional graph filter
        limit: Maximum results
        current_user: Authenticated user
        
    Returns:
        Search results ranked by semantic similarity
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    import time
    start_time = time.time()
    
    # Get all atoms for user
    atoms = await store.get_all_atoms(subject=user_id)
    
    # Apply filters
    if atom_type:
        atoms = [a for a in atoms if a.atom_type.value == atom_type]
    
    if graph:
        atoms = [a for a in atoms if a.graph.value == graph]
    
    # Generate query embedding
    query_embedding = await vector_store.generate_embedding(q)
    
    # Calculate semantic similarity for each atom
    results = []
    
    for atom in atoms:
        # Get atom embedding
        atom_text = f"{atom.subject} {atom.predicate} {atom.object}"
        atom_embedding = await vector_store.generate_embedding(atom_text)
        
        # Calculate cosine similarity
        import numpy as np
        similarity = np.dot(query_embedding, atom_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(atom_embedding)
        )
        
        if similarity >= threshold:
            stability = decay_engine.calculate_stability(atom)
            
            results.append(SearchResult(
                atom_id=atom.id,
                subject=atom.subject,
                predicate=atom.predicate,
                object=atom.object,
                atom_type=atom.atom_type.value,
                confidence=atom.confidence,
                graph=atom.graph.value,
                score=float(similarity),
                stability=stability
            ))
    
    # Sort by similarity (descending)
    results.sort(key=lambda r: r.score, reverse=True)
    
    # Limit results
    results = results[:limit]
    
    search_time = (time.time() - start_time) * 1000
    
    return SearchResponse(
        query=q,
        total_results=len(results),
        results=results,
        search_time_ms=search_time
    )


# ============================================================================
# HYBRID SEARCH
# ============================================================================

@router.get("/{user_id}/hybrid", response_model=SearchResponse)
async def hybrid_search(
    user_id: str,
    q: str = Query(..., description="Search query"),
    semantic_weight: float = Query(0.5, ge=0.0, le=1.0),
    threshold: float = Query(0.3, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Hybrid search combining full-text and semantic search.
    
    Args:
        user_id: User identifier
        q: Search query
        semantic_weight: Weight for semantic score (0.0-1.0)
        threshold: Minimum combined score threshold
        limit: Maximum results
        current_user: Authenticated user
        
    Returns:
        Search results ranked by combined score
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    import time
    import numpy as np
    start_time = time.time()
    
    # Get all atoms for user
    atoms = await store.get_all_atoms(subject=user_id)
    
    # Generate query embedding
    query_embedding = await vector_store.generate_embedding(q)
    query_lower = q.lower()
    
    # Calculate combined scores
    results = []
    
    for atom in atoms:
        # Full-text score
        text_score = 0.0
        highlights = []
        
        if query_lower in atom.subject.lower():
            text_score += 1.0
            highlights.append(f"subject: {atom.subject}")
        
        if query_lower in atom.predicate.lower():
            text_score += 2.0
            highlights.append(f"predicate: {atom.predicate}")
        
        if query_lower in atom.object.lower():
            text_score += 1.5
            highlights.append(f"object: {atom.object}")
        
        # Normalize text score (max 4.5)
        text_score = min(text_score / 4.5, 1.0)
        
        # Semantic score
        atom_text = f"{atom.subject} {atom.predicate} {atom.object}"
        atom_embedding = await vector_store.generate_embedding(atom_text)
        
        semantic_score = np.dot(query_embedding, atom_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(atom_embedding)
        )
        
        # Combined score
        combined_score = (
            (1 - semantic_weight) * text_score +
            semantic_weight * semantic_score
        )
        
        if combined_score >= threshold:
            stability = decay_engine.calculate_stability(atom)
            
            results.append(SearchResult(
                atom_id=atom.id,
                subject=atom.subject,
                predicate=atom.predicate,
                object=atom.object,
                atom_type=atom.atom_type.value,
                confidence=atom.confidence,
                graph=atom.graph.value,
                score=float(combined_score),
                stability=stability,
                highlights=highlights if highlights else None
            ))
    
    # Sort by combined score (descending)
    results.sort(key=lambda r: r.score, reverse=True)
    
    # Limit results
    results = results[:limit]
    
    search_time = (time.time() - start_time) * 1000
    
    return SearchResponse(
        query=q,
        total_results=len(results),
        results=results,
        search_time_ms=search_time
    )


# ============================================================================
# FACETED SEARCH
# ============================================================================

@router.post("/{user_id}/faceted", response_model=SearchResponse)
async def faceted_search(
    user_id: str,
    request: FacetedSearchRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Faceted search with multiple filters.
    
    Args:
        user_id: User identifier
        request: Faceted search request
        current_user: Authenticated user
        
    Returns:
        Search results with facet counts
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    import time
    start_time = time.time()
    
    # Get all atoms for user
    atoms = await store.get_all_atoms(subject=user_id)
    
    # Apply facet filters
    if "atom_type" in request.facets:
        atoms = [a for a in atoms if a.atom_type.value in request.facets["atom_type"]]
    
    if "graph" in request.facets:
        atoms = [a for a in atoms if a.graph.value in request.facets["graph"]]
    
    if "predicate" in request.facets:
        atoms = [a for a in atoms if a.predicate in request.facets["predicate"]]
    
    if "min_confidence" in request.facets:
        atoms = [a for a in atoms if a.confidence >= request.facets["min_confidence"]]
    
    if "min_stability" in request.facets:
        atoms = [
            a for a in atoms
            if decay_engine.calculate_stability(a) >= request.facets["min_stability"]
        ]
    
    # Apply text query if provided
    if request.query:
        query_lower = request.query.lower()
        atoms = [
            a for a in atoms
            if (query_lower in a.subject.lower() or
                query_lower in a.predicate.lower() or
                query_lower in a.object.lower())
        ]
    
    # Calculate facet counts
    facet_counts = {
        "atom_type": {},
        "graph": {},
        "predicate": {},
    }
    
    for atom in atoms:
        # Count by atom type
        atom_type = atom.atom_type.value
        facet_counts["atom_type"][atom_type] = facet_counts["atom_type"].get(atom_type, 0) + 1
        
        # Count by graph
        graph = atom.graph.value
        facet_counts["graph"][graph] = facet_counts["graph"].get(graph, 0) + 1
        
        # Count by predicate
        predicate = atom.predicate
        facet_counts["predicate"][predicate] = facet_counts["predicate"].get(predicate, 0) + 1
    
    # Convert to results
    results = []
    for atom in atoms[:request.limit]:
        stability = decay_engine.calculate_stability(atom)
        
        results.append(SearchResult(
            atom_id=atom.id,
            subject=atom.subject,
            predicate=atom.predicate,
            object=atom.object,
            atom_type=atom.atom_type.value,
            confidence=atom.confidence,
            graph=atom.graph.value,
            score=1.0,
            stability=stability
        ))
    
    search_time = (time.time() - start_time) * 1000
    
    return SearchResponse(
        query=request.query or "",
        total_results=len(atoms),
        results=results,
        search_time_ms=search_time,
        facets=facet_counts
    )


# ============================================================================
# PREDICATE SEARCH
# ============================================================================

@router.get("/{user_id}/by-predicate/{predicate}", response_model=List[SearchResult])
async def search_by_predicate(
    user_id: str,
    predicate: str,
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Search atoms by predicate.
    
    Args:
        user_id: User identifier
        predicate: Predicate to search for
        limit: Maximum results
        current_user: Authenticated user
        
    Returns:
        List of atoms with matching predicate
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Search by predicate
    atoms = await store.find_by_triple(
        subject=user_id,
        predicate=predicate,
        exclude_historical=True
    )
    
    # Limit results
    atoms = atoms[:limit]
    
    # Convert to results
    results = []
    for atom in atoms:
        stability = decay_engine.calculate_stability(atom)
        
        results.append(SearchResult(
            atom_id=atom.id,
            subject=atom.subject,
            predicate=atom.predicate,
            object=atom.object,
            atom_type=atom.atom_type.value,
            confidence=atom.confidence,
            graph=atom.graph.value,
            score=atom.confidence,
            stability=stability
        ))
    
    return results


# ============================================================================
# TEMPORAL SEARCH
# ============================================================================

@router.get("/{user_id}/temporal", response_model=List[SearchResult])
async def temporal_search(
    user_id: str,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Search atoms by time range.
    
    Args:
        user_id: User identifier
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        limit: Maximum results
        current_user: Authenticated user
        
    Returns:
        List of atoms in time range
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    from datetime import datetime
    
    # Get all atoms
    atoms = await store.get_all_atoms(subject=user_id)
    
    # Apply date filters
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        atoms = [a for a in atoms if a.first_observed >= start_dt]
    
    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        atoms = [a for a in atoms if a.first_observed <= end_dt]
    
    # Sort by date (newest first)
    atoms.sort(key=lambda a: a.first_observed, reverse=True)
    
    # Limit results
    atoms = atoms[:limit]
    
    # Convert to results
    results = []
    for atom in atoms:
        stability = decay_engine.calculate_stability(atom)
        
        results.append(SearchResult(
            atom_id=atom.id,
            subject=atom.subject,
            predicate=atom.predicate,
            object=atom.object,
            atom_type=atom.atom_type.value,
            confidence=atom.confidence,
            graph=atom.graph.value,
            score=atom.confidence,
            stability=stability
        ))
    
    return results
