"""
MetaJudge: Judge Quality Monitoring System

This is NOT a deliberation judge - it's an observability layer that:
1. Tracks judge accuracy over time
2. Monitors judge performance metrics
3. Provides insights for system improvement

Does not participate in conflict resolution decisions.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from loguru import logger
from prometheus_client import Counter, Histogram, Gauge

from src.core.models import JudgeVerdict


# Prometheus Metrics
judge_evaluations_total = Counter(
    'judge_evaluations_total',
    'Total number of evaluations by judge',
    ['judge_name', 'verdict']
)

judge_accuracy = Gauge(
    'judge_accuracy',
    'Historical accuracy of judge verdicts',
    ['judge_name']
)

judge_latency_seconds = Histogram(
    'judge_latency_seconds',
    'Time taken for judge evaluation',
    ['judge_name'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

judge_confidence = Histogram(
    'judge_confidence',
    'Confidence scores from judge verdicts',
    ['judge_name'],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

judge_conflict_detection_rate = Gauge(
    'judge_conflict_detection_rate',
    'Rate at which judge detects conflicts',
    ['judge_name']
)


class MetaJudge:
    """
    Monitors and tracks judge quality over time.
    
    This is an observability layer, NOT a deliberation judge.
    It does not participate in conflict resolution - only monitors it.
    
    Features:
    - Track judge accuracy against ground truth
    - Monitor judge performance metrics
    - Identify which judges catch most issues
    - Compare judge latency
    - Provide insights for system improvement
    """
    
    def __init__(self):
        self.judge_stats: Dict[str, Dict] = defaultdict(lambda: {
            'total_evaluations': 0,
            'correct_verdicts': 0,
            'conflicts_detected': 0,
            'total_latency': 0.0,
            'confidence_scores': [],
            'verdict_history': [],
        })
        logger.info("MetaJudge initialized (observability layer)")
    
    def track_evaluation(
        self,
        judge_name: str,
        verdict: JudgeVerdict,
        confidence: float,
        latency_seconds: float,
        ground_truth: Optional[JudgeVerdict] = None,
    ) -> None:
        """
        Track a judge evaluation.
        
        Args:
            judge_name: Name of the judge
            verdict: Verdict given by judge
            confidence: Confidence score (0.0-1.0)
            latency_seconds: Time taken for evaluation
            ground_truth: Optional ground truth verdict for accuracy tracking
        """
        stats = self.judge_stats[judge_name]
        
        # Update counters
        stats['total_evaluations'] += 1
        stats['total_latency'] += latency_seconds
        stats['confidence_scores'].append(confidence)
        stats['verdict_history'].append({
            'verdict': verdict,
            'confidence': confidence,
            'timestamp': datetime.utcnow(),
            'ground_truth': ground_truth,
        })
        
        # Track conflicts detected
        if verdict == JudgeVerdict.REJECT:
            stats['conflicts_detected'] += 1
        
        # Track accuracy if ground truth provided
        if ground_truth is not None:
            if verdict == ground_truth:
                stats['correct_verdicts'] += 1
        
        # Update Prometheus metrics
        judge_evaluations_total.labels(
            judge_name=judge_name,
            verdict=verdict.value
        ).inc()
        
        judge_latency_seconds.labels(judge_name=judge_name).observe(latency_seconds)
        judge_confidence.labels(judge_name=judge_name).observe(confidence)
        
        # Update accuracy gauge if we have ground truth
        if ground_truth is not None and stats['total_evaluations'] > 0:
            accuracy = stats['correct_verdicts'] / stats['total_evaluations']
            judge_accuracy.labels(judge_name=judge_name).set(accuracy)
        
        # Update conflict detection rate
        if stats['total_evaluations'] > 0:
            detection_rate = stats['conflicts_detected'] / stats['total_evaluations']
            judge_conflict_detection_rate.labels(judge_name=judge_name).set(detection_rate)
        
        logger.debug(
            f"MetaJudge tracked: {judge_name} -> {verdict.value} "
            f"(confidence: {confidence:.2f}, latency: {latency_seconds*1000:.1f}ms)"
        )
    
    def get_judge_accuracy(self, judge_name: str) -> float:
        """
        Get historical accuracy of a specific judge.
        
        Returns:
            Accuracy as a float (0.0-1.0), or 0.0 if no data
        """
        stats = self.judge_stats.get(judge_name)
        if not stats or stats['total_evaluations'] == 0:
            return 0.0
        
        # Only calculate accuracy if we have ground truth data
        evaluations_with_truth = sum(
            1 for entry in stats['verdict_history']
            if entry['ground_truth'] is not None
        )
        
        if evaluations_with_truth == 0:
            return 0.0
        
        return stats['correct_verdicts'] / evaluations_with_truth
    
    def get_judge_reliability(self, judge_name: str) -> Dict[str, float]:
        """
        Get comprehensive reliability metrics for a judge.
        
        Returns:
            Dict with accuracy, avg_confidence, avg_latency, conflict_detection_rate
        """
        stats = self.judge_stats.get(judge_name)
        if not stats or stats['total_evaluations'] == 0:
            return {
                'accuracy': 0.0,
                'avg_confidence': 0.0,
                'avg_latency_ms': 0.0,
                'conflict_detection_rate': 0.0,
                'total_evaluations': 0,
            }
        
        avg_confidence = (
            sum(stats['confidence_scores']) / len(stats['confidence_scores'])
            if stats['confidence_scores'] else 0.0
        )
        
        avg_latency_ms = (
            (stats['total_latency'] / stats['total_evaluations']) * 1000
            if stats['total_evaluations'] > 0 else 0.0
        )
        
        conflict_detection_rate = (
            stats['conflicts_detected'] / stats['total_evaluations']
            if stats['total_evaluations'] > 0 else 0.0
        )
        
        return {
            'accuracy': self.get_judge_accuracy(judge_name),
            'avg_confidence': avg_confidence,
            'avg_latency_ms': avg_latency_ms,
            'conflict_detection_rate': conflict_detection_rate,
            'total_evaluations': stats['total_evaluations'],
        }
    
    def get_all_judges_summary(self) -> List[Dict]:
        """
        Get summary of all judges for comparison.
        
        Returns:
            List of dicts with judge stats, sorted by accuracy
        """
        summaries = []
        
        for judge_name in self.judge_stats.keys():
            reliability = self.get_judge_reliability(judge_name)
            summaries.append({
                'judge_name': judge_name,
                **reliability
            })
        
        # Sort by accuracy (descending)
        summaries.sort(key=lambda x: x['accuracy'], reverse=True)
        
        return summaries
    
    def get_top_performers(self, metric: str = 'accuracy', limit: int = 3) -> List[str]:
        """
        Get top performing judges by a specific metric.
        
        Args:
            metric: One of 'accuracy', 'conflict_detection_rate', 'avg_confidence'
            limit: Number of top judges to return
        
        Returns:
            List of judge names
        """
        summaries = self.get_all_judges_summary()
        
        if metric not in ['accuracy', 'conflict_detection_rate', 'avg_confidence']:
            logger.warning(f"Invalid metric: {metric}, defaulting to accuracy")
            metric = 'accuracy'
        
        summaries.sort(key=lambda x: x.get(metric, 0.0), reverse=True)
        
        return [s['judge_name'] for s in summaries[:limit]]
    
    def get_judge_trends(
        self,
        judge_name: str,
        window_hours: int = 24
    ) -> Dict[str, List]:
        """
        Get trends for a judge over a time window.
        
        Args:
            judge_name: Name of the judge
            window_hours: Time window in hours
        
        Returns:
            Dict with time-series data for accuracy, confidence, latency
        """
        stats = self.judge_stats.get(judge_name)
        if not stats:
            return {'timestamps': [], 'accuracy': [], 'confidence': [], 'latency': []}
        
        cutoff_time = datetime.utcnow() - timedelta(hours=window_hours)
        
        recent_history = [
            entry for entry in stats['verdict_history']
            if entry['timestamp'] >= cutoff_time
        ]
        
        if not recent_history:
            return {'timestamps': [], 'accuracy': [], 'confidence': [], 'latency': []}
        
        # Calculate rolling metrics
        timestamps = []
        accuracy_values = []
        confidence_values = []
        
        for i, entry in enumerate(recent_history):
            timestamps.append(entry['timestamp'].isoformat())
            confidence_values.append(entry['confidence'])
            
            # Calculate accuracy up to this point
            if entry['ground_truth'] is not None:
                correct = sum(
                    1 for e in recent_history[:i+1]
                    if e['ground_truth'] is not None and e['verdict'] == e['ground_truth']
                )
                total_with_truth = sum(
                    1 for e in recent_history[:i+1]
                    if e['ground_truth'] is not None
                )
                accuracy = correct / total_with_truth if total_with_truth > 0 else 0.0
                accuracy_values.append(accuracy)
            else:
                accuracy_values.append(None)
        
        return {
            'timestamps': timestamps,
            'accuracy': accuracy_values,
            'confidence': confidence_values,
        }
    
    def generate_report(self) -> str:
        """
        Generate a human-readable report of all judges.
        
        Returns:
            Formatted string report
        """
        summaries = self.get_all_judges_summary()
        
        if not summaries:
            return "No judge data available yet."
        
        report_lines = [
            "=" * 80,
            "METAJUDGE REPORT - JUDGE QUALITY MONITORING",
            "=" * 80,
            "",
        ]
        
        for summary in summaries:
            report_lines.extend([
                f"Judge: {summary['judge_name']}",
                f"  Accuracy:              {summary['accuracy']:.1%}",
                f"  Avg Confidence:        {summary['avg_confidence']:.1%}",
                f"  Avg Latency:           {summary['avg_latency_ms']:.1f}ms",
                f"  Conflict Detection:    {summary['conflict_detection_rate']:.1%}",
                f"  Total Evaluations:     {summary['total_evaluations']}",
                "",
            ])
        
        # Add top performers
        top_accurate = self.get_top_performers('accuracy', 3)
        top_detectors = self.get_top_performers('conflict_detection_rate', 3)
        
        report_lines.extend([
            "TOP PERFORMERS",
            f"  Most Accurate:         {', '.join(top_accurate)}",
            f"  Best Conflict Detectors: {', '.join(top_detectors)}",
            "",
            "=" * 80,
        ])
        
        return "\n".join(report_lines)
    
    def reset_stats(self, judge_name: Optional[str] = None) -> None:
        """
        Reset statistics for a judge or all judges.
        
        Args:
            judge_name: Specific judge to reset, or None for all
        """
        if judge_name:
            if judge_name in self.judge_stats:
                del self.judge_stats[judge_name]
                logger.info(f"Reset stats for {judge_name}")
        else:
            self.judge_stats.clear()
            logger.info("Reset stats for all judges")


# Global instance
meta_judge = MetaJudge()
