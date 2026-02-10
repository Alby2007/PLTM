"""
Multi-Domain Cascade Simulator

Simulates how trigger events propagate across interconnected domains.
Uses stored knowledge atoms to build a dependency graph, then models
cascade effects with configurable propagation rules.

Output: timeline of effects, Φ trajectories per domain, critical failure points.
"""

import json
import math
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class CascadeEvent:
    step: int
    domain: str
    effect: str
    severity: float  # 0.0 - 1.0
    caused_by: str  # which event/domain triggered this
    phi_before: float
    phi_after: float


@dataclass
class CascadeResult:
    trigger_events: List[str]
    timeline: str
    total_steps: int
    events: List[CascadeEvent]
    phi_trajectories: Dict[str, List[float]]
    critical_failures: List[Dict]
    cascade_depth: int
    domains_affected: int
    total_phi_loss: float


class CascadeSimulator:
    """Simulate multi-domain cascade effects from trigger events."""
    
    # Default domain interdependency weights
    # Format: (source_domain, target_domain) -> propagation_strength
    DEFAULT_DEPENDENCIES = {
        ("military", "economic"): 0.7,
        ("military", "energy"): 0.6,
        ("military", "cyber"): 0.5,
        ("military", "infrastructure"): 0.6,
        ("economic", "military"): 0.4,
        ("economic", "energy"): 0.5,
        ("economic", "infrastructure"): 0.4,
        ("economic", "political"): 0.6,
        ("energy", "economic"): 0.8,
        ("energy", "military"): 0.5,
        ("energy", "infrastructure"): 0.7,
        ("cyber", "infrastructure"): 0.8,
        ("cyber", "economic"): 0.6,
        ("cyber", "military"): 0.4,
        ("infrastructure", "economic"): 0.7,
        ("infrastructure", "military"): 0.5,
        ("infrastructure", "energy"): 0.6,
        ("political", "military"): 0.5,
        ("political", "economic"): 0.4,
        ("geopolitics", "military"): 0.6,
        ("geopolitics", "economic"): 0.5,
        ("geopolitics", "political"): 0.7,
    }
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent.parent.parent / "data" / "pltm_mcp.db"
        self.dependencies = dict(self.DEFAULT_DEPENDENCIES)
    
    def simulate(
        self,
        trigger_events: List[Dict[str, Any]],
        domains: Optional[List[str]] = None,
        timeline: str = "2027-Q2",
        max_steps: int = 10,
        propagation_threshold: float = 0.15,
        initial_phi: Optional[Dict[str, float]] = None,
    ) -> CascadeResult:
        """
        Simulate cascade from trigger events.
        
        Args:
            trigger_events: [{domain, event, severity}]
            domains: domains to simulate (default: all in dependencies)
            timeline: label for the scenario
            max_steps: max propagation steps
            propagation_threshold: minimum severity to propagate
            initial_phi: starting Φ per domain (default: 0.7 for all)
        """
        # Initialize domains
        if domains is None:
            domains = list(set(
                [d for pair in self.dependencies for d in pair] +
                [t["domain"] for t in trigger_events]
            ))
        
        # Initialize Φ values
        phi = {}
        for d in domains:
            phi[d] = (initial_phi or {}).get(d, 0.70)
        
        phi_trajectories = {d: [phi[d]] for d in domains}
        events = []
        active_effects = []  # (domain, severity, source)
        
        # Seed with trigger events
        for t in trigger_events:
            domain = t["domain"]
            severity = float(t.get("severity", 0.5))
            event_desc = t.get("event", "trigger")
            
            if domain not in phi:
                phi[domain] = 0.70
                phi_trajectories[domain] = [0.70]
            
            phi_before = phi[domain]
            phi_drop = severity * 0.5  # Direct hit reduces Φ by up to 50%
            phi[domain] = max(0.0, phi[domain] - phi_drop)
            
            events.append(CascadeEvent(
                step=0, domain=domain, effect=event_desc,
                severity=severity, caused_by="trigger",
                phi_before=round(phi_before, 3), phi_after=round(phi[domain], 3)
            ))
            active_effects.append((domain, severity, "trigger"))
        
        # Propagate
        for step in range(1, max_steps + 1):
            new_effects = []
            
            for source_domain, source_severity, source_cause in active_effects:
                # Find all domains this can propagate to
                for (src, tgt), weight in self.dependencies.items():
                    if src != source_domain or tgt not in phi:
                        continue
                    
                    propagated_severity = source_severity * weight * 0.7  # Decay factor
                    
                    if propagated_severity < propagation_threshold:
                        continue
                    
                    phi_before = phi[tgt]
                    phi_drop = propagated_severity * 0.3  # Indirect effects are weaker
                    phi[tgt] = max(0.0, phi[tgt] - phi_drop)
                    
                    effect_desc = f"cascade from {source_domain}: {propagated_severity:.0%} severity propagated"
                    
                    events.append(CascadeEvent(
                        step=step, domain=tgt, effect=effect_desc,
                        severity=round(propagated_severity, 3),
                        caused_by=source_domain,
                        phi_before=round(phi_before, 3),
                        phi_after=round(phi[tgt], 3)
                    ))
                    new_effects.append((tgt, propagated_severity, source_domain))
            
            # Record Φ for this step
            for d in domains:
                phi_trajectories[d].append(round(phi[d], 3))
            
            if not new_effects:
                break  # Cascade exhausted
            
            active_effects = new_effects
        
        # Identify critical failures (Φ < 0.3)
        critical_failures = []
        for d in domains:
            if phi[d] < 0.30:
                critical_failures.append({
                    "domain": d,
                    "final_phi": round(phi[d], 3),
                    "phi_loss": round(phi_trajectories[d][0] - phi[d], 3),
                })
        
        total_phi_loss = sum(phi_trajectories[d][0] - phi[d] for d in domains)
        
        return CascadeResult(
            trigger_events=[t.get("event", t["domain"]) for t in trigger_events],
            timeline=timeline,
            total_steps=len(set(e.step for e in events)),
            events=events,
            phi_trajectories=phi_trajectories,
            critical_failures=critical_failures,
            cascade_depth=max(e.step for e in events) if events else 0,
            domains_affected=sum(1 for d in domains if phi[d] < phi_trajectories[d][0]),
            total_phi_loss=round(total_phi_loss, 3),
        )
    
    def add_dependency(self, source: str, target: str, weight: float):
        """Add or update a domain dependency"""
        self.dependencies[(source, target)] = max(0.0, min(1.0, weight))
    
    def to_compact(self, result: CascadeResult) -> Dict:
        """Token-efficient serialization"""
        return {
            "triggers": result.trigger_events,
            "timeline": result.timeline,
            "steps": result.total_steps,
            "depth": result.cascade_depth,
            "domains_hit": result.domains_affected,
            "total_phi_loss": result.total_phi_loss,
            "critical_failures": result.critical_failures,
            "phi_final": {d: traj[-1] for d, traj in result.phi_trajectories.items()},
            "phi_trajectories": result.phi_trajectories,
            "events": [
                {"step": e.step, "domain": e.domain, "severity": e.severity,
                 "from": e.caused_by, "phi": f"{e.phi_before}->{e.phi_after}",
                 "effect": e.effect[:80]}
                for e in result.events
            ],
        }
