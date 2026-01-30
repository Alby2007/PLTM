"""Memory retrieval with automatic reconsolidation"""

from typing import List, Optional, Tuple
from datetime import datetime
from loguru import logger

from src.core.models import MemoryAtom, GraphType
from src.core.decay import DecayEngine
from src.storage.sqlite_store import SQLiteGraphStore


class MemoryRetriever:
    """
    Retrieve atoms with automatic reconsolidation.
    
    Biological Inspiration:
    - Retrieving a memory strengthens it (reconsolidation)
    - Frequently accessed memories become more stable
    - Unused memories fade over time
    
    Features:
    - Automatic reconsolidation on retrieval
    - Stability-based filtering
    - Decay-aware sorting
    """
    
    def __init__(
        self,
        store: SQLiteGraphStore,
        decay_engine: Optional[DecayEngine] = None
    ):
        """
        Initialize memory retriever.
        
        Args:
            store: Graph store for atom persistence
            decay_engine: Optional decay engine for reconsolidation
        """
        self.store = store
        self.decay_engine = decay_engine or DecayEngine()
        self.retrievals = 0
        logger.info("MemoryRetriever initialized with automatic reconsolidation")
    
    async def get_atoms(
        self,
        user_id: str,
        reconsolidate: bool = True,
        min_stability: float = 0.0
    ) -> List[MemoryAtom]:
        """
        Retrieve atoms with optional reconsolidation.
        
        Args:
            user_id: User identifier
            reconsolidate: If True, strengthen retrieved memories
            min_stability: Minimum stability threshold (0.0-1.0)
            
        Returns:
            List of memory atoms
        """
        self.retrievals += 1
        
        # Get substantiated atoms
        atoms = await self.store.get_substantiated_atoms(subject=user_id)
        
        logger.debug(f"Retrieved {len(atoms)} substantiated atoms for {user_id}")
        
        # Filter by stability if threshold set
        if min_stability > 0.0:
            filtered_atoms = []
            for atom in atoms:
                stability = self.decay_engine.calculate_stability(atom)
                if stability >= min_stability:
                    filtered_atoms.append(atom)
            
            logger.debug(
                f"Filtered to {len(filtered_atoms)} atoms with stability >= {min_stability}"
            )
            atoms = filtered_atoms
        
        # Reconsolidate if requested
        if reconsolidate:
            for atom in atoms:
                self.decay_engine.reconsolidate(atom)
                await self.store.update_atom(atom)
            
            logger.debug(f"Reconsolidated {len(atoms)} atoms")
        
        return atoms
    
    async def get_with_stability(
        self,
        user_id: str,
        reconsolidate: bool = False
    ) -> List[Tuple[MemoryAtom, float]]:
        """
        Retrieve atoms with their current stability scores.
        
        Useful for:
        - Displaying memory strength to user
        - Identifying weak memories
        - Prioritizing reconsolidation
        
        Args:
            user_id: User identifier
            reconsolidate: If True, strengthen retrieved memories
            
        Returns:
            List of (atom, stability) tuples, sorted by stability (highest first)
        """
        atoms = await self.store.get_all_atoms(subject=user_id)
        
        results = []
        for atom in atoms:
            stability = self.decay_engine.calculate_stability(atom)
            results.append((atom, stability))
        
        # Sort by stability (highest first = strongest memories)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Reconsolidate if requested
        if reconsolidate:
            for atom, _ in results:
                self.decay_engine.reconsolidate(atom)
                await self.store.update_atom(atom)
        
        logger.debug(
            f"Retrieved {len(results)} atoms with stability scores for {user_id}"
        )
        
        return results
    
    async def get_weak_memories(
        self,
        user_id: str,
        threshold: float = 0.5
    ) -> List[Tuple[MemoryAtom, float]]:
        """
        Find memories that have decayed below threshold.
        
        Useful for:
        - Identifying memories needing reconsolidation
        - Prompting user to confirm weak memories
        - Scheduling background reconsolidation
        
        Args:
            user_id: User identifier
            threshold: Stability threshold (default: 0.5)
            
        Returns:
            List of (atom, stability) tuples for weak memories
        """
        atoms = await self.store.get_substantiated_atoms(subject=user_id)
        
        weak_memories = []
        for atom in atoms:
            stability = self.decay_engine.calculate_stability(atom)
            if stability < threshold:
                weak_memories.append((atom, stability))
        
        # Sort by stability (lowest first = weakest)
        weak_memories.sort(key=lambda x: x[1])
        
        logger.info(
            f"Found {len(weak_memories)} weak memories for {user_id} "
            f"(stability < {threshold})"
        )
        
        return weak_memories
    
    async def get_at_risk_memories(
        self,
        user_id: str,
        hours_until_dissolution: int = 24
    ) -> List[Tuple[MemoryAtom, float]]:
        """
        Find unsubstantiated memories at risk of dissolution.
        
        Args:
            user_id: User identifier
            hours_until_dissolution: Warning threshold in hours
            
        Returns:
            List of (atom, hours_remaining) tuples
        """
        atoms = await self.store.get_atoms_by_graph(
            GraphType.UNSUBSTANTIATED,
            subject=user_id
        )
        
        at_risk = []
        for atom in atoms:
            time_remaining = self.decay_engine.get_time_to_dissolution(atom)
            if time_remaining and time_remaining.total_seconds() / 3600 < hours_until_dissolution:
                hours_remaining = time_remaining.total_seconds() / 3600
                at_risk.append((atom, hours_remaining))
        
        # Sort by time remaining (least time first)
        at_risk.sort(key=lambda x: x[1])
        
        logger.warning(
            f"Found {len(at_risk)} memories at risk of dissolution for {user_id} "
            f"(< {hours_until_dissolution}h remaining)"
        )
        
        return at_risk
    
    async def dissolve_forgotten_atoms(
        self,
        user_id: Optional[str] = None
    ) -> int:
        """
        Delete atoms that have decayed below dissolution threshold.
        
        Args:
            user_id: Optional user filter (if None, process all users)
            
        Returns:
            Number of atoms dissolved
        """
        # Get unsubstantiated atoms
        if user_id:
            atoms = await self.store.get_atoms_by_graph(
                GraphType.UNSUBSTANTIATED,
                subject=user_id
            )
        else:
            atoms = await self.store.get_atoms_by_graph(
                GraphType.UNSUBSTANTIATED
            )
        
        dissolved_count = 0
        for atom in atoms:
            if self.decay_engine.should_dissolve(atom):
                await self.store.delete_atom(atom.id)
                dissolved_count += 1
                logger.debug(
                    f"Dissolved atom {atom.id} ({atom.atom_type.value}) "
                    f"due to decay"
                )
        
        logger.info(f"Dissolved {dissolved_count} forgotten atoms")
        return dissolved_count
    
    async def reconsolidate_weak_memories(
        self,
        user_id: str,
        threshold: float = 0.5,
        boost_factor: float = 1.5
    ) -> int:
        """
        Automatically reconsolidate weak substantiated memories.
        
        Args:
            user_id: User identifier
            threshold: Stability threshold
            boost_factor: Reconsolidation strength multiplier
            
        Returns:
            Number of atoms reconsolidated
        """
        weak_memories = await self.get_weak_memories(user_id, threshold)
        
        for atom, stability in weak_memories:
            self.decay_engine.reconsolidate(atom, boost_factor)
            await self.store.update_atom(atom)
        
        logger.info(
            f"Reconsolidated {len(weak_memories)} weak memories for {user_id}"
        )
        
        return len(weak_memories)
    
    def get_stats(self) -> dict:
        """Get retrieval statistics"""
        return {
            "retrievals": self.retrievals,
            "decay_stats": self.decay_engine.get_stats(),
        }
