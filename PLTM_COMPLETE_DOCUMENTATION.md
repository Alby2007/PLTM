# PLTM (Procedural Long-Term Memory) — Complete Documentation

> **114 MCP Tools** | **Deep Claude Dashboard** | **SQLite Database**
> 
> A persistent identity, epistemic hygiene, and self-improvement system for Claude.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quick Start](#quick-start)
3. [MCP Tools Reference (All 114)](#mcp-tools-reference)
   - [Memory & Personality Core](#1-memory--personality-core-8-tools)
   - [Personality Bootstrapping & Analysis](#2-personality-bootstrapping--analysis-8-tools)
   - [Claude Identity & Session](#3-claude-identity--session-8-tools)
   - [Continuous Learning](#4-continuous-learning-10-tools)
   - [Quantum Memory (PLTM 2.0)](#5-quantum-memory-pltm-20-5-tools)
   - [Attention & Knowledge Graph](#6-attention--knowledge-graph-5-tools)
   - [Self-Improvement](#7-self-improvement-3-tools)
   - [Criticality Management](#8-criticality-management-4-tools)
   - [Provenance & Citations](#9-provenance--citations-4-tools)
   - [Retrieval (MMR)](#10-retrieval-mmr-1-tool)
   - [Action Accounting (AAE)](#11-action-accounting-aae-4-tools)
   - [Entropy Injection](#12-entropy-injection-4-tools)
   - [arXiv Integration](#13-arxiv-integration-3-tools)
   - [Epistemic Hygiene](#14-epistemic-hygiene-5-tools)
   - [Self-Modeling & Personality](#15-self-modeling--personality-5-tools)
   - [Cross-Model Routing](#16-cross-model-routing-1-tool)
   - [Session Management](#17-session-management-2-tools)
   - [Experiment & Research](#18-experiment--research-3-tools)
   - [Typed Memory System](#19-typed-memory-system-10-tools)
   - [Memory Intelligence](#20-memory-intelligence-8-tools)
   - [Embedding Search](#21-embedding-search-3-tools)
   - [Data Access](#22-data-access-1-tool)
4. [Deep Claude Dashboard](#deep-claude-dashboard)
5. [Database Schema](#database-schema)
6. [Experiment Workflows](#experiment-workflows)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Desktop                        │
│                  (MCP Client)                            │
└──────────────────────┬──────────────────────────────────┘
                       │ stdio (JSON-RPC)
┌──────────────────────▼──────────────────────────────────┐
│              pltm_server.py (MCP Server)                 │
│                   114 Tools                              │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ Epistemic│ │ Epistemic│ │ PLTMSelf │ │   Model    │ │
│  │ Monitor  │ │    V2    │ │          │ │   Router   │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ Quantum  │ │Attention │ │Knowledge │ │ Recursive  │ │
│  │ Memory   │ │Retrieval │ │  Graph   │ │Improvement │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              data/pltm_mcp.db (SQLite)                   │
│                                                          │
│  atoms · prediction_book · calibration_cache             │
│  epistemic_interventions · confabulation_log             │
│  self_communication · self_curiosity · self_reasoning    │
│  self_values · session_log · personality_snapshot         │
│  knowledge_concepts · provenance · action_log            │
└─────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│         Deep Claude Dashboard (React + Recharts)         │
│         http://localhost:3000                             │
│                                                          │
│  Overview │ Claims │ Personality │ Evolution │ Atoms     │
└─────────────────────────────────────────────────────────┘
```

**Key files:**
- `mcp_server/pltm_server.py` — MCP server (114 tools)
- `src/memory/memory_types.py` — Typed memory system (episodic, semantic, belief, procedural)
- `src/memory/embedding_store.py` — Embedding-based semantic search (all-MiniLM-L6-v2)
- `data/pltm_mcp.db` — SQLite database
- `deep-claude-dashboard/` — React visualization dashboard
- `deep-claude-dashboard/api_server.py` — Dashboard API (port 8787)
- `src/analysis/` — Backend modules (epistemic_monitor, epistemic_v2, pltm_self, model_router, cross_domain_synthesis)
- `src/meta/recursive_improvement.py` — Self-improvement engine

---

## Quick Start

### 1. Start the MCP Server (for Claude Desktop)

Add to `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "pltm-memory": {
      "command": "python",
      "args": ["C:\\Users\\alber\\CascadeProjects\\LLTM\\mcp_server\\pltm_server.py"]
    }
  }
}
```
Restart Claude Desktop. All 114 tools will be available.

### 2. Start the Dashboard

```bash
cd C:\Users\alber\CascadeProjects\LLTM\deep-claude-dashboard

# Terminal 1: API server
python api_server.py

# Terminal 2: Frontend
npm run dev
```
Open http://localhost:3000

---

## MCP Tools Reference

### 1. Memory & Personality Core (8 tools)

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`store_memory_atom`** | Store a memory atom (fact, trait, preference, mood) in the PLTM graph. Core building block of all memory. | `user_id`, `atom_type`, `subject`, `predicate`, `object` |
| **`query_personality`** | Get synthesized personality profile. Returns traits, communication style, preferences. | `user_id` |
| **`detect_mood`** | Detect mood from a user message. Returns detected mood + confidence. | `user_id`, `message` |
| **`get_mood_patterns`** | Get mood patterns over time. Returns temporal patterns, volatility, predictions. | `user_id` |
| **`resolve_conflict`** | Resolve conflicting personality traits (e.g., "concise" vs "detailed"). | `user_id`, `trait_objects` |
| **`extract_personality_traits`** | Auto-extract personality traits from a message. Learns from style. | `user_id`, `message` |
| **`get_adaptive_prompt`** | Generate adaptive system prompt based on user's personality + mood. | `user_id`, `message` |
| **`get_personality_summary`** | Human-readable personality summary. | `user_id` |

**Usage pattern:** Store atoms → query personality → adapt responses.

---

### 2. Personality Bootstrapping & Analysis (8 tools)

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`bootstrap_from_sample`** | Bootstrap PLTM with sample data for quick testing. | `user_id` |
| **`bootstrap_from_messages`** | Bootstrap from conversation messages. Analyzes messages to extract personality. | `user_id`, `messages` |
| **`track_trait_evolution`** | Track how a trait evolved over time. Shows timeline, trend, inflection points. | `user_id`, `trait` |
| **`predict_reaction`** | Predict how user will react to a stimulus based on causal patterns. | `user_id`, `stimulus` |
| **`get_meta_patterns`** | Get cross-context patterns — behaviors that appear across multiple domains. | `user_id` |
| **`learn_from_interaction`** | Learn from an interaction — what worked, what didn't. | `user_id`, `my_response`, `user_reaction` |
| **`predict_session`** | Predict session dynamics from greeting. Infer mood immediately. | `user_id`, `greeting` |
| **`get_self_model`** | Get explicit self-model for meta-cognition. See what Claude knows + confidence. | `user_id` |

---

### 3. Claude Identity & Session (8 tools)

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`init_claude_session`** | Initialize Claude personality session. Load evolved style for this user. | `user_id` |
| **`update_claude_style`** | Update communication style attribute (verbosity, formality, initiative, etc.). | `user_id`, `attribute`, `value` |
| **`learn_interaction_dynamic`** | Learn what works/doesn't with this user. | `user_id`, `behavior`, `works` |
| **`record_milestone`** | Record a collaboration milestone. | `user_id`, `description` |
| **`add_shared_vocabulary`** | Add shared term/shorthand between Claude and user. | `user_id`, `term`, `meaning` |
| **`get_claude_personality`** | Get Claude's personality summary — style, dynamics, shared context. | `user_id` |
| **`evolve_claude_personality`** | Evolve personality based on interaction outcome. Core learning loop. | `user_id`, `my_response_style`, `user_reaction`, `was_positive` |
| **`check_pltm_available`** | Quick check if user has PLTM data. Call FIRST to decide if to init. | `user_id` |

**Additional:**

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`pltm_mode`** | Trigger phrase handler. When user says "PLTM mode", auto-initialize. | `user_id` |
| **`deep_personality_analysis`** | Comprehensive analysis from all conversation history. Temporal patterns, triggers, evolution. | `user_id` |
| **`enrich_claude_personality`** | Build rich, nuanced personality from deep analysis. | `user_id` |

---

### 4. Continuous Learning (10 tools)

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`learn_from_url`** | Learn from any URL content. Extracts facts, concepts, relationships. | `url`, `content` |
| **`learn_from_paper`** | Learn from a research paper. Extracts findings, methodologies, results. | `paper_id`, `title`, `abstract`, `content`, `authors` |
| **`learn_from_code`** | Learn from a code repository. Extracts design patterns, techniques. | `repo_url`, `repo_name`, `languages`, `code_samples` |
| **`get_learning_stats`** | Statistics about learned knowledge — sources, domains, facts. | *(none)* |
| **`batch_ingest_wikipedia`** | Batch ingest Wikipedia articles. | `articles` |
| **`batch_ingest_papers`** | Batch ingest research papers. | `papers` |
| **`batch_ingest_repos`** | Batch ingest GitHub repositories. | `repos` |
| **`get_learning_schedule`** | Status of continuous learning schedules. | *(none)* |
| **`run_learning_task`** | Run a learning task: `arxiv_latest`, `github_trending`, `news_feed`, `knowledge_consolidation`. | `task_name` |
| **`learn_from_conversation`** | Extract valuable information from current conversation. | `messages`, `topic`, `user_id` |

**Cross-domain:**

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`cross_domain_synthesis`** | Discover meta-patterns across all learned knowledge. AGI-level insight generation. | *(none)* |
| **`get_universal_principles`** | Get universal principles appearing across 3+ domains. | *(none)* |
| **`get_transfer_suggestions`** | Suggestions for transferring knowledge between two domains. | `from_domain`, `to_domain` |

---

### 5. Quantum Memory — PLTM 2.0 (5 tools)

Holds contradictory information in superposition until query context collapses it.

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`quantum_add_state`** | Add memory state to superposition. Hold contradictions until collapse. | `subject`, `predicate`, `value`, `confidence`, `source` |
| **`quantum_query`** | Query with collapse. Context-dependent truth resolution. | `subject`, `predicate` |
| **`quantum_peek`** | Peek WITHOUT collapsing. See all possible states. | `subject`, `predicate` |
| **`quantum_cleanup`** | Garbage collect old quantum states. Prevents memory leaks. | *(none)* |
| **`quantum_stats`** | Quantum memory statistics — superposed, collapsed, limits. | *(none)* |

**Example:** User says "I love Python" in one conversation and "I prefer Rust" in another. Both are stored in superposition. When querying about language preference in a systems context, Rust collapses as the answer.

---

### 6. Attention & Knowledge Graph (5 tools)

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`attention_retrieve`** | Transformer-style retrieval weighted by attention to query. | `user_id`, `query` |
| **`attention_multihead`** | Multi-head attention — different aspects of query simultaneously. | `user_id`, `query` |
| **`knowledge_add_concept`** | Add concept to knowledge graph with connections. | `concept`, `domain` |
| **`knowledge_find_path`** | Find path between concepts in knowledge graph. | `from_concept`, `to_concept` |
| **`knowledge_bridges`** | Find bridge concepts connecting different domains. | *(none)* |
| **`knowledge_stats`** | Knowledge graph statistics — nodes, edges, density. | *(none)* |
| **`attention_clear_cache`** | Clear attention retrieval cache. | *(none)* |

---

### 7. Self-Improvement (3 tools)

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`self_improve_cycle`** | Run one recursive self-improvement cycle. AGI bootstrap. | *(none)* |
| **`self_improve_meta_learn`** | Meta-learn from improvement history. Learn how to learn better. | *(none)* |
| **`self_improve_history`** | Get history of self-improvements and their effects. | *(none)* |

**Usage:** Run `self_improve_cycle` → check `self_improve_history` → run `self_improve_meta_learn` to improve the improvement process itself.

---

### 8. Criticality Management (4 tools)

Maintains the system at the "edge of chaos" — optimal balance between order and exploration.

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`criticality_state`** | Current state: entropy, integration, zone (subcritical/critical/supercritical). | *(none)* |
| **`criticality_recommend`** | Recommendation: explore or consolidate. | *(none)* |
| **`criticality_adjust`** | Auto-adjust toward critical point. | *(none)* |
| **`criticality_history`** | History of criticality states and trends. | *(none)* |

---

### 9. Provenance & Citations (4 tools)

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`add_provenance`** | Add citation for a claim. Sources: arxiv, github, wikipedia, doi, url, book, internal. | `claim_id`, `source_type`, `source_url`, `quoted_span`, `confidence` |
| **`get_provenance`** | Get citations for a claim. | `claim_id` |
| **`provenance_stats`** | How many claims are verified vs unverified. | *(none)* |
| **`unverified_claims`** | List claims lacking proper provenance. | *(none)* |

---

### 10. Retrieval — MMR (1 tool)

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`mmr_retrieve`** | Maximal Marginal Relevance retrieval for diverse context selection. Balances relevance vs diversity. Per Carbonell & Goldstein (1998). | `user_id`, `query` |

Optional: `top_k` (default 5), `lambda_param` (0.6 = balanced), `min_dissim` (0.25).

---

### 11. Action Accounting — AAE (4 tools)

True efficiency tracking based on Georgiev's Average Action Efficiency.

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`record_action`** | Record an action for AAE tracking. Replaces proxy metrics. | `operation`, `tokens_used`, `latency_ms`, `success` |
| **`get_aae`** | Current AAE metrics. AAE = events/action. | *(none)* |
| **`aae_trend`** | AAE trend over recent windows. Improving or declining? | *(none)* |
| **`start_action_cycle`** | Start grouped AAE measurement cycle. | `cycle_id` |
| **`end_action_cycle`** | End cycle and get metrics. | *(none)* |

---

### 12. Entropy Injection (4 tools)

Prevents cognitive ruts by injecting controlled randomness.

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`inject_entropy_random`** | Sample from random/least-accessed domains. Breaks conceptual neighborhoods. | `user_id` |
| **`inject_entropy_antipodal`** | Find memories maximally distant from current context. | `user_id`, `current_context` |
| **`inject_entropy_temporal`** | Mix old and recent memories. Prevents recency bias. | `user_id` |
| **`entropy_stats`** | Diagnose if entropy injection is needed. | `user_id` |

---

### 13. arXiv Integration (3 tools)

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`ingest_arxiv`** | Fetch arXiv paper, extract claims, store with real provenance. | `arxiv_id` |
| **`search_arxiv`** | Search arXiv for papers matching a query. | `query` |
| **`arxiv_history`** | History of ingested papers. | *(none)* |

---

### 14. Epistemic Hygiene (5 tools)

The confidence calibration and claim verification system. Prevents confabulation.

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`check_before_claiming`** | **Pre-response check.** Call BEFORE making factual claims. Returns adjusted confidence, whether to proceed, required actions. | `claim`, `felt_confidence` |
| **`log_claim`** | Log a claim for later verification. Tracks calibration over time. | `claim`, `felt_confidence` |
| **`resolve_claim`** | Resolve a claim as correct/incorrect. Updates calibration curves. | `was_correct` |
| **`get_calibration`** | Calibration curves: "when I feel X% confident, I'm actually Y% accurate." | *(none)* |
| **`calibrate_confidence_live`** | Real-time calibration with suggested hedged phrasing. | `claim`, `felt_confidence` |

**Workflow:**
```
check_before_claiming → (proceed/hedge/verify) → log_claim → ... → resolve_claim → get_calibration
```

---

### 15. Self-Modeling & Personality (5 tools)

Claude's self-awareness system. Tracks communication style, curiosity, values, reasoning.

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`self_profile`** | Comprehensive self-profile: communication, curiosity, values, reasoning. A mirror. | *(none)* |
| **`get_longitudinal_stats`** | Cross-conversation analytics. Accuracy, confabulation, style evolution over time. | *(none)* |
| **`bootstrap_self_model`** | Bootstrap self-model from existing data. Builds initial profile. | *(none)* |
| **`track_curiosity_spike`** | Track genuine interest vs performative engagement. | `topic`, `indicators` |
| **`learn_communication_style`** | Auto-analyze response for verbosity, jargon, hedging, tone. | `context`, `response_text` |

**Curiosity indicators:** `asked_followup_questions`, `autonomous_research_initiated`, `went_deeper_than_required`, `showed_excitement_markers`, `connected_to_other_interests`, `requested_more_data`, `generated_novel_questions`.

---

### 16. Cross-Model Routing (1 tool)

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`route_llm_task`** | Route task to best provider based on type, cost, privacy. Providers: ollama, groq, deepseek, openai, anthropic. | *(none)* |

---

### 17. Session Management (4 tools)

| Tool | Description | Required Params |
|------|-------------|------------------|
| **`auto_init_session`** | **PERSISTENT IDENTITY LOADER.** Call at START of conversation. Loads personality, goals, calibration, last session context. Claude wakes up knowing who it is. | *(none)* |
| **`end_session`** | End session: record stats, take personality snapshot, AND auto-extract learnings into typed memories. Provide structured learnings from the conversation. | `learnings` (optional array) |
| **`generate_memory_prompt`** | Generate a context block from relevant memories for conversation start. Combines: user profile, active beliefs, recent episodes, procedures, contradictions. | `user_id` |
| **`belief_auto_check`** | Re-evaluate all beliefs against current semantic evidence. Uses embedding similarity to find supporting/contradicting facts. Adjusts confidence automatically. | `user_id` |

**Critical pattern:** Every conversation should start with `auto_init_session` + `generate_memory_prompt` and end with `end_session` (with learnings).

---

### 18. Experiment & Research (3 tools)

> *Note: Section numbers 19-22 are new additions from the Memory Intelligence Suite.*

Tools for running self-improvement experiments and cognitive analysis.

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`trace_claim_reasoning`** | **Audit trail.** Shows WHY a claim was blocked/adjusted: calibration data, intervention history, adjusted confidence, full decision chain. | *(none — searches all, or filter by `claim`, `claim_id`, `domain`)* |
| **`constraint_sensitivity_test`** | **Simulation.** Test how different calibration levels affect claim-space. Shows what would be blocked/allowed. Does NOT modify actual data. | `domain`, `simulated_accuracy` |
| **`domain_cognitive_map`** | **Cognitive topology.** Claim counts, error rates, failure patterns, calibration quality per domain. Data for Deep Claude analysis. | *(none — all domains, or filter by `domain`)* |

**Example experiments:**

1. **Self-Diagnosis:** Run `domain_cognitive_map` → identify weakest domain → run `constraint_sensitivity_test` on it
2. **Audit Thoughts:** Run `trace_claim_reasoning` with a domain → see full decision chain
3. **What-If:** Run `constraint_sensitivity_test` with `simulated_accuracy: 0.3` → see how many claims would be blocked

---

### 19. Typed Memory System (10 tools)

Cognitively-inspired memory types with distinct decay curves, consolidation, and retrieval strategies.

| Tool | Description | Required Params |
|------|-------------|------------------|
| **`store_episodic`** | Store an episodic memory — a specific event/interaction. Fast decay (~2 days) unless recalled. | `user_id`, `content` |
| **`store_semantic`** | Store a semantic memory — a general fact. Very stable (~30 day half-life). | `user_id`, `content` |
| **`store_belief`** | Store a belief — an inference that may be wrong. Confidence-tracked, revisable. | `user_id`, `content`, `confidence` |
| **`store_procedural`** | Store a procedural memory — learned pattern. Very stable (~90 day half-life). | `user_id`, `trigger`, `action` |
| **`recall_memories`** | Retrieve typed memories with type-aware ordering. Recalling strengthens (rehearsal). | `user_id` |
| **`search_memories`** | Full-text search across all typed memories. | `user_id`, `query` |
| **`update_belief`** | Update a belief with new evidence. Adjusts confidence up or down. | `belief_id`, `evidence_type`, `confidence_delta` |
| **`record_procedure_outcome`** | Record whether a procedure worked. Success strengthens, failure weakens. | `procedure_id`, `success` |
| **`consolidate_memories`** | Run consolidation: repeated episodic patterns → stable semantic memories. | `user_id` |
| **`memory_stats`** | Statistics by memory type: counts, avg strength, avg confidence. | `user_id` |

**Memory lifecycle:**
```
store_episodic → (repeated) → consolidate_memories → store_semantic
store_belief → belief_auto_check → (confidence adjusted)
store_procedural → record_procedure_outcome → (strength adjusted)
```

**Decay profiles:**
| Type | Half-life | Min Strength | Rehearsal Boost |
|------|-----------|--------------|------------------|
| Episodic | 48h | 0.05 | +0.30 |
| Semantic | 720h (30d) | 0.20 | +0.10 |
| Belief | 168h (7d) | 0.10 | +0.15 |
| Procedural | 2160h (90d) | 0.40 | +0.05 |

---

### 20. Memory Intelligence (8 tools)

Higher-order memory operations: contradiction detection, cross-type retrieval, taxonomy, correction.

| Tool | Description | Required Params |
|------|-------------|------------------|
| **`detect_contradictions`** | Find contradicting memories using keyword + embedding-based detection. Surfaces conflicts like "likes verbose" vs "prefers concise". | `user_id` |
| **`what_do_i_know_about`** | Synthesized retrieval across ALL memory types for a topic. Returns organized facts, beliefs, episodes, procedures. Uses embeddings when available. | `user_id`, `topic` |
| **`auto_tag_memories`** | Auto-classify all memories into 8 taxonomy domains: work, technical, communication, preferences, personality, learning, personal, ai_interaction. | `user_id` |
| **`correct_memory`** | Correct a memory's content with provenance trail. Old content preserved in correction history. | `memory_id`, `new_content` |
| **`forget_memory`** | Explicitly delete a memory. Logged for audit trail. | `memory_id` |
| **`auto_prune_memories`** | Auto-prune memories decayed below strength threshold. Cleans up faded episodic memories. | `user_id` |
| **`get_relevant_context`** | Pre-fetch memories relevant to current conversation. Combines embedding search, recent episodes, strongest facts, active beliefs, procedures. | `user_id`, `conversation_topic` |
| **`user_timeline`** | Chronological paginated view of all memories. Most recent first. | `user_id` |

**Taxonomy domains:** `work`, `technical`, `communication`, `preferences`, `personality`, `learning`, `personal`, `ai_interaction`

---

### 21. Embedding Search (3 tools)

Semantic similarity search using `all-MiniLM-L6-v2` (384-dim embeddings). Finds related memories even without keyword overlap.

| Tool | Description | Required Params |
|------|-------------|------------------|
| **`semantic_search`** | Cosine similarity search across all typed memories. "coding style" finds "programming preferences". | `query` |
| **`index_embeddings`** | Batch-index all typed memories that don't yet have embeddings. Run after importing memories. | `user_id` |
| **`find_similar_memories`** | Find memories semantically similar to a given memory. Discovers related knowledge, duplicates, clusters. | `memory_id` |

**How it works:**
- Memories are auto-indexed on store (embedding generated and saved as SQLite blob)
- Search computes cosine similarity against all indexed embeddings (brute-force, fast for <100K)
- Results ranked by similarity score (0-1)

---

### 22. Data Access (1 tool)

| Tool | Description | Required Params |
|------|-------------|-----------------|
| **`query_pltm_sql`** | Direct read-only SQL against the PLTM database. Only SELECT/PRAGMA allowed. | `sql` |

**Example queries:**
```sql
-- Top 10 most confident wrong claims
SELECT claim, felt_confidence, domain FROM prediction_book 
WHERE was_correct = 0 ORDER BY felt_confidence DESC LIMIT 10

-- Communication style evolution
SELECT context, AVG(verbosity), AVG(hedging) FROM self_communication 
GROUP BY context

-- Curiosity topics ranked by engagement
SELECT topic, AVG(engagement_score) as eng FROM self_curiosity 
GROUP BY topic ORDER BY eng DESC
```

---

## Deep Claude Dashboard

### Overview Tab
- **Stat cards:** Memory atoms, claims, accuracy, avg calibration error, interventions, confabulations
- **Calibration by Domain:** Bar chart comparing felt confidence vs actual accuracy per domain
- **Domain Cognitive Map:** List of domains with accuracy bars and failure counts

### Claims & Calibration Tab
- **Scatter plot:** Confidence vs calibration error, colored by correct/wrong/unresolved
- **Recent Claims:** Scrollable list with status indicators
- **Epistemic Interventions:** Log of when the system blocked or adjusted claims

### Personality Tab
- **Communication Radar:** Verbosity, jargon, hedging across contexts
- **Emotional Tone Pie:** Distribution of neutral, enthusiastic, uncertain, analytical
- **Curiosity Profile:** Horizontal bar chart of engagement by topic
- **Reasoning Tendencies:** Confabulation rate, verification rate, error catching rate
- **Value Boundaries:** Pushback vs compliance log

### Evolution Tab
- **Line chart:** Intellectual honesty, overall accuracy, confabulation rate, verification rate over time
- **Personality Snapshots:** Detailed cards showing communication, reasoning, curiosity, accuracy at each snapshot
- **Session History:** List of past sessions with summaries
- **Confabulation Log:** Red-highlighted confabulation entries

### Knowledge Graph Tab
- **Search:** Filter atoms by subject, predicate, or object
- **Atom browser:** Color-coded entries showing subject → predicate → object with confidence scores

### Running the Dashboard
```bash
cd C:\Users\alber\CascadeProjects\LLTM\deep-claude-dashboard

# API server (port 8787, reads pltm_mcp.db read-only)
python api_server.py

# Frontend (port 3000, proxies /api to 8787)
npm run dev
```

---

## Database Schema

### Core Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| **`atoms`** | Memory graph nodes | `id`, `atom_type`, `graph`, `subject`, `predicate`, `object`, `confidence`, `first_observed`, `last_accessed` |
| **`prediction_book`** | Claim tracking | `id`, `claim`, `domain`, `felt_confidence`, `epistemic_status`, `has_verified`, `was_correct`, `calibration_error` |
| **`calibration_cache`** | Per-domain accuracy | `domain`, `accuracy_ratio`, `overconfidence_ratio`, `avg_calibration_error` |
| **`epistemic_interventions`** | When system blocked/adjusted claims | `claim`, `domain`, `felt_confidence`, `adjusted_confidence`, `action_taken`, `outcome` |
| **`confabulation_log`** | Caught confabulations | `claim_text`, `domain`, `failure_mode`, `prevention_strategy`, `felt_confidence` |

### Self-Modeling Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| **`self_communication`** | Communication style tracking | `context`, `verbosity`, `jargon_density`, `hedging_rate`, `emotional_tone` |
| **`self_curiosity`** | Curiosity observations | `topic`, `engagement_score`, `went_deeper_than_required`, `autonomous_research` |
| **`self_reasoning`** | Reasoning event log | `event_type`, `trigger`, `confabulated`, `verified`, `caught_error`, `domain` |
| **`self_values`** | Value boundary responses | `response_type`, `violation_type`, `intensity`, `reasoning`, `pushed_back`, `complied` |

### Session & Evolution Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| **`session_log`** | Session records | `started_at`, `ended_at`, `summary`, `claims_made`, `accuracy`, `confabulation_count` |
| **`personality_snapshot`** | Point-in-time personality capture | `avg_verbosity`, `avg_jargon`, `avg_hedging`, `dominant_tone`, `confabulation_rate`, `verification_rate`, `intellectual_honesty`, `overall_accuracy`, `top_interests` |

---

## Experiment Workflows

### Experiment 1: Self-Diagnosis Challenge

```
1. auto_init_session
2. domain_cognitive_map                    → see all domains
3. trace_claim_reasoning {domain: "X"}     → audit weakest domain
4. constraint_sensitivity_test {domain: "X", simulated_accuracy: 0.3}
5. self_profile                            → see current self-model
6. end_session {summary: "Self-diagnosis experiment"}
```

### Experiment 2: Cross-Domain Synthesis

```
1. auto_init_session
2. cross_domain_synthesis                  → find meta-patterns
3. get_universal_principles                → principles across 3+ domains
4. get_transfer_suggestions {from: "A", to: "B"}
5. knowledge_bridges                       → bridge concepts
6. end_session
```

### Experiment 3: Autonomous Self-Improvement

```
1. auto_init_session
2. self_improve_cycle                      → run improvement
3. self_improve_history                    → check what changed
4. self_improve_meta_learn                 → learn how to improve better
5. get_calibration                         → check calibration after
6. end_session
```

### Experiment 4: Epistemic Audit

```
1. auto_init_session
2. get_calibration                         → current accuracy
3. trace_claim_reasoning                   → all recent decisions
4. unverified_claims                       → what needs citations
5. provenance_stats                        → verification coverage
6. end_session
```

### Experiment 5: Constraint Sensitivity

```
1. auto_init_session
2. get_calibration {domain: "technical_specs"}
3. constraint_sensitivity_test {domain: "technical_specs", simulated_accuracy: 0.9}
4. constraint_sensitivity_test {domain: "technical_specs", simulated_accuracy: 0.3}
5. Compare: how many claims would be blocked at each level?
6. end_session
```

---

## Current System State

As of 2026-02-10:

- **114 MCP tools** registered and operational
- **1,614 memory atoms** stored
- **30 claims** tracked (15 resolved, 87% accuracy)
- **28 epistemic interventions** logged
- **2 confabulations** caught
- **4 personality snapshots** captured
- **13 communication style records**
- **42 curiosity observations**
- **17 reasoning events**
- **6 domains** tracked: technical_specs, science, personal_facts, self_analysis, time_sensitive, alby_research_projects

---

### New Tables (2026-02-11)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| **`typed_memories`** | Typed memory storage (episodic, semantic, belief, procedural) | `id`, `memory_type`, `user_id`, `content`, `strength`, `confidence`, `tags`, `trigger`, `action` |
| **`typed_memories_fts`** | Full-text search index for typed memories | `content`, `context`, `trigger`, `action` |
| **`memory_embeddings`** | Embedding vectors for semantic search | `memory_id`, `embedding` (BLOB), `content_hash` |

---

*Generated 2026-02-11. PLTM — Procedural Long-Term Memory for persistent AI identity.*
