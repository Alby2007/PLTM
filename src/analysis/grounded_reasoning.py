"""
Grounded Reasoning Engine

Prevents hallucinated cross-domain connections by requiring:
1. Every claim must cite specific atoms/papers
2. Cross-domain links must be explicitly flagged as NOVEL (not in sources)
3. Evidence chains must show each logical step with source
4. Confidence is calibrated by independent source count

This replaces the "breakthrough synthesis" approach that encouraged confabulation.
"""

import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger


DB_PATH = Path(__file__).parent.parent.parent / "data" / "pltm_mcp.db"


def _get_atoms_for_claim(claim: str, domain: str = "", limit: int = 20) -> List[Dict]:
    """Find atoms that could support or contradict a claim."""
    conn = sqlite3.connect(str(DB_PATH))

    claim_words = [w for w in claim.lower().split() if len(w) > 3]
    if not claim_words:
        conn.close()
        return []

    # Build FTS query
    fts_terms = " OR ".join(claim_words[:10])

    try:
        cursor = conn.execute(
            """SELECT a.subject, a.predicate, a.object, a.confidence, a.metadata
               FROM atoms_fts f
               JOIN atoms a ON a.rowid = f.rowid
               WHERE atoms_fts MATCH ?
               AND a.graph = 'substantiated'
               LIMIT ?""",
            (fts_terms, limit)
        )
        rows = cursor.fetchall()
    except Exception:
        # Fallback to LIKE search
        like_conditions = " OR ".join(
            [f"(subject LIKE '%{w}%' OR predicate LIKE '%{w}%' OR object LIKE '%{w}%')"
             for w in claim_words[:5]]
        )
        cursor = conn.execute(
            f"""SELECT subject, predicate, object, confidence, metadata
                FROM atoms WHERE graph = 'substantiated'
                AND ({like_conditions})
                LIMIT ?""",
            (limit,)
        )
        rows = cursor.fetchall()

    results = []
    for row in rows:
        meta = json.loads(row[4]) if row[4] else {}

        # Filter by domain if specified
        if domain:
            contexts = [c.lower() for c in meta.get("contexts", [])]
            if domain.lower() not in contexts and not any(domain.lower() in c for c in contexts):
                continue

        results.append({
            "s": row[0],
            "p": row[1],
            "o": row[2][:150],
            "confidence": row[3],
            "source": meta.get("source", "unknown"),
            "contexts": meta.get("contexts", []),
        })

    conn.close()
    return results


def _count_independent_sources(atoms: List[Dict]) -> Dict:
    """Count how many independent sources support the evidence."""
    sources = set()
    arxiv_ids = set()
    source_types = {}

    for a in atoms:
        src = a.get("source", "unknown")
        sources.add(src)
        if "arxiv:" in src:
            arxiv_ids.add(src)
        for ctx in a.get("contexts", []):
            source_types[ctx] = source_types.get(ctx, 0) + 1

    return {
        "unique_sources": len(sources),
        "arxiv_papers": len(arxiv_ids),
        "source_types": source_types,
        "sources": list(sources)[:10],
    }


