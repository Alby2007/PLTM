"""Background worker for automated decay processing"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from src.core.decay import DecayEngine
from src.core.retrieval import MemoryRetriever
from src.storage.sqlite_store import SQLiteGraphStore


class DecayWorker:
    """
    Background worker for Deep Lane decay processing.
    
    Responsibilities:
    - Dissolve forgotten unsubstantiated atoms
    - Reconsolidate weak substantiated atoms
    - Track decay statistics
    - Run on schedule or idle triggers
    
    Triggers:
    - Scheduled: Every N hours (configurable)
    - Idle: After N minutes of user inactivity
    - Manual: On-demand via API
    """
    
    def __init__(
        self,
        store: SQLiteGraphStore,
        decay_engine: Optional[DecayEngine] = None,
        retriever: Optional[MemoryRetriever] = None
    ):
        """
        Initialize decay worker.
        
        Args:
            store: Graph store for atom persistence
            decay_engine: Optional decay engine (creates new if None)
            retriever: Optional retriever (creates new if None)
        """
        self.store = store
        self.decay_engine = decay_engine or DecayEngine()
        self.retriever = retriever or MemoryRetriever(store, self.decay_engine)
        
        self.runs = 0
        self.last_run: Optional[datetime] = None
        
        logger.info("DecayWorker initialized")
    
    async def process_decay(
        self,
        user_id: Optional[str] = None,
        dissolve_threshold: float = 0.1,
        reconsolidate_threshold: float = 0.5
    ) -> dict:
        """
        Execute decay processing for user(s).
        
        Args:
            user_id: Optional user filter (if None, process all users)
            dissolve_threshold: Stability threshold for dissolution
            reconsolidate_threshold: Stability threshold for reconsolidation
            
        Returns:
            Dict with processing statistics
        """
        self.runs += 1
        self.last_run = datetime.now()
        
        logger.info(
            f"Starting decay processing (run #{self.runs})"
            + (f" for user {user_id}" if user_id else " for all users")
        )
        
        stats = {
            "run_number": self.runs,
            "timestamp": self.last_run.isoformat(),
            "user_id": user_id,
            "atoms_dissolved": 0,
            "atoms_reconsolidated": 0,
            "processing_time_ms": 0,
        }
        
        start_time = datetime.now()
        
        try:
            # Step 1: Dissolve forgotten atoms
            dissolved = await self.retriever.dissolve_forgotten_atoms(user_id)
            stats["atoms_dissolved"] = dissolved
            
            # Step 2: Reconsolidate weak memories (if user specified)
            if user_id:
                reconsolidated = await self.retriever.reconsolidate_weak_memories(
                    user_id,
                    threshold=reconsolidate_threshold
                )
                stats["atoms_reconsolidated"] = reconsolidated
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            stats["processing_time_ms"] = processing_time
            
            logger.info(
                f"Decay processing complete: "
                f"dissolved={dissolved}, reconsolidated={stats['atoms_reconsolidated']}, "
                f"time={processing_time:.0f}ms"
            )
            
        except Exception as e:
            logger.error(f"Error during decay processing: {e}")
            stats["error"] = str(e)
        
        return stats
    
    async def process_all_users(
        self,
        dissolve_threshold: float = 0.1
    ) -> dict:
        """
        Process decay for all users in system.
        
        Args:
            dissolve_threshold: Stability threshold for dissolution
            
        Returns:
            Dict with aggregate statistics
        """
        logger.info("Processing decay for all users")
        
        # Get all unique user IDs
        all_atoms = await self.store.get_all_atoms()
        user_ids = set(atom.subject for atom in all_atoms)
        
        aggregate_stats = {
            "total_users": len(user_ids),
            "total_dissolved": 0,
            "total_reconsolidated": 0,
            "users_processed": 0,
            "errors": [],
        }
        
        for user_id in user_ids:
            try:
                stats = await self.process_decay(
                    user_id=user_id,
                    dissolve_threshold=dissolve_threshold
                )
                
                aggregate_stats["total_dissolved"] += stats["atoms_dissolved"]
                aggregate_stats["total_reconsolidated"] += stats["atoms_reconsolidated"]
                aggregate_stats["users_processed"] += 1
                
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {e}")
                aggregate_stats["errors"].append({
                    "user_id": user_id,
                    "error": str(e)
                })
        
        logger.info(
            f"Processed {aggregate_stats['users_processed']} users: "
            f"dissolved={aggregate_stats['total_dissolved']}, "
            f"reconsolidated={aggregate_stats['total_reconsolidated']}"
        )
        
        return aggregate_stats
    
    async def get_decay_report(
        self,
        user_id: Optional[str] = None
    ) -> dict:
        """
        Generate decay status report without making changes.
        
        Args:
            user_id: Optional user filter
            
        Returns:
            Dict with decay statistics
        """
        if user_id:
            atoms = await self.store.get_all_atoms(subject=user_id)
        else:
            atoms = await self.store.get_all_atoms()
        
        report = {
            "total_atoms": len(atoms),
            "by_graph": {},
            "by_type": {},
            "stability_distribution": {
                "0.0-0.1": 0,
                "0.1-0.3": 0,
                "0.3-0.5": 0,
                "0.5-0.7": 0,
                "0.7-0.9": 0,
                "0.9-1.0": 0,
            },
            "at_risk_count": 0,
            "weak_memory_count": 0,
        }
        
        for atom in atoms:
            # Count by graph
            graph_type = atom.graph.value
            report["by_graph"][graph_type] = report["by_graph"].get(graph_type, 0) + 1
            
            # Count by type
            atom_type = atom.atom_type.value
            report["by_type"][atom_type] = report["by_type"].get(atom_type, 0) + 1
            
            # Calculate stability
            stability = self.decay_engine.calculate_stability(atom)
            
            # Stability distribution
            if stability < 0.1:
                report["stability_distribution"]["0.0-0.1"] += 1
                report["at_risk_count"] += 1
            elif stability < 0.3:
                report["stability_distribution"]["0.1-0.3"] += 1
                report["at_risk_count"] += 1
            elif stability < 0.5:
                report["stability_distribution"]["0.3-0.5"] += 1
                report["weak_memory_count"] += 1
            elif stability < 0.7:
                report["stability_distribution"]["0.5-0.7"] += 1
            elif stability < 0.9:
                report["stability_distribution"]["0.7-0.9"] += 1
            else:
                report["stability_distribution"]["0.9-1.0"] += 1
        
        return report
    
    def get_stats(self) -> dict:
        """Get worker statistics"""
        return {
            "runs": self.runs,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "decay_engine_stats": self.decay_engine.get_stats(),
            "retriever_stats": self.retriever.get_stats(),
        }


class IdleHeartbeat:
    """
    Triggers decay processing when user is idle.
    
    Monitors user activity and triggers decay processing after
    a period of inactivity.
    """
    
    def __init__(
        self,
        worker: DecayWorker,
        idle_threshold_minutes: int = 5
    ):
        """
        Initialize idle heartbeat monitor.
        
        Args:
            worker: Decay worker to trigger
            idle_threshold_minutes: Minutes of inactivity before trigger
        """
        self.worker = worker
        self.idle_threshold = timedelta(minutes=idle_threshold_minutes)
        self.last_activity: dict[str, datetime] = {}
        self.timers: dict[str, asyncio.Task] = {}
        
        logger.info(
            f"IdleHeartbeat initialized "
            f"(threshold: {idle_threshold_minutes} minutes)"
        )
    
    def on_activity(self, user_id: str) -> None:
        """
        Record user activity.
        
        Args:
            user_id: User who was active
        """
        self.last_activity[user_id] = datetime.now()
        
        # Cancel existing timer
        if user_id in self.timers:
            self.timers[user_id].cancel()
        
        # Start new timer
        timer = asyncio.create_task(self._wait_and_trigger(user_id))
        self.timers[user_id] = timer
    
    async def _wait_and_trigger(self, user_id: str) -> None:
        """
        Wait for idle threshold, then trigger decay processing.
        
        Args:
            user_id: User to process
        """
        await asyncio.sleep(self.idle_threshold.total_seconds())
        
        # Check if still idle
        if user_id in self.last_activity:
            elapsed = datetime.now() - self.last_activity[user_id]
            if elapsed >= self.idle_threshold:
                logger.info(
                    f"Idle detected for {user_id} "
                    f"({elapsed.total_seconds():.0f}s), triggering decay processing"
                )
                await self.worker.process_decay(user_id)


class ScheduledDecayProcessor:
    """
    Runs decay processing on a schedule.
    
    Simple scheduler for periodic decay processing.
    For production, use Celery or similar task queue.
    """
    
    def __init__(
        self,
        worker: DecayWorker,
        interval_hours: int = 6
    ):
        """
        Initialize scheduled processor.
        
        Args:
            worker: Decay worker to run
            interval_hours: Hours between runs
        """
        self.worker = worker
        self.interval = timedelta(hours=interval_hours)
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        logger.info(f"ScheduledDecayProcessor initialized (interval: {interval_hours}h)")
    
    async def start(self) -> None:
        """Start scheduled processing"""
        if self.running:
            logger.warning("Scheduled processor already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        logger.info("Scheduled decay processing started")
    
    async def stop(self) -> None:
        """Stop scheduled processing"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduled decay processing stopped")
    
    async def _run_loop(self) -> None:
        """Main processing loop"""
        while self.running:
            try:
                # Process all users
                await self.worker.process_all_users()
                
                # Wait for next interval
                await asyncio.sleep(self.interval.total_seconds())
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduled decay processing: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
