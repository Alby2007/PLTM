"""
Fact-Checking & Verification System

Fetches actual source text from arXiv papers and verifies claims against them.
Uses Groq (free) for verification judgments. Closes the hallucination loop.

Tools:
  - fetch_arxiv_context: Get actual text snippets from a paper matching a query
  - verify_claim: Check if a claim is supported by its cited source
"""

import json
import os
import re
import sqlite3
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


def _fetch_url(url: str, timeout: int = 20) -> str:
    """Fetch URL content."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "PLTM/2.0 (Research Verification Bot)",
        "Accept": "text/html,application/xml,text/plain,application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _get_arxiv_metadata(arxiv_id: str) -> Dict:
    """Fetch paper metadata from arXiv API."""
    clean_id = arxiv_id.strip().replace("arxiv:", "").replace("arXiv:", "")
    # Strip version suffix for API lookup if needed
    base_id = re.sub(r'v\d+$', '', clean_id)

    url = f"http://export.arxiv.org/api/query?id_list={base_id}&max_results=1"
    raw = _fetch_url(url)
    root = ET.fromstring(raw)

    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    entry = root.find("atom:entry", ns)
    if entry is None:
        return {"ok": False, "err": f"Paper not found: {arxiv_id}"}

    title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
    abstract = entry.findtext("atom:summary", "", ns).strip().replace("\n", " ")
    published = entry.findtext("atom:published", "", ns)[:10] if entry.findtext("atom:published", "", ns) else ""

    authors = []
    for author in entry.findall("atom:author", ns):
        name = author.findtext("atom:name", "", ns)
        if name:
            authors.append(name)

    categories = []
    for cat in entry.findall("atom:category", ns):
        term = cat.get("term", "")
        if term:
            categories.append(term)

    # Get PDF/HTML links
    links = {}
    for link in entry.findall("atom:link", ns):
        rel = link.get("rel", "")
        href = link.get("href", "")
        link_type = link.get("type", "")
        if "pdf" in link_type or "pdf" in href:
            links["pdf"] = href
        elif rel == "alternate":
            links["abstract_page"] = href

    return {
        "ok": True,
        "arxiv_id": clean_id,
        "title": title,
        "authors": authors,
        "published": published,
        "categories": categories,
        "abstract": abstract,
        "links": links,
    }


def _find_relevant_sentences(text: str, query: str, max_snippets: int = 10) -> List[Dict]:
    """Find sentences in text most relevant to query, with context."""
    query_words = set(query.lower().split())

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)

    scored = []
    for i, sent in enumerate(sentences):
        sent_clean = sent.strip()
        if len(sent_clean) < 15:
            continue

        words = set(sent_clean.lower().split())
        overlap = len(query_words & words)
        if overlap == 0:
            continue

        score = overlap / max(len(query_words), 1)

        # Bonus for exact phrase matches
        for qw in query_words:
            if qw in sent_clean.lower():
                score += 0.1

        # Build context window (sentence before + after)
        context_before = sentences[i - 1].strip() if i > 0 else ""
        context_after = sentences[i + 1].strip() if i < len(sentences) - 1 else ""

        scored.append({
            "sentence": sent_clean[:300],
            "context_before": context_before[:150],
            "context_after": context_after[:150],
            "relevance": round(score, 3),
            "position": i,
        })

    scored.sort(key=lambda x: x["relevance"], reverse=True)
    return scored[:max_snippets]


class FactChecker:
    """Fact-checking and source verification system."""

    def fetch_arxiv_context(self, arxiv_id: str, query: str,
                            max_snippets: int = 5) -> Dict:
        """
        Fetch actual text from an arXiv paper and find snippets relevant to query.
        Returns the abstract + matching sentences for manual verification.
        """
        try:
            meta = _get_arxiv_metadata(arxiv_id)
            if not meta.get("ok"):
                return meta

            abstract = meta["abstract"]

            # Find relevant snippets in abstract
            snippets = _find_relevant_sentences(abstract, query, max_snippets)

            # Also check stored atoms from this paper
            db_path = Path(__file__).parent.parent.parent / "data" / "pltm_mcp.db"
            stored_claims = []
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.execute(
                    "SELECT subject, predicate, object FROM atoms WHERE metadata LIKE ? LIMIT 20",
                    (f'%{arxiv_id.replace("v1","").replace("v2","")}%',)
                )
                for row in cursor.fetchall():
                    stored_claims.append({
                        "s": row[0][:50], "p": row[1][:30], "o": row[2][:100]
                    })
                conn.close()
            except Exception:
                pass

            return {
                "ok": True,
                "arxiv_id": meta["arxiv_id"],
                "title": meta["title"],
                "authors": meta["authors"][:5],
                "published": meta["published"],
                "abstract": abstract,
                "query": query,
                "matching_snippets": snippets,
                "stored_claims_from_paper": stored_claims[:10],
                "note": "Abstract only. For full text, check PDF at: " + meta.get("links", {}).get("pdf", "N/A"),
            }
        except Exception as e:
            return {"ok": False, "err": str(e)[:200], "arxiv_id": arxiv_id}

    def verify_claim(self, claim: str, source_arxiv_id: str = "",
                     source_text: str = "", domain: str = "") -> Dict:
        """
        Verify a claim against its source. Uses Groq to judge accuracy.

        Provide either:
          - source_arxiv_id: fetches the paper abstract automatically
          - source_text: raw text to verify against
        """
        try:
            # Step 1: Get source text
            if source_arxiv_id:
                meta = _get_arxiv_metadata(source_arxiv_id)
                if not meta.get("ok"):
                    return {"ok": False, "err": f"Could not fetch paper: {meta.get('err', 'unknown')}"}
                source_text = meta["abstract"]
                source_label = f"arXiv:{meta['arxiv_id']} - {meta['title'][:80]}"
                authors = meta.get("authors", [])[:5]
            elif source_text:
                source_label = "provided_text"
                authors = []
            else:
                # Try to find source from stored atoms
                source_text, source_label, authors = self._find_source_from_db(claim, domain)
                if not source_text:
                    return {
                        "ok": False,
                        "err": "No source provided and could not find matching source in DB. Provide source_arxiv_id or source_text.",
                    }

            # Step 2: Find relevant snippets
            snippets = _find_relevant_sentences(source_text, claim, max_snippets=5)

            # Step 3: Use Groq to verify
            from src.analysis.model_router import ModelRouter
            router = ModelRouter()

            prompt = f"""You are a rigorous fact-checker. Compare this CLAIM against the SOURCE TEXT.