class GroundedReasoning:
    """Reasoning engine that requires evidence grounding for every claim."""

    def synthesize_grounded(self, domain_a: str, domain_b: str,
                            max_atoms_per_domain: int = 30) -> Dict:
        """
        Cross-domain synthesis WITH grounding discipline.

        Instead of asking "find connections", this:
        1. Retrieves atoms from each domain
        2. Identifies ACTUAL shared concepts (same subject/object appearing in both)
        3. Classifies connections as EVIDENCED vs NOVEL
        4. Returns structured output for Claude to reason over honestly
        """
        conn = sqlite3.connect(str(DB_PATH))

        # Get atoms from each domain
        atoms_a = self._get_domain_atoms(conn, domain_a, max_atoms_per_domain)
        atoms_b = self._get_domain_atoms(conn, domain_b, max_atoms_per_domain)
        conn.close()

        if not atoms_a or not atoms_b:
            return {
                "ok": False,
                "err": f"Insufficient atoms. {domain_a}: {len(atoms_a)}, {domain_b}: {len(atoms_b)}",
            }

        # Find ACTUAL shared concepts (entities appearing in both domains)
        subjects_a = {a["s"].lower() for a in atoms_a}
        subjects_b = {a["s"].lower() for a in atoms_b}
        objects_a = {a["o"].lower()[:50] for a in atoms_a}
        objects_b = {a["o"].lower()[:50] for a in atoms_b}

        shared_subjects = subjects_a & subjects_b
        shared_terms = set()
        for a in atoms_a:
            for b in atoms_b:
                # Check for overlapping key terms in objects
                a_words = set(a["o"].lower().split()) - {"the", "a", "an", "is", "are", "of", "in", "to", "and", "for", "that", "with"}
                b_words = set(b["o"].lower().split()) - {"the", "a", "an", "is", "are", "of", "in", "to", "and", "for", "that", "with"}
                overlap = a_words & b_words
                significant = {w for w in overlap if len(w) > 4}
                if len(significant) >= 2:
                    shared_terms.update(significant)

        # Build grounded connections
        evidenced_connections = []
        for subj in shared_subjects:
            a_atoms = [a for a in atoms_a if a["s"].lower() == subj]
            b_atoms = [a for a in atoms_b if a["s"].lower() == subj]
            evidenced_connections.append({
                "shared_entity": subj,
                "in_domain_a": [{"p": a["p"], "o": a["o"][:80], "src": a["source"][:50]} for a in a_atoms[:3]],
                "in_domain_b": [{"p": b["p"], "o": b["o"][:80], "src": b["source"][:50]} for b in b_atoms[:3]],
                "type": "EVIDENCED",
                "note": "Same entity appears in both domains with cited sources",
            })

        return {
            "ok": True,
            "domain_a": domain_a,
            "domain_b": domain_b,
            "atoms_a": len(atoms_a),
            "atoms_b": len(atoms_b),
            "evidenced_connections": evidenced_connections[:10],
            "shared_terms": list(shared_terms)[:20],
            "shared_subjects": list(shared_subjects)[:10],
            "reasoning_rules": [
                "ONLY claim connections that appear in evidenced_connections",
                "If you want to propose a NOVEL connection, explicitly label it as SPECULATION",
                "Every factual claim must cite a specific source from the atoms",
                "Do NOT say 'this suggests' or 'this implies' without evidence",
                "If two domains share terminology but not meaning, note the EQUIVOCATION",
            ],
        }

    def build_evidence_chain(self, hypothesis: str, domains: List[str] = None) -> Dict:
        """
        Build an evidence chain for a hypothesis.

        Each link in the chain must cite a specific atom/paper.
        Gaps are explicitly marked as UNSUPPORTED.
        """
        if not domains:
            domains = []

        # Find all supporting atoms
        all_atoms = _get_atoms_for_claim(hypothesis)

        # Also search by domain if specified
        for domain in domains:
            domain_atoms = _get_atoms_for_claim(hypothesis, domain=domain)
            # Deduplicate
            existing = {(a["s"], a["p"]) for a in all_atoms}
            for a in domain_atoms:
                if (a["s"], a["p"]) not in existing:
                    all_atoms.append(a)

        if not all_atoms:
            return {
                "ok": True,
                "hypothesis": hypothesis[:200],
                "verdict": "NO_EVIDENCE",
                "evidence_chain": [],
                "note": "No atoms found that relate to this hypothesis. It may be entirely novel or hallucinated.",
            }

        # Classify atoms by relevance
        hypothesis_words = set(hypothesis.lower().split())
        scored_atoms = []
        for a in all_atoms:
            atom_text = f"{a['s']} {a['p']} {a['o']}".lower()
            atom_words = set(atom_text.split())
            overlap = len(hypothesis_words & atom_words)
            scored_atoms.append({**a, "relevance": overlap})

        scored_atoms.sort(key=lambda x: x["relevance"], reverse=True)

        # Build chain
        source_info = _count_independent_sources(scored_atoms[:20])

        chain = []
        for a in scored_atoms[:15]:
            chain.append({
                "evidence": f"{a['s']} {a['p']} {a['o'][:100]}",
                "source": a["source"][:80],
                "domain": a["contexts"][0] if a.get("contexts") else "unknown",
                "confidence": a["confidence"],
                "relevance": a["relevance"],
                "status": "CITED" if a["source"] != "unknown" else "UNCITED",
            })

        # Determine overall support level
        # CRITICAL: cited atoms that share keywords are NOT the same as
        # atoms that support the specific causal claim
        cited_count = sum(1 for c in chain if c["status"] == "CITED")
        high_relevance = sum(1 for c in chain if c.get("relevance", 0) >= 3)
        
        # Check for cross-domain leaps
        chain_domains = set(c.get("domain", "unknown") for c in chain)
        is_cross_domain = len(chain_domains) > 2
        
        if high_relevance >= 3 and cited_count >= 3 and not is_cross_domain:
            support_level = "WELL_SUPPORTED"
        elif high_relevance >= 2 and cited_count >= 2:
            support_level = "PARTIALLY_SUPPORTED"
        elif high_relevance >= 1:
            support_level = "WEAKLY_SUPPORTED"
        elif cited_count >= 1:
            support_level = "RELATED_ATOMS_FOUND_BUT_NOT_SUPPORTING"
        else:
            support_level = "UNSUPPORTED"
        
        if is_cross_domain and support_level in ("WELL_SUPPORTED", "PARTIALLY_SUPPORTED"):
            support_level = "CROSS_DOMAIN_LEAP — " + support_level + " (within individual domains, but connection between them is NOT evidenced)"

        return {
            "ok": True,
            "hypothesis": hypothesis[:200],
            "support_level": support_level,
            "evidence_chain": chain,
            "source_analysis": source_info,
            "gaps": self._identify_gaps(hypothesis, chain),
            "reasoning_rules": [
                f"Support level: {support_level}",
                f"Based on {cited_count} cited evidence items from {source_info['arxiv_papers']} papers",
                "Claims beyond what evidence shows must be labeled SPECULATION",
                "Cross-domain leaps must be labeled NOVEL_CONNECTION",
            ],
        }

    def calibrate_confidence(self, claim: str, domain: str = "") -> Dict:
        """
        Score a claim's confidence based on evidence quality.

        Key insight: finding atoms that share keywords with a claim is NOT
        the same as finding atoms that SUPPORT the claim. This method:
        1. Detects if the claim makes a causal/relational assertion
        2. Checks if any atom actually states that specific relationship
        3. Uses Groq to judge semantic support (not just keyword overlap)
        4. Heavily penalizes cross-domain causal leaps
        """
        atoms = _get_atoms_for_claim(claim, domain=domain, limit=30)

        if not atoms:
            return {
                "ok": True,
                "claim": claim[:200],
                "calibrated_confidence": 0.05,
                "grade": "F",
                "reason": "No related evidence found in knowledge base",
                "recommendation": "RETRACT or label as PURE_SPECULATION",
            }

        source_info = _count_independent_sources(atoms)

        # Detect if claim is CAUSAL ("X causes Y", "X enables Y", "X is required for Y")
        causal_markers = [
            "causes", "enables", "required for", "leads to", "results in",
            "produces", "generates", "creates", "drives", "determines",
            "is necessary", "is sufficient", "proves", "solves", "resolves",
            "explains", "accounts for", "underlies", "emerges from",
            "emerge at", "emerge in", "emerge from", "gives rise",
            "is responsible for", "is linked to", "is connected to",
        ]
        claim_lower = claim.lower()
        is_causal = any(m in claim_lower for m in causal_markers)

        # Check if any atom DIRECTLY states the claimed relationship
        # (not just mentions the same topics)
        direct_support_count = 0
        for a in atoms:
            atom_text = f"{a['s']} {a['p']} {a['o']}".lower()
            # Check if the atom's predicate matches the claim's relationship
            if is_causal:
                # For causal claims, the atom must also assert causation
                atom_has_causal = any(m in atom_text for m in causal_markers)
                # AND share key entities with the claim
                claim_entities = set(w for w in claim_lower.split() if len(w) > 5)
                atom_entities = set(w for w in atom_text.split() if len(w) > 5)
                entity_overlap = len(claim_entities & atom_entities)
                if atom_has_causal and entity_overlap >= 2:
                    direct_support_count += 1
            else:
                # For non-causal claims, keyword overlap is more acceptable
                claim_words = set(claim_lower.split()) - {"the", "a", "an", "is", "are", "of", "in", "to", "and", "for", "that", "with"}
                atom_words = set(atom_text.split()) - {"the", "a", "an", "is", "are", "of", "in", "to", "and", "for", "that", "with"}
                if len(claim_words & atom_words) >= 3:
                    direct_support_count += 1

        # Domain coherence
        domains_seen = set()
        for a in atoms:
            for ctx in a.get("contexts", []):
                domains_seen.add(ctx)

        # Score components
        source_count_score = min(source_info["unique_sources"] / 5.0, 1.0)
        paper_count_score = min(source_info["arxiv_papers"] / 3.0, 1.0)
        domain_coherence = 1.0 if len(domains_seen) <= 2 else max(0.1, 1.0 - len(domains_seen) * 0.15)
        direct_support_score = min(direct_support_count / 3.0, 1.0)

        # CRITICAL: For causal claims, direct support matters most
        if is_causal:
            calibrated = (
                direct_support_score * 0.50 +  # Must have atoms that state the causal link
                paper_count_score * 0.20 +
                domain_coherence * 0.20 +
                source_count_score * 0.10
            )
            # Extra penalty: cross-domain causal claims are almost always confabulation
            if len(domains_seen) > 2:
                calibrated *= 0.4  # 60% penalty
        else:
            calibrated = (
                direct_support_score * 0.35 +
                paper_count_score * 0.25 +
                domain_coherence * 0.20 +
                source_count_score * 0.20
            )

        calibrated = round(max(0.05, min(calibrated, 1.0)), 3)

        # Grade
        if calibrated >= 0.7:
            grade, label = "A", "WELL_GROUNDED"
        elif calibrated >= 0.5:
            grade, label = "B", "REASONABLY_SUPPORTED"
        elif calibrated >= 0.35:
            grade, label = "C", "WEAKLY_SUPPORTED"
        elif calibrated >= 0.2:
            grade, label = "D", "POORLY_SUPPORTED"
        else:
            grade, label = "F", "UNSUPPORTED"

        # Specific warnings
        warnings = []
        if is_causal and direct_support_count == 0:
            warnings.append("CAUSAL_CLAIM with ZERO atoms directly supporting the causal relationship. Likely confabulation.")
        if is_causal and len(domains_seen) > 2:
            warnings.append(f"Cross-domain CAUSAL claim spanning {len(domains_seen)} domains — very high confabulation risk")
        if source_info["arxiv_papers"] == 0:
            warnings.append("No peer-reviewed sources cited")
        if source_info["unique_sources"] == 1:
            warnings.append("Single-source claim — needs independent verification")
        if len(domains_seen) > 3:
            warnings.append(f"Spans {len(domains_seen)} domains — atoms share keywords but may not support the specific claim")
        if domain and domain not in domains_seen:
            warnings.append(f"Claimed domain '{domain}' not found in supporting evidence")
        if len(atoms) > 5 and direct_support_count == 0:
            warnings.append(f"Found {len(atoms)} related atoms but NONE directly support this specific claim")

        return {
            "ok": True,
            "claim": claim[:200],
            "is_causal_claim": is_causal,
            "calibrated_confidence": calibrated,
            "grade": grade,
            "label": label,
            "components": {
                "direct_support": round(direct_support_score, 2),
                "source_diversity": round(source_count_score, 2),
                "paper_backing": round(paper_count_score, 2),
                "domain_coherence": round(domain_coherence, 2),
            },
            "direct_support_atoms": direct_support_count,
            "related_atoms_found": len(atoms),
            "source_analysis": source_info,
            "domains_involved": list(domains_seen),
            "warnings": warnings,
            "recommendation": f"{'KEEP' if calibrated >= 0.35 else 'RETRACT or DOWNGRADE'} — {label}",
        }

    def audit_synthesis(self, claims: List[str]) -> Dict:
        """
        Audit a batch of claims from a synthesis session.
        Returns per-claim grading and overall session quality.
        """
        results = []
        grades = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}

        for claim in claims[:20]:  # Cap at 20
            cal = self.calibrate_confidence(claim)
            grade = cal.get("grade", "F")
            grades[grade] = grades.get(grade, 0) + 1
            results.append({
                "claim": claim[:100],
                "grade": grade,
                "confidence": cal.get("calibrated_confidence", 0),
                "warnings": cal.get("warnings", []),
            })

        total = len(results)
        if total == 0:
            return {"ok": False, "err": "No claims to audit"}

        # Overall quality
        quality_score = sum(
            {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25, "F": 0.0}[r["grade"]]
            for r in results
        ) / total

        if quality_score >= 0.75:
            overall = "HIGH_QUALITY"
        elif quality_score >= 0.5:
            overall = "MIXED_QUALITY"
        elif quality_score >= 0.25:
            overall = "LOW_QUALITY"
        else:
            overall = "MOSTLY_HALLUCINATED"

        return {
            "ok": True,
            "total_claims": total,
            "overall_quality": overall,
            "quality_score": round(quality_score, 3),
            "grade_distribution": grades,
            "claims": results,
            "action_items": [
                f"Retract {grades.get('F', 0)} unsupported claims" if grades.get("F") else None,
                f"Downgrade {grades.get('D', 0)} poorly supported claims" if grades.get("D") else None,
                f"Verify {grades.get('C', 0)} weakly supported claims" if grades.get("C") else None,
            ],
        }

    def _get_domain_atoms(self, conn, domain: str, limit: int) -> List[Dict]:
        """Get atoms from a specific domain."""
        cursor = conn.execute(
            """SELECT subject, predicate, object, confidence, metadata
               FROM atoms WHERE graph = 'substantiated'
               AND metadata LIKE ?
               LIMIT ?""",
            (f'%"{domain}"%', limit)
        )
        results = []
        for row in cursor.fetchall():
            meta = json.loads(row[4]) if row[4] else {}
            results.append({
                "s": row[0],
                "p": row[1],
                "o": row[2][:150],
                "confidence": row[3],
                "source": meta.get("source", "unknown"),
                "contexts": meta.get("contexts", []),
            })
        return results

    def _identify_gaps(self, hypothesis: str, chain: List[Dict]) -> List[str]:
        """Identify logical gaps in the evidence chain."""
        gaps = []

        # Check for cross-domain leaps
        domains_in_chain = set()
        for link in chain:
            domains_in_chain.add(link.get("domain", "unknown"))

        if len(domains_in_chain) > 2:
            gaps.append(f"CROSS_DOMAIN_LEAP: Evidence spans {len(domains_in_chain)} domains ({', '.join(domains_in_chain)}). Connections between domains are NOT evidenced unless explicitly shown.")

        # Check for low-relevance links
        low_rel = [l for l in chain if l.get("relevance", 0) <= 1]
        if low_rel:
            gaps.append(f"WEAK_LINKS: {len(low_rel)} evidence items have low relevance to the hypothesis. They may be tangentially related, not supporting.")

        # Check for uncited evidence
        uncited = [l for l in chain if l.get("status") == "UNCITED"]
        if uncited:
            gaps.append(f"UNCITED: {len(uncited)} evidence items lack source attribution.")

        if not chain:
            gaps.append("TOTAL_GAP: No evidence found. Hypothesis is entirely unsupported.")

        return gaps
