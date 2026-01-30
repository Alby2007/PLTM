"""Celery tasks for decay processing"""

from typing import Optional
from loguru import logger

from src.workers.celery_app import celery_app
from src.core.decay import DecayEngine
from src.core.retrieval import MemoryRetriever
from src.storage.sqlite_store import SQLiteGraphStore
from src.storage.redis_cache import RedisCache, RedisConfig


@celery_app.task(name="src.workers.tasks.decay_tasks.process_decay_for_user")
def process_decay_for_user(
    user_id: str,
    dissolve_threshold: float = 0.1,
    reconsolidate_threshold: float = 0.5,
    tenant_id: str = "default"
) -> dict:
    """
    Process decay for a specific user.
    
    Args:
        user_id: User identifier
        dissolve_threshold: Stability threshold for dissolution
        reconsolidate_threshold: Stability threshold for reconsolidation
        tenant_id: Tenant identifier
        
    Returns:
        Dict with processing statistics
    """
    logger.info(f"Starting decay processing for user {user_id}")
    
    try:
        # Initialize components
        store = SQLiteGraphStore()
        decay_engine = DecayEngine()
        retriever = MemoryRetriever(store, decay_engine)
        
        # Dissolve forgotten atoms
        dissolved = 0
        # Note: In production, this would use Neo4j store
        # dissolved = await retriever.dissolve_forgotten_atoms(user_id)
        
        # Reconsolidate weak memories
        reconsolidated = 0
        # reconsolidated = await retriever.reconsolidate_weak_memories(
        #     user_id, threshold=reconsolidate_threshold
        # )
        
        stats = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "atoms_dissolved": dissolved,
            "atoms_reconsolidated": reconsolidated,
            "status": "success"
        }
        
        logger.info(
            f"Decay processing complete for {user_id}: "
            f"dissolved={dissolved}, reconsolidated={reconsolidated}"
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Error processing decay for {user_id}: {e}")
        return {
            "user_id": user_id,
            "status": "error",
            "error": str(e)
        }


@celery_app.task(name="src.workers.tasks.decay_tasks.process_decay_all_users")
def process_decay_all_users(
    dissolve_threshold: float = 0.1,
    tenant_id: str = "default"
) -> dict:
    """
    Process decay for all users in system.
    
    Args:
        dissolve_threshold: Stability threshold for dissolution
        tenant_id: Tenant identifier
        
    Returns:
        Dict with aggregate statistics
    """
    logger.info("Starting decay processing for all users")
    
    try:
        # Initialize components
        store = SQLiteGraphStore()
        
        # Get all unique user IDs
        # In production, this would query Neo4j
        all_atoms = store.get_all_atoms()
        user_ids = set(atom.subject for atom in all_atoms)
        
        aggregate_stats = {
            "total_users": len(user_ids),
            "total_dissolved": 0,
            "total_reconsolidated": 0,
            "users_processed": 0,
            "errors": []
        }
        
        # Process each user
        for user_id in user_ids:
            try:
                result = process_decay_for_user.apply(
                    args=[user_id, dissolve_threshold],
                    kwargs={"tenant_id": tenant_id}
                )
                
                if result.get("status") == "success":
                    aggregate_stats["total_dissolved"] += result.get("atoms_dissolved", 0)
                    aggregate_stats["total_reconsolidated"] += result.get("atoms_reconsolidated", 0)
                    aggregate_stats["users_processed"] += 1
                else:
                    aggregate_stats["errors"].append({
                        "user_id": user_id,
                        "error": result.get("error", "Unknown error")
                    })
                    
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
        
    except Exception as e:
        logger.error(f"Error in batch decay processing: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@celery_app.task(name="src.workers.tasks.decay_tasks.reconsolidate_weak_memories")
def reconsolidate_weak_memories(
    user_id: str,
    threshold: float = 0.5,
    boost_factor: float = 1.5,
    tenant_id: str = "default"
) -> dict:
    """
    Reconsolidate weak memories for a user.
    
    Args:
        user_id: User identifier
        threshold: Stability threshold
        boost_factor: Reconsolidation strength multiplier
        tenant_id: Tenant identifier
        
    Returns:
        Dict with reconsolidation statistics
    """
    logger.info(f"Reconsolidating weak memories for user {user_id}")
    
    try:
        store = SQLiteGraphStore()
        decay_engine = DecayEngine()
        retriever = MemoryRetriever(store, decay_engine)
        
        # Reconsolidate weak memories
        # In production: await retriever.reconsolidate_weak_memories(...)
        reconsolidated = 0
        
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "atoms_reconsolidated": reconsolidated,
            "threshold": threshold,
            "boost_factor": boost_factor,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error reconsolidating for {user_id}: {e}")
        return {
            "user_id": user_id,
            "status": "error",
            "error": str(e)
        }


@celery_app.task(name="src.workers.tasks.decay_tasks.get_decay_report")
def get_decay_report(
    user_id: Optional[str] = None,
    tenant_id: str = "default"
) -> dict:
    """
    Generate decay status report.
    
    Args:
        user_id: Optional user filter
        tenant_id: Tenant identifier
        
    Returns:
        Dict with decay statistics
    """
    logger.info(f"Generating decay report for user {user_id or 'all'}")
    
    try:
        store = SQLiteGraphStore()
        decay_engine = DecayEngine()
        
        if user_id:
            atoms = store.get_all_atoms(subject=user_id)
        else:
            atoms = store.get_all_atoms()
        
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
            stability = decay_engine.calculate_stability(atom)
            
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
        
    except Exception as e:
        logger.error(f"Error generating decay report: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
