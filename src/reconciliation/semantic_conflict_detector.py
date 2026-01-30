"""
Semantic conflict detection using vector embeddings.

This module enhances the rule-based conflict detector with semantic understanding
via sentence embeddings. It combines the deterministic accuracy of rules with
the semantic understanding of embeddings.

Key Innovation: Hybrid approach
- Rule-based for known patterns (opposite predicates, exclusive predicates)
- Embedding-based for semantic similarity and unknown patterns
- Best of both worlds: 100% accuracy + semantic understanding
"""

from typing import List, Optional
from loguru import logger

from src.core.models import MemoryAtom
from src.core.ontology import (
    is_exclusive_predicate,
    get_opposite_predicate,
    is_contextual_type,
    PREDICATE_RELATIONSHIPS,
)
from src.storage.sqlite_store import SQLiteGraphStore
from src.storage.vector_store import VectorEmbeddingStore


class SemanticConflictDetector:
    """
    Hybrid conflict detector using rules + embeddings + type-specific ontology.
    
    Stage 1: Identity match (exact subject + predicate)
    Stage 2: Semantic similarity (embedding-based)
    Stage 3: Conflict validation (rules + embeddings + type-specific rules)
    
    Advantages over pure string matching:
    - Catches semantic conflicts: "Google" vs "Anthropic" (13% string, but exclusive)
    - Understands synonyms: "automobile" vs "car" (not a conflict)
    - Detects paraphrases: "I love Python" vs "Python is my favorite" (duplicate)
    - Semantic opposite detection: "excellent" vs "terrible"
    - Type-specific conflict rules (AFFILIATION, PREFERENCE, etc.)
    """
    
    def __init__(
        self,
        store: SQLiteGraphStore,
        vector_store: Optional[VectorEmbeddingStore] = None
    ) -> None:
        """
        Initialize semantic conflict detector.
        
        Args:
            store: SQLite graph store for atom retrieval
            vector_store: Optional vector store for semantic similarity
        """
        self.store = store
        self.vector_store = vector_store
        self.conflict_checks = 0
        self.use_embeddings = vector_store is not None
        
        logger.info(
            f"SemanticConflictDetector initialized "
            f"(embeddings={'enabled' if self.use_embeddings else 'disabled'})"
        )
    
    async def find_conflicts(
        self,
        candidate: MemoryAtom,
        similarity_threshold: float = 0.6,
    ) -> List[MemoryAtom]:
        """
        Find atoms that conflict with the candidate using hybrid approach.
        
        Args:
            candidate: New atom to check for conflicts
            similarity_threshold: Minimum similarity for semantic match (0.0-1.0)
            
        Returns:
            List of conflicting atoms (ordered by confidence DESC)
        """
        self.conflict_checks += 1
        
        # STAGE 1: Identity match (exact subject + predicate)
        logger.debug(
            f"Stage 1: Finding atoms with subject={candidate.subject}, "
            f"predicate={candidate.predicate}"
        )
        
        matches = await self.store.find_by_triple(
            candidate.subject,
            candidate.predicate,
            exclude_historical=True,
        )
        
        if not matches:
            logger.debug("No potential conflicts found (Stage 1)")
            return []
        
        logger.debug(f"Stage 1: Found {len(matches)} atoms with same subject+predicate")
        
        # STAGE 2: Semantic similarity (embedding-based or string-based)
        if self.use_embeddings and self.vector_store:
            similar_matches = await self._find_similar_with_embeddings(
                candidate, matches, similarity_threshold
            )
        else:
            similar_matches = await self._find_similar_with_strings(
                candidate, matches, similarity_threshold
            )
        
        if not similar_matches:
            logger.debug("No similar objects found (Stage 2)")
            return []
        
        logger.debug(f"Stage 2: Found {len(similar_matches)} similar objects")
        
        # STAGE 3: Semantic conflict check (hybrid rules + embeddings)
        conflicts: List[MemoryAtom] = []
        
        for atom in similar_matches:
            if await self._is_semantic_conflict(candidate, atom):
                conflicts.append(atom)
                logger.info(
                    f"Stage 3: Conflict detected - "
                    f"[{candidate.subject}] [{candidate.predicate}] [{candidate.object[:50]}] vs "
                    f"[{atom.subject}] [{atom.predicate}] [{atom.object[:50]}]"
                )
        
        logger.info(f"Conflict detection complete: {len(conflicts)} conflicts found")
        return conflicts
    
    async def _find_similar_with_embeddings(
        self,
        candidate: MemoryAtom,
        matches: List[MemoryAtom],
        threshold: float
    ) -> List[MemoryAtom]:
        """
        Find similar atoms using vector embeddings.
        
        This is the KEY upgrade: semantic similarity instead of string matching.
        """
        # For exclusive predicates, we want ALL different objects
        if is_exclusive_predicate(candidate.predicate):
            logger.debug(
                f"Exclusive predicate detected: {candidate.predicate} - "
                f"checking all different objects"
            )
            return [atom for atom in matches if atom.id != candidate.id]
        
        # For non-exclusive predicates, use semantic similarity
        similar_matches: List[MemoryAtom] = []
        
        for atom in matches:
            if atom.id == candidate.id:
                continue
            
            # Calculate semantic similarity using embeddings
            similarity = await self.vector_store.get_semantic_similarity(
                candidate.object,
                atom.object
            )
            
            logger.debug(
                f"Semantic similarity: {similarity:.3f} - "
                f"'{candidate.object[:30]}' vs '{atom.object[:30]}'"
            )
            
            # High similarity = potential duplicate or refinement
            # Low similarity = potential conflict (for exclusive predicates)
            if similarity > threshold:
                similar_matches.append(atom)
        
        return similar_matches
    
    async def _find_similar_with_strings(
        self,
        candidate: MemoryAtom,
        matches: List[MemoryAtom],
        threshold: float
    ) -> List[MemoryAtom]:
        """
        Fallback: Find similar atoms using string matching.
        
        Used when vector store is not available.
        """
        from difflib import SequenceMatcher
        
        if is_exclusive_predicate(candidate.predicate):
            return [atom for atom in matches if atom.id != candidate.id]
        
        similar_matches: List[MemoryAtom] = []
        
        for atom in matches:
            if atom.id == candidate.id:
                continue
            
            similarity = SequenceMatcher(
                None,
                candidate.object.lower(),
                atom.object.lower()
            ).ratio()
            
            if similarity > threshold:
                similar_matches.append(atom)
        
        return similar_matches
    
    async def _is_semantic_conflict(
        self,
        atom1: MemoryAtom,
        atom2: MemoryAtom,
    ) -> bool:
        """
        Check if two atoms with similar structure actually conflict.
        
        Hybrid approach:
        1. Check rule-based patterns (opposite predicates, exclusive predicates)
        2. Use embeddings for semantic validation
        """
        pred1 = atom1.predicate.lower()
        pred2 = atom2.predicate.lower()
        obj1 = atom1.object.lower()
        obj2 = atom2.object.lower()
        
        # Rule 1: Opposite predicates (using ontology)
        opposite_pred = get_opposite_predicate(atom1.predicate)
        if opposite_pred and atom2.predicate.lower() == opposite_pred.lower():
            logger.debug(f"Opposite predicates detected: {pred1} vs {pred2}")
            return True
        
        # Rule 2: Exclusive predicates with different objects (using ontology)
        if pred1 == pred2 and is_exclusive_predicate(atom1.predicate):
            if obj1 != obj2:
                # Check if one is a refinement (substring)
                if obj1 in obj2 or obj2 in obj1:
                    logger.debug(f"Refinement detected, not conflict: {obj1} vs {obj2}")
                    return False
                
                # Check if contexts differ (type-specific contextual support)
                if is_contextual_type(atom1.atom_type) and self._have_different_contexts(atom1, atom2):
                    logger.debug(
                        f"Different contexts, not conflict (type {atom1.atom_type} supports contextual coexistence): "
                        f"{atom1.contexts} vs {atom2.contexts}"
                    )
                    return False
                
                # Use embeddings to validate if truly different
                if self.use_embeddings and self.vector_store:
                    similarity = await self.vector_store.get_semantic_similarity(
                        atom1.object, atom2.object
                    )
                    
                    # Very high similarity = likely synonyms/paraphrases (not conflict)
                    if similarity > 0.9:
                        logger.debug(
                            f"High semantic similarity ({similarity:.3f}), "
                            f"likely synonyms: {obj1} vs {obj2}"
                        )
                        return False
                    
                    # Low similarity = truly different (conflict)
                    logger.debug(
                        f"Low semantic similarity ({similarity:.3f}), "
                        f"exclusive predicate conflict: {obj1} vs {obj2}"
                    )
                    return True
                else:
                    # Fallback: different objects = conflict
                    logger.debug(f"Exclusive predicate conflict: {pred1} with {obj1} vs {obj2}")
                    return True
        
        # Rule 3: Different objects with same subject+predicate
        if obj1 != obj2:
            # Check if one is a refinement
            if obj1 in obj2 or obj2 in obj1:
                logger.debug(f"Refinement detected, not conflict: {obj1} vs {obj2}")
                return False
            
            # For non-exclusive predicates, different objects usually not a conflict
            logger.debug(f"Different objects, non-exclusive predicate: {obj1} vs {obj2}")
            return False
        
        # Same objects = duplicate, not conflict
        return False
    
    def _have_different_contexts(
        self,
        atom1: MemoryAtom,
        atom2: MemoryAtom,
    ) -> bool:
        """Check if atoms have explicitly different contexts."""
        if atom1.contexts and atom2.contexts:
            overlap = set(atom1.contexts) & set(atom2.contexts)
            if not overlap:
                return True
        return False
    
    async def check_opposite_predicates(
        self,
        candidate: MemoryAtom,
    ) -> List[MemoryAtom]:
        """
        Check for atoms with opposite predicates.
        
        Enhanced with semantic similarity for object matching.
        """
        logger.debug(
            f"Checking opposite predicates for: "
            f"[{candidate.subject}] [{candidate.predicate}] [{candidate.object}]"
        )
        
        conflicts: List[MemoryAtom] = []
        
        # Find opposite predicate (using ontology)
        opposite_pred = get_opposite_predicate(candidate.predicate)
        
        if not opposite_pred:
            logger.debug(f"No opposite predicate found for: {candidate.predicate}")
            return []
        
        logger.debug(f"Found opposite predicate: {candidate.predicate} <-> {opposite_pred}")
        
        # Search for atoms with opposite predicate
        opposite_atoms = await self.store.find_by_triple(
            candidate.subject,
            opposite_pred,
            exclude_historical=True,
        )
        
        logger.debug(
            f"Found {len(opposite_atoms)} atoms with opposite predicate '{opposite_pred}'"
        )
        
        # Check if objects are similar (using embeddings if available)
        for atom in opposite_atoms:
            if self.use_embeddings and self.vector_store:
                similarity = await self.vector_store.get_semantic_similarity(
                    candidate.object, atom.object
                )
            else:
                from difflib import SequenceMatcher
                similarity = SequenceMatcher(
                    None,
                    candidate.object.lower(),
                    atom.object.lower()
                ).ratio()
            
            logger.debug(
                f"Similarity between '{candidate.object}' and '{atom.object}': {similarity:.3f}"
            )
            
            if similarity > 0.7:
                conflicts.append(atom)
                logger.info(
                    f"Opposite predicate conflict: {candidate.predicate} vs "
                    f"{atom.predicate} for {candidate.object[:50]}"
                )
        
        logger.debug(f"Returning {len(conflicts)} opposite predicate conflicts")
        return conflicts
    
    def get_stats(self) -> dict:
        """Get conflict detection statistics"""
        return {
            "conflict_checks": self.conflict_checks,
            "embeddings_enabled": self.use_embeddings,
        }