CLAIM: "{claim}"

SOURCE TEXT:
\"\"\"{source_text[:4000]}\"\"\"

RELEVANT SNIPPETS FROM SOURCE:
{json.dumps([s["sentence"] for s in snippets[:5]], indent=2) if snippets else "No directly matching sentences found."}

Evaluate the claim and respond with ONLY this JSON (no other text):
{{
  "verdict": "SUPPORTED" or "PARTIALLY_SUPPORTED" or "NOT_SUPPORTED" or "EXAGGERATED" or "CONFLATED" or "HALLUCINATED",
  "confidence": 0.0 to 1.0,
  "explanation": "Brief explanation of your judgment",
  "actual_text": "The closest actual quote from the source that relates to this claim",
  "issues": ["list of specific issues found, if any"],
  "corrected_claim": "If the claim needs correction, provide the accurate version. Otherwise null."
}}"""

            result = router.call(
                prompt=prompt,
                provider="groq",
                task_type="verification",
                max_tokens=1000,
                temperature=0.1,
            )

            if not result.get("ok"):
                # Fallback to ollama
                result = router.call(
                    prompt=prompt,
                    provider="ollama",
                    task_type="verification",
                    max_tokens=1000,
                    temperature=0.1,
                )

            if not result.get("ok"):
                return {
                    "ok": True,
                    "verdict": "UNVERIFIABLE",
                    "reason": "LLM unavailable for verification",
                    "source": source_label,
                    "snippets": snippets[:3],
                    "note": "Manual verification needed. Snippets provided for human review.",
                }

            # Parse LLM response
            response_text = result.get("text", "")
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

            if json_match:
                try:
                    verification = json.loads(json_match.group())
                except (json.JSONDecodeError, TypeError):
                    verification = {"verdict": "PARSE_ERROR", "raw": response_text[:300]}
            else:
                verification = {"verdict": "PARSE_ERROR", "raw": response_text[:300]}

            # Log verification
            self._log_verification(claim, source_label, verification)

            return {
                "ok": True,
                "claim": claim[:200],
                "source": source_label,
                "source_authors": authors[:3] if authors else [],
                "verdict": verification.get("verdict", "UNKNOWN"),
                "confidence": verification.get("confidence", 0.0),
                "explanation": verification.get("explanation", ""),
                "actual_text": verification.get("actual_text", ""),
                "issues": verification.get("issues", []),
                "corrected_claim": verification.get("corrected_claim"),
                "matching_snippets": [s["sentence"][:150] for s in snippets[:3]],
            }

        except Exception as e:
            return {"ok": False, "err": str(e)[:200], "claim": claim[:100]}

    def _find_source_from_db(self, claim: str, domain: str = "") -> tuple:
        """Try to find the source paper for a claim from stored atoms."""
        db_path = Path(__file__).parent.parent.parent / "data" / "pltm_mcp.db"
        try:
            conn = sqlite3.connect(str(db_path))

            # Search for atoms matching the claim
            claim_words = claim.lower().split()[:8]
            conditions = " OR ".join([f"object LIKE '%{w}%'" for w in claim_words if len(w) > 3])
            if not conditions:
                conn.close()
                return "", "", []

            cursor = conn.execute(
                f"SELECT subject, predicate, object, metadata FROM atoms WHERE ({conditions}) LIMIT 20"
            )
            rows = cursor.fetchall()

            # Find arxiv IDs in the results
            arxiv_ids = set()
            for row in rows:
                meta = json.loads(row[3]) if row[3] else {}
                source = meta.get("source", "")
                if "arxiv:" in source:
                    arxiv_ids.add(source.replace("arxiv:", ""))
                # Check if subject is an arxiv ID
                if re.match(r'\d{4}\.\d{4,5}', row[0]):
                    arxiv_ids.add(row[0].replace("v1", "").replace("v2", ""))

            conn.close()

            if arxiv_ids:
                # Fetch the first matching paper
                aid = list(arxiv_ids)[0]
                meta = _get_arxiv_metadata(aid)
                if meta.get("ok"):
                    return meta["abstract"], f"arXiv:{aid} - {meta['title'][:80]}", meta.get("authors", [])

        except Exception as e:
            logger.warning(f"DB source lookup failed: {e}")

        return "", "", []

    def _log_verification(self, claim: str, source: str, verification: Dict):
        """Log verification results to DB."""
        db_path = Path(__file__).parent.parent.parent / "data" / "pltm_mcp.db"
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS verification_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    claim TEXT,
                    source TEXT,
                    verdict TEXT,
                    confidence REAL,
                    explanation TEXT
                )
            """)
            conn.execute(
                "INSERT INTO verification_log (timestamp, claim, source, verdict, confidence, explanation) VALUES (?, ?, ?, ?, ?, ?)",
                (time.time(), claim[:500], source[:200],
                 verification.get("verdict", "UNKNOWN"),
                 verification.get("confidence", 0.0),
                 verification.get("explanation", "")[:500])
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to log verification: {e}")

    def verification_history(self, last_n: int = 20) -> Dict:
        """Get recent verification results."""
        db_path = Path(__file__).parent.parent.parent / "data" / "pltm_mcp.db"
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS verification_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    claim TEXT,
                    source TEXT,
                    verdict TEXT,
                    confidence REAL,
                    explanation TEXT
                )
            """)
            cursor = conn.execute(
                "SELECT timestamp, claim, source, verdict, confidence, explanation FROM verification_log ORDER BY timestamp DESC LIMIT ?",
                (last_n,)
            )
            rows = cursor.fetchall()
            conn.close()

            history = []
            verdicts = {"SUPPORTED": 0, "PARTIALLY_SUPPORTED": 0, "NOT_SUPPORTED": 0,
                        "EXAGGERATED": 0, "CONFLATED": 0, "HALLUCINATED": 0}
            for row in rows:
                v = row[3]
                if v in verdicts:
                    verdicts[v] += 1
                history.append({
                    "time": row[0],
                    "claim": row[1][:100],
                    "source": row[2][:60],
                    "verdict": row[3],
                    "confidence": row[4],
                })

            return {
                "ok": True,
                "total": len(history),
                "verdicts_summary": {k: v for k, v in verdicts.items() if v > 0},
                "history": history,
            }
        except Exception as e:
            return {"ok": False, "err": str(e)[:200]}
