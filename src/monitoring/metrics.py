"""Prometheus metrics for LTM system monitoring"""

from prometheus_client import Counter, Gauge, Histogram, Summary
from typing import Optional
from datetime import datetime

# ============================================================================
# EXTRACTION METRICS
# ============================================================================

extraction_attempts = Counter(
    'lltm_extraction_attempts_total',
    'Total number of extraction attempts',
    ['extractor_type', 'user_id']
)

atoms_extracted = Counter(
    'lltm_atoms_extracted_total',
    'Total number of atoms extracted',
    ['atom_type', 'extractor_type']
)

extraction_duration = Histogram(
    'lltm_extraction_duration_seconds',
    'Time spent extracting atoms from messages',
    ['extractor_type'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# ============================================================================
# JURY METRICS
# ============================================================================

jury_deliberations = Counter(
    'lltm_jury_deliberations_total',
    'Total number of jury deliberations',
    ['verdict', 'judge']
)

jury_duration = Histogram(
    'lltm_jury_duration_seconds',
    'Time spent in jury deliberation',
    ['stage'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

jury_confidence_adjustment = Summary(
    'lltm_jury_confidence_adjustment',
    'Confidence adjustments made by jury'
)

# ============================================================================
# CONFLICT DETECTION METRICS
# ============================================================================

conflict_checks = Counter(
    'lltm_conflict_checks_total',
    'Total number of conflict checks performed',
    ['detector_type']
)

conflicts_found = Counter(
    'lltm_conflicts_found_total',
    'Total number of conflicts detected',
    ['conflict_type', 'atom_type']
)

conflict_detection_duration = Histogram(
    'lltm_conflict_detection_duration_seconds',
    'Time spent detecting conflicts',
    ['detector_type'],
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0]
)

semantic_similarity_score = Histogram(
    'lltm_semantic_similarity_score',
    'Distribution of semantic similarity scores',
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# ============================================================================
# RECONCILIATION METRICS
# ============================================================================

reconciliation_actions = Counter(
    'lltm_reconciliation_actions_total',
    'Total number of reconciliation actions',
    ['action_type', 'atom_type']
)

reconciliation_duration = Histogram(
    'lltm_reconciliation_duration_seconds',
    'Time spent reconciling conflicts',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
)

# ============================================================================
# STORAGE METRICS
# ============================================================================

atoms_stored = Counter(
    'lltm_atoms_stored_total',
    'Total number of atoms stored',
    ['graph_type', 'atom_type']
)

atoms_retrieved = Counter(
    'lltm_atoms_retrieved_total',
    'Total number of atoms retrieved',
    ['graph_type']
)

atoms_deleted = Counter(
    'lltm_atoms_deleted_total',
    'Total number of atoms deleted',
    ['reason']
)

storage_operation_duration = Histogram(
    'lltm_storage_operation_duration_seconds',
    'Time spent on storage operations',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# Current atom counts by graph
atoms_by_graph = Gauge(
    'lltm_atoms_by_graph',
    'Current number of atoms in each graph',
    ['graph_type', 'user_id']
)

atoms_by_type = Gauge(
    'lltm_atoms_by_type',
    'Current number of atoms by type',
    ['atom_type', 'user_id']
)

# ============================================================================
# VECTOR EMBEDDING METRICS
# ============================================================================

embeddings_generated = Counter(
    'lltm_embeddings_generated_total',
    'Total number of embeddings generated'
)

embedding_generation_duration = Histogram(
    'lltm_embedding_generation_duration_seconds',
    'Time spent generating embeddings',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5]
)

vector_similarity_searches = Counter(
    'lltm_vector_similarity_searches_total',
    'Total number of vector similarity searches'
)

vector_search_duration = Histogram(
    'lltm_vector_search_duration_seconds',
    'Time spent on vector similarity searches',
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# ============================================================================
# DECAY METRICS
# ============================================================================

stability_checks = Counter(
    'lltm_stability_checks_total',
    'Total number of stability checks',
    ['atom_type']
)

stability_score = Histogram(
    'lltm_stability_score',
    'Distribution of stability scores',
    ['atom_type'],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

reconsolidations = Counter(
    'lltm_reconsolidations_total',
    'Total number of memory reconsolidations',
    ['atom_type']
)

dissolutions = Counter(
    'lltm_dissolutions_total',
    'Total number of atom dissolutions',
    ['atom_type', 'reason']
)

decay_processing_duration = Histogram(
    'lltm_decay_processing_duration_seconds',
    'Time spent processing decay',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
)

# Current stability distribution
atoms_by_stability = Gauge(
    'lltm_atoms_by_stability',
    'Current number of atoms by stability range',
    ['stability_range', 'user_id']
)

weak_memories_count = Gauge(
    'lltm_weak_memories_count',
    'Current number of weak memories (stability < 0.5)',
    ['user_id']
)

at_risk_memories_count = Gauge(
    'lltm_at_risk_memories_count',
    'Current number of at-risk memories (near dissolution)',
    ['user_id']
)

# ============================================================================
# PIPELINE METRICS
# ============================================================================

pipeline_requests = Counter(
    'lltm_pipeline_requests_total',
    'Total number of pipeline requests',
    ['user_id', 'session_id']
)

pipeline_duration = Histogram(
    'lltm_pipeline_duration_seconds',
    'End-to-end pipeline processing time',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

pipeline_errors = Counter(
    'lltm_pipeline_errors_total',
    'Total number of pipeline errors',
    ['error_type', 'stage']
)

# ============================================================================
# API METRICS
# ============================================================================

api_requests = Counter(
    'lltm_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code']
)

api_request_duration = Histogram(
    'lltm_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

active_users = Gauge(
    'lltm_active_users',
    'Number of active users in the last hour'
)

# ============================================================================
# SYSTEM METRICS
# ============================================================================

system_info = Gauge(
    'lltm_system_info',
    'System information',
    ['version', 'environment']
)

uptime_seconds = Gauge(
    'lltm_uptime_seconds',
    'System uptime in seconds'
)


class MetricsCollector:
    """Helper class for collecting and updating metrics"""
    
    def __init__(self):
        self.start_time = datetime.now()
    
    def record_extraction(
        self,
        extractor_type: str,
        user_id: str,
        atom_count: int,
        atom_types: dict,
        duration: float
    ):
        """Record extraction metrics"""
        extraction_attempts.labels(
            extractor_type=extractor_type,
            user_id=user_id
        ).inc()
        
        for atom_type, count in atom_types.items():
            atoms_extracted.labels(
                atom_type=atom_type,
                extractor_type=extractor_type
            ).inc(count)
        
        extraction_duration.labels(
            extractor_type=extractor_type
        ).observe(duration)
    
    def record_conflict_check(
        self,
        detector_type: str,
        conflicts_found_count: int,
        conflict_types: dict,
        duration: float
    ):
        """Record conflict detection metrics"""
        conflict_checks.labels(
            detector_type=detector_type
        ).inc()
        
        for conflict_type, count in conflict_types.items():
            conflicts_found.labels(
                conflict_type=conflict_type,
                atom_type="unknown"
            ).inc(count)
        
        conflict_detection_duration.labels(
            detector_type=detector_type
        ).observe(duration)
    
    def record_stability_check(
        self,
        atom_type: str,
        stability: float
    ):
        """Record stability check metrics"""
        stability_checks.labels(
            atom_type=atom_type
        ).inc()
        
        stability_score.labels(
            atom_type=atom_type
        ).observe(stability)
    
    def record_reconsolidation(self, atom_type: str):
        """Record reconsolidation"""
        reconsolidations.labels(
            atom_type=atom_type
        ).inc()
    
    def record_dissolution(self, atom_type: str, reason: str):
        """Record dissolution"""
        dissolutions.labels(
            atom_type=atom_type,
            reason=reason
        ).inc()
    
    def update_atom_counts(
        self,
        user_id: str,
        by_graph: dict,
        by_type: dict,
        by_stability: dict
    ):
        """Update current atom count gauges"""
        for graph_type, count in by_graph.items():
            atoms_by_graph.labels(
                graph_type=graph_type,
                user_id=user_id
            ).set(count)
        
        for atom_type, count in by_type.items():
            atoms_by_type.labels(
                atom_type=atom_type,
                user_id=user_id
            ).set(count)
        
        for stability_range, count in by_stability.items():
            atoms_by_stability.labels(
                stability_range=stability_range,
                user_id=user_id
            ).set(count)
    
    def update_uptime(self):
        """Update system uptime"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        uptime_seconds.set(uptime)
    
    def get_stats(self) -> dict:
        """Get current metrics statistics"""
        return {
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "start_time": self.start_time.isoformat(),
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()
