"""Bulk operations API routes"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from loguru import logger
import json
import io

from src.core.models import MemoryAtom, AtomType, Provenance, GraphType
from src.api.auth_routes import get_current_user, UserInfo, require_scope
from src.storage.sqlite_store import SQLiteGraphStore
from src.core.decay import DecayEngine

# Create router
router = APIRouter(prefix="/api/v1/bulk", tags=["bulk"])

# Initialize components
store = SQLiteGraphStore()
decay_engine = DecayEngine()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class BulkAtomData(BaseModel):
    """Bulk atom data"""
    subject: str
    predicate: str
    object: str
    atom_type: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.9)
    contexts: List[str] = []


class BulkImportRequest(BaseModel):
    """Bulk import request"""
    atoms: List[BulkAtomData]
    validate: bool = True
    skip_duplicates: bool = True


class BulkImportResponse(BaseModel):
    """Bulk import response"""
    total_atoms: int
    imported: int
    skipped: int
    failed: int
    errors: List[dict] = []
    processing_time_ms: float


class BulkExportRequest(BaseModel):
    """Bulk export request"""
    format: str = Field("json", description="json or csv")
    filters: Optional[dict] = None


class BulkDeleteRequest(BaseModel):
    """Bulk delete request"""
    atom_ids: List[str]


class BulkUpdateRequest(BaseModel):
    """Bulk update request"""
    atom_ids: List[str]
    updates: dict


# ============================================================================
# BULK IMPORT
# ============================================================================

@router.post("/{user_id}/import", response_model=BulkImportResponse)
async def bulk_import(
    user_id: str,
    request: BulkImportRequest,
    current_user: UserInfo = Depends(require_scope("write"))
):
    """
    Bulk import memory atoms.
    
    Args:
        user_id: User identifier
        request: Bulk import data
        current_user: Authenticated user
        
    Returns:
        Import results
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    start_time = datetime.utcnow()
    
    imported = 0
    skipped = 0
    failed = 0
    errors = []
    
    # Get existing atoms for duplicate detection
    existing_atoms = await store.get_all_atoms(subject=user_id)
    existing_triples = {
        (a.subject, a.predicate, a.object) for a in existing_atoms
    }
    
    for idx, atom_data in enumerate(request.atoms):
        try:
            # Check for duplicates
            triple = (atom_data.subject, atom_data.predicate, atom_data.object)
            if request.skip_duplicates and triple in existing_triples:
                skipped += 1
                continue
            
            # Validate atom type
            if request.validate:
                try:
                    AtomType(atom_data.atom_type)
                except ValueError:
                    errors.append({
                        "index": idx,
                        "error": f"Invalid atom type: {atom_data.atom_type}"
                    })
                    failed += 1
                    continue
            
            # Create atom
            atom = MemoryAtom(
                id=f"atom_{datetime.utcnow().timestamp()}_{idx}",
                subject=atom_data.subject,
                predicate=atom_data.predicate,
                object=atom_data.object,
                atom_type=AtomType(atom_data.atom_type),
                provenance=Provenance.USER_STATED,
                confidence=atom_data.confidence,
                graph=GraphType.UNSUBSTANTIATED,
                contexts=atom_data.contexts
            )
            
            # Insert atom
            await store.insert_atom(atom)
            imported += 1
            
        except Exception as e:
            errors.append({
                "index": idx,
                "error": str(e)
            })
            failed += 1
    
    processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    logger.info(
        f"Bulk import for {user_id}: "
        f"imported={imported}, skipped={skipped}, failed={failed}"
    )
    
    return BulkImportResponse(
        total_atoms=len(request.atoms),
        imported=imported,
        skipped=skipped,
        failed=failed,
        errors=errors,
        processing_time_ms=processing_time
    )


