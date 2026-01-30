# MetaJudge: Judge Quality Monitoring

## Overview

**MetaJudge** is an observability layer that monitors and tracks the quality of judges in the Procedural LTM jury system.

**Important:** MetaJudge is **NOT** a deliberation judge. It does not participate in conflict resolution decisions. It only observes and measures judge performance.

## Purpose

MetaJudge provides:
1. **Judge accuracy tracking** - How often judges make correct decisions
2. **Performance metrics** - Latency, confidence scores, throughput
3. **Conflict detection rates** - Which judges catch the most issues
4. **Comparative analysis** - Judge-to-judge performance comparison
5. **Trend analysis** - Performance over time

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Jury System                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Safety   │  │ Memory   │  │ Time     │             │
│  │ Judge    │  │ Judge    │  │ Judge    │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       │             │             │                     │
│       └─────────────┴─────────────┘                     │
│                     │                                   │
│                     ▼                                   │
│            ┌─────────────────┐                         │
│            │   Consensus     │                         │
│            │   Judge         │                         │
│            └────────┬────────┘                         │
│                     │                                   │
└─────────────────────┼───────────────────────────────────┘
                      │
                      │ (observes, doesn't participate)
                      ▼
            ┌──────────────────┐
            │    MetaJudge     │
            │  (Observability) │
            └────────┬─────────┘
                     │
                     ▼
            ┌──────────────────┐
            │   Prometheus     │
            │   Metrics        │
            └────────┬─────────┘
                     │
                     ▼
            ┌──────────────────┐
            │   Grafana        │
            │   Dashboard      │
            └──────────────────┘
```

## Key Features

### 1. Accuracy Tracking

Track judge verdicts against ground truth:

```python
from src.observability import meta_judge

# After a judge evaluation
meta_judge.track_evaluation(
    judge_name="SafetyJudge",
    verdict=JudgeVerdict.APPROVE,
    confidence=0.95,
    latency_seconds=0.012,
    ground_truth=JudgeVerdict.APPROVE  # Optional
)

# Get accuracy
accuracy = meta_judge.get_judge_accuracy("SafetyJudge")
print(f"SafetyJudge accuracy: {accuracy:.1%}")
```

### 2. Reliability Metrics

Get comprehensive reliability data:

```python
reliability = meta_judge.get_judge_reliability("MemoryJudge")
print(f"""
MemoryJudge Reliability:
  Accuracy:              {reliability['accuracy']:.1%}
  Avg Confidence:        {reliability['avg_confidence']:.1%}
  Avg Latency:           {reliability['avg_latency_ms']:.1f}ms
  Conflict Detection:    {reliability['conflict_detection_rate']:.1%}
  Total Evaluations:     {reliability['total_evaluations']}
""")
```

### 3. Comparative Analysis

Compare all judges:

```python
# Get summary of all judges
summary = meta_judge.get_all_judges_summary()

for judge in summary:
    print(f"{judge['judge_name']}: {judge['accuracy']:.1%} accuracy")

# Get top performers
top_accurate = meta_judge.get_top_performers('accuracy', limit=3)
print(f"Most accurate: {', '.join(top_accurate)}")

top_detectors = meta_judge.get_top_performers('conflict_detection_rate', limit=3)
print(f"Best detectors: {', '.join(top_detectors)}")
```

### 4. Trend Analysis

Track performance over time:

```python
# Get 24-hour trends
trends = meta_judge.get_judge_trends("SafetyJudge", window_hours=24)

# trends contains:
# - timestamps: List of ISO timestamps
# - accuracy: List of accuracy values over time
# - confidence: List of confidence scores over time
```

### 5. Human-Readable Reports

Generate reports:

```python
report = meta_judge.generate_report()
print(report)
```

Output:
```
================================================================================
METAJUDGE REPORT - JUDGE QUALITY MONITORING
================================================================================

Judge: SafetyJudge
  Accuracy:              98.5%
  Avg Confidence:        94.2%
  Avg Latency:           12.3ms
  Conflict Detection:    15.2%
  Total Evaluations:     1,247

Judge: MemoryJudge
  Accuracy:              99.1%
  Avg Confidence:        96.8%
  Avg Latency:           8.7ms
  Conflict Detection:    22.4%
  Total Evaluations:     1,189

TOP PERFORMERS
  Most Accurate:         MemoryJudge, SafetyJudge, TimeJudge
  Best Conflict Detectors: MemoryJudge, SafetyJudge, TimeJudge

================================================================================
```

## Prometheus Metrics

MetaJudge exports the following Prometheus metrics:

### 1. `judge_evaluations_total`
**Type:** Counter  
**Labels:** `judge_name`, `verdict`  
**Description:** Total number of evaluations by each judge

```promql
# Rate of evaluations per second
rate(judge_evaluations_total[5m])

# Total evaluations by judge
sum(judge_evaluations_total) by (judge_name)
```

### 2. `judge_accuracy`
**Type:** Gauge  
**Labels:** `judge_name`  
**Description:** Historical accuracy of judge verdicts (0.0-1.0)

```promql
# Current accuracy by judge
judge_accuracy

# Average accuracy across all judges
avg(judge_accuracy)

# Top 3 most accurate judges
topk(3, judge_accuracy)
```

### 3. `judge_latency_seconds`
**Type:** Histogram  
**Labels:** `judge_name`  
**Description:** Time taken for judge evaluation

```promql
# p95 latency by judge
histogram_quantile(0.95, rate(judge_latency_seconds_bucket[5m]))

# p99 latency
histogram_quantile(0.99, rate(judge_latency_seconds_bucket[5m]))

# Average latency
rate(judge_latency_seconds_sum[5m]) / rate(judge_latency_seconds_count[5m])
```

### 4. `judge_confidence`
**Type:** Histogram  
**Labels:** `judge_name`  
**Description:** Confidence scores from judge verdicts (0.0-1.0)

```promql
# Average confidence by judge
rate(judge_confidence_sum[5m]) / rate(judge_confidence_count[5m])

# Confidence distribution
rate(judge_confidence_bucket[5m])
```

### 5. `judge_conflict_detection_rate`
**Type:** Gauge  
**Labels:** `judge_name`  
**Description:** Rate at which judge detects conflicts (0.0-1.0)

```promql
# Current detection rate
judge_conflict_detection_rate

# Best conflict detector
topk(1, judge_conflict_detection_rate)
```

## Grafana Dashboard

A comprehensive Grafana dashboard is provided at:
`monitoring/grafana/dashboards/judge_quality.json`

### Dashboard Panels

1. **Judge Accuracy Over Time** - Line graph showing accuracy trends
2. **Judge Evaluations by Verdict** - Rate of evaluations (APPROVE/REJECT/DEFER)
3. **Judge Latency (p50, p95, p99)** - Performance percentiles
4. **Conflict Detection Rate** - Which judges catch most conflicts
5. **Judge Confidence Distribution** - Heatmap of confidence scores
6. **Top Performing Judges** - Table of best judges by accuracy
7. **Judge Comparison Matrix** - Side-by-side comparison
8. **Total Evaluations** - Count by judge
9. **Average Judge Accuracy** - System-wide metric
10. **Best Conflict Detector** - Top performer
11. **Fastest Judge** - Lowest p95 latency

### Importing the Dashboard

```bash
# Copy dashboard to Grafana
cp monitoring/grafana/dashboards/judge_quality.json /var/lib/grafana/dashboards/

# Or import via Grafana UI:
# 1. Go to Dashboards → Import
# 2. Upload judge_quality.json
# 3. Select Prometheus data source
# 4. Click Import
```

## Integration with Jury System

### Automatic Tracking

Integrate MetaJudge into your jury pipeline:

```python
from src.jury import SafetyJudge, MemoryJudge, TimeJudge, ConsensusJudge
from src.observability import meta_judge
import time

class InstrumentedJudge:
    """Wrapper that adds MetaJudge tracking to any judge"""
    
    def __init__(self, judge, ground_truth_fn=None):
        self.judge = judge
        self.ground_truth_fn = ground_truth_fn
    
    def evaluate(self, atom):
        start_time = time.time()
        
        # Run judge evaluation
        result = self.judge.evaluate(atom)
        
        latency = time.time() - start_time
        
        # Get ground truth if available
        ground_truth = None
        if self.ground_truth_fn:
            ground_truth = self.ground_truth_fn(atom, result['verdict'])
        
        # Track with MetaJudge
        meta_judge.track_evaluation(
            judge_name=self.judge.name,
            verdict=result['verdict'],
            confidence=result.get('confidence', 1.0),
            latency_seconds=latency,
            ground_truth=ground_truth
        )
        
        return result

# Usage
safety_judge = InstrumentedJudge(SafetyJudge())
memory_judge = InstrumentedJudge(MemoryJudge())
time_judge = InstrumentedJudge(TimeJudge())

# Evaluate with automatic tracking
result = safety_judge.evaluate(atom)
```

### Manual Tracking

Or track manually in your pipeline:

```python
import time
from src.observability import meta_judge

# In your jury pipeline
start = time.time()
result = safety_judge.evaluate(atom)
latency = time.time() - start

meta_judge.track_evaluation(
    judge_name="SafetyJudge",
    verdict=result['verdict'],
    confidence=result['confidence'],
    latency_seconds=latency
)
```

## Use Cases

### 1. Identify Underperforming Judges

```python
summary = meta_judge.get_all_judges_summary()

for judge in summary:
    if judge['accuracy'] < 0.85:
        print(f"⚠️ {judge['judge_name']} accuracy below threshold: {judge['accuracy']:.1%}")
```

### 2. Optimize Judge Selection

```python
# Use fastest judge for time-critical paths
fastest = meta_judge.get_top_performers('avg_latency_ms', limit=1)[0]
print(f"Use {fastest} for fast path")

# Use most accurate for critical decisions
most_accurate = meta_judge.get_top_performers('accuracy', limit=1)[0]
print(f"Use {most_accurate} for critical decisions")
```

### 3. A/B Testing New Judges

```python
# Deploy new judge alongside existing
meta_judge.track_evaluation("SafetyJudge_v1", verdict, confidence, latency)
meta_judge.track_evaluation("SafetyJudge_v2", verdict, confidence, latency)

# Compare after 1000 evaluations
v1_reliability = meta_judge.get_judge_reliability("SafetyJudge_v1")
v2_reliability = meta_judge.get_judge_reliability("SafetyJudge_v2")

if v2_reliability['accuracy'] > v1_reliability['accuracy']:
    print("v2 is better, promote to production")
```

### 4. Detect Performance Degradation

```python
# Set up alerts in Grafana
# Alert if accuracy drops below 90%
# Alert if p95 latency exceeds 100ms
# Alert if conflict detection rate drops below 10%
```

## Best Practices

### 1. Always Track Ground Truth When Available

```python
# Good: Track with ground truth
meta_judge.track_evaluation(
    judge_name="MemoryJudge",
    verdict=verdict,
    confidence=confidence,
    latency_seconds=latency,
    ground_truth=expected_verdict  # ✅ Enables accuracy tracking
)

# Okay: Track without ground truth
meta_judge.track_evaluation(
    judge_name="MemoryJudge",
    verdict=verdict,
    confidence=confidence,
    latency_seconds=latency
    # ⚠️ No accuracy tracking, but still useful for latency/confidence
)
```

### 2. Use Consistent Judge Names

```python
# Good: Consistent naming
meta_judge.track_evaluation("SafetyJudge", ...)
meta_judge.track_evaluation("SafetyJudge", ...)

# Bad: Inconsistent naming
meta_judge.track_evaluation("SafetyJudge", ...)
meta_judge.track_evaluation("safety_judge", ...)  # ❌ Treated as different judge
```

### 3. Monitor Regularly

```python
# Generate daily reports
import schedule

def daily_report():
    report = meta_judge.generate_report()
    send_to_slack(report)

schedule.every().day.at("09:00").do(daily_report)
```

### 4. Set Up Alerts

Configure Grafana alerts for:
- Accuracy drops below 90%
- p95 latency exceeds 100ms
- Conflict detection rate drops significantly
- Total evaluations drops (judge not being used)

## API Reference

### `MetaJudge.track_evaluation()`
Track a judge evaluation.

**Parameters:**
- `judge_name` (str): Name of the judge
- `verdict` (JudgeVerdict): Verdict given
- `confidence` (float): Confidence score (0.0-1.0)
- `latency_seconds` (float): Evaluation time in seconds
- `ground_truth` (JudgeVerdict, optional): Expected verdict for accuracy tracking

### `MetaJudge.get_judge_accuracy(judge_name: str) -> float`
Get historical accuracy of a judge.

**Returns:** Accuracy as float (0.0-1.0)

### `MetaJudge.get_judge_reliability(judge_name: str) -> Dict`
Get comprehensive reliability metrics.

**Returns:** Dict with `accuracy`, `avg_confidence`, `avg_latency_ms`, `conflict_detection_rate`, `total_evaluations`

### `MetaJudge.get_all_judges_summary() -> List[Dict]`
Get summary of all judges, sorted by accuracy.

**Returns:** List of dicts with judge stats

### `MetaJudge.get_top_performers(metric: str, limit: int) -> List[str]`
Get top performing judges by metric.

**Parameters:**
- `metric`: One of `'accuracy'`, `'conflict_detection_rate'`, `'avg_confidence'`
- `limit`: Number of top judges to return

**Returns:** List of judge names

### `MetaJudge.generate_report() -> str`
Generate human-readable report.

**Returns:** Formatted string report

## Performance Impact

MetaJudge is designed to have **minimal performance impact**:

- **Overhead:** <0.1ms per evaluation
- **Memory:** ~100 bytes per tracked evaluation
- **Storage:** Metrics stored in Prometheus (time-series DB)

The observability benefits far outweigh the tiny performance cost.

## Future Enhancements

Potential future additions:

1. **Automated Judge Tuning** - Adjust judge parameters based on performance
2. **Anomaly Detection** - Alert on unusual judge behavior
3. **Judge Recommendations** - Suggest which judge to use for specific scenarios
4. **Multi-Tenant Tracking** - Track judge performance per tenant
5. **Judge Versioning** - Track performance across judge versions

---

**Status:** ✅ Production Ready  
**Version:** 1.0  
**Last Updated:** January 30, 2026