@router.post("/{user_id}/import-file")
async def bulk_import_file(
    user_id: str,
    file: UploadFile = File(...),
    validate: bool = True,
    skip_duplicates: bool = True,
    current_user: UserInfo = Depends(require_scope("write"))
):
    """
    Bulk import from JSON file.
    
    Args:
        user_id: User identifier
        file: JSON file with atoms
        validate: Validate atoms before import
        skip_duplicates: Skip duplicate atoms
        current_user: Authenticated user
        
    Returns:
        Import results
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Read file
    content = await file.read()
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON file"
        )
    
    # Parse atoms
    atoms = []
    for item in data:
        atoms.append(BulkAtomData(**item))
    
    # Import atoms
    request = BulkImportRequest(
        atoms=atoms,
        validate=validate,
        skip_duplicates=skip_duplicates
    )
    
    return await bulk_import(user_id, request, current_user)


# ============================================================================
# BULK EXPORT
# ============================================================================

@router.get("/{user_id}/export")
async def bulk_export(
    user_id: str,
    format: str = "json",
    atom_type: Optional[str] = None,
    graph: Optional[str] = None,
    min_confidence: Optional[float] = None,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Bulk export memory atoms.
    
    Args:
        user_id: User identifier
        format: Export format (json or csv)
        atom_type: Optional atom type filter
        graph: Optional graph filter
        min_confidence: Minimum confidence threshold
        current_user: Authenticated user
        
    Returns:
        File download
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get atoms
    atoms = await store.get_all_atoms(subject=user_id)
    
    # Apply filters
    if atom_type:
        atoms = [a for a in atoms if a.atom_type.value == atom_type]
    
    if graph:
        atoms = [a for a in atoms if a.graph.value == graph]
    
    if min_confidence:
        atoms = [a for a in atoms if a.confidence >= min_confidence]
    
    # Export based on format
    if format == "json":
        # JSON export
        data = []
        for atom in atoms:
            data.append({
                "id": atom.id,
                "subject": atom.subject,
                "predicate": atom.predicate,
                "object": atom.object,
                "atom_type": atom.atom_type.value,
                "provenance": atom.provenance.value,
                "confidence": atom.confidence,
                "graph": atom.graph.value,
                "first_observed": atom.first_observed.isoformat(),
                "last_accessed": atom.last_accessed.isoformat(),
                "assertion_count": atom.assertion_count,
                "contexts": atom.contexts or [],
                "stability": decay_engine.calculate_stability(atom)
            })
        
        json_str = json.dumps(data, indent=2)
        
        return StreamingResponse(
            io.BytesIO(json_str.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=memory_export_{user_id}.json"
            }
        )
    
    elif format == "csv":
        # CSV export
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "id", "subject", "predicate", "object", "atom_type",
            "confidence", "graph", "first_observed", "stability"
        ])
        
        # Data
        for atom in atoms:
            writer.writerow([
                atom.id,
                atom.subject,
                atom.predicate,
                atom.object,
                atom.atom_type.value,
                atom.confidence,
                atom.graph.value,
                atom.first_observed.isoformat(),
                decay_engine.calculate_stability(atom)
            ])
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=memory_export_{user_id}.csv"
            }
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Use 'json' or 'csv'"
        )


# ============================================================================
# BULK UPDATE
# ============================================================================

@router.put("/{user_id}/update", dependencies=[Depends(require_scope("write"))])
async def bulk_update(
    user_id: str,
    request: BulkUpdateRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Bulk update memory atoms.
    
    Args:
        user_id: User identifier
        request: Bulk update data
        current_user: Authenticated user
        
    Returns:
        Update results
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    updated = 0
    failed = 0
    errors = []
    
    for atom_id in request.atom_ids:
        try:
            # Get atom
            atom = await store.get_atom(atom_id)
            
            if not atom or atom.subject != user_id:
                errors.append({
                    "atom_id": atom_id,
                    "error": "Atom not found"
                })
                failed += 1
                continue
            
            # Apply updates
            if "confidence" in request.updates:
                atom.confidence = request.updates["confidence"]
            
            if "contexts" in request.updates:
                atom.contexts = request.updates["contexts"]
            
            if "graph" in request.updates:
                atom.graph = GraphType(request.updates["graph"])
            
            # Save changes
            await store.update_atom(atom)
            updated += 1
            
        except Exception as e:
            errors.append({
                "atom_id": atom_id,
                "error": str(e)
            })
            failed += 1
    
    logger.info(f"Bulk update for {user_id}: updated={updated}, failed={failed}")
    
    return {
        "total_atoms": len(request.atom_ids),
        "updated": updated,
        "failed": failed,
        "errors": errors
    }


# ============================================================================
# BULK DELETE
# ============================================================================

@router.delete("/{user_id}/delete", dependencies=[Depends(require_scope("write"))])
async def bulk_delete(
    user_id: str,
    request: BulkDeleteRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Bulk delete memory atoms.
    
    Args:
        user_id: User identifier
        request: Bulk delete data
        current_user: Authenticated user
        
    Returns:
        Delete results
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    deleted = 0
    failed = 0
    errors = []
    
    for atom_id in request.atom_ids:
        try:
            # Get atom
            atom = await store.get_atom(atom_id)
            
            if not atom or atom.subject != user_id:
                errors.append({
                    "atom_id": atom_id,
                    "error": "Atom not found"
                })
                failed += 1
                continue
            
            # Delete atom
            await store.delete_atom(atom_id)
            deleted += 1
            
        except Exception as e:
            errors.append({
                "atom_id": atom_id,
                "error": str(e)
            })
            failed += 1
    
    logger.info(f"Bulk delete for {user_id}: deleted={deleted}, failed={failed}")
    
    return {
        "total_atoms": len(request.atom_ids),
        "deleted": deleted,
        "failed": failed,
        "errors": errors
    }


# ============================================================================
# BULK RECONSOLIDATION
# ============================================================================

@router.post("/{user_id}/reconsolidate", dependencies=[Depends(require_scope("write"))])
async def bulk_reconsolidate(
    user_id: str,
    atom_ids: Optional[List[str]] = None,
    threshold: float = 0.5,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Bulk reconsolidate memory atoms.
    
    Args:
        user_id: User identifier
        atom_ids: Optional list of atom IDs (if None, reconsolidate all weak memories)
        threshold: Stability threshold
        current_user: Authenticated user
        
    Returns:
        Reconsolidation results
    """
    # Verify access
    if current_user.user_id != user_id and "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    reconsolidated = 0
    
    if atom_ids:
        # Reconsolidate specific atoms
        for atom_id in atom_ids:
            atom = await store.get_atom(atom_id)
            
            if atom and atom.subject == user_id:
                decay_engine.reconsolidate(atom)
                await store.update_atom(atom)
                reconsolidated += 1
    else:
        # Reconsolidate all weak memories
        atoms = await store.get_substantiated_atoms(subject=user_id)
        
        for atom in atoms:
            stability = decay_engine.calculate_stability(atom)
            if stability < threshold:
                decay_engine.reconsolidate(atom)
                await store.update_atom(atom)
                reconsolidated += 1
    
    logger.info(f"Bulk reconsolidation for {user_id}: reconsolidated={reconsolidated}")
    
    return {
        "reconsolidated": reconsolidated,
        "threshold": threshold
    }
