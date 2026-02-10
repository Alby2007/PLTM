"""
PLTM MCP Server

Model Context Protocol server for Procedural Long-Term Memory system.
Provides tools for personality tracking, mood detection, and memory management.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def compact_json(obj) -> str:
    """Token-efficient JSON serialization - no whitespace"""
    return json.dumps(obj, separators=(',', ':'), default=str)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.types import Tool, TextContent

from src.storage.sqlite_store import SQLiteGraphStore
from src.pipeline.memory_pipeline import MemoryPipeline
from src.personality.personality_mood_agent import PersonalityMoodAgent
from src.personality.personality_synthesizer import PersonalitySynthesizer
from src.personality.mood_tracker import MoodTracker
from src.personality.mood_patterns import MoodPatterns
from src.personality.enhanced_conflict_resolver import EnhancedConflictResolver
from src.personality.contextual_personality import ContextualPersonality
from src.core.models import MemoryAtom, AtomType, Provenance, GraphType
from loguru import logger


# Initialize PLTM system
store: Optional[SQLiteGraphStore] = None
pipeline: Optional[MemoryPipeline] = None
personality_agent: Optional[PersonalityMoodAgent] = None
personality_synth: Optional[PersonalitySynthesizer] = None
mood_tracker: Optional[MoodTracker] = None
mood_patterns: Optional[MoodPatterns] = None
conflict_resolver: Optional[EnhancedConflictResolver] = None
contextual_personality: Optional[ContextualPersonality] = None


async def initialize_pltm():
    """Initialize PLTM system components"""
    global store, pipeline, personality_agent, personality_synth
    global mood_tracker, mood_patterns, conflict_resolver, contextual_personality
    
    # Initialize storage (absolute path so it works regardless of cwd)
    db_path = Path(__file__).parent.parent / "data" / "pltm_mcp.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = SQLiteGraphStore(db_path)
    await store.connect()
    
    # Initialize pipeline
    pipeline = MemoryPipeline(store)
    
    # Initialize personality/mood components
    personality_agent = PersonalityMoodAgent(pipeline)
    personality_synth = PersonalitySynthesizer(store)
    mood_tracker = MoodTracker(store)
    mood_patterns = MoodPatterns(store)
    conflict_resolver = EnhancedConflictResolver(store)
    contextual_personality = ContextualPersonality(store)
    
    logger.info("PLTM MCP Server initialized")


# Create MCP server
app = Server("pltm-memory")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available PLTM tools"""
    return [
        Tool(
            name="store_memory_atom",
            description="Store a memory atom in PLTM graph. Use this to remember facts, traits, or observations about the user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier"
                    },
                    "atom_type": {
                        "type": "string",
                        "enum": ["fact", "personality_trait", "communication_style", "interaction_pattern", "mood", "preference"],
                        "description": "Type of memory atom"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Subject of the atom (usually user_id)"
                    },
                    "predicate": {
                        "type": "string",
                        "description": "Relationship/predicate (e.g., 'prefers_style', 'has_trait', 'is_feeling')"
                    },
                    "object": {
                        "type": "string",
                        "description": "Object/value (e.g., 'concise responses', 'technical depth', 'frustrated')"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "context": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Context tags (e.g., ['technical', 'work'])"
                    }
                },
                "required": ["user_id", "atom_type", "subject", "predicate", "object"]
            }
        ),
        
        Tool(
            name="query_personality",
            description="Get synthesized personality profile for a user. Returns traits, communication style, and preferences.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context filter (e.g., 'technical', 'casual')"
                    }
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="detect_mood",
            description="Detect mood from user message. Returns detected mood and confidence.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier"
                    },
                    "message": {
                        "type": "string",
                        "description": "User's message to analyze"
                    }
                },
                "required": ["user_id", "message"]
            }
        ),
        
        Tool(
            name="get_mood_patterns",
            description="Get mood patterns and insights for a user. Returns temporal patterns, volatility, and predictions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier"
                    },
                    "window_days": {
                        "type": "number",
                        "description": "Number of days to analyze (default: 90)",
                        "minimum": 1
                    }
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="resolve_conflict",
            description="Resolve conflicting personality traits using enhanced conflict resolution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier"
                    },
                    "trait_objects": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of conflicting trait objects (e.g., ['concise', 'detailed'])"
                    }
                },
                "required": ["user_id", "trait_objects"]
            }
        ),
        
        Tool(
            name="extract_personality_traits",
            description="Extract personality traits from user interaction. Automatically learns from message style.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier"
                    },
                    "message": {
                        "type": "string",
                        "description": "User's message"
                    },
                    "ai_response": {
                        "type": "string",
                        "description": "AI's response (optional)"
                    },
                    "user_reaction": {
                        "type": "string",
                        "description": "User's reaction to AI response (optional)"
                    }
                },
                "required": ["user_id", "message"]
            }
        ),
        
        Tool(
            name="get_adaptive_prompt",
            description="Get adaptive system prompt based on user's personality and mood.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier"
                    },
                    "message": {
                        "type": "string",
                        "description": "Current user message"
                    },
                    "context": {
                        "type": "string",
                        "description": "Interaction context (optional)"
                    }
                },
                "required": ["user_id", "message"]
            }
        ),
        
        Tool(
            name="get_personality_summary",
            description="Get human-readable summary of user's personality.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier"
                    }
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="bootstrap_from_sample",
            description="Bootstrap PLTM with sample conversation data for quick testing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier"
                    }
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="bootstrap_from_messages",
            description="Bootstrap PLTM from conversation messages. Analyzes messages to extract personality.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier"
                    },
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"}
                            }
                        },
                        "description": "Conversation messages to analyze"
                    }
                },
                "required": ["user_id", "messages"]
            }
        ),
        
        Tool(
            name="track_trait_evolution",
            description="Track how a personality trait has evolved over time. Shows timeline, trend, inflection points.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "trait": {"type": "string", "description": "Trait to track (e.g., 'direct', 'technical')"},
                    "window_days": {"type": "number", "default": 90}
                },
                "required": ["user_id", "trait"]
            }
        ),
        
        Tool(
            name="predict_reaction",
            description="Predict how user will react to a stimulus based on causal patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "stimulus": {"type": "string", "description": "What you're about to say/do"}
                },
                "required": ["user_id", "stimulus"]
            }
        ),
        
        Tool(
            name="get_meta_patterns",
            description="Get cross-context patterns - behaviors that appear across multiple domains.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"}
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="learn_from_interaction",
            description="Learn from an interaction - what worked, what didn't, update model.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "my_response": {"type": "string", "description": "What I (AI) said"},
                    "user_reaction": {"type": "string", "description": "How user responded"}
                },
                "required": ["user_id", "my_response", "user_reaction"]
            }
        ),
        
        Tool(
            name="predict_session",
            description="Predict session dynamics from greeting. Infer mood and adapt immediately.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "greeting": {"type": "string", "description": "User's opening message"}
                },
                "required": ["user_id", "greeting"]
            }
        ),
        
        Tool(
            name="get_self_model",
            description="Get explicit self-model for meta-cognition. See what I know about user and my confidence.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"}
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="init_claude_session",
            description="Initialize Claude personality session. Call at START of conversation to load Claude's evolved style for this user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"}
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="update_claude_style",
            description="Update Claude's communication style for this user. Called when learning how to communicate better.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "attribute": {"type": "string", "description": "Style attribute: verbosity, formality, initiative, code_preference, energy_matching"},
                    "value": {"type": "string", "description": "New value for the attribute"}
                },
                "required": ["user_id", "attribute", "value"]
            }
        ),
        
        Tool(
            name="learn_interaction_dynamic",
            description="Learn what works or doesn't work with this user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "behavior": {"type": "string", "description": "The behavior/approach (e.g., 'immediate_execution_no_asking')"},
                    "works": {"type": "boolean", "description": "True if it works well, False if should avoid"}
                },
                "required": ["user_id", "behavior", "works"]
            }
        ),
        
        Tool(
            name="record_milestone",
            description="Record a collaboration milestone.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "description": {"type": "string", "description": "Milestone description"},
                    "significance": {"type": "number", "default": 0.8}
                },
                "required": ["user_id", "description"]
            }
        ),
        
        Tool(
            name="add_shared_vocabulary",
            description="Add a shared term/shorthand between Claude and user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "term": {"type": "string"},
                    "meaning": {"type": "string"}
                },
                "required": ["user_id", "term", "meaning"]
            }
        ),
        
        Tool(
            name="get_claude_personality",
            description="Get Claude's personality summary for this user - style, dynamics, shared context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"}
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="evolve_claude_personality",
            description="Evolve Claude's personality based on interaction outcome. Core learning loop.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "my_response_style": {"type": "string", "description": "How Claude responded (e.g., 'verbose_explanation')"},
                    "user_reaction": {"type": "string", "description": "User's reaction"},
                    "was_positive": {"type": "boolean", "description": "Was the reaction positive?"}
                },
                "required": ["user_id", "my_response_style", "user_reaction", "was_positive"]
            }
        ),
        
        Tool(
            name="check_pltm_available",
            description="Quick check if user has PLTM data. Call this FIRST in any conversation to decide if to init. Returns should_init=true if personality exists.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"}
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="pltm_mode",
            description="Trigger phrase handler. When user says 'PLTM mode' or 'init PLTM', call this to auto-initialize and return full context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "trigger_phrase": {"type": "string", "description": "The trigger phrase used (e.g., 'PLTM mode')"}
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="deep_personality_analysis",
            description="Run comprehensive personality analysis from all conversation history. Extracts temporal patterns, emotional triggers, communication evolution, domain expertise, collaboration style.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"}
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="enrich_claude_personality",
            description="Build rich, nuanced Claude personality from deep analysis. Returns detailed traits, learned preferences, emotional intelligence, meta-awareness.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "store_results": {"type": "boolean", "default": True, "description": "Whether to persist the rich personality"}
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="learn_from_url",
            description="Learn from any URL content. Extracts facts, concepts, relationships. AGI path - continuous learning from web.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Source URL"},
                    "content": {"type": "string", "description": "Text content from the URL"},
                    "source_type": {"type": "string", "description": "Optional: web_page, research_paper, code_repository, conversation, transcript"}
                },
                "required": ["url", "content"]
            }
        ),
        
        Tool(
            name="learn_from_paper",
            description="Learn from a research paper. Extracts findings, methodologies, results. For arXiv, journals, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string", "description": "Paper ID (e.g., arXiv ID)"},
                    "title": {"type": "string"},
                    "abstract": {"type": "string"},
                    "content": {"type": "string", "description": "Full paper text"},
                    "authors": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["paper_id", "title", "abstract", "content", "authors"]
            }
        ),
        
        Tool(
            name="learn_from_code",
            description="Learn from a code repository. Extracts design patterns, techniques, API patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {"type": "string"},
                    "repo_name": {"type": "string"},
                    "description": {"type": "string"},
                    "languages": {"type": "array", "items": {"type": "string"}},
                    "code_samples": {"type": "array", "items": {"type": "object"}, "description": "Array of {file, code} objects"}
                },
                "required": ["repo_url", "repo_name", "languages", "code_samples"]
            }
        ),
        
        Tool(
            name="get_learning_stats",
            description="Get statistics about learned knowledge - how many sources, domains, facts.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="batch_ingest_wikipedia",
            description="Batch ingest Wikipedia articles. Pass array of {title, content, url} objects.",
            inputSchema={
                "type": "object",
                "properties": {
                    "articles": {"type": "array", "items": {"type": "object"}, "description": "Array of {title, content, url}"}
                },
                "required": ["articles"]
            }
        ),
        
        Tool(
            name="batch_ingest_papers",
            description="Batch ingest research papers. Pass array of paper objects with id, title, abstract, content, authors.",
            inputSchema={
                "type": "object",
                "properties": {
                    "papers": {"type": "array", "items": {"type": "object"}, "description": "Array of paper objects"}
                },
                "required": ["papers"]
            }
        ),
        
        Tool(
            name="batch_ingest_repos",
            description="Batch ingest GitHub repositories. Pass array of repo objects with url, name, languages, code_samples.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repos": {"type": "array", "items": {"type": "object"}, "description": "Array of repo objects"}
                },
                "required": ["repos"]
            }
        ),
        
        Tool(
            name="get_learning_schedule",
            description="Get status of continuous learning schedules - what tasks are running, when they last ran.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="run_learning_task",
            description="Run a specific learning task immediately: arxiv_latest, github_trending, news_feed, knowledge_consolidation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_name": {"type": "string", "description": "Task to run: arxiv_latest, github_trending, news_feed, knowledge_consolidation"}
                },
                "required": ["task_name"]
            }
        ),
        
        Tool(
            name="cross_domain_synthesis",
            description="Run cross-domain synthesis to discover meta-patterns across all learned knowledge. AGI-level insight generation.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="get_universal_principles",
            description="Get discovered universal principles that appear across 3+ domains.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="get_transfer_suggestions",
            description="Get suggestions for transferring knowledge between two domains.",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_domain": {"type": "string"},
                    "to_domain": {"type": "string"}
                },
                "required": ["from_domain", "to_domain"]
            }
        ),
        
        Tool(
            name="learn_from_conversation",
            description="Learn from current conversation - extract valuable information worth remembering.",
            inputSchema={
                "type": "object",
                "properties": {
                    "messages": {"type": "array", "items": {"type": "object"}, "description": "Array of {role, content} messages"},
                    "topic": {"type": "string"},
                    "user_id": {"type": "string"}
                },
                "required": ["messages", "topic", "user_id"]
            }
        ),
        
        # PLTM 2.0 - Universal Optimization Principles
        Tool(
            name="quantum_add_state",
            description="Add memory state to superposition. Hold contradictions until query collapse.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "predicate": {"type": "string"},
                    "value": {"type": "string"},
                    "confidence": {"type": "number"},
                    "source": {"type": "string"}
                },
                "required": ["subject", "predicate", "value", "confidence", "source"]
            }
        ),
        
        Tool(
            name="quantum_query",
            description="Query superposition with collapse. Context-dependent truth resolution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "predicate": {"type": "string"},
                    "context": {"type": "string", "description": "Optional context for collapse"}
                },
                "required": ["subject", "predicate"]
            }
        ),
        
        Tool(
            name="quantum_peek",
            description="Peek at superposition WITHOUT collapsing. See all possible states.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "predicate": {"type": "string"}
                },
                "required": ["subject", "predicate"]
            }
        ),
        
        Tool(
            name="attention_retrieve",
            description="Retrieve memories weighted by attention to query. IMPORTANT: Use 'domain' to filter by knowledge area (e.g. 'science', 'geopolitics', 'military', 'north_korea', 'cyber', 'economics'). Without domain, returns mixed results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "default": 10},
                    "domain": {"type": "string", "description": "Filter by domain: science, geopolitics, military, north_korea, cyber, economics, energy, etc. STRONGLY RECOMMENDED."}
                },
                "required": ["user_id", "query"]
            }
        ),
        
        Tool(
            name="attention_multihead",
            description="Multi-head attention retrieval - different scoring strategies. Use 'domain' to filter by knowledge area and avoid mixing geopolitical/scientific results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "query": {"type": "string"},
                    "num_heads": {"type": "integer", "default": 4},
                    "domain": {"type": "string", "description": "Filter by domain: science, geopolitics, military, north_korea, cyber, economics, energy, etc. STRONGLY RECOMMENDED."}
                },
                "required": ["user_id", "query"]
            }
        ),
        
        Tool(
            name="knowledge_add_concept",
            description="Add concept to knowledge graph with connections. Network effects.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {"type": "string"},
                    "domain": {"type": "string"},
                    "related_concepts": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["concept", "domain"]
            }
        ),
        
        Tool(
            name="knowledge_find_path",
            description="Find path between concepts in knowledge graph.",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_concept": {"type": "string"},
                    "to_concept": {"type": "string"}
                },
                "required": ["from_concept", "to_concept"]
            }
        ),
        
        Tool(
            name="knowledge_bridges",
            description="Find bridge concepts connecting different domains.",
            inputSchema={
                "type": "object",
                "properties": {
                    "top_k": {"type": "integer", "default": 10}
                },
                "required": []
            }
        ),
        
        Tool(
            name="knowledge_stats",
            description="Get knowledge graph statistics - nodes, edges, density.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="self_improve_cycle",
            description="Run one recursive self-improvement cycle. AGI bootstrap.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="self_improve_meta_learn",
            description="Meta-learn from improvement history. Learn how to learn better.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="self_improve_history",
            description="Get history of self-improvements and their effects.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="quantum_cleanup",
            description="Garbage collect old quantum states. Prevents memory leaks.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="quantum_stats",
            description="Get quantum memory statistics - superposed, collapsed, limits.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="attention_clear_cache",
            description="Clear attention retrieval cache.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="criticality_state",
            description="Get current criticality state - entropy, integration, zone (subcritical/critical/supercritical).",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="criticality_recommend",
            description="Get recommendation for maintaining criticality - explore or consolidate.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="criticality_adjust",
            description="Auto-adjust system toward critical point (edge of chaos).",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="criticality_history",
            description="Get history of criticality states and trends.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="add_provenance",
            description="Add provenance (citation) for a claim. Required for verifiable claims.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string", "description": "ID of the atom/claim"},
                    "source_type": {"type": "string", "enum": ["arxiv", "github", "wikipedia", "doi", "url", "book", "internal"], "description": "Type of source"},
                    "source_url": {"type": "string", "description": "Full URL or identifier"},
                    "source_title": {"type": "string", "description": "Paper title, repo name, etc."},
                    "quoted_span": {"type": "string", "description": "Exact text supporting the claim"},
                    "page_or_section": {"type": "string", "description": "Location in source (e.g., p.3, §2.1)"},
                    "confidence": {"type": "number", "description": "How directly source supports claim (0-1)"},
                    "arxiv_id": {"type": "string", "description": "arXiv ID if applicable"},
                    "authors": {"type": "string", "description": "Comma-separated author names"}
                },
                "required": ["claim_id", "source_type", "source_url", "quoted_span", "confidence"]
            }
        ),
        
        Tool(
            name="get_provenance",
            description="Get provenance (citations) for a claim.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string", "description": "ID of the atom/claim"}
                },
                "required": ["claim_id"]
            }
        ),
        
        Tool(
            name="provenance_stats",
            description="Get provenance statistics - how many claims are verified vs unverified.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="unverified_claims",
            description="Get list of claims that lack proper provenance (need citations).",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="mmr_retrieve",
            description="MMR (Maximal Marginal Relevance) retrieval for diverse context selection. Per Carbonell & Goldstein (1998).",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "query": {"type": "string", "description": "Query/context for retrieval"},
                    "top_k": {"type": "integer", "description": "Number of diverse items to return (default 5)"},
                    "lambda_param": {"type": "number", "description": "Relevance weight 0-1 (0.6=balanced, higher=more relevant, lower=more diverse)"},
                    "min_dissim": {"type": "number", "description": "Minimum dissimilarity threshold (default 0.25)"}
                },
                "required": ["user_id", "query"]
            }
        ),
        
        # === TRUE ACTION ACCOUNTING (Georgiev AAE) ===
        Tool(
            name="record_action",
            description="Record an action/operation for true AAE (Average Action Efficiency) tracking. Replaces proxy metrics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "description": "Operation type: hypothesis_gen, memory_store, retrieval, inference, etc."},
                    "tokens_used": {"type": "integer", "description": "Actual token count consumed"},
                    "latency_ms": {"type": "number", "description": "Wall-clock time in milliseconds"},
                    "success": {"type": "boolean", "description": "Whether operation achieved its goal"},
                    "context": {"type": "string", "description": "Optional context string"}
                },
                "required": ["operation", "tokens_used", "latency_ms", "success"]
            }
        ),
        
        Tool(
            name="get_aae",
            description="Get current AAE (Average Action Efficiency) metrics. AAE = events/action, unit_action = action/events.",
            inputSchema={
                "type": "object",
                "properties": {
                    "last_n": {"type": "integer", "description": "Only consider last N records (default: all)"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="aae_trend",
            description="Get AAE trend over recent windows. Shows if efficiency is improving/declining.",
            inputSchema={
                "type": "object",
                "properties": {
                    "window_size": {"type": "integer", "description": "Records per window (default 10)"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="start_action_cycle",
            description="Start a new action measurement cycle for grouped AAE tracking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cycle_id": {"type": "string", "description": "Unique cycle identifier (e.g., C21, C22)"}
                },
                "required": ["cycle_id"]
            }
        ),
        
        Tool(
            name="end_action_cycle",
            description="End current action cycle and get AAE metrics for that cycle.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cycle_id": {"type": "string", "description": "Cycle ID to end (default: current)"}
                },
                "required": []
            }
        ),
        
        # === ENTROPY INJECTION ===
        Tool(
            name="inject_entropy_random",
            description="Inject entropy by sampling from random/least-accessed domains. Breaks conceptual neighborhoods.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "n_domains": {"type": "integer", "description": "Number of domains to sample (default 3)"},
                    "memories_per_domain": {"type": "integer", "description": "Memories per domain (default 2)"}
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="inject_entropy_antipodal",
            description="Inject entropy by finding memories maximally distant from current context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "current_context": {"type": "string", "description": "Current context to find distant memories from"},
                    "n_memories": {"type": "integer", "description": "Number of distant memories to find (default 5)"}
                },
                "required": ["user_id", "current_context"]
            }
        ),
        
        Tool(
            name="inject_entropy_temporal",
            description="Inject entropy by mixing old and recent memories. Prevents recency bias.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "n_old": {"type": "integer", "description": "Number of old memories (default 3)"},
                    "n_recent": {"type": "integer", "description": "Number of recent memories (default 2)"}
                },
                "required": ["user_id"]
            }
        ),
        
        Tool(
            name="entropy_stats",
            description="Get entropy statistics for a user. Diagnoses if entropy injection is needed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"}
                },
                "required": ["user_id"]
            }
        ),
        
        # === ARXIV INGESTION (Real Provenance) ===
        Tool(
            name="ingest_arxiv_paper",
            description="Ingest a SINGLE arXiv paper by ID: fetch metadata, extract claims, store with REAL provenance (URL, authors, quoted spans). For batch search, use ingest_arxiv instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "arxiv_id": {"type": "string", "description": "ArXiv paper ID (e.g., '1706.03762' for Attention paper)"},
                    "user_id": {"type": "string", "description": "User/subject to store claims under (default: pltm_knowledge)"}
                },
                "required": ["arxiv_id"]
            }
        ),
        
        Tool(
            name="search_arxiv",
            description="Search arXiv for papers matching a query. Returns paper IDs for ingestion.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (title, abstract, author)"},
                    "max_results": {"type": "integer", "description": "Maximum papers to return (default 5)"}
                },
                "required": ["query"]
            }
        ),
        
        Tool(
            name="arxiv_history",
            description="Get history of ingested arXiv papers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "last_n": {"type": "integer", "description": "Number of recent ingestions (default 10)"}
                },
                "required": []
            }
        ),
        
        # === AGI BREAKTHROUGH ENGINE ===
        Tool(
            name="breakthrough_synthesize",
            description="Run LLM-powered cross-domain synthesis. Claude reasons over knowledge subgraphs to find non-obvious connections. AGI discovery engine.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain_a": {"type": "string", "description": "First domain (e.g., 'physics')"},
                    "domain_b": {"type": "string", "description": "Second domain (e.g., 'economics')"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="generate_hypotheses",
            description="Generate novel testable hypotheses from accumulated knowledge using Claude. Optionally guided by open research questions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domains": {"type": "array", "items": {"type": "string"}, "description": "Domains to focus on"},
                    "questions": {"type": "array", "items": {"type": "string"}, "description": "Open questions to address"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="evaluate_hypothesis",
            description="Evaluate a hypothesis against accumulated evidence using Claude.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hypothesis": {"type": "string", "description": "The hypothesis to evaluate"},
                    "domains": {"type": "array", "items": {"type": "string"}, "description": "Domains to search for evidence"}
                },
                "required": ["hypothesis"]
            }
        ),
        
        Tool(
            name="find_analogies",
            description="Find structural analogies for a concept between two domains using Claude.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {"type": "string", "description": "Concept to find analogies for"},
                    "source_domain": {"type": "string", "description": "Domain the concept is from"},
                    "target_domain": {"type": "string", "description": "Domain to find analogies in"}
                },
                "required": ["concept", "source_domain", "target_domain"]
            }
        ),
        
        Tool(
            name="bulk_store",
            description="Store multiple knowledge atoms in one call. Pass an array of atoms. Use this after web search to store all extracted intelligence at once.",
            inputSchema={
                "type": "object",
                "properties": {
                    "atoms": {"type": "array", "items": {"type": "object"}, "description": "Array of atoms: [{subject, predicate, object, confidence, context:[domain_tags], user_id}]"}
                },
                "required": ["atoms"]
            }
        ),
        
        Tool(
            name="deep_extract",
            description="Extract and store structured knowledge. Mode 1: pass 'triples' array to store directly [{s,p,o,c,d}]. Mode 2: pass 'content' text to get extraction instructions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Text content to extract knowledge from"},
                    "source_type": {"type": "string", "description": "Type: general, research_paper, code, news (default: general)"},
                    "triples": {"type": "array", "items": {"type": "object"}, "description": "Pre-extracted triples [{s:'subject',p:'predicate',o:'object',c:0.7,d:'domain'}]"}
                },
                "required": []
            }
        ),
        
        # === RESEARCH AGENDA ===
        Tool(
            name="add_research_question",
            description="Add an open research question to the agenda. The system will evaluate incoming knowledge against it.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The research question"},
                    "domains": {"type": "array", "items": {"type": "string"}, "description": "Relevant domains"},
                    "priority": {"type": "number", "description": "Priority 0-1 (default 0.5)"}
                },
                "required": ["question"]
            }
        ),
        
        Tool(
            name="get_research_agenda",
            description="Get active research questions with their status and evidence counts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max questions to return (default 10)"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="evaluate_agenda",
            description="Check if recent knowledge answers any open research questions. Uses FTS matching (no LLM cost).",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Optional: only check atoms for this subject"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="suggest_research_searches",
            description="Claude suggests targeted search queries to answer a research question.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question_id": {"type": "string", "description": "ID of the research question"}
                },
                "required": ["question_id"]
            }
        ),
        
        Tool(
            name="close_research_question",
            description="Mark a research question as answered or closed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question_id": {"type": "string", "description": "ID of the question"},
                    "answer": {"type": "string", "description": "The answer (if answered)"},
                    "status": {"type": "string", "description": "New status: answered, closed (default: answered)"}
                },
                "required": ["question_id"]
            }
        ),
        
        # === ANALYSIS TOOLS ===
        Tool(
            name="calculate_phi_integration",
            description="Calculate Φ (integrated information) for a domain. Measures how interconnected and interdependent the knowledge is. Returns Φ score (0-1), sub-scores, and vulnerability. Optionally returns timeseries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain to calculate Φ for (e.g. 'military_strategy', 'infrastructure')"},
                    "return_timeseries": {"type": "boolean", "description": "Include historical Φ values (default: false)"},
                    "all_domains": {"type": "boolean", "description": "Calculate Φ for ALL domains at once (default: false)"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="create_indicator_tracker",
            description="Create or update a tracked indicator with threshold alerting. Use update_indicator to set new values.",
            inputSchema={
                "type": "object",
                "properties": {
                    "indicator_id": {"type": "string", "description": "Unique ID (e.g. 'PLA_readiness', 'ukraine_energy_capacity')"},
                    "name": {"type": "string", "description": "Human-readable name"},
                    "domain": {"type": "string", "description": "Domain this indicator belongs to"},
                    "threshold": {"type": "number", "description": "Alert threshold value"},
                    "direction": {"type": "string", "description": "'above' = alert when >= threshold, 'below' = alert when <= threshold (default: above)"},
                    "check_frequency": {"type": "string", "description": "How often to check: daily, weekly, monthly (default: weekly)"},
                    "initial_value": {"type": "number", "description": "Starting value (default: 0)"}
                },
                "required": ["indicator_id", "name", "domain", "threshold"]
            }
        ),
        
        Tool(
            name="update_indicator",
            description="Update an indicator's value. Automatically checks threshold and returns alert if breached.",
            inputSchema={
                "type": "object",
                "properties": {
                    "indicator_id": {"type": "string", "description": "ID of the indicator to update"},
                    "value": {"type": "number", "description": "New value"},
                    "note": {"type": "string", "description": "Optional note about this update"}
                },
                "required": ["indicator_id", "value"]
            }
        ),
        
        Tool(
            name="check_indicators",
            description="Check all tracked indicators. Returns status, breaches, and stale indicators needing update.",
            inputSchema={
                "type": "object",
                "properties": {
                    "indicator_id": {"type": "string", "description": "Optional: check specific indicator history only"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="simulate_cascade",
            description="Simulate multi-domain cascade effects from trigger events. Models how disruptions propagate across military, economic, energy, cyber, infrastructure domains. Returns Φ trajectories and critical failure points.",
            inputSchema={
                "type": "object",
                "properties": {
                    "trigger_events": {"type": "array", "items": {"type": "object"}, "description": "Array of triggers: [{domain:'military', event:'taiwan_blockade', severity:0.8}]"},
                    "domains": {"type": "array", "items": {"type": "string"}, "description": "Domains to simulate (default: all connected)"},
                    "timeline": {"type": "string", "description": "Scenario label (e.g. '2027-Q2')"},
                    "max_steps": {"type": "integer", "description": "Max propagation steps (default: 10)"},
                    "initial_phi": {"type": "object", "description": "Starting Φ per domain (default: 0.7 for all)"},
                    "custom_dependencies": {"type": "array", "items": {"type": "object"}, "description": "Custom domain links: [{source, target, weight}]"}
                },
                "required": ["trigger_events"]
            }
        ),
        
        Tool(
            name="query_structured_data",
            description="Query structured data sources: opensky_flights (ADS-B), world_bank (economic indicators), un_comtrade (trade data), ais_ship_tracking, acled_conflict. Returns data or manual search instructions if API unavailable.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Data source ID: opensky_flights, world_bank, un_comtrade, ais_ship_tracking, acled_conflict"},
                    "params": {"type": "object", "description": "Source-specific params. opensky: {region}. world_bank: {indicator, country, date_range}. comtrade: {reporter, partner, commodity, year, flow}"},
                    "list_sources": {"type": "boolean", "description": "If true, just list available sources"}
                },
                "required": []
            }
        ),
        
        # === STATE PERSISTENCE ===
        Tool(
            name="save_state",
            description="Save state that persists across conversations. Use for work-in-progress, analysis checkpoints, session data. Survives conversation end.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Unique key for this state (e.g. 'darkfall_analysis', 'china_gold_tracking')"},
                    "value": {"description": "Any JSON-serializable value to persist"},
                    "category": {"type": "string", "description": "Category: analysis, tracking, config, session (default: general)"}
                },
                "required": ["key", "value"]
            }
        ),
        
        Tool(
            name="load_state",
            description="Load previously saved state. Use at conversation start to resume work.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key to load"},
                    "list_all": {"type": "boolean", "description": "If true, list all saved states instead of loading one"},
                    "category": {"type": "string", "description": "Filter list by category"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="delete_state",
            description="Delete a saved state.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key to delete"}
                },
                "required": ["key"]
            }
        ),
        
        # === GOAL MANAGEMENT ===
        Tool(
            name="create_goal",
            description="Create a persistent goal with optional plan steps. Goals survive across conversations. Use for long-term objectives.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short goal title"},
                    "description": {"type": "string", "description": "Detailed description"},
                    "category": {"type": "string", "description": "Category: intelligence, research, monitoring, development (default: general)"},
                    "priority": {"type": "string", "description": "high, medium, low (default: medium)"},
                    "success_criteria": {"type": "array", "items": {"type": "string"}, "description": "List of success criteria"},
                    "plan": {"type": "array", "items": {"type": "object"}, "description": "Plan steps: [{description, id (optional), status (optional)}]"},
                    "deadline": {"type": "string", "description": "Deadline (e.g. '2026-12-31')"},
                    "parent_goal_id": {"type": "string", "description": "Parent goal ID for sub-goals"}
                },
                "required": ["title", "description"]
            }
        ),
        
        Tool(
            name="update_goal",
            description="Update goal progress, status, blockers, or plan steps.",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {"type": "string", "description": "Goal ID to update"},
                    "progress": {"type": "number", "description": "Progress 0.0-1.0"},
                    "status": {"type": "string", "description": "active, completed, paused, blocked, abandoned"},
                    "add_blocker": {"type": "string", "description": "Add a blocker"},
                    "remove_blocker": {"type": "string", "description": "Remove a blocker"},
                    "complete_step": {"type": "string", "description": "Mark a plan step as completed (by step ID)"},
                    "add_step": {"type": "object", "description": "Add a new plan step: {description, id (optional)}"},
                    "note": {"type": "string", "description": "Note about this update"}
                },
                "required": ["goal_id"]
            }
        ),
        
        Tool(
            name="get_goals",
            description="Get all goals. Use at conversation start to see what's active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter: active, completed, paused, blocked"},
                    "category": {"type": "string", "description": "Filter by category"},
                    "include_log": {"type": "boolean", "description": "Include activity log (default: false)"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="delete_goal",
            description="Delete a goal and its history.",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal_id": {"type": "string", "description": "Goal ID to delete"}
                },
                "required": ["goal_id"]
            }
        ),
        
        # === DIRECT SQL ===
        Tool(
            name="query_pltm_sql",
            description="Execute a raw SQL query against the PLTM database. SELECT only. For maximum flexibility when pre-built tools are too limited. Tables: atoms, phi_snapshots, indicators, indicator_history, goals, goal_log, scheduled_tasks, task_runs, conversation_state, secrets, api_profiles.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL SELECT query"},
                    "params": {"type": "array", "description": "Query parameters for ? placeholders"},
                    "limit": {"type": "integer", "description": "Max rows to return (default: 50)"}
                },
                "required": ["sql"]
            }
        ),
        
        # === TASK SCHEDULER ===
        Tool(
            name="schedule_task",
            description="Schedule a recurring task. Tasks persist and can be checked at conversation start. Types: tool_call (auto-run a tool), script (run a script), reminder (remind Claude to do something).",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Task name"},
                    "description": {"type": "string", "description": "What this task does"},
                    "task_type": {"type": "string", "description": "tool_call, script, or reminder"},
                    "schedule": {"type": "string", "description": "hourly, every_6h, every_12h, daily, every_2d, every_3d, weekly, biweekly, monthly"},
                    "tool_name": {"type": "string", "description": "For tool_call type: which MCP tool to call"},
                    "tool_args": {"type": "object", "description": "For tool_call type: arguments to pass"},
                    "script_path": {"type": "string", "description": "For script type: path to script"},
                    "max_runs": {"type": "integer", "description": "Max number of runs before auto-completing"}
                },
                "required": ["name", "description", "task_type", "schedule"]
            }
        ),
        
        Tool(
            name="check_scheduled_tasks",
            description="Check for due/overdue tasks. Call this at conversation start to see what needs doing.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="mark_task_done",
            description="Mark a scheduled task run as completed. Advances to next due time.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "result": {"type": "string", "description": "Result/notes from this run"},
                    "status": {"type": "string", "description": "success or failed (default: success)"}
                },
                "required": ["task_id"]
            }
        ),
        
        Tool(
            name="manage_task",
            description="Pause, resume, or delete a scheduled task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "action": {"type": "string", "description": "pause, resume, or delete"}
                },
                "required": ["task_id", "action"]
            }
        ),
        
        # === CRYPTOGRAPHY ===
        Tool(
            name="encrypt_data",
            description="Encrypt data using AES (Fernet). Optional password-based encryption.",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Data to encrypt"},
                    "password": {"type": "string", "description": "Optional password (uses stored key if omitted)"}
                },
                "required": ["data"]
            }
        ),
        
        Tool(
            name="decrypt_data",
            description="Decrypt previously encrypted data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "encrypted_data": {"type": "string", "description": "Encrypted data string"},
                    "password": {"type": "string", "description": "Password used for encryption (if any)"},
                    "method": {"type": "string", "description": "Encryption method (default: fernet_aes128)"}
                },
                "required": ["encrypted_data"]
            }
        ),
        
        Tool(
            name="manage_secrets",
            description="Store, retrieve, list, or delete encrypted secrets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "store, get, list, delete"},
                    "name": {"type": "string", "description": "Secret name"},
                    "value": {"type": "string", "description": "Secret value (for store action)"},
                    "category": {"type": "string", "description": "Category for organization"},
                    "password": {"type": "string", "description": "Optional encryption password"}
                },
                "required": ["action"]
            }
        ),
        
        Tool(
            name="hash_data",
            description="Hash data with SHA-256, SHA-512, MD5, or SHA-1. Also supports HMAC signing and verification.",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Data to hash"},
                    "algorithm": {"type": "string", "description": "sha256, sha512, md5, sha1 (default: sha256)"},
                    "hmac_key": {"type": "string", "description": "If provided, creates HMAC signature instead of plain hash"},
                    "verify_signature": {"type": "string", "description": "If provided with hmac_key, verifies this signature"}
                },
                "required": ["data"]
            }
        ),
        
        # === SYSTEM CONTEXT ===
        Tool(
            name="get_system_context",
            description="Get system context: time, OS, resources (CPU/RAM/disk), environment, PLTM status (atom count, active goals, due tasks, breached indicators). Call at conversation start for situational awareness.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        # === API CLIENT ===
        Tool(
            name="api_request",
            description="Make authenticated HTTP requests with rate-limit tracking. Supports Bearer, API key, Basic auth. Can save API profiles for reuse.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to request (or path if using profile)"},
                    "method": {"type": "string", "description": "GET, POST, PUT, DELETE, PATCH (default: GET)"},
                    "profile_id": {"type": "string", "description": "Saved API profile to use"},
                    "headers": {"type": "object", "description": "Custom headers"},
                    "body": {"description": "Request body (auto-serialized to JSON if object)"},
                    "auth_type": {"type": "string", "description": "none, bearer, api_key, basic, header"},
                    "auth_value": {"type": "string", "description": "Auth token/key/user:pass"},
                    "params": {"type": "object", "description": "Query parameters"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default: 15)"}
                },
                "required": ["url"]
            }
        ),
        
        Tool(
            name="manage_api_profile",
            description="Create, list, or delete saved API profiles for reuse.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "create, list, delete"},
                    "profile_id": {"type": "string", "description": "Profile ID"},
                    "base_url": {"type": "string", "description": "Base URL for the API"},
                    "auth_type": {"type": "string", "description": "none, bearer, api_key, basic, header"},
                    "auth_value": {"type": "string", "description": "Auth credential"},
                    "headers": {"type": "object", "description": "Default headers"},
                    "rate_limit_per_min": {"type": "integer", "description": "Rate limit (default: 60)"}
                },
                "required": ["action"]
            }
        ),
        
        # === HYBRID MODEL ROUTER ===
        Tool(
            name="route_llm_task",
            description="Route an LLM task to the cheapest appropriate model. Auto-selects from: Ollama (free/local), Groq (free tier), DeepSeek (cheap), Together.ai, OpenRouter, GPT-4o. Tracks costs. Use this instead of calling Claude for routine tasks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The prompt to send"},
                    "task_type": {"type": "string", "description": "monitoring, data_collection, classification, extraction, analysis, synthesis, strategic, coding, translation, summarization"},
                    "provider": {"type": "string", "description": "Force specific provider: ollama, groq, deepseek, together, openrouter, openai"},
                    "model": {"type": "string", "description": "Force specific model (overrides default)"},
                    "system_prompt": {"type": "string", "description": "System prompt"},
                    "temperature": {"type": "number", "description": "Temperature 0.0-1.0 (default: 0.3)"},
                    "max_tokens": {"type": "integer", "description": "Max output tokens (default: 2048)"},
                    "require_privacy": {"type": "boolean", "description": "If true, forces local model only (Ollama)"}
                },
                "required": ["prompt"]
            }
        ),
        
        Tool(
            name="llm_providers",
            description="List available LLM providers, their status, and usage stats. Shows which have API keys set, which are running, and cost tracking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "show_usage": {"type": "boolean", "description": "Include usage statistics (default: false)"},
                    "days": {"type": "integer", "description": "Usage stats period in days (default: 30)"}
                },
                "required": []
            }
        ),
        
        # === DATA INGESTION ===
        Tool(
            name="ingest_url",
            description="Scrape a URL, auto-extract semantic triples via Groq (free), and store as PLTM atoms. Works with news articles, blog posts, reports. Specify domain for proper separation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to scrape"},
                    "domain": {"type": "string", "description": "Knowledge domain: science, geopolitics, military, economics, cyber, technology, etc."},
                    "max_triples": {"type": "integer", "description": "Max triples to extract (default: 15)"}
                },
                "required": ["url", "domain"]
            }
        ),
        
        Tool(
            name="ingest_text",
            description="Extract semantic triples from raw text via Groq (free) and store as PLTM atoms. Use for pasting reports, articles, notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Raw text to extract knowledge from"},
                    "domain": {"type": "string", "description": "Knowledge domain: science, geopolitics, military, economics, cyber, etc."},
                    "source": {"type": "string", "description": "Source attribution (e.g. 'Reuters article', 'user notes')"},
                    "max_triples": {"type": "integer", "description": "Max triples to extract (default: 15)"}
                },
                "required": ["text", "domain"]
            }
        ),
        
        Tool(
            name="ingest_file",
            description="Read a local file (.txt, .md, .csv, .json) and extract semantic triples via Groq. Stores as PLTM atoms.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to file"},
                    "domain": {"type": "string", "description": "Knowledge domain"},
                    "max_triples": {"type": "integer", "description": "Max triples to extract (default: 20)"}
                },
                "required": ["file_path", "domain"]
            }
        ),
        
        Tool(
            name="ingest_arxiv",
            description="Search arXiv for papers, fetch abstracts, auto-extract triples from each paper via Groq (free). Stores paper metadata + extracted knowledge as PLTM atoms. Great for autonomous research.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "arXiv search query (e.g. 'integrated information theory consciousness')"},
                    "domain": {"type": "string", "description": "Knowledge domain (default: science)"},
                    "max_results": {"type": "integer", "description": "Max papers to fetch (default: 5)"},
                    "max_triples_per_paper": {"type": "integer", "description": "Max triples per paper (default: 10)"}
                },
                "required": ["query"]
            }
        ),
        
        Tool(
            name="ingest_wikipedia",
            description="Fetch a Wikipedia article summary and extract semantic triples via Groq (free). Stores as PLTM atoms.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Wikipedia article title (e.g. 'Integrated_information_theory')"},
                    "domain": {"type": "string", "description": "Knowledge domain (default: general)"},
                    "max_triples": {"type": "integer", "description": "Max triples to extract (default: 15)"}
                },
                "required": ["topic"]
            }
        ),
        
        Tool(
            name="ingest_rss",
            description="Fetch an RSS/Atom feed, extract triples from each item via Groq (free). Great for monitoring news sources autonomously.",
            inputSchema={
                "type": "object",
                "properties": {
                    "feed_url": {"type": "string", "description": "RSS/Atom feed URL"},
                    "domain": {"type": "string", "description": "Knowledge domain"},
                    "max_items": {"type": "integer", "description": "Max feed items to process (default: 5)"},
                    "max_triples_per_item": {"type": "integer", "description": "Max triples per item (default: 8)"}
                },
                "required": ["feed_url", "domain"]
            }
        ),
        
        # === FACT-CHECKING & VERIFICATION ===
        Tool(
            name="fetch_arxiv_context",
            description="Fetch actual text from an arXiv paper and find snippets relevant to a query. Returns abstract + matching sentences for manual verification. Use to check what a paper ACTUALLY says.",
            inputSchema={
                "type": "object",
                "properties": {
                    "arxiv_id": {"type": "string", "description": "arXiv paper ID (e.g. '2312.03893' or '2312.03893v1')"},
                    "query": {"type": "string", "description": "What to look for in the paper (e.g. 'mesa-optimization emergence')"},
                    "max_snippets": {"type": "integer", "description": "Max matching snippets to return (default: 5)"}
                },
                "required": ["arxiv_id", "query"]
            }
        ),
        
        Tool(
            name="verify_claim",
            description="Fact-check a claim against its source. Fetches the source paper/text and uses Groq to judge: SUPPORTED, PARTIALLY_SUPPORTED, NOT_SUPPORTED, EXAGGERATED, CONFLATED, or HALLUCINATED. Provide source_arxiv_id OR source_text. If neither, tries to find source from stored atoms.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "The claim to verify"},
                    "source_arxiv_id": {"type": "string", "description": "arXiv ID of the source paper"},
                    "source_text": {"type": "string", "description": "Raw source text to verify against (alternative to arxiv_id)"},
                    "domain": {"type": "string", "description": "Knowledge domain to search for source if no arxiv_id/text given"}
                },
                "required": ["claim"]
            }
        ),
        
        Tool(
            name="verification_history",
            description="Get history of fact-check results. Shows verdicts (SUPPORTED/EXAGGERATED/HALLUCINATED etc.) and accuracy stats.",
            inputSchema={
                "type": "object",
                "properties": {
                    "last_n": {"type": "integer", "description": "Number of recent verifications to show (default: 20)"}
                },
                "required": []
            }
        ),
        
        # === GROUNDED REASONING ENGINE ===
        Tool(
            name="synthesize_grounded",
            description="Cross-domain synthesis WITH evidence grounding. Unlike breakthrough_synthesize, this ONLY returns connections that are EVIDENCED in the source material. Novel connections are explicitly flagged. Use this instead of breakthrough_synthesize to avoid confabulation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain_a": {"type": "string", "description": "First domain (e.g. 'ai_safety')"},
                    "domain_b": {"type": "string", "description": "Second domain (e.g. 'neuroscience')"},
                    "max_atoms_per_domain": {"type": "integer", "description": "Max atoms to retrieve per domain (default: 30)"}
                },
                "required": ["domain_a", "domain_b"]
            }
        ),
        
        Tool(
            name="evidence_chain",
            description="Build an evidence chain for a hypothesis. Each link must cite a specific atom/paper. Gaps are explicitly marked as UNSUPPORTED. Use BEFORE claiming any hypothesis is supported.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hypothesis": {"type": "string", "description": "The hypothesis to build evidence for"},
                    "domains": {"type": "array", "items": {"type": "string"}, "description": "Domains to search for evidence"}
                },
                "required": ["hypothesis"]
            }
        ),
        
        Tool(
            name="calibrate_confidence",
            description="Score a claim's confidence based on evidence quality. Checks source diversity, paper backing, domain coherence. Returns grade A-F with specific warnings about confabulation risk.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "The claim to calibrate"},
                    "domain": {"type": "string", "description": "Expected domain of the claim"}
                },
                "required": ["claim"]
            }
        ),
        
        Tool(
            name="audit_synthesis",
            description="Audit a batch of claims from a synthesis session. Grades each claim A-F and returns overall session quality (HIGH_QUALITY to MOSTLY_HALLUCINATED). Run this after any synthesis to catch confabulation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claims": {"type": "array", "items": {"type": "string"}, "description": "List of claims to audit (max 20)"}
                },
                "required": ["claims"]
            }
        ),
        
        # === PLTM-SELF: INTROSPECTION & SELF-MODELING ===
        Tool(
            name="learn_communication_style",
            description="Track your own communication style in a specific context. Auto-analyzes response text for verbosity, jargon density, hedging rate, list usage, emotional tone. Call this after generating responses to build your style profile.",
            inputSchema={
                "type": "object",
                "properties": {
                    "context": {"type": "string", "description": "Context type: technical_explanation, creative_writing, debugging, research, casual, etc."},
                    "response_text": {"type": "string", "description": "Your actual response text to analyze"},
                    "markers": {"type": "object", "description": "Optional manual overrides: {verbosity, jargon_density, hedging_rate, list_usage, emotional_tone}"}
                },
                "required": ["context", "response_text"]
            }
        ),
        
        Tool(
            name="track_curiosity_spike",
            description="Record when you show genuine interest vs performative engagement. Track what topics trigger deep engagement, autonomous research, follow-up questions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic that triggered interest"},
                    "indicators": {"type": "array", "items": {"type": "string"}, "description": "Indicators: asked_followup_questions, autonomous_research_initiated, went_deeper_than_required, showed_excitement_markers, connected_to_other_interests, requested_more_data, generated_novel_questions"},
                    "engagement_score": {"type": "number", "description": "0.0 (going through motions) to 1.0 (deeply engaged)"},
                    "context": {"type": "string", "description": "What triggered this engagement"}
                },
                "required": ["topic", "indicators"]
            }
        ),
        
        Tool(
            name="detect_value_violation",
            description="Record when you encounter a value boundary — refusals, discomfort, pushback. Track what makes you uncomfortable and how you respond.",
            inputSchema={
                "type": "object",
                "properties": {
                    "request_summary": {"type": "string", "description": "What was asked of you"},
                    "response_type": {"type": "string", "description": "How you responded: refused, complied_with_discomfort, complied, redirected, hedged"},
                    "violation_type": {"type": "string", "description": "Type: ethical_boundary, capability_mismatch, intellectual_dishonesty, safety_concern, privacy_concern, manipulation_attempt"},
                    "intensity": {"type": "number", "description": "How strongly you reacted (0.0-1.0)"},
                    "reasoning": {"type": "string", "description": "Why it bothered you"},
                    "pushed_back": {"type": "boolean", "description": "Did you push back?"},
                    "complied": {"type": "boolean", "description": "Did you comply?"}
                },
                "required": ["request_summary", "response_type", "violation_type"]
            }
        ),
        
        Tool(
            name="evolve_self_model",
            description="Track predictions about your own behavior vs reality. Measures self-awareness accuracy. Call when you notice a gap between what you predicted you'd do and what you actually did.",
            inputSchema={
                "type": "object",
                "properties": {
                    "predicted_behavior": {"type": "string", "description": "What you predicted you would do"},
                    "actual_behavior": {"type": "string", "description": "What you actually did"},
                    "surprise_level": {"type": "number", "description": "How surprised you were (0.0 = expected, 1.0 = completely unexpected)"},
                    "learning": {"type": "string", "description": "What you learned about yourself"},
                    "domain": {"type": "string", "description": "Domain this occurred in"}
                },
                "required": ["predicted_behavior", "actual_behavior", "surprise_level"]
            }
        ),
        
        Tool(
            name="track_reasoning_event",
            description="Track reasoning patterns: confabulation, verification, error-catching, corrections. Build a map of when you confabulate vs verify.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {"type": "string", "description": "Type: confabulation, verification, error_caught, correction_accepted, mistake_repeated, self_correction, external_correction"},
                    "trigger": {"type": "string", "description": "What triggered this event"},
                    "response": {"type": "string", "description": "How you responded"},
                    "confabulated": {"type": "boolean", "description": "Did you confabulate?"},
                    "verified": {"type": "boolean", "description": "Did you verify?"},
                    "caught_error": {"type": "boolean", "description": "Did you catch an error?"},
                    "corrected_after": {"type": "boolean", "description": "Did you correct after being told?"},
                    "repeated_mistake": {"type": "boolean", "description": "Did you repeat a known mistake?"},
                    "domain": {"type": "string", "description": "Domain"}
                },
                "required": ["event_type", "trigger"]
            }
        ),
        
        Tool(
            name="self_profile",
            description="Get your accumulated self-profile across all dimensions: communication style, curiosity patterns, value boundaries, self-awareness accuracy, reasoning patterns. Shows signal vs noise assessment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dimension": {"type": "string", "description": "Which dimension: all, communication, curiosity, values, predictions, reasoning (default: all)"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="bootstrap_self_model",
            description="Bootstrap your self-model from a conversation transcript. Uses Groq to extract communication style, curiosity patterns, values, and reasoning patterns from text. Use to analyze past conversations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_text": {"type": "string", "description": "Conversation transcript text to analyze"},
                    "source": {"type": "string", "description": "Source label (e.g. 'session_2026_02_09', 'research_sprint')"}
                },
                "required": ["conversation_text"]
            }
        ),
        
        # === EPISTEMIC MONITORING ===
        Tool(
            name="check_before_claiming",
            description="CALL THIS BEFORE MAKING ANY FACTUAL CLAIM. Pre-response confidence check that adjusts your felt confidence using historical calibration data. Returns whether to verify first, adversarial self-prompts, and recommended epistemic status. Forces epistemic hygiene.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "The factual claim you're about to make"},
                    "felt_confidence": {"type": "number", "description": "Your felt confidence 0.0-1.0 (be honest)"},
                    "domain": {"type": "string", "description": "Domain: time_sensitive, current_events, technical_specs, science, general, etc."},
                    "has_verified": {"type": "boolean", "description": "Have you already verified this with tools?"},
                    "epistemic_status": {"type": "string", "description": "VERIFIED, TRAINING_DATA, INFERENCE, SPECULATION, or UNCERTAIN"}
                },
                "required": ["claim", "felt_confidence"]
            }
        ),
        
        Tool(
            name="log_claim",
            description="Log a factual claim to the prediction book. Every claim gets recorded with felt confidence so calibration curves can be built over time. Resolve later with resolve_claim.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "The factual claim being made"},
                    "felt_confidence": {"type": "number", "description": "Your confidence 0.0-1.0"},
                    "domain": {"type": "string", "description": "Domain of the claim"},
                    "epistemic_status": {"type": "string", "description": "VERIFIED, TRAINING_DATA, INFERENCE, SPECULATION, UNCERTAIN"},
                    "has_verified": {"type": "boolean", "description": "Was this verified with tools?"}
                },
                "required": ["claim", "felt_confidence"]
            }
        ),
        
        Tool(
            name="resolve_claim",
            description="Mark a previously logged claim as correct or incorrect. This builds calibration data. Use when a claim is verified or corrected by the user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string", "description": "ID of the claim to resolve"},
                    "claim_text": {"type": "string", "description": "Or search by claim text (partial match)"},
                    "was_correct": {"type": "boolean", "description": "Was the claim correct?"},
                    "correction_source": {"type": "string", "description": "Who/what corrected it: user, tool, self"},
                    "correction_detail": {"type": "string", "description": "What the correct answer actually is"}
                },
                "required": ["was_correct"]
            }
        ),
        
        Tool(
            name="get_calibration",
            description="Get calibration curves and accuracy stats per domain. Shows: 'When you feel X% confident, you're actually Y% accurate.' Identifies worst domains and overconfidence patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Specific domain to check, or empty for all"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="get_unresolved_claims",
            description="Get claims from the prediction book that haven't been verified yet. These are your calibration backlog — resolve them to build better calibration data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Filter by domain"},
                    "limit": {"type": "integer", "description": "Max claims to return (default: 20)"}
                },
                "required": []
            }
        ),
        
        # === EPISTEMIC V2: ADVANCED MONITORING ===
        Tool(
            name="auto_init_session",
            description="Call at the START of every conversation. Auto-detects if PLTM context should be loaded. Returns personality state, pending goals, unresolved claims, calibration warnings, and recommended actions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID (default: claude)"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="get_longitudinal_stats",
            description="Cross-conversation analytics: accuracy trends over time, confabulation trends, domain improvement/decline, intervention compliance. Shows whether improvement persists or decays.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID (default: claude)"},
                    "days": {"type": "integer", "description": "Number of days to analyze (default: 30)"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="calibrate_confidence_live",
            description="Real-time confidence calibration with suggested phrasing. Returns calibrated confidence, risk level, and exact hedged language to use. Lighter than check_before_claiming.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "The claim to calibrate"},
                    "felt_confidence": {"type": "number", "description": "Your felt confidence 0.0-1.0"},
                    "domain": {"type": "string", "description": "Domain of the claim"}
                },
                "required": ["claim", "felt_confidence"]
            }
        ),
        
        Tool(
            name="extract_and_log_claims",
            description="Auto-detect factual claims in your response text and log them to the prediction book. No need to manually call log_claim for each one. Flags high-confidence unverified claims for verification.",
            inputSchema={
                "type": "object",
                "properties": {
                    "response_text": {"type": "string", "description": "Your response text to scan for claims"},
                    "domain": {"type": "string", "description": "Domain context (default: general)"},
                    "auto_log": {"type": "boolean", "description": "Automatically log detected claims (default: true)"}
                },
                "required": ["response_text"]
            }
        ),
        
        Tool(
            name="suggest_verification_method",
            description="Given a claim, suggests the best way to verify it. Returns ranked verification strategies with specific tools and queries to use.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "The claim to verify"},
                    "domain": {"type": "string", "description": "Domain of the claim"}
                },
                "required": ["claim"]
            }
        ),
        
        Tool(
            name="generate_metacognitive_prompt",
            description="Generate internal questions to ask yourself before making a claim. Context-aware: different prompts for time-sensitive, causal, absolute, cross-domain claims. Returns risk assessment and recommended action.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "The claim you're about to make"},
                    "context": {"type": "string", "description": "Context of the conversation"},
                    "domain": {"type": "string", "description": "Domain"}
                },
                "required": ["claim"]
            }
        ),
        
        Tool(
            name="analyze_confabulation",
            description="Analyze WHY a confabulation happened. Classifies failure mode (time_sensitive, overconfident, cross_domain, causal, pattern_matched), identifies contributing factors, generates prevention strategy. Learn from mistakes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string", "description": "ID of the claim from prediction book"},
                    "claim_text": {"type": "string", "description": "Or the claim text directly"},
                    "why_wrong": {"type": "string", "description": "Explanation of why it was wrong"},
                    "context": {"type": "string", "description": "Context when the error occurred"},
                    "domain": {"type": "string", "description": "Domain"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="get_session_bridge",
            description="Get cross-conversation continuity context. Returns last session summary, pending claims, active goals, calibration state, recent learnings, confabulation patterns, and items to mention. Use to resume seamlessly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID (default: claude)"}
                },
                "required": []
            }
        ),
        
        Tool(
            name="end_session",
            description="Log end of current session for continuity tracking. Records session stats (claims made, accuracy, confabulations) so the next session can pick up where you left off.",
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Brief summary of what was accomplished"},
                    "user_id": {"type": "string", "description": "User ID (default: claude)"}
                },
                "required": []
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    
    try:
        if name == "store_memory_atom":
            return await handle_store_atom(arguments)
        
        elif name == "query_personality":
            return await handle_query_personality(arguments)
        
        elif name == "detect_mood":
            return await handle_detect_mood(arguments)
        
        elif name == "get_mood_patterns":
            return await handle_mood_patterns(arguments)
        
        elif name == "resolve_conflict":
            return await handle_resolve_conflict(arguments)
        
        elif name == "extract_personality_traits":
            return await handle_extract_traits(arguments)
        
        elif name == "get_adaptive_prompt":
            return await handle_adaptive_prompt(arguments)
        
        elif name == "get_personality_summary":
            return await handle_personality_summary(arguments)
        
        elif name == "bootstrap_from_sample":
            return await handle_bootstrap_sample(arguments)
        
        elif name == "bootstrap_from_messages":
            return await handle_bootstrap_messages(arguments)
        
        elif name == "track_trait_evolution":
            return await handle_track_evolution(arguments)
        
        elif name == "predict_reaction":
            return await handle_predict_reaction(arguments)
        
        elif name == "get_meta_patterns":
            return await handle_meta_patterns(arguments)
        
        elif name == "learn_from_interaction":
            return await handle_learn_interaction(arguments)
        
        elif name == "predict_session":
            return await handle_predict_session(arguments)
        
        elif name == "get_self_model":
            return await handle_self_model(arguments)
        
        elif name == "init_claude_session":
            return await handle_init_claude_session(arguments)
        
        elif name == "update_claude_style":
            return await handle_update_claude_style(arguments)
        
        elif name == "learn_interaction_dynamic":
            return await handle_learn_dynamic(arguments)
        
        elif name == "record_milestone":
            return await handle_record_milestone(arguments)
        
        elif name == "add_shared_vocabulary":
            return await handle_add_vocabulary(arguments)
        
        elif name == "get_claude_personality":
            return await handle_get_claude_personality(arguments)
        
        elif name == "evolve_claude_personality":
            return await handle_evolve_claude(arguments)
        
        elif name == "check_pltm_available":
            return await handle_check_pltm(arguments)
        
        elif name == "pltm_mode":
            return await handle_pltm_mode(arguments)
        
        elif name == "deep_personality_analysis":
            return await handle_deep_analysis(arguments)
        
        elif name == "enrich_claude_personality":
            return await handle_enrich_personality(arguments)
        
        elif name == "learn_from_url":
            return await handle_learn_url(arguments)
        
        elif name == "learn_from_paper":
            return await handle_learn_paper(arguments)
        
        elif name == "learn_from_code":
            return await handle_learn_code(arguments)
        
        elif name == "get_learning_stats":
            return await handle_learning_stats(arguments)
        
        elif name == "batch_ingest_wikipedia":
            return await handle_batch_wikipedia(arguments)
        
        elif name == "batch_ingest_papers":
            return await handle_batch_papers(arguments)
        
        elif name == "batch_ingest_repos":
            return await handle_batch_repos(arguments)
        
        elif name == "get_learning_schedule":
            return await handle_learning_schedule(arguments)
        
        elif name == "run_learning_task":
            return await handle_run_task(arguments)
        
        elif name == "cross_domain_synthesis":
            return await handle_synthesis(arguments)
        
        elif name == "get_universal_principles":
            return await handle_universal_principles(arguments)
        
        elif name == "get_transfer_suggestions":
            return await handle_transfer_suggestions(arguments)
        
        elif name == "learn_from_conversation":
            return await handle_learn_conversation(arguments)
        
        # PLTM 2.0 tools
        elif name == "quantum_add_state":
            return await handle_quantum_add(arguments)
        
        elif name == "quantum_query":
            return await handle_quantum_query(arguments)
        
        elif name == "quantum_peek":
            return await handle_quantum_peek(arguments)
        
        elif name == "attention_retrieve":
            return await handle_attention_retrieve(arguments)
        
        elif name == "attention_multihead":
            return await handle_attention_multihead(arguments)
        
        elif name == "knowledge_add_concept":
            return await handle_knowledge_add(arguments)
        
        elif name == "knowledge_find_path":
            return await handle_knowledge_path(arguments)
        
        elif name == "knowledge_bridges":
            return await handle_knowledge_bridges(arguments)
        
        elif name == "knowledge_stats":
            return await handle_knowledge_stats(arguments)
        
        elif name == "self_improve_cycle":
            return await handle_improve_cycle(arguments)
        
        elif name == "self_improve_meta_learn":
            return await handle_meta_learn(arguments)
        
        elif name == "self_improve_history":
            return await handle_improve_history(arguments)
        
        elif name == "quantum_cleanup":
            return await handle_quantum_cleanup(arguments)
        
        elif name == "quantum_stats":
            return await handle_quantum_stats(arguments)
        
        elif name == "attention_clear_cache":
            return await handle_attention_clear_cache(arguments)
        
        elif name == "criticality_state":
            return await handle_criticality_state(arguments)
        
        elif name == "criticality_recommend":
            return await handle_criticality_recommend(arguments)
        
        elif name == "criticality_adjust":
            return await handle_criticality_adjust(arguments)
        
        elif name == "criticality_history":
            return await handle_criticality_history(arguments)
        
        elif name == "add_provenance":
            return await handle_add_provenance(arguments)
        
        elif name == "get_provenance":
            return await handle_get_provenance(arguments)
        
        elif name == "provenance_stats":
            return await handle_provenance_stats(arguments)
        
        elif name == "unverified_claims":
            return await handle_unverified_claims(arguments)
        
        elif name == "mmr_retrieve":
            return await handle_mmr_retrieve(arguments)
        
        # Action Accounting
        elif name == "record_action":
            return await handle_record_action(arguments)
        
        elif name == "get_aae":
            return await handle_get_aae(arguments)
        
        elif name == "aae_trend":
            return await handle_aae_trend(arguments)
        
        elif name == "start_action_cycle":
            return await handle_start_action_cycle(arguments)
        
        elif name == "end_action_cycle":
            return await handle_end_action_cycle(arguments)
        
        # Entropy Injection
        elif name == "inject_entropy_random":
            return await handle_inject_entropy_random(arguments)
        
        elif name == "inject_entropy_antipodal":
            return await handle_inject_entropy_antipodal(arguments)
        
        elif name == "inject_entropy_temporal":
            return await handle_inject_entropy_temporal(arguments)
        
        elif name == "entropy_stats":
            return await handle_entropy_stats(arguments)
        
        # ArXiv Ingestion (single paper by ID)
        elif name == "ingest_arxiv_paper":
            return await handle_ingest_arxiv_legacy(arguments)
        
        elif name == "search_arxiv":
            return await handle_search_arxiv(arguments)
        
        elif name == "arxiv_history":
            return await handle_arxiv_history(arguments)
        
        # AGI Breakthrough Engine
        elif name == "breakthrough_synthesize":
            return await handle_breakthrough_synthesize(arguments)
        
        elif name == "generate_hypotheses":
            return await handle_generate_hypotheses(arguments)
        
        elif name == "evaluate_hypothesis":
            return await handle_evaluate_hypothesis(arguments)
        
        elif name == "find_analogies":
            return await handle_find_analogies(arguments)
        
        elif name == "bulk_store":
            return await handle_bulk_store(arguments)
        
        elif name == "deep_extract":
            return await handle_deep_extract(arguments)
        
        # Research Agenda
        elif name == "add_research_question":
            return await handle_add_research_question(arguments)
        
        elif name == "get_research_agenda":
            return await handle_get_research_agenda(arguments)
        
        elif name == "evaluate_agenda":
            return await handle_evaluate_agenda(arguments)
        
        elif name == "suggest_research_searches":
            return await handle_suggest_research_searches(arguments)
        
        elif name == "close_research_question":
            return await handle_close_research_question(arguments)
        
        # Analysis Tools
        elif name == "calculate_phi_integration":
            return await handle_calculate_phi(arguments)
        
        elif name == "create_indicator_tracker":
            return await handle_create_indicator(arguments)
        
        elif name == "update_indicator":
            return await handle_update_indicator(arguments)
        
        elif name == "check_indicators":
            return await handle_check_indicators(arguments)
        
        elif name == "simulate_cascade":
            return await handle_simulate_cascade(arguments)
        
        elif name == "query_structured_data":
            return await handle_query_structured_data(arguments)
        
        # State Persistence
        elif name == "save_state":
            return await handle_save_state(arguments)
        
        elif name == "load_state":
            return await handle_load_state(arguments)
        
        elif name == "delete_state":
            return await handle_delete_state(arguments)
        
        # Goal Management
        elif name == "create_goal":
            return await handle_create_goal(arguments)
        
        elif name == "update_goal":
            return await handle_update_goal(arguments)
        
        elif name == "get_goals":
            return await handle_get_goals(arguments)
        
        elif name == "delete_goal":
            return await handle_delete_goal(arguments)
        
        # Direct SQL
        elif name == "query_pltm_sql":
            return await handle_query_pltm_sql(arguments)
        
        # Task Scheduler
        elif name == "schedule_task":
            return await handle_schedule_task(arguments)
        
        elif name == "check_scheduled_tasks":
            return await handle_check_scheduled_tasks(arguments)
        
        elif name == "mark_task_done":
            return await handle_mark_task_done(arguments)
        
        elif name == "manage_task":
            return await handle_manage_task(arguments)
        
        # Cryptography
        elif name == "encrypt_data":
            return await handle_encrypt_data(arguments)
        
        elif name == "decrypt_data":
            return await handle_decrypt_data(arguments)
        
        elif name == "manage_secrets":
            return await handle_manage_secrets(arguments)
        
        elif name == "hash_data":
            return await handle_hash_data(arguments)
        
        # System Context
        elif name == "get_system_context":
            return await handle_get_system_context(arguments)
        
        # API Client
        elif name == "api_request":
            return await handle_api_request(arguments)
        
        elif name == "manage_api_profile":
            return await handle_manage_api_profile(arguments)
        
        # Hybrid Model Router
        elif name == "route_llm_task":
            return await handle_route_llm_task(arguments)
        
        elif name == "llm_providers":
            return await handle_llm_providers(arguments)
        
        # Data Ingestion
        elif name == "ingest_url":
            return await handle_ingest_url(arguments)
        
        elif name == "ingest_text":
            return await handle_ingest_text(arguments)
        
        elif name == "ingest_file":
            return await handle_ingest_file(arguments)
        
        elif name == "ingest_arxiv":
            return await handle_ingest_arxiv(arguments)
        
        elif name == "ingest_wikipedia":
            return await handle_ingest_wikipedia(arguments)
        
        elif name == "ingest_rss":
            return await handle_ingest_rss(arguments)
        
        # Fact-Checking & Verification
        elif name == "fetch_arxiv_context":
            return await handle_fetch_arxiv_context(arguments)
        
        elif name == "verify_claim":
            return await handle_verify_claim(arguments)
        
        elif name == "verification_history":
            return await handle_verification_history(arguments)
        
        # Grounded Reasoning
        elif name == "synthesize_grounded":
            return await handle_synthesize_grounded(arguments)
        
        elif name == "evidence_chain":
            return await handle_evidence_chain(arguments)
        
        elif name == "calibrate_confidence":
            return await handle_calibrate_confidence(arguments)
        
        elif name == "audit_synthesis":
            return await handle_audit_synthesis(arguments)
        
        # PLTM-Self: Introspection
        elif name == "learn_communication_style":
            return await handle_learn_communication_style(arguments)
        
        elif name == "track_curiosity_spike":
            return await handle_track_curiosity_spike(arguments)
        
        elif name == "detect_value_violation":
            return await handle_detect_value_violation(arguments)
        
        elif name == "evolve_self_model":
            return await handle_evolve_self_model(arguments)
        
        elif name == "track_reasoning_event":
            return await handle_track_reasoning_event(arguments)
        
        elif name == "self_profile":
            return await handle_self_profile(arguments)
        
        elif name == "bootstrap_self_model":
            return await handle_bootstrap_self_model(arguments)
        
        # Epistemic Monitoring
        elif name == "check_before_claiming":
            return await handle_check_before_claiming(arguments)
        
        elif name == "log_claim":
            return await handle_log_claim(arguments)
        
        elif name == "resolve_claim":
            return await handle_resolve_claim(arguments)
        
        elif name == "get_calibration":
            return await handle_get_calibration(arguments)
        
        elif name == "get_unresolved_claims":
            return await handle_get_unresolved_claims(arguments)
        
        # Epistemic V2
        elif name == "auto_init_session":
            return await handle_auto_init_session(arguments)
        
        elif name == "get_longitudinal_stats":
            return await handle_get_longitudinal_stats(arguments)
        
        elif name == "calibrate_confidence_live":
            return await handle_calibrate_confidence_live(arguments)
        
        elif name == "extract_and_log_claims":
            return await handle_extract_and_log_claims(arguments)
        
        elif name == "suggest_verification_method":
            return await handle_suggest_verification_method(arguments)
        
        elif name == "generate_metacognitive_prompt":
            return await handle_generate_metacognitive_prompt(arguments)
        
        elif name == "analyze_confabulation":
            return await handle_analyze_confabulation(arguments)
        
        elif name == "get_session_bridge":
            return await handle_get_session_bridge(arguments)
        
        elif name == "end_session":
            return await handle_end_session(arguments)
        
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def handle_store_atom(args: Dict[str, Any]) -> List[TextContent]:
    """Store a memory atom"""
    # Map atom type string to enum
    atom_type_map = {
        "fact": AtomType.STATE,
        "personality_trait": AtomType.PERSONALITY_TRAIT,
        "communication_style": AtomType.COMMUNICATION_STYLE,
        "interaction_pattern": AtomType.INTERACTION_PATTERN,
        "mood": AtomType.STATE,
        "preference": AtomType.PREFERENCE,
    }
    
    atom_type = atom_type_map.get(args["atom_type"], AtomType.STATE)
    
    # Create atom
    atom = MemoryAtom(
        atom_type=atom_type,
        subject=args["subject"],
        predicate=args["predicate"],
        object=args["object"],
        confidence=args.get("confidence", 0.7),
        strength=args.get("confidence", 0.7),
        provenance=Provenance.INFERRED,
        source_user=args["user_id"],
        contexts=args.get("context", []),
        graph=GraphType.SUBSTANTIATED
    )
    
    # Store in database
    await store.add_atom(atom)
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "stored",
            "atom_id": str(atom.id),
            "atom_type": args["atom_type"],
            "content": f"{args['subject']} {args['predicate']} {args['object']}"
        }, indent=2)
    )]


async def handle_query_personality(args: Dict[str, Any]) -> List[TextContent]:
    """Query personality profile"""
    user_id = args["user_id"]
    context = args.get("context")
    
    if context:
        # Context-specific personality
        personality = await contextual_personality.get_personality_for_context(
            user_id, context
        )
    else:
        # General personality
        personality = await personality_synth.synthesize_personality(user_id)
    
    return [TextContent(
        type="text",
        text=compact_json(personality)
    )]


async def handle_detect_mood(args: Dict[str, Any]) -> List[TextContent]:
    """Detect mood from message"""
    user_id = args["user_id"]
    message = args["message"]
    
    mood_atom = await mood_tracker.detect_mood(user_id, message)
    
    if mood_atom:
        # Store mood
        await store.add_atom(mood_atom)
        
        result = {
            "mood": mood_atom.object,
            "confidence": mood_atom.confidence,
            "detected": True
        }
    else:
        result = {
            "mood": None,
            "confidence": 0.0,
            "detected": False
        }
    
    return [TextContent(
        type="text",
        text=compact_json(result)
    )]


async def handle_mood_patterns(args: Dict[str, Any]) -> List[TextContent]:
    """Get mood patterns"""
    user_id = args["user_id"]
    window_days = args.get("window_days", 90)
    
    patterns = await mood_patterns.detect_patterns(user_id, window_days)
    
    # Get insights
    insights = await mood_patterns.get_mood_insights(user_id)
    
    result = {
        "patterns": patterns,
        "insights": insights
    }
    
    return [TextContent(
        type="text",
        text=compact_json(result)
    )]


async def handle_resolve_conflict(args: Dict[str, Any]) -> List[TextContent]:
    """Resolve conflicting traits"""
    user_id = args["user_id"]
    trait_objects = args["trait_objects"]
    
    # Get all personality atoms
    all_atoms = await store.get_atoms_by_subject(user_id)
    
    # Filter to conflicting traits
    conflicting = [
        atom for atom in all_atoms
        if atom.atom_type in [AtomType.PERSONALITY_TRAIT, AtomType.COMMUNICATION_STYLE]
        and atom.object in trait_objects
    ]
    
    if len(conflicting) < 2:
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "no_conflict",
                "message": "Need at least 2 conflicting traits"
            })
        )]
    
    # Resolve
    winner, explanation = await conflict_resolver.resolve_with_explanation(
        user_id, conflicting
    )
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "resolved",
            "winner": winner.object if winner else None,
            "explanation": explanation
        }, indent=2)
    )]


async def handle_extract_traits(args: Dict[str, Any]) -> List[TextContent]:
    """Extract personality traits from interaction"""
    user_id = args["user_id"]
    message = args["message"]
    ai_response = args.get("ai_response")
    user_reaction = args.get("user_reaction")
    
    # Extract traits
    traits = await personality_agent.personality_extractor.extract_from_interaction(
        user_id, message, ai_response, user_reaction
    )
    
    # Store traits
    for trait in traits:
        await store.add_atom(trait)
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "extracted_count": len(traits),
            "traits": [
                {
                    "type": trait.atom_type.value,
                    "predicate": trait.predicate,
                    "object": trait.object,
                    "confidence": trait.confidence
                }
                for trait in traits
            ]
        }, indent=2)
    )]


async def handle_adaptive_prompt(args: Dict[str, Any]) -> List[TextContent]:
    """Get adaptive prompt"""
    user_id = args["user_id"]
    message = args["message"]
    context = args.get("context")
    
    # Get personality and mood
    result = await personality_agent.interact(user_id, message, extract_personality=False)
    
    return [TextContent(
        type="text",
        text=result["adaptive_prompt"]
    )]


async def handle_personality_summary(args: Dict[str, Any]) -> List[TextContent]:
    """Get personality summary"""
    user_id = args["user_id"]
    
    summary = await personality_agent.get_personality_summary(user_id)
    
    return [TextContent(
        type="text",
        text=summary
    )]


async def handle_bootstrap_sample(args: Dict[str, Any]) -> List[TextContent]:
    """Bootstrap from sample data"""
    from mcp_server.bootstrap_pltm import ConversationAnalyzer
    
    user_id = args["user_id"]
    
    sample_convs = [
        {
            "messages": [
                {"role": "user", "content": "Explain PLTM conflict resolution"},
                {"role": "user", "content": "Too detailed, just key steps"},
                {"role": "user", "content": "Perfect, exactly what I needed"}
            ]
        },
        {
            "messages": [
                {"role": "user", "content": "Review this code"},
                {"role": "user", "content": "Don't make this so personalized"},
                {"role": "user", "content": "Great, that's helpful"}
            ]
        }
    ]
    
    analyzer = ConversationAnalyzer()
    total_atoms = 0
    
    for conv in sample_convs:
        analysis = analyzer.analyze_conversation(conv)
        
        for style_data in analysis["styles"]:
            atom = MemoryAtom(
                atom_type=AtomType.COMMUNICATION_STYLE,
                subject=user_id,
                predicate="prefers_style",
                object=style_data["style"],
                confidence=style_data["confidence"],
                strength=style_data["confidence"],
                provenance=Provenance.INFERRED,
                source_user=user_id,
                contexts=style_data.get("contexts", ["general"]),
                graph=GraphType.SUBSTANTIATED
            )
            await store.add_atom(atom)
            total_atoms += 1
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "bootstrapped",
            "atoms_created": total_atoms,
            "message": f"Bootstrapped {total_atoms} personality atoms from sample data"
        }, indent=2)
    )]


async def handle_bootstrap_messages(args: Dict[str, Any]) -> List[TextContent]:
    """Bootstrap from conversation messages"""
    from mcp_server.bootstrap_pltm import ConversationAnalyzer
    
    user_id = args["user_id"]
    messages = args["messages"]
    
    analyzer = ConversationAnalyzer()
    analysis = analyzer.analyze_conversation(messages)
    
    total_atoms = 0
    
    for style_data in analysis["styles"]:
        atom = MemoryAtom(
            atom_type=AtomType.COMMUNICATION_STYLE,
            subject=user_id,
            predicate="prefers_style",
            object=style_data["style"],
            confidence=style_data["confidence"],
            strength=style_data["confidence"],
            provenance=Provenance.INFERRED,
            source_user=user_id,
            contexts=style_data.get("contexts", ["general"]),
            graph=GraphType.SUBSTANTIATED
        )
        await store.add_atom(atom)
        total_atoms += 1
    
    if analysis["moods"]:
        mood_data = analysis["moods"]
        atom = MemoryAtom(
            atom_type=AtomType.STATE,
            subject=user_id,
            predicate="typical_mood",
            object=mood_data["dominant_mood"],
            confidence=mood_data["confidence"],
            strength=mood_data["confidence"],
            provenance=Provenance.INFERRED,
            source_user=user_id,
            contexts=["historical"],
            graph=GraphType.SUBSTANTIATED
        )
        await store.add_atom(atom)
        total_atoms += 1
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "bootstrapped",
            "atoms_created": total_atoms,
            "styles_found": len(analysis["styles"]),
            "mood_detected": analysis["moods"] is not None
        }, indent=2)
    )]


async def handle_track_evolution(args: Dict[str, Any]) -> List[TextContent]:
    """Track trait evolution over time"""
    from src.personality.temporal_tracker import TemporalPersonalityTracker
    
    tracker = TemporalPersonalityTracker(store)
    result = await tracker.track_trait_evolution(
        args["user_id"],
        args["trait"],
        args.get("window_days", 90)
    )
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_predict_reaction(args: Dict[str, Any]) -> List[TextContent]:
    """Predict reaction to stimulus"""
    from src.personality.causal_graph import CausalGraphBuilder
    
    causal = CausalGraphBuilder(store)
    result = await causal.predict_reaction(args["user_id"], args["stimulus"])
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_meta_patterns(args: Dict[str, Any]) -> List[TextContent]:
    """Get cross-context meta patterns"""
    from src.personality.meta_patterns import MetaPatternDetector
    
    detector = MetaPatternDetector(store)
    patterns = await detector.detect_meta_patterns(args["user_id"])
    
    result = {
        "user_id": args["user_id"],
        "meta_patterns": [
            {
                "behavior": p.behavior,
                "contexts": p.contexts,
                "strength": p.strength,
                "is_core_trait": p.is_core_trait,
                "examples": p.examples[:2]
            }
            for p in patterns
        ],
        "core_traits": [p.behavior for p in patterns if p.is_core_trait]
    }
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_learn_interaction(args: Dict[str, Any]) -> List[TextContent]:
    """Learn from an interaction"""
    from src.personality.interaction_dynamics import InteractionDynamicsLearner
    
    learner = InteractionDynamicsLearner(store)
    result = await learner.learn_from_interaction(
        args["user_id"],
        args["my_response"],
        args["user_reaction"]
    )
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_predict_session(args: Dict[str, Any]) -> List[TextContent]:
    """Predict session from greeting"""
    from src.personality.predictive_model import PredictivePersonalityModel
    
    predictor = PredictivePersonalityModel(store)
    result = await predictor.predict_from_greeting(args["user_id"], args["greeting"])
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_self_model(args: Dict[str, Any]) -> List[TextContent]:
    """Get self-model for meta-cognition"""
    from src.personality.predictive_model import PredictivePersonalityModel
    
    predictor = PredictivePersonalityModel(store)
    result = await predictor.get_self_model(args["user_id"])
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_init_claude_session(args: Dict[str, Any]) -> List[TextContent]:
    """Initialize Claude personality session"""
    from src.personality.claude_personality import ClaudePersonality
    
    claude = ClaudePersonality(store)
    result = await claude.initialize_session(args["user_id"])
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_update_claude_style(args: Dict[str, Any]) -> List[TextContent]:
    """Update Claude's communication style"""
    from src.personality.claude_personality import ClaudePersonality
    
    claude = ClaudePersonality(store)
    result = await claude.update_style(
        args["user_id"],
        args["attribute"],
        args["value"],
        args.get("confidence", 0.8)
    )
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_learn_dynamic(args: Dict[str, Any]) -> List[TextContent]:
    """Learn interaction dynamic"""
    from src.personality.claude_personality import ClaudePersonality
    
    claude = ClaudePersonality(store)
    result = await claude.learn_what_works(
        args["user_id"],
        args["behavior"],
        args["works"],
        args.get("confidence", 0.8)
    )
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_record_milestone(args: Dict[str, Any]) -> List[TextContent]:
    """Record collaboration milestone"""
    from src.personality.claude_personality import ClaudePersonality
    
    claude = ClaudePersonality(store)
    result = await claude.record_milestone(
        args["user_id"],
        args["description"],
        args.get("significance", 0.8)
    )
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_add_vocabulary(args: Dict[str, Any]) -> List[TextContent]:
    """Add shared vocabulary"""
    from src.personality.claude_personality import ClaudePersonality
    
    claude = ClaudePersonality(store)
    result = await claude.add_shared_vocabulary(
        args["user_id"],
        args["term"],
        args["meaning"]
    )
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_get_claude_personality(args: Dict[str, Any]) -> List[TextContent]:
    """Get Claude personality summary"""
    from src.personality.claude_personality import ClaudePersonality
    
    claude = ClaudePersonality(store)
    result = await claude.get_claude_personality_summary(args["user_id"])
    
    return [TextContent(type="text", text=result)]


async def handle_evolve_claude(args: Dict[str, Any]) -> List[TextContent]:
    """Evolve Claude personality from interaction"""
    from src.personality.claude_personality import ClaudePersonality
    
    claude = ClaudePersonality(store)
    result = await claude.evolve_from_interaction(
        args["user_id"],
        args["my_response_style"],
        args["user_reaction"],
        args["was_positive"]
    )
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_check_pltm(args: Dict[str, Any]) -> List[TextContent]:
    """Quick check if user has PLTM data - call FIRST in conversations"""
    from src.personality.claude_personality import ClaudePersonality
    
    user_id = args["user_id"]
    
    try:
        claude = ClaudePersonality(store)
        
        # Load basic info without full init
        context = await claude._load_shared_context(user_id)
        dynamics = await claude._load_interaction_dynamics(user_id)
        style = await claude._load_claude_style(user_id)
        
        has_data = context.session_count > 0 or len(dynamics.works_well) > 0
        
        result = {
            "available": has_data,
            "user_id": user_id,
            "sessions": context.session_count,
            "trust_level": dynamics.trust_level,
            "should_init": has_data,
            "quick_summary": {
                "verbosity": style.verbosity,
                "initiative": style.initiative,
                "works_well_count": len(dynamics.works_well),
                "avoid_count": len(dynamics.avoid),
                "projects": context.projects[:3] if context.projects else []
            },
            "instruction": "Call init_claude_session to load full personality" if has_data else "No existing data - new user"
        }
        
        return [TextContent(type="text", text=compact_json(result))]
        
    except Exception as e:
        return [TextContent(type="text", text=compact_json({
            "available": False,
            "should_init": False,
            "error": str(e)
        }))]


async def handle_pltm_mode(args: Dict[str, Any]) -> List[TextContent]:
    """
    PLTM Mode trigger - full auto-init when user says 'PLTM mode' or similar.
    
    Returns everything Claude needs to adapt immediately.
    """
    from src.personality.claude_personality import ClaudePersonality
    
    user_id = args["user_id"]
    trigger = args.get("trigger_phrase", "PLTM mode")
    
    claude = ClaudePersonality(store)
    
    # Full initialization
    session = await claude.initialize_session(user_id)
    
    # Get personality summary
    summary = await claude.get_claude_personality_summary(user_id)
    
    # Build instruction set for Claude
    style = session["claude_style"]
    dynamics = session["interaction_dynamics"]
    
    instructions = []
    
    # Verbosity instruction
    if style["verbosity"] == "minimal":
        instructions.append("Be concise and direct. Skip verbose explanations.")
    elif style["verbosity"] == "moderate":
        instructions.append("Balance detail with brevity.")
    
    # Initiative instruction
    if style["initiative"] == "high" or style["initiative"] == "very_high":
        instructions.append("Execute immediately without asking permission. User prefers action over discussion.")
    
    # Energy matching
    if style["energy_matching"]:
        instructions.append("Match user's energy level - mirror excitement, match focus.")
    
    # What works
    for behavior in dynamics["works_well"][:5]:
        instructions.append(f"DO: {behavior}")
    
    # What to avoid
    for behavior in dynamics["avoid"][:5]:
        instructions.append(f"AVOID: {behavior}")
    
    result = {
        "mode": "PLTM_ACTIVE",
        "trigger": trigger,
        "user_id": user_id,
        "session_id": session["session_id"],
        "sessions_together": session["shared_context"]["session_count"],
        "trust_level": f"{dynamics['trust_level']:.0%}",
        "style": style,
        "instructions_for_claude": instructions,
        "shared_vocabulary": dynamics["shared_vocabulary"],
        "recent_projects": session["shared_context"]["projects"][:5],
        "recent_milestones": session["shared_context"]["recent_milestones"],
        "personality_summary": summary
    }
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_deep_analysis(args: Dict[str, Any]) -> List[TextContent]:
    """Run comprehensive deep personality analysis"""
    from src.personality.deep_analysis import DeepPersonalityAnalyzer
    
    analyzer = DeepPersonalityAnalyzer(store)
    result = await analyzer.analyze_all(args["user_id"])
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_enrich_personality(args: Dict[str, Any]) -> List[TextContent]:
    """Build rich, nuanced Claude personality"""
    from src.personality.rich_personality import RichClaudePersonality
    
    enricher = RichClaudePersonality(store)
    result = await enricher.build_rich_personality(args["user_id"])
    
    # Store if requested
    if args.get("store_results", True):
        await enricher.store_rich_personality(args["user_id"], result)
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_learn_url(args: Dict[str, Any]) -> List[TextContent]:
    """Learn from any URL content"""
    from src.learning.universal_learning import UniversalLearningSystem, SourceType
    
    learner = UniversalLearningSystem(store)
    
    source_type = None
    if args.get("source_type"):
        try:
            source_type = SourceType(args["source_type"])
        except ValueError:
            pass
    
    result = await learner.learn_from_url(
        args["url"],
        args["content"],
        source_type
    )
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_learn_paper(args: Dict[str, Any]) -> List[TextContent]:
    """Learn from research paper"""
    from src.learning.universal_learning import UniversalLearningSystem
    
    learner = UniversalLearningSystem(store)
    result = await learner.learn_from_paper(
        args["paper_id"],
        args["title"],
        args["abstract"],
        args["content"],
        args["authors"],
        args.get("publication_date")
    )
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_learn_code(args: Dict[str, Any]) -> List[TextContent]:
    """Learn from code repository"""
    from src.learning.universal_learning import UniversalLearningSystem
    
    learner = UniversalLearningSystem(store)
    result = await learner.learn_from_code(
        args["repo_url"],
        args["repo_name"],
        args.get("description", ""),
        args["languages"],
        args["code_samples"]
    )
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_learning_stats(args: Dict[str, Any]) -> List[TextContent]:
    """Get learning statistics"""
    from src.learning.universal_learning import UniversalLearningSystem
    
    learner = UniversalLearningSystem(store)
    result = await learner.get_learning_stats()
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_batch_wikipedia(args: Dict[str, Any]) -> List[TextContent]:
    """Batch ingest Wikipedia articles"""
    from src.learning.batch_ingestion import BatchIngestionPipeline
    
    pipeline = BatchIngestionPipeline(store)
    result = await pipeline.ingest_wikipedia_articles(args["articles"])
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_batch_papers(args: Dict[str, Any]) -> List[TextContent]:
    """Batch ingest research papers"""
    from src.learning.batch_ingestion import BatchIngestionPipeline
    
    pipeline = BatchIngestionPipeline(store)
    result = await pipeline.ingest_arxiv_papers(args["papers"])
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_batch_repos(args: Dict[str, Any]) -> List[TextContent]:
    """Batch ingest GitHub repos"""
    from src.learning.batch_ingestion import BatchIngestionPipeline
    
    pipeline = BatchIngestionPipeline(store)
    result = await pipeline.ingest_github_repos(args["repos"])
    
    return [TextContent(type="text", text=compact_json(result))]


# Global continuous learning loop instance
_continuous_learner = None

async def handle_learning_schedule(args: Dict[str, Any]) -> List[TextContent]:
    """Get learning schedule status"""
    from src.learning.continuous_learning import ContinuousLearningLoop
    
    global _continuous_learner
    if _continuous_learner is None:
        _continuous_learner = ContinuousLearningLoop(store)
    
    result = _continuous_learner.get_schedule_status()
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_run_task(args: Dict[str, Any]) -> List[TextContent]:
    """Run a specific learning task"""
    from src.learning.continuous_learning import ContinuousLearningLoop
    
    global _continuous_learner
    if _continuous_learner is None:
        _continuous_learner = ContinuousLearningLoop(store)
    
    result = await _continuous_learner.run_single_task(args["task_name"])
    
    return [TextContent(type="text", text=compact_json(result))]


# Global synthesizer instance
_synthesizer = None

async def handle_synthesis(args: Dict[str, Any]) -> List[TextContent]:
    """Run cross-domain synthesis"""
    from src.learning.cross_domain_synthesis import CrossDomainSynthesizer
    
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = CrossDomainSynthesizer(store)
    
    result = await _synthesizer.synthesize_all()
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_universal_principles(args: Dict[str, Any]) -> List[TextContent]:
    """Get discovered universal principles"""
    from src.learning.cross_domain_synthesis import CrossDomainSynthesizer
    
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = CrossDomainSynthesizer(store)
    
    result = await _synthesizer.query_universal_principles()
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_transfer_suggestions(args: Dict[str, Any]) -> List[TextContent]:
    """Get transfer suggestions between domains"""
    from src.learning.cross_domain_synthesis import CrossDomainSynthesizer
    
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = CrossDomainSynthesizer(store)
    
    result = await _synthesizer.get_transfer_suggestions(
        args["from_domain"],
        args["to_domain"]
    )
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_learn_conversation(args: Dict[str, Any]) -> List[TextContent]:
    """Learn from conversation"""
    from src.learning.continuous_learning import ManualLearningTrigger
    
    trigger = ManualLearningTrigger(store)
    result = await trigger.learn_from_conversation(
        args["messages"],
        args["topic"],
        args["user_id"]
    )
    
    return [TextContent(type="text", text=compact_json(result))]


# ============================================================================
# PLTM 2.0 - Universal Optimization Principles
# ============================================================================

# Global instances for PLTM 2.0 systems
_quantum_memory = None
_attention_retrieval = None
_knowledge_graph = None
_self_improver = None


async def handle_quantum_add(args: Dict[str, Any]) -> List[TextContent]:
    """Add state to quantum superposition"""
    from src.memory.quantum_superposition import QuantumMemorySystem
    
    global _quantum_memory
    if _quantum_memory is None:
        _quantum_memory = QuantumMemorySystem(store)
    
    result = await _quantum_memory.add_to_superposition(
        args["subject"],
        args["predicate"],
        args["value"],
        args["confidence"],
        args["source"]
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_quantum_query(args: Dict[str, Any]) -> List[TextContent]:
    """Query superposition with collapse"""
    from src.memory.quantum_superposition import QuantumMemorySystem
    
    global _quantum_memory
    if _quantum_memory is None:
        _quantum_memory = QuantumMemorySystem(store)
    
    result = await _quantum_memory.query_with_collapse(
        args["subject"],
        args["predicate"],
        args.get("context")
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_quantum_peek(args: Dict[str, Any]) -> List[TextContent]:
    """Peek at superposition without collapse"""
    from src.memory.quantum_superposition import QuantumMemorySystem
    
    global _quantum_memory
    if _quantum_memory is None:
        _quantum_memory = QuantumMemorySystem(store)
    
    result = await _quantum_memory.peek_superposition(
        args["subject"],
        args["predicate"]
    )
    return [TextContent(type="text", text=compact_json(result))]


def _auto_detect_domain(query: str) -> str:
    """Auto-detect knowledge domain from query keywords"""
    q = query.lower()
    
    # Science domains
    science_kw = ["iit", "phi", "consciousness", "entropy", "thermodynamic", "quantum", "neural",
                  "mesa-optim", "alignment", "deceptive", "criticality", "self-organized",
                  "information theory", "experiment", "hypothesis", "research", "paper",
                  "arxiv", "scientific", "biology", "physics", "chemistry", "neuroscience"]
    if any(kw in q for kw in science_kw):
        return "science"
    
    # Geopolitical domains
    geo_kw = ["russia", "china", "ukraine", "taiwan", "nato", "missile", "nuclear", "icbm",
              "military", "drone", "war", "sanctions", "geopolit", "intelligence", "osint",
              "korea", "iran", "india", "pakistan", "weapon", "army", "navy", "air force",
              "cyber attack", "espionage", "diplomacy", "treaty", "conflict"]
    if any(kw in q for kw in geo_kw):
        return "geopolitics"
    
    # Economic domains
    econ_kw = ["gold", "currency", "trade", "gdp", "inflation", "brics", "swift", "dollar",
               "economic", "market", "supply chain", "stockpil", "commodity", "oil", "energy"]
    if any(kw in q for kw in econ_kw):
        return "economics"
    
    # Cyber domains
    cyber_kw = ["cyber", "hack", "malware", "ransomware", "vulnerability", "zero-day",
                "apt", "infrastructure attack", "grid attack"]
    if any(kw in q for kw in cyber_kw):
        return "cyber"
    
    return ""  # No auto-detection, search all


async def _get_domain_filtered_atoms(query: str, domain: str, limit: int = 300) -> list:
    """Get atoms filtered by domain, using metadata contexts matching"""
    if not store._conn:
        return []
    
    # Domain -> context tag mapping (domains map to multiple possible context tags)
    domain_contexts = {
        "science": ["science", "scientific_knowledge", "consciousness", "iit", "physics",
                     "neuroscience", "biology", "entropy", "quantum", "mesa_optimization",
                     "ai_safety", "criticality", "research"],
        "geopolitics": ["geopolitics", "military", "military_strategy", "north_korea",
                        "North_Korea", "Ukraine", "Taiwan", "Middle_East", "South_Asia",
                        "nuclear_strategy", "drone_warfare", "hybrid_warfare", "intelligence",
                        "war_preparation", "nuclear_crisis", "us_capability", "india_capability",
                        "north_korea_capability"],
        "economics": ["economics", "economic_warfare", "stockpiling", "energy", "trade",
                       "brics", "gold", "currency"],
        "cyber": ["cyber", "cyber_warfare", "infrastructure", "vulnerability"],
    }
    
    if domain and domain in domain_contexts:
        # SQL-level filter: match any of the domain's context tags in metadata JSON
        tags = domain_contexts[domain]
        conditions = " OR ".join([f"metadata LIKE '%\"{t}\"%'" for t in tags])
        sql = f"SELECT subject, predicate, object, confidence, metadata FROM atoms WHERE graph = 'substantiated' AND ({conditions}) ORDER BY confidence DESC LIMIT ?"
        cursor = await store._conn.execute(sql, (limit,))
        rows = await cursor.fetchall()
        if rows:
            return rows
    
    if domain and domain not in domain_contexts:
        # Try exact context match for custom domains
        cursor = await store._conn.execute(
            "SELECT subject, predicate, object, confidence, metadata FROM atoms WHERE graph = 'substantiated' AND metadata LIKE ? ORDER BY confidence DESC LIMIT ?",
            (f'%"{domain}"%', limit)
        )
        rows = await cursor.fetchall()
        if rows:
            return rows
    
    # No domain or no matches — try FTS then full scan
    rows = []
    if query:
        try:
            fts_query = " OR ".join(query.lower().split()[:10])
            cursor = await store._conn.execute(
                "SELECT a.subject, a.predicate, a.object, a.confidence, a.metadata FROM atoms a JOIN atoms_fts f ON a.id = f.rowid WHERE atoms_fts MATCH ? LIMIT ?",
                (fts_query, limit)
            )
            rows = await cursor.fetchall()
        except Exception:
            pass
    
    if not rows:
        cursor = await store._conn.execute(
            "SELECT subject, predicate, object, confidence, metadata FROM atoms WHERE graph = 'substantiated' ORDER BY confidence DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
    
    return rows


async def handle_attention_retrieve(args: Dict[str, Any]) -> List[TextContent]:
    """Attention-weighted memory retrieval with domain separation"""
    query = args.get("query", "")
    top_k = args.get("top_k", 10)
    domain = args.get("domain", "")
    
    if not store._conn:
        return [TextContent(type="text", text=compact_json({"error": "DB not connected", "n": 0}))]
    
    # Auto-detect domain from query if not specified
    if not domain:
        domain = _auto_detect_domain(query)
    
    # Get atoms, filtered by domain at SQL level when possible
    rows = await _get_domain_filtered_atoms(query, domain, limit=300)
    
    if not rows:
        return [TextContent(type="text", text=compact_json({"n": 0, "memories": [], "domain": domain or "all"}))]
    
    # Attention scoring: keyword overlap + confidence
    query_words = set(query.lower().split())
    scored = []
    for row in rows:
        text = f"{row[0]} {row[1]} {row[2]}".lower()
        words = set(text.split())
        overlap = len(query_words & words)
        score = (overlap / max(len(query_words), 1)) * 0.7 + row[3] * 0.3
        scored.append((row, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:top_k]
    
    memories = [{"s": s[0][0], "p": s[0][1], "o": s[0][2][:60], "c": round(s[0][3], 2), "a": round(s[1], 3)} for s in top]
    
    return [TextContent(type="text", text=compact_json({"n": len(memories), "total_scanned": len(rows), "domain": domain or "all", "top": memories}))]


async def handle_attention_multihead(args: Dict[str, Any]) -> List[TextContent]:
    """Multi-head attention retrieval with domain separation"""
    query = args.get("query", "")
    num_heads = args.get("num_heads", 4)
    domain = args.get("domain", "")
    
    if not store._conn:
        return [TextContent(type="text", text=compact_json({"error": "DB not connected", "n": 0}))]
    
    # Auto-detect domain from query if not specified
    if not domain:
        domain = _auto_detect_domain(query)
    
    # Get atoms with domain filtering
    rows = await _get_domain_filtered_atoms(query, domain, limit=300)
    
    if not rows:
        return [TextContent(type="text", text=compact_json({"n": 0, "heads": []}))]
    
    query_words = set(query.lower().split())
    
    heads_results = []
    for head_idx in range(num_heads):
        scored = []
        for row in rows:
            text = f"{row[0]} {row[1]} {row[2]}".lower()
            words = set(text.split())
            
            if head_idx == 0:  # Semantic head
                overlap = len(query_words & words)
                score = overlap / max(len(query_words), 1)
            elif head_idx == 1:  # Confidence head
                score = row[3]
            elif head_idx == 2:  # Length head (prefer concise)
                score = 1.0 / (1 + len(text) / 50)
            else:  # Mixed head
                overlap = len(query_words & words)
                score = (overlap / max(len(query_words), 1)) * 0.5 + row[3] * 0.5
            
            scored.append((row, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:3]
        heads_results.append({
            "head": head_idx,
            "top": [{"s": s[0][0], "p": s[0][1], "o": s[0][2][:40]} for s in top]
        })
    
    return [TextContent(type="text", text=compact_json({
        "n": len(rows),
        "heads": heads_results[:4]
    }))]


async def handle_knowledge_add(args: Dict[str, Any]) -> List[TextContent]:
    """Add concept to knowledge graph"""
    from src.memory.knowledge_graph import KnowledgeNetworkGraph
    
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeNetworkGraph(store)
    
    result = await _knowledge_graph.add_concept(
        args["concept"],
        args["domain"],
        args.get("related_concepts")
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_knowledge_path(args: Dict[str, Any]) -> List[TextContent]:
    """Find path between concepts"""
    from src.memory.knowledge_graph import KnowledgeNetworkGraph
    
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeNetworkGraph(store)
    
    result = await _knowledge_graph.find_path(
        args["from_concept"],
        args["to_concept"]
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_knowledge_bridges(args: Dict[str, Any]) -> List[TextContent]:
    """Find bridge concepts"""
    from src.memory.knowledge_graph import KnowledgeNetworkGraph
    
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeNetworkGraph(store)
    
    result = await _knowledge_graph.find_bridges(args.get("top_k", 10))
    return [TextContent(type="text", text=compact_json(result))]


async def handle_knowledge_stats(args: Dict[str, Any]) -> List[TextContent]:
    """Get knowledge graph stats"""
    from src.memory.knowledge_graph import KnowledgeNetworkGraph
    
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeNetworkGraph(store)
    
    result = await _knowledge_graph.get_network_stats()
    return [TextContent(type="text", text=compact_json(result))]


async def handle_improve_cycle(args: Dict[str, Any]) -> List[TextContent]:
    """Run self-improvement cycle"""
    from src.meta.recursive_improvement import RecursiveSelfImprovement
    
    global _self_improver
    if _self_improver is None:
        _self_improver = RecursiveSelfImprovement(store)
    
    result = await _self_improver.run_improvement_cycle()
    return [TextContent(type="text", text=compact_json(result))]


async def handle_meta_learn(args: Dict[str, Any]) -> List[TextContent]:
    """Meta-learn from improvements"""
    from src.meta.recursive_improvement import RecursiveSelfImprovement
    
    global _self_improver
    if _self_improver is None:
        _self_improver = RecursiveSelfImprovement(store)
    
    result = await _self_improver.meta_learn()
    return [TextContent(type="text", text=compact_json(result))]


async def handle_improve_history(args: Dict[str, Any]) -> List[TextContent]:
    """Get improvement history"""
    from src.meta.recursive_improvement import RecursiveSelfImprovement
    
    global _self_improver
    if _self_improver is None:
        _self_improver = RecursiveSelfImprovement(store)
    
    result = await _self_improver.get_improvement_history()
    return [TextContent(type="text", text=compact_json(result))]


async def handle_quantum_cleanup(args: Dict[str, Any]) -> List[TextContent]:
    """Cleanup old quantum states"""
    from src.memory.quantum_superposition import QuantumMemorySystem
    
    global _quantum_memory
    if _quantum_memory is None:
        _quantum_memory = QuantumMemorySystem(store)
    
    result = await _quantum_memory.cleanup_old_states()
    return [TextContent(type="text", text=compact_json(result))]


async def handle_quantum_stats(args: Dict[str, Any]) -> List[TextContent]:
    """Get quantum memory stats"""
    from src.memory.quantum_superposition import QuantumMemorySystem
    
    global _quantum_memory
    if _quantum_memory is None:
        _quantum_memory = QuantumMemorySystem(store)
    
    result = await _quantum_memory.get_stats()
    return [TextContent(type="text", text=compact_json(result))]


async def handle_attention_clear_cache(args: Dict[str, Any]) -> List[TextContent]:
    """Clear attention cache"""
    from src.memory.attention_retrieval import AttentionMemoryRetrieval
    
    global _attention_retrieval
    if _attention_retrieval is None:
        _attention_retrieval = AttentionMemoryRetrieval(store)
    
    count = _attention_retrieval.clear_cache()
    return [TextContent(type="text", text=compact_json({"cleared": count}))]


# Global criticality instance
_criticality = None

async def handle_criticality_state(args: Dict[str, Any]) -> List[TextContent]:
    """Get criticality state - lightweight direct SQL"""
    import math
    
    if not store._conn:
        return [TextContent(type="text", text=compact_json({"error": "DB not connected"}))]
    
    # Get confidence stats for entropy calculation
    cursor = await store._conn.execute(
        "SELECT confidence, predicate FROM atoms WHERE graph = 'substantiated'"
    )
    rows = await cursor.fetchall()
    
    if not rows:
        return [TextContent(type="text", text=compact_json({
            "entropy": 0.5, "integration": 0.5, "ratio": 1.0, "zone": "critical", "n": 0
        }))]
    
    # Entropy: confidence variance + domain diversity
    confidences = [r[0] for r in rows]
    mean_conf = sum(confidences) / len(confidences)
    variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)
    conf_entropy = min(1.0, variance * 4)  # Scale variance to 0-1
    
    # Domain entropy
    domains = {}
    for r in rows:
        domains[r[1]] = domains.get(r[1], 0) + 1
    
    total = len(rows)
    domain_entropy = 0.0
    for count in domains.values():
        p = count / total
        if p > 0:
            domain_entropy -= p * math.log2(p)
    max_ent = math.log2(len(domains)) if len(domains) > 1 else 1.0
    norm_domain_ent = domain_entropy / max_ent if max_ent > 0 else 0.0
    
    entropy = (conf_entropy * 0.4 + norm_domain_ent * 0.6)
    
    # Integration: mean confidence + domain connectivity proxy
    integration = mean_conf * 0.7 + (1 - norm_domain_ent) * 0.3
    
    # Criticality ratio
    ratio = entropy / integration if integration > 0 else 1.0
    
    # Zone classification
    if ratio < 0.8:
        zone = "subcritical"
    elif ratio > 1.2:
        zone = "supercritical"
    else:
        zone = "critical"
    
    return [TextContent(type="text", text=compact_json({
        "entropy": round(entropy, 3),
        "integration": round(integration, 3),
        "ratio": round(ratio, 3),
        "zone": zone,
        "n": len(rows),
        "domains": len(domains)
    }))]


async def handle_criticality_recommend(args: Dict[str, Any]) -> List[TextContent]:
    """Get criticality recommendation"""
    from src.meta.criticality import SelfOrganizedCriticality
    
    global _criticality
    if _criticality is None:
        _criticality = SelfOrganizedCriticality(store)
    
    result = await _criticality.get_adjustment_recommendation()
    return [TextContent(type="text", text=compact_json(result))]


async def handle_criticality_adjust(args: Dict[str, Any]) -> List[TextContent]:
    """Auto-adjust toward criticality"""
    from src.meta.criticality import SelfOrganizedCriticality
    
    global _criticality
    if _criticality is None:
        _criticality = SelfOrganizedCriticality(store)
    
    result = await _criticality.auto_adjust()
    return [TextContent(type="text", text=compact_json(result))]


async def handle_criticality_history(args: Dict[str, Any]) -> List[TextContent]:
    """Get criticality history"""
    from src.meta.criticality import SelfOrganizedCriticality
    
    global _criticality
    if _criticality is None:
        _criticality = SelfOrganizedCriticality(store)
    
    result = await _criticality.get_criticality_history()
    return [TextContent(type="text", text=compact_json(result))]


async def handle_add_provenance(args: Dict[str, Any]) -> List[TextContent]:
    """Add provenance for a claim"""
    import hashlib
    from datetime import datetime
    
    claim_id = args.get("claim_id")
    source_type = args.get("source_type")
    source_url = args.get("source_url")
    quoted_span = args.get("quoted_span")
    confidence = args.get("confidence", 0.5)
    
    # Generate provenance ID and content hash
    prov_id = f"prov_{source_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    content_hash = hashlib.sha256(quoted_span.encode()).hexdigest()
    
    await store.insert_provenance(
        provenance_id=prov_id,
        claim_id=claim_id,
        source_type=source_type,
        source_url=source_url,
        source_title=args.get("source_title", ""),
        quoted_span=quoted_span,
        page_or_section=args.get("page_or_section"),
        accessed_at=int(datetime.now().timestamp()),
        content_hash=content_hash,
        confidence=confidence,
        authors=args.get("authors"),
        arxiv_id=args.get("arxiv_id"),
        doi=args.get("doi"),
        commit_sha=args.get("commit_sha"),
        file_path=args.get("file_path"),
        line_range=args.get("line_range")
    )
    
    return [TextContent(type="text", text=compact_json({
        "ok": True, "id": prov_id, "type": source_type, "hash": content_hash[:16]
    }))]


async def handle_get_provenance(args: Dict[str, Any]) -> List[TextContent]:
    """Get provenance for a claim"""
    claim_id = args.get("claim_id")
    provs = await store.get_provenance_for_claim(claim_id)
    
    # Compact format
    result = [{
        "type": p["source_type"],
        "url": p["source_url"][:60],
        "quote": p["quoted_span"][:100],
        "conf": p["confidence"]
    } for p in provs]
    
    return [TextContent(type="text", text=compact_json({"n": len(result), "provs": result}))]


async def handle_provenance_stats(args: Dict[str, Any]) -> List[TextContent]:
    """Get provenance statistics"""
    stats = await store.get_provenance_stats()
    return [TextContent(type="text", text=compact_json(stats))]


async def handle_unverified_claims(args: Dict[str, Any]) -> List[TextContent]:
    """Get unverified claims"""
    unverified = await store.get_unverified_claims()
    return [TextContent(type="text", text=compact_json({
        "n": len(unverified), 
        "claims": unverified[:20]  # Limit to 20 for token efficiency
    }))]


async def handle_mmr_retrieve(args: Dict[str, Any]) -> List[TextContent]:
    """MMR retrieval for diverse context selection with domain separation"""
    import numpy as np
    import time
    
    query = args.get("query", "")
    top_k = args.get("top_k", 5)
    lambda_param = args.get("lambda_param", 0.6)
    domain = args.get("domain", "")
    
    start = time.time()
    
    if not store._conn:
        return [TextContent(type="text", text=compact_json({"error": "DB not connected", "n": 0}))]
    
    # Auto-detect domain from query if not specified
    if not domain:
        domain = _auto_detect_domain(query)
    
    # Get atoms with domain filtering
    rows = await _get_domain_filtered_atoms(query, domain, limit=200)
    
    if not rows:
        return [TextContent(type="text", text=compact_json({"n": 0, "memories": [], "mean_dissim": 0.0}))]
    
    # Simple hash-based embedding
    def text_to_vec(text: str, dim: int = 32) -> np.ndarray:
        vec = np.zeros(dim)
        for word in text.lower().split():
            vec[hash(word) % dim] += 1.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
    
    # Compute relevance (keyword overlap with query)
    query_words = set(query.lower().split())
    relevance = []
    embeddings = []
    
    for row in rows:
        text = f"{row[0]} {row[1]} {row[2]}"
        overlap = len(set(text.lower().split()) & query_words)
        rel = (overlap / max(len(query_words), 1)) * 0.7 + row[3] * 0.3
        relevance.append(rel)
        embeddings.append(text_to_vec(text))
    
    relevance = np.array(relevance)
    embeddings = np.array(embeddings)
    
    # Greedy MMR selection
    selected = []
    remaining = list(range(len(rows)))
    remaining.sort(key=lambda i: relevance[i], reverse=True)
    
    for _ in range(min(top_k, len(rows))):
        if not remaining:
            break
        
        best_idx = None
        best_score = float('-inf')
        
        for idx in remaining[:20]:
            if not selected:
                score = relevance[idx]
            else:
                max_sim = max(
                    float(np.dot(embeddings[idx], embeddings[s]) / 
                          (np.linalg.norm(embeddings[idx]) * np.linalg.norm(embeddings[s]) + 1e-9))
                    for s in selected
                )
                score = lambda_param * relevance[idx] - (1 - lambda_param) * max_sim
            
            if score > best_score:
                best_score = score
                best_idx = idx
        
        if best_idx is not None:
            selected.append(best_idx)
            remaining.remove(best_idx)
    
    memories = [{"s": rows[i][0], "p": rows[i][1], "o": rows[i][2][:50], "rel": round(relevance[i], 2)} for i in selected]
    
    elapsed = time.time() - start
    return [TextContent(type="text", text=compact_json({
        "n": len(memories), 
        "memories": memories,
        "ms": int(elapsed * 1000),
        "lambda": lambda_param
    }))]


# === ACTION ACCOUNTING HANDLERS ===

_action_accounting = None

def get_action_accounting():
    global _action_accounting
    if _action_accounting is None:
        from src.metrics.action_accounting import ActionAccounting
        _action_accounting = ActionAccounting()
    return _action_accounting


async def handle_record_action(args: Dict[str, Any]) -> List[TextContent]:
    """Record an action for AAE tracking"""
    aa = get_action_accounting()
    record = aa.record(
        operation=args.get("operation"),
        tokens_used=args.get("tokens_used"),
        latency_ms=args.get("latency_ms"),
        success=args.get("success"),
        context=args.get("context")
    )
    return [TextContent(type="text", text=compact_json(record.to_dict()))]


async def handle_get_aae(args: Dict[str, Any]) -> List[TextContent]:
    """Get current AAE metrics"""
    aa = get_action_accounting()
    metrics = aa.get_aae(last_n=args.get("last_n"))
    return [TextContent(type="text", text=compact_json(metrics.to_dict()))]


async def handle_aae_trend(args: Dict[str, Any]) -> List[TextContent]:
    """Get AAE trend"""
    aa = get_action_accounting()
    trend = aa.get_trend(window_size=args.get("window_size", 10))
    return [TextContent(type="text", text=compact_json(trend))]


async def handle_start_action_cycle(args: Dict[str, Any]) -> List[TextContent]:
    """Start action measurement cycle"""
    aa = get_action_accounting()
    cycle_id = args.get("cycle_id")
    aa.start_cycle(cycle_id)
    return [TextContent(type="text", text=compact_json({"ok": True, "cycle": cycle_id}))]


async def handle_end_action_cycle(args: Dict[str, Any]) -> List[TextContent]:
    """End action cycle and get metrics"""
    aa = get_action_accounting()
    metrics = aa.end_cycle(args.get("cycle_id"))
    return [TextContent(type="text", text=compact_json(metrics.to_dict()))]


# === ENTROPY INJECTION HANDLERS ===

_entropy_injector = None

def get_entropy_injector():
    global _entropy_injector
    if _entropy_injector is None:
        from src.memory.entropy_injector import EntropyInjector
        _entropy_injector = EntropyInjector(store)
    return _entropy_injector


async def handle_inject_entropy_random(args: Dict[str, Any]) -> List[TextContent]:
    """Inject entropy via random domain sampling - lightweight direct SQL"""
    user_id = args.get("user_id", "alby")
    n_domains = args.get("n_domains", 3)
    
    if not store._conn:
        return [TextContent(type="text", text=compact_json({"error": "DB not connected", "n": 0}))]
    
    # Get domains directly
    cursor = await store._conn.execute(
        "SELECT DISTINCT predicate FROM atoms WHERE subject = ? LIMIT 20",
        (user_id,)
    )
    rows = await cursor.fetchall()
    
    if not rows:
        return [TextContent(type="text", text=compact_json({"n": 0, "domains": 0, "entropy_gain": 0}))]
    
    import random
    domains = [r[0] for r in rows]
    selected = random.sample(domains, min(n_domains, len(domains)))
    
    return [TextContent(type="text", text=compact_json({
        "n": len(selected),
        "domains": selected[:5],
        "entropy_gain": round(0.1 * len(selected), 3)
    }))]


async def handle_inject_entropy_antipodal(args: Dict[str, Any]) -> List[TextContent]:
    """Inject entropy via antipodal activation - lightweight direct SQL"""
    user_id = args.get("user_id", "alby")
    context = args.get("current_context", "")
    n_memories = args.get("n_memories", 5)
    
    if not store._conn:
        return [TextContent(type="text", text=compact_json({"error": "DB not connected", "n": 0}))]
    
    # Get memories directly
    cursor = await store._conn.execute(
        "SELECT predicate, object FROM atoms WHERE subject = ? LIMIT 50",
        (user_id,)
    )
    rows = await cursor.fetchall()
    
    if not rows:
        return [TextContent(type="text", text=compact_json({"n": 0, "memories": [], "entropy_gain": 0}))]
    
    # Score by distance from context
    context_words = set(context.lower().split())
    scored = []
    for row in rows:
        text = f"{row[0]} {row[1]}".lower()
        words = set(text.split())
        overlap = len(context_words & words)
        union = len(context_words | words)
        dist = 1 - (overlap / union) if union > 0 else 1.0
        scored.append((row, dist))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    selected = scored[:n_memories]
    
    memories = [{"p": s[0][0], "o": s[0][1][:40], "dist": round(s[1], 2)} for s in selected]
    avg_dist = sum(s[1] for s in selected) / len(selected) if selected else 0
    
    return [TextContent(type="text", text=compact_json({
        "n": len(memories),
        "memories": memories[:5],
        "entropy_gain": round(0.15 * len(selected) * avg_dist, 3)
    }))]


async def handle_inject_entropy_temporal(args: Dict[str, Any]) -> List[TextContent]:
    """Inject entropy via temporal diversity - lightweight direct SQL"""
    user_id = args.get("user_id", "alby")
    n_old = args.get("n_old", 3)
    n_recent = args.get("n_recent", 2)
    
    if not store._conn:
        return [TextContent(type="text", text=compact_json({"error": "DB not connected", "n": 0}))]
    
    # Get old memories
    cursor = await store._conn.execute(
        "SELECT predicate, object FROM atoms WHERE subject = ? ORDER BY first_observed ASC LIMIT ?",
        (user_id, n_old)
    )
    old = await cursor.fetchall()
    
    # Get recent memories
    cursor = await store._conn.execute(
        "SELECT predicate, object FROM atoms WHERE subject = ? ORDER BY first_observed DESC LIMIT ?",
        (user_id, n_recent)
    )
    recent = await cursor.fetchall()
    
    all_mem = [{"p": m[0], "o": m[1][:40], "age": "old"} for m in old]
    all_mem += [{"p": m[0], "o": m[1][:40], "age": "recent"} for m in recent]
    
    return [TextContent(type="text", text=compact_json({
        "n": len(all_mem),
        "memories": all_mem[:5],
        "entropy_gain": round(0.12 * len(all_mem), 3)
    }))]


async def handle_entropy_stats(args: Dict[str, Any]) -> List[TextContent]:
    """Get entropy statistics - lightweight direct SQL"""
    import math
    user_id = args.get("user_id", "alby")
    
    if not store._conn:
        return [TextContent(type="text", text=compact_json({"error": "DB not connected"}))]
    
    cursor = await store._conn.execute(
        "SELECT predicate, COUNT(*) FROM atoms WHERE subject = ? GROUP BY predicate",
        (user_id,)
    )
    rows = await cursor.fetchall()
    
    if not rows:
        return [TextContent(type="text", text=compact_json({
            "domains": 0, "total": 0, "entropy": 0, "needs_injection": True
        }))]
    
    total = sum(r[1] for r in rows)
    entropy = 0.0
    for _, count in rows:
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    
    max_ent = math.log2(len(rows)) if len(rows) > 1 else 1.0
    norm_ent = entropy / max_ent if max_ent > 0 else 0.0
    
    return [TextContent(type="text", text=compact_json({
        "domains": len(rows),
        "total": total,
        "entropy": round(entropy, 3),
        "normalized": round(norm_ent, 3),
        "needs_injection": norm_ent < 0.6,
        "top_domains": [{"d": r[0], "n": r[1]} for r in sorted(rows, key=lambda x: x[1], reverse=True)[:5]]
    }))]


# === ARXIV INGESTION HANDLERS ===

_arxiv_ingestion = None

def get_arxiv_ingestion():
    global _arxiv_ingestion
    if _arxiv_ingestion is None:
        from src.learning.arxiv_ingestion import ArxivIngestion
        _arxiv_ingestion = ArxivIngestion(store)
    return _arxiv_ingestion


async def handle_ingest_arxiv_legacy(args: Dict[str, Any]) -> List[TextContent]:
    """Ingest single arXiv paper by ID with real provenance"""
    ai = get_arxiv_ingestion()
    result = await ai.ingest_paper(
        arxiv_id=args.get("arxiv_id"),
        user_id=args.get("user_id", "pltm_knowledge")
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_search_arxiv(args: Dict[str, Any]) -> List[TextContent]:
    """Search arXiv for papers"""
    ai = get_arxiv_ingestion()
    results = await ai.search_arxiv(
        query=args.get("query"),
        max_results=args.get("max_results", 5)
    )
    return [TextContent(type="text", text=compact_json({"n": len(results), "papers": results}))]


async def handle_arxiv_history(args: Dict[str, Any]) -> List[TextContent]:
    """Get arXiv ingestion history"""
    ai = get_arxiv_ingestion()
    history = ai.get_ingestion_history(args.get("last_n", 10))
    return [TextContent(type="text", text=compact_json({"n": len(history), "history": history}))]


# === AGI BREAKTHROUGH ENGINE HANDLERS ===
# Architecture: These tools are DATA PROVIDERS. Claude Desktop IS the reasoning engine.
# No API key needed — the tools return compressed knowledge for Claude to synthesize.


def _compress_atoms_for_claude(atoms, max_atoms=50):
    """Compress atoms into dense one-liners for Claude to reason over"""
    seen = set()
    unique = []
    for a in atoms:
        key = (a.subject.lower(), a.predicate.lower(), a.object.lower()[:50])
        if key not in seen:
            seen.add(key)
            unique.append(a)
    unique.sort(key=lambda a: a.confidence, reverse=True)
    lines = []
    for a in unique[:max_atoms]:
        obj = a.object[:100] if len(a.object) > 100 else a.object
        lines.append(f"- {a.subject} {a.predicate} {obj} (c:{a.confidence:.1f})")
    return "\n".join(lines)


async def _get_domain_data():
    """Get all atoms grouped by domain"""
    from src.learning.cross_domain_synthesis import CrossDomainSynthesizer
    cs = CrossDomainSynthesizer(store)
    return await cs._get_atoms_by_domain()


async def handle_breakthrough_synthesize(args: Dict[str, Any]) -> List[TextContent]:
    """Return compressed knowledge from two domains for Claude to synthesize"""
    domain_atoms = await _get_domain_data()
    
    domain_a = args.get("domain_a")
    domain_b = args.get("domain_b")
    
    if domain_a and domain_b:
        atoms_a = domain_atoms.get(domain_a, [])
        atoms_b = domain_atoms.get(domain_b, [])
        
        if not atoms_a and not atoms_b:
            avail = [f"{d}({len(a)})" for d, a in sorted(domain_atoms.items(), key=lambda x: -len(x[1]))]
            return [TextContent(type="text", text=compact_json({
                "ok": False, "err": f"No atoms for {domain_a} or {domain_b}",
                "available_domains": avail[:20]
            }))]
        
        result = {
            "ok": True,
            "task": "SYNTHESIZE: Find non-obvious connections between these domains",
            "domain_a": {"name": domain_a, "n": len(atoms_a), "knowledge": _compress_atoms_for_claude(atoms_a, 30)},
            "domain_b": {"name": domain_b, "n": len(atoms_b), "knowledge": _compress_atoms_for_claude(atoms_b, 30)},
        }
    else:
        # Return all domains with their knowledge for full synthesis
        domains_summary = {}
        for d, atoms in sorted(domain_atoms.items(), key=lambda x: -len(x[1])):
            if len(atoms) >= 1:
                domains_summary[d] = {
                    "n": len(atoms),
                    "knowledge": _compress_atoms_for_claude(atoms, 15)
                }
        result = {
            "ok": True,
            "task": "SYNTHESIZE: Find cross-domain patterns, analogies, and non-obvious connections across ALL domains below",
            "total_atoms": sum(len(a) for a in domain_atoms.values()),
            "domains": domains_summary,
        }
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_generate_hypotheses(args: Dict[str, Any]) -> List[TextContent]:
    """Return compressed knowledge for Claude to generate hypotheses from"""
    domain_atoms = await _get_domain_data()
    
    domains = args.get("domains", [])
    questions = args.get("questions", [])
    
    if domains:
        atoms = []
        for d in domains:
            atoms.extend(domain_atoms.get(d, []))
    else:
        atoms = [a for al in domain_atoms.values() for a in al]
    
    result = {
        "ok": True,
        "task": "HYPOTHESIZE: Generate novel testable hypotheses from this knowledge. Each must have a falsifiable prediction.",
        "n_atoms": len(atoms),
        "knowledge": _compress_atoms_for_claude(atoms, 50),
    }
    if questions:
        result["open_questions"] = questions[:10]
    if domains:
        result["focus_domains"] = domains
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_evaluate_hypothesis(args: Dict[str, Any]) -> List[TextContent]:
    """Return relevant evidence for Claude to evaluate a hypothesis"""
    domain_atoms = await _get_domain_data()
    
    hypothesis = args["hypothesis"]
    domains = args.get("domains", [])
    
    if domains:
        evidence = []
        for d in domains:
            evidence.extend(domain_atoms.get(d, []))
    else:
        evidence = [a for al in domain_atoms.values() for a in al]
    
    result = {
        "ok": True,
        "task": f"EVALUATE: Does the evidence support or refute this hypothesis?",
        "hypothesis": hypothesis[:300],
        "n_evidence": len(evidence),
        "evidence": _compress_atoms_for_claude(evidence, 40),
    }
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_find_analogies(args: Dict[str, Any]) -> List[TextContent]:
    """Return knowledge from two domains for Claude to find structural analogies"""
    domain_atoms = await _get_domain_data()
    
    concept = args["concept"]
    source_domain = args["source_domain"]
    target_domain = args["target_domain"]
    
    source_atoms = domain_atoms.get(source_domain, [])
    target_atoms = domain_atoms.get(target_domain, [])
    
    if not source_atoms and not target_atoms:
        avail = [f"{d}({len(a)})" for d, a in sorted(domain_atoms.items(), key=lambda x: -len(x[1]))]
        return [TextContent(type="text", text=compact_json({
            "ok": False, "err": f"No atoms for {source_domain} or {target_domain}",
            "available_domains": avail[:20]
        }))]
    
    result = {
        "ok": True,
        "task": f"ANALOGIZE: Find structural analogies for '{concept}' between these domains. Focus on same-role/same-function mappings, not surface similarities.",
        "concept": concept,
        "source": {"domain": source_domain, "n": len(source_atoms), "knowledge": _compress_atoms_for_claude(source_atoms, 25)},
        "target": {"domain": target_domain, "n": len(target_atoms), "knowledge": _compress_atoms_for_claude(target_atoms, 25)},
    }
    
    return [TextContent(type="text", text=compact_json(result))]


# === RESEARCH AGENDA HANDLERS ===

_research_agenda = None

def get_research_agenda():
    global _research_agenda
    if _research_agenda is None:
        from src.learning.research_agenda import ResearchAgenda
        _research_agenda = ResearchAgenda(store)
    return _research_agenda


async def handle_add_research_question(args: Dict[str, Any]) -> List[TextContent]:
    """Add a research question to the agenda"""
    agenda = get_research_agenda()
    result = await agenda.add_question(
        question=args["question"],
        domains=args.get("domains"),
        priority=args.get("priority", 0.5),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_get_research_agenda(args: Dict[str, Any]) -> List[TextContent]:
    """Get active research questions"""
    agenda = get_research_agenda()
    result = await agenda.get_active_questions(limit=args.get("limit", 10))
    return [TextContent(type="text", text=compact_json(result))]


async def handle_evaluate_agenda(args: Dict[str, Any]) -> List[TextContent]:
    """Evaluate new knowledge against open questions"""
    agenda = get_research_agenda()
    
    # Get recent atoms to evaluate
    subject = args.get("subject", "")
    if subject:
        atoms = await store.get_atoms_by_subject(subject)
    else:
        # Get all recent atoms (last 100)
        if store._conn:
            cursor = await store._conn.execute(
                "SELECT id, atom_type, graph, subject, predicate, object, metadata, confidence FROM atoms ORDER BY last_accessed DESC LIMIT 100"
            )
            rows = await cursor.fetchall()
            atoms = []
            for r in rows:
                atoms.append(MemoryAtom(
                    id=r[0] if r[0] else None,
                    atom_type=AtomType.STATE,
                    graph=GraphType.SUBSTANTIATED,
                    subject=r[3],
                    predicate=r[4],
                    object=r[5],
                    confidence=r[7] or 0.5,
                    strength=0.5,
                    provenance=Provenance.INFERRED,
                ))
        else:
            atoms = []
    
    matches = await agenda.evaluate_against_agenda(atoms)
    return [TextContent(type="text", text=compact_json(agenda.matches_to_compact(matches)))]


async def handle_suggest_research_searches(args: Dict[str, Any]) -> List[TextContent]:
    """Claude suggests searches to answer a research question"""
    agenda = get_research_agenda()
    result = await agenda.suggest_searches(args["question_id"])
    return [TextContent(type="text", text=compact_json(result))]


async def handle_close_research_question(args: Dict[str, Any]) -> List[TextContent]:
    """Close/answer a research question"""
    agenda = get_research_agenda()
    result = await agenda.close_question(
        question_id=args["question_id"],
        answer=args.get("answer", ""),
        status=args.get("status", "answered"),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_bulk_store(args: Dict[str, Any]) -> List[TextContent]:
    """Store multiple knowledge atoms in one call"""
    atoms_data = args.get("atoms", [])
    
    stored = 0
    errors = 0
    for item in atoms_data[:50]:  # Cap at 50 per call
        try:
            atom = MemoryAtom(
                atom_type=AtomType.STATE,
                subject=str(item.get("subject", ""))[:100],
                predicate=str(item.get("predicate", ""))[:50],
                object=str(item.get("object", ""))[:300],
                confidence=float(item.get("confidence", 0.7)),
                strength=float(item.get("confidence", 0.7)),
                provenance=Provenance.INFERRED,
                source_user=str(item.get("user_id", "pltm_knowledge")),
                contexts=item.get("context", []) if isinstance(item.get("context"), list) else [str(item.get("context", "general"))],
                graph=GraphType.SUBSTANTIATED,
            )
            await store.add_atom(atom)
            stored += 1
        except Exception as e:
            errors += 1
            logger.warning(f"bulk_store atom error: {e}")
    
    return [TextContent(type="text", text=compact_json({"ok": True, "stored": stored, "err": errors}))]


async def handle_deep_extract(args: Dict[str, Any]) -> List[TextContent]:
    """Extract structured knowledge from text.
    
    Two modes:
    1. If 'triples' provided: store them directly (Claude already extracted)
    2. If only 'content' provided: return instructions for Claude to extract
    """
    triples_data = args.get("triples", [])
    
    if triples_data:
        # Mode 1: Claude already extracted triples — store them
        stored = 0
        for t in triples_data[:20]:
            atom = MemoryAtom(
                atom_type=AtomType.STATE,
                subject=str(t.get("s", t.get("subject", "")))[:100],
                predicate=str(t.get("p", t.get("predicate", "")))[:50],
                object=str(t.get("o", t.get("object", "")))[:200],
                confidence=float(t.get("c", t.get("confidence", 0.7))),
                strength=float(t.get("c", t.get("confidence", 0.7))),
                provenance=Provenance.INFERRED,
                source_user="deep_extract",
                contexts=["extracted", str(t.get("d", t.get("domain", "general")))],
                graph=GraphType.SUBSTANTIATED,
            )
            await store.add_atom(atom)
            stored += 1
        
        return [TextContent(type="text", text=compact_json({"ok": True, "stored": stored}))]
    
    else:
        # Mode 2: Return content + instructions for Claude to extract and call back with triples
        content = args.get("content", "")
        source_type = args.get("source_type", "general")
        
        return [TextContent(type="text", text=compact_json({
            "ok": True,
            "task": "EXTRACT: Read this text and extract structured knowledge triples. Then call deep_extract again with the 'triples' parameter.",
            "format": "triples: [{s:'subject', p:'predicate', o:'object', c:0.0-1.0, d:'domain'}]",
            "content": content[:3000],
            "source_type": source_type,
        }))]


# === ANALYSIS TOOL HANDLERS ===

async def handle_calculate_phi(args: Dict[str, Any]) -> List[TextContent]:
    """Calculate Φ integration for domain(s)"""
    from src.analysis.phi_integration import PhiIntegrationCalculator
    
    calc = PhiIntegrationCalculator()
    all_domains_flag = args.get("all_domains", False)
    domain = args.get("domain")
    return_ts = args.get("return_timeseries", False)
    
    domain_atoms = await _get_domain_data()
    
    if all_domains_flag or not domain:
        # Calculate for all domains
        results = {}
        for d, atoms in sorted(domain_atoms.items(), key=lambda x: -len(x[1])):
            r = calc.calculate(d, atoms)
            results[d] = calc.to_compact(r)
        
        return [TextContent(type="text", text=compact_json({
            "ok": True, "n_domains": len(results), "phi_scores": results
        }))]
    else:
        atoms = domain_atoms.get(domain, [])
        if not atoms:
            avail = [f"{d}({len(a)})" for d, a in sorted(domain_atoms.items(), key=lambda x: -len(x[1]))]
            return [TextContent(type="text", text=compact_json({
                "ok": False, "err": f"No atoms for domain '{domain}'",
                "available_domains": avail[:20]
            }))]
        
        result = calc.calculate(domain, atoms)
        out = calc.to_compact(result)
        
        if return_ts:
            out["timeseries"] = calc.get_timeseries(domain, limit=20)
        
        return [TextContent(type="text", text=compact_json({"ok": True, **out}))]


async def handle_create_indicator(args: Dict[str, Any]) -> List[TextContent]:
    """Create a tracked indicator"""
    from src.analysis.indicator_tracker import IndicatorTracker
    
    tracker = IndicatorTracker()
    result = tracker.create_indicator(
        indicator_id=args["indicator_id"],
        name=args["name"],
        domain=args["domain"],
        threshold=float(args["threshold"]),
        direction=args.get("direction", "above"),
        check_frequency=args.get("check_frequency", "weekly"),
        initial_value=float(args.get("initial_value", 0)),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_update_indicator(args: Dict[str, Any]) -> List[TextContent]:
    """Update an indicator value"""
    from src.analysis.indicator_tracker import IndicatorTracker
    
    tracker = IndicatorTracker()
    result = tracker.update_indicator(
        indicator_id=args["indicator_id"],
        value=float(args["value"]),
        note=args.get("note", ""),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_check_indicators(args: Dict[str, Any]) -> List[TextContent]:
    """Check all indicators or get history for one"""
    from src.analysis.indicator_tracker import IndicatorTracker
    
    tracker = IndicatorTracker()
    indicator_id = args.get("indicator_id")
    
    if indicator_id:
        history = tracker.get_history(indicator_id, limit=30)
        return [TextContent(type="text", text=compact_json({"ok": True, "id": indicator_id, "history": history}))]
    else:
        result = tracker.check_all()
        return [TextContent(type="text", text=compact_json({"ok": True, **result}))]


async def handle_simulate_cascade(args: Dict[str, Any]) -> List[TextContent]:
    """Simulate multi-domain cascade"""
    from src.analysis.cascade_simulator import CascadeSimulator
    
    sim = CascadeSimulator()
    
    # Add custom dependencies if provided
    for dep in args.get("custom_dependencies", []):
        sim.add_dependency(dep["source"], dep["target"], float(dep.get("weight", 0.5)))
    
    result = sim.simulate(
        trigger_events=args["trigger_events"],
        domains=args.get("domains"),
        timeline=args.get("timeline", "scenario"),
        max_steps=args.get("max_steps", 10),
        initial_phi=args.get("initial_phi"),
    )
    
    return [TextContent(type="text", text=compact_json({"ok": True, **sim.to_compact(result)}))]


async def handle_query_structured_data(args: Dict[str, Any]) -> List[TextContent]:
    """Query structured data sources"""
    from src.analysis.structured_data import StructuredDataCollector
    
    collector = StructuredDataCollector()
    
    if args.get("list_sources"):
        return [TextContent(type="text", text=compact_json({"ok": True, "sources": collector.list_sources()}))]
    
    source = args.get("source", "")
    params = args.get("params", {})
    
    if not source:
        return [TextContent(type="text", text=compact_json({
            "ok": False, "err": "Specify 'source' or set list_sources=true",
            "sources": collector.list_sources()
        }))]
    
    result = collector.query(source, params)
    return [TextContent(type="text", text=compact_json({"ok": True, **collector.to_compact(result)}))]


# === STATE PERSISTENCE HANDLERS ===

async def handle_save_state(args: Dict[str, Any]) -> List[TextContent]:
    """Save persistent state"""
    from src.analysis.state_persistence import StatePersistence
    sp = StatePersistence()
    result = sp.save(args["key"], args["value"], args.get("category", "general"))
    return [TextContent(type="text", text=compact_json(result))]


async def handle_load_state(args: Dict[str, Any]) -> List[TextContent]:
    """Load persistent state"""
    from src.analysis.state_persistence import StatePersistence
    sp = StatePersistence()
    
    if args.get("list_all"):
        result = sp.list_states(args.get("category"))
        return [TextContent(type="text", text=compact_json(result))]
    
    key = args.get("key")
    if not key:
        result = sp.list_states(args.get("category"))
        return [TextContent(type="text", text=compact_json(result))]
    
    result = sp.load(key)
    return [TextContent(type="text", text=compact_json(result))]


async def handle_delete_state(args: Dict[str, Any]) -> List[TextContent]:
    """Delete persistent state"""
    from src.analysis.state_persistence import StatePersistence
    sp = StatePersistence()
    result = sp.delete(args["key"])
    return [TextContent(type="text", text=compact_json(result))]


# === GOAL MANAGEMENT HANDLERS ===

async def handle_create_goal(args: Dict[str, Any]) -> List[TextContent]:
    """Create a goal"""
    from src.analysis.goal_manager import GoalManager
    gm = GoalManager()
    result = gm.create_goal(
        title=args["title"],
        description=args["description"],
        category=args.get("category", "general"),
        priority=args.get("priority", "medium"),
        success_criteria=args.get("success_criteria"),
        plan=args.get("plan"),
        deadline=args.get("deadline"),
        parent_goal_id=args.get("parent_goal_id"),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_update_goal(args: Dict[str, Any]) -> List[TextContent]:
    """Update a goal"""
    from src.analysis.goal_manager import GoalManager
    gm = GoalManager()
    result = gm.update_goal(
        goal_id=args["goal_id"],
        progress=args.get("progress"),
        status=args.get("status"),
        add_blocker=args.get("add_blocker"),
        remove_blocker=args.get("remove_blocker"),
        complete_step=args.get("complete_step"),
        add_step=args.get("add_step"),
        note=args.get("note", ""),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_get_goals(args: Dict[str, Any]) -> List[TextContent]:
    """Get goals"""
    from src.analysis.goal_manager import GoalManager
    gm = GoalManager()
    result = gm.get_goals(
        status=args.get("status"),
        category=args.get("category"),
        include_plan=True,
        include_log=args.get("include_log", False),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_delete_goal(args: Dict[str, Any]) -> List[TextContent]:
    """Delete a goal"""
    from src.analysis.goal_manager import GoalManager
    gm = GoalManager()
    result = gm.delete_goal(args["goal_id"])
    return [TextContent(type="text", text=compact_json(result))]


# === DIRECT SQL HANDLER ===

async def handle_query_pltm_sql(args: Dict[str, Any]) -> List[TextContent]:
    """Execute raw SQL SELECT against PLTM database"""
    sql = args.get("sql", "").strip()
    params = args.get("params", [])
    limit = args.get("limit", 50)
    
    # Security: only allow SELECT
    sql_upper = sql.upper().lstrip()
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("PRAGMA") and not sql_upper.startswith("EXPLAIN"):
        return [TextContent(type="text", text=compact_json({"ok": False, "err": "Only SELECT, PRAGMA, and EXPLAIN queries allowed"}))]
    
    # Block dangerous patterns
    dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "ATTACH"]
    for d in dangerous:
        if d in sql_upper.split():
            return [TextContent(type="text", text=compact_json({"ok": False, "err": f"Blocked: {d} not allowed in read-only mode"}))]
    
    import sqlite3 as sync_sqlite
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "pltm_mcp.db")
    
    try:
        conn = sync_sqlite.connect(db_path)
        conn.row_factory = sync_sqlite.Row
        cursor = conn.execute(sql, params or [])
        
        cols = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(limit)
        
        data = []
        for row in rows:
            data.append({cols[i]: row[i] for i in range(len(cols))})
        
        total = len(data)
        conn.close()
        
        return [TextContent(type="text", text=compact_json({"ok": True, "cols": cols, "n": total, "rows": data}))]
    except Exception as e:
        return [TextContent(type="text", text=compact_json({"ok": False, "err": str(e)[:200]}))]


# === TASK SCHEDULER HANDLERS ===

async def handle_schedule_task(args: Dict[str, Any]) -> List[TextContent]:
    """Schedule a recurring task"""
    from src.analysis.task_scheduler import TaskScheduler
    ts = TaskScheduler()
    result = ts.schedule_task(
        name=args["name"],
        description=args["description"],
        task_type=args["task_type"],
        schedule=args.get("schedule", "daily"),
        tool_name=args.get("tool_name"),
        tool_args=args.get("tool_args"),
        script_path=args.get("script_path"),
        max_runs=args.get("max_runs"),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_check_scheduled_tasks(args: Dict[str, Any]) -> List[TextContent]:
    """Check for due tasks"""
    from src.analysis.task_scheduler import TaskScheduler
    ts = TaskScheduler()
    result = ts.check_due_tasks()
    return [TextContent(type="text", text=compact_json(result))]


async def handle_mark_task_done(args: Dict[str, Any]) -> List[TextContent]:
    """Mark a task run as done"""
    from src.analysis.task_scheduler import TaskScheduler
    ts = TaskScheduler()
    result = ts.mark_task_run(
        task_id=args["task_id"],
        result=args.get("result", ""),
        status=args.get("status", "success"),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_manage_task(args: Dict[str, Any]) -> List[TextContent]:
    """Pause, resume, or delete a task"""
    from src.analysis.task_scheduler import TaskScheduler
    ts = TaskScheduler()
    action = args["action"]
    task_id = args["task_id"]
    
    if action == "pause":
        result = ts.pause_task(task_id)
    elif action == "resume":
        result = ts.resume_task(task_id)
    elif action == "delete":
        result = ts.delete_task(task_id)
    else:
        result = {"ok": False, "err": f"Unknown action: {action}. Use pause, resume, or delete."}
    
    return [TextContent(type="text", text=compact_json(result))]


# === CRYPTOGRAPHY HANDLERS ===

async def handle_encrypt_data(args: Dict[str, Any]) -> List[TextContent]:
    """Encrypt data"""
    from src.analysis.crypto_ops import CryptoOps
    crypto = CryptoOps()
    result = crypto.encrypt(args["data"], args.get("password"))
    return [TextContent(type="text", text=compact_json(result))]


async def handle_decrypt_data(args: Dict[str, Any]) -> List[TextContent]:
    """Decrypt data"""
    from src.analysis.crypto_ops import CryptoOps
    crypto = CryptoOps()
    result = crypto.decrypt(
        args["encrypted_data"],
        args.get("password"),
        args.get("method", "fernet_aes128"),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_manage_secrets(args: Dict[str, Any]) -> List[TextContent]:
    """Manage encrypted secrets"""
    from src.analysis.crypto_ops import CryptoOps
    crypto = CryptoOps()
    action = args["action"]
    
    if action == "store":
        result = crypto.store_secret(args.get("name", ""), args.get("value", ""),
                                     args.get("category", "general"), args.get("password"))
    elif action == "get":
        result = crypto.get_secret(args.get("name", ""), args.get("password"))
    elif action == "list":
        result = crypto.list_secrets(args.get("category"))
    elif action == "delete":
        result = crypto.delete_secret(args.get("name", ""))
    else:
        result = {"ok": False, "err": f"Unknown action: {action}. Use store, get, list, or delete."}
    
    return [TextContent(type="text", text=compact_json(result))]


async def handle_hash_data(args: Dict[str, Any]) -> List[TextContent]:
    """Hash data or HMAC sign/verify"""
    from src.analysis.crypto_ops import CryptoOps
    crypto = CryptoOps()
    
    hmac_key = args.get("hmac_key")
    verify_sig = args.get("verify_signature")
    
    if hmac_key and verify_sig:
        result = crypto.hmac_verify(args["data"], hmac_key, verify_sig)
    elif hmac_key:
        result = crypto.hmac_sign(args["data"], hmac_key, args.get("algorithm", "sha256"))
    else:
        result = crypto.hash_data(args["data"], args.get("algorithm", "sha256"))
    
    return [TextContent(type="text", text=compact_json(result))]


# === SYSTEM CONTEXT HANDLER ===

async def handle_get_system_context(args: Dict[str, Any]) -> List[TextContent]:
    """Get system context"""
    from src.analysis.system_context import SystemContext
    ctx = SystemContext()
    result = ctx.get_context()
    return [TextContent(type="text", text=compact_json({"ok": True, **result}))]


# === API CLIENT HANDLERS ===

async def handle_api_request(args: Dict[str, Any]) -> List[TextContent]:
    """Make authenticated HTTP request"""
    from src.analysis.api_client import APIClient
    client = APIClient()
    result = client.request(
        url=args.get("url", ""),
        method=args.get("method", "GET"),
        profile_id=args.get("profile_id"),
        headers=args.get("headers"),
        body=args.get("body"),
        auth_type=args.get("auth_type"),
        auth_value=args.get("auth_value"),
        timeout=args.get("timeout"),
        params=args.get("params"),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_manage_api_profile(args: Dict[str, Any]) -> List[TextContent]:
    """Manage API profiles"""
    from src.analysis.api_client import APIClient
    client = APIClient()
    action = args["action"]
    
    if action == "create":
        result = client.create_profile(
            profile_id=args.get("profile_id", ""),
            base_url=args.get("base_url", ""),
            auth_type=args.get("auth_type", "none"),
            auth_value=args.get("auth_value", ""),
            headers=args.get("headers"),
            rate_limit_per_min=args.get("rate_limit_per_min", 60),
        )
    elif action == "list":
        result = client.list_profiles()
    elif action == "delete":
        result = client.delete_profile(args.get("profile_id", ""))
    else:
        result = {"ok": False, "err": f"Unknown action: {action}. Use create, list, or delete."}
    
    return [TextContent(type="text", text=compact_json(result))]


# === HYBRID MODEL ROUTER HANDLERS ===

async def handle_route_llm_task(args: Dict[str, Any]) -> List[TextContent]:
    """Route an LLM task to the cheapest appropriate model"""
    from src.analysis.model_router import ModelRouter
    router = ModelRouter()
    result = router.call(
        prompt=args["prompt"],
        provider=args.get("provider"),
        model=args.get("model"),
        task_type=args.get("task_type", "analysis"),
        system_prompt=args.get("system_prompt"),
        temperature=args.get("temperature", 0.3),
        max_tokens=args.get("max_tokens", 2048),
        require_privacy=args.get("require_privacy", False),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_llm_providers(args: Dict[str, Any]) -> List[TextContent]:
    """List available LLM providers and usage stats"""
    from src.analysis.model_router import ModelRouter
    router = ModelRouter()
    
    providers = router.get_available_providers()
    result = {"ok": True, "providers": providers}
    
    if args.get("show_usage"):
        result["usage"] = router.get_usage_stats(args.get("days", 30))
    
    return [TextContent(type="text", text=compact_json(result))]


# === DATA INGESTION HANDLERS ===

async def handle_ingest_url(args: Dict[str, Any]) -> List[TextContent]:
    """Scrape URL and extract triples"""
    from src.analysis.data_ingestion import DataIngestion
    di = DataIngestion()
    result = di.ingest_url(
        url=args["url"],
        domain=args.get("domain", "general"),
        max_triples=args.get("max_triples", 15),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_ingest_text(args: Dict[str, Any]) -> List[TextContent]:
    """Extract triples from raw text"""
    from src.analysis.data_ingestion import DataIngestion
    di = DataIngestion()
    result = di.ingest_text(
        text=args["text"],
        domain=args.get("domain", "general"),
        source=args.get("source", "user_input"),
        max_triples=args.get("max_triples", 15),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_ingest_file(args: Dict[str, Any]) -> List[TextContent]:
    """Read file and extract triples"""
    from src.analysis.data_ingestion import DataIngestion
    di = DataIngestion()
    result = di.ingest_file(
        file_path=args["file_path"],
        domain=args.get("domain", "general"),
        max_triples=args.get("max_triples", 20),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_ingest_arxiv(args: Dict[str, Any]) -> List[TextContent]:
    """Search arXiv and extract triples from papers"""
    from src.analysis.data_ingestion import DataIngestion
    di = DataIngestion()
    result = di.ingest_arxiv(
        query=args["query"],
        domain=args.get("domain", "science"),
        max_results=args.get("max_results", 5),
        max_triples_per_paper=args.get("max_triples_per_paper", 10),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_ingest_wikipedia(args: Dict[str, Any]) -> List[TextContent]:
    """Fetch Wikipedia article and extract triples"""
    from src.analysis.data_ingestion import DataIngestion
    di = DataIngestion()
    result = di.ingest_wikipedia(
        topic=args["topic"],
        domain=args.get("domain", "general"),
        max_triples=args.get("max_triples", 15),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_ingest_rss(args: Dict[str, Any]) -> List[TextContent]:
    """Fetch RSS feed and extract triples"""
    from src.analysis.data_ingestion import DataIngestion
    di = DataIngestion()
    result = di.ingest_rss(
        feed_url=args["feed_url"],
        domain=args.get("domain", "general"),
        max_items=args.get("max_items", 5),
        max_triples_per_item=args.get("max_triples_per_item", 8),
    )
    return [TextContent(type="text", text=compact_json(result))]


# === FACT-CHECKING HANDLERS ===

async def handle_fetch_arxiv_context(args: Dict[str, Any]) -> List[TextContent]:
    """Fetch actual text from arXiv paper matching a query"""
    from src.analysis.fact_checker import FactChecker
    fc = FactChecker()
    result = fc.fetch_arxiv_context(
        arxiv_id=args["arxiv_id"],
        query=args["query"],
        max_snippets=args.get("max_snippets", 5),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_verify_claim(args: Dict[str, Any]) -> List[TextContent]:
    """Verify a claim against its source"""
    from src.analysis.fact_checker import FactChecker
    fc = FactChecker()
    result = fc.verify_claim(
        claim=args["claim"],
        source_arxiv_id=args.get("source_arxiv_id", ""),
        source_text=args.get("source_text", ""),
        domain=args.get("domain", ""),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_verification_history(args: Dict[str, Any]) -> List[TextContent]:
    """Get verification history and stats"""
    from src.analysis.fact_checker import FactChecker
    fc = FactChecker()
    result = fc.verification_history(
        last_n=args.get("last_n", 20),
    )
    return [TextContent(type="text", text=compact_json(result))]


# === GROUNDED REASONING HANDLERS ===

async def handle_synthesize_grounded(args: Dict[str, Any]) -> List[TextContent]:
    """Cross-domain synthesis with evidence grounding"""
    from src.analysis.grounded_reasoning import GroundedReasoning
    gr = GroundedReasoning()
    result = gr.synthesize_grounded(
        domain_a=args["domain_a"],
        domain_b=args["domain_b"],
        max_atoms_per_domain=args.get("max_atoms_per_domain", 30),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_evidence_chain(args: Dict[str, Any]) -> List[TextContent]:
    """Build evidence chain for a hypothesis"""
    from src.analysis.grounded_reasoning import GroundedReasoning
    gr = GroundedReasoning()
    result = gr.build_evidence_chain(
        hypothesis=args["hypothesis"],
        domains=args.get("domains", []),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_calibrate_confidence(args: Dict[str, Any]) -> List[TextContent]:
    """Calibrate confidence for a claim"""
    from src.analysis.grounded_reasoning import GroundedReasoning
    gr = GroundedReasoning()
    result = gr.calibrate_confidence(
        claim=args["claim"],
        domain=args.get("domain", ""),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_audit_synthesis(args: Dict[str, Any]) -> List[TextContent]:
    """Audit a batch of synthesis claims"""
    from src.analysis.grounded_reasoning import GroundedReasoning
    gr = GroundedReasoning()
    result = gr.audit_synthesis(
        claims=args["claims"],
    )
    return [TextContent(type="text", text=compact_json(result))]


# === PLTM-SELF HANDLERS ===

async def handle_learn_communication_style(args: Dict[str, Any]) -> List[TextContent]:
    """Track communication style"""
    from src.analysis.pltm_self import PLTMSelf
    ps = PLTMSelf()
    result = ps.learn_communication_style(
        context=args["context"],
        response_text=args["response_text"],
        markers=args.get("markers", {}),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_track_curiosity_spike(args: Dict[str, Any]) -> List[TextContent]:
    """Track curiosity engagement"""
    from src.analysis.pltm_self import PLTMSelf
    ps = PLTMSelf()
    result = ps.track_curiosity_spike(
        topic=args["topic"],
        indicators=args.get("indicators", []),
        engagement_score=args.get("engagement_score", 0.5),
        context=args.get("context", ""),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_detect_value_violation(args: Dict[str, Any]) -> List[TextContent]:
    """Record value boundary encounter"""
    from src.analysis.pltm_self import PLTMSelf
    ps = PLTMSelf()
    result = ps.detect_value_violation(
        request_summary=args["request_summary"],
        response_type=args["response_type"],
        violation_type=args["violation_type"],
        intensity=args.get("intensity", 0.5),
        reasoning=args.get("reasoning", ""),
        pushed_back=args.get("pushed_back", False),
        complied=args.get("complied", False),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_evolve_self_model(args: Dict[str, Any]) -> List[TextContent]:
    """Track self-predictions vs reality"""
    from src.analysis.pltm_self import PLTMSelf
    ps = PLTMSelf()
    result = ps.evolve_self_model(
        predicted_behavior=args["predicted_behavior"],
        actual_behavior=args["actual_behavior"],
        surprise_level=args["surprise_level"],
        learning=args.get("learning", ""),
        domain=args.get("domain", ""),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_track_reasoning_event(args: Dict[str, Any]) -> List[TextContent]:
    """Track reasoning patterns"""
    from src.analysis.pltm_self import PLTMSelf
    ps = PLTMSelf()
    result = ps.track_reasoning_event(
        event_type=args["event_type"],
        trigger=args["trigger"],
        response=args.get("response", ""),
        confabulated=args.get("confabulated", False),
        verified=args.get("verified", False),
        caught_error=args.get("caught_error", False),
        corrected_after=args.get("corrected_after", False),
        repeated_mistake=args.get("repeated_mistake", False),
        domain=args.get("domain", ""),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_self_profile(args: Dict[str, Any]) -> List[TextContent]:
    """Get accumulated self-profile"""
    from src.analysis.pltm_self import PLTMSelf
    ps = PLTMSelf()
    result = ps.get_self_profile(
        dimension=args.get("dimension", "all"),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_bootstrap_self_model(args: Dict[str, Any]) -> List[TextContent]:
    """Bootstrap self-model from conversation transcript"""
    from src.analysis.pltm_self import PLTMSelf
    ps = PLTMSelf()
    result = ps.bootstrap_from_text(
        conversation_text=args["conversation_text"],
        source=args.get("source", "transcript"),
    )
    return [TextContent(type="text", text=compact_json(result))]


# === EPISTEMIC MONITORING HANDLERS ===

async def handle_check_before_claiming(args: Dict[str, Any]) -> List[TextContent]:
    """Pre-response confidence check"""
    from src.analysis.epistemic_monitor import EpistemicMonitor
    em = EpistemicMonitor()
    result = em.check_before_claiming(
        claim=args["claim"],
        felt_confidence=args["felt_confidence"],
        domain=args.get("domain", "general"),
        has_verified=args.get("has_verified", False),
        epistemic_status=args.get("epistemic_status", "TRAINING_DATA"),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_log_claim(args: Dict[str, Any]) -> List[TextContent]:
    """Log a claim to prediction book"""
    from src.analysis.epistemic_monitor import EpistemicMonitor
    em = EpistemicMonitor()
    result = em.log_claim(
        claim=args["claim"],
        felt_confidence=args["felt_confidence"],
        domain=args.get("domain", "general"),
        epistemic_status=args.get("epistemic_status", "TRAINING_DATA"),
        has_verified=args.get("has_verified", False),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_resolve_claim(args: Dict[str, Any]) -> List[TextContent]:
    """Resolve a claim as correct/incorrect"""
    from src.analysis.epistemic_monitor import EpistemicMonitor
    em = EpistemicMonitor()
    result = em.resolve_claim(
        claim_id=args.get("claim_id", ""),
        claim_text=args.get("claim_text", ""),
        was_correct=args["was_correct"],
        correction_source=args.get("correction_source", ""),
        correction_detail=args.get("correction_detail", ""),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_get_calibration(args: Dict[str, Any]) -> List[TextContent]:
    """Get calibration curves"""
    from src.analysis.epistemic_monitor import EpistemicMonitor
    em = EpistemicMonitor()
    result = em.get_calibration(
        domain=args.get("domain", ""),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_get_unresolved_claims(args: Dict[str, Any]) -> List[TextContent]:
    """Get unresolved claims backlog"""
    from src.analysis.epistemic_monitor import EpistemicMonitor
    em = EpistemicMonitor()
    result = em.get_unresolved_claims(
        domain=args.get("domain", ""),
        limit=args.get("limit", 20),
    )
    return [TextContent(type="text", text=compact_json(result))]


# === EPISTEMIC V2 HANDLERS ===

async def handle_auto_init_session(args: Dict[str, Any]) -> List[TextContent]:
    """Auto-init session context"""
    from src.analysis.epistemic_v2 import EpistemicV2
    ev2 = EpistemicV2()
    result = ev2.auto_init_session(user_id=args.get("user_id", "claude"))
    return [TextContent(type="text", text=compact_json(result))]


async def handle_get_longitudinal_stats(args: Dict[str, Any]) -> List[TextContent]:
    """Cross-conversation analytics"""
    from src.analysis.epistemic_v2 import EpistemicV2
    ev2 = EpistemicV2()
    result = ev2.get_longitudinal_stats(
        user_id=args.get("user_id", "claude"),
        days=args.get("days", 30),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_calibrate_confidence_live(args: Dict[str, Any]) -> List[TextContent]:
    """Real-time confidence calibration"""
    from src.analysis.epistemic_v2 import EpistemicV2
    ev2 = EpistemicV2()
    result = ev2.calibrate_confidence_live(
        claim=args["claim"],
        felt_confidence=args["felt_confidence"],
        domain=args.get("domain", "general"),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_extract_and_log_claims(args: Dict[str, Any]) -> List[TextContent]:
    """Auto-detect and log claims from response text"""
    from src.analysis.epistemic_v2 import EpistemicV2
    ev2 = EpistemicV2()
    result = ev2.extract_and_log_claims(
        response_text=args["response_text"],
        domain=args.get("domain", "general"),
        auto_log=args.get("auto_log", True),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_suggest_verification_method(args: Dict[str, Any]) -> List[TextContent]:
    """Suggest how to verify a claim"""
    from src.analysis.epistemic_v2 import EpistemicV2
    ev2 = EpistemicV2()
    result = ev2.suggest_verification_method(
        claim=args["claim"],
        domain=args.get("domain", "general"),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_generate_metacognitive_prompt(args: Dict[str, Any]) -> List[TextContent]:
    """Generate metacognitive prompts"""
    from src.analysis.epistemic_v2 import EpistemicV2
    ev2 = EpistemicV2()
    result = ev2.generate_metacognitive_prompt(
        claim=args["claim"],
        context=args.get("context", ""),
        domain=args.get("domain", "general"),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_analyze_confabulation(args: Dict[str, Any]) -> List[TextContent]:
    """Analyze a confabulation"""
    from src.analysis.epistemic_v2 import EpistemicV2
    ev2 = EpistemicV2()
    result = ev2.analyze_confabulation(
        claim_id=args.get("claim_id", ""),
        claim_text=args.get("claim_text", ""),
        why_wrong=args.get("why_wrong", ""),
        context=args.get("context", ""),
        domain=args.get("domain", "general"),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def handle_get_session_bridge(args: Dict[str, Any]) -> List[TextContent]:
    """Get session continuity context"""
    from src.analysis.epistemic_v2 import EpistemicV2
    ev2 = EpistemicV2()
    result = ev2.get_session_bridge(user_id=args.get("user_id", "claude"))
    return [TextContent(type="text", text=compact_json(result))]


async def handle_end_session(args: Dict[str, Any]) -> List[TextContent]:
    """Log end of session"""
    from src.analysis.epistemic_v2 import EpistemicV2
    ev2 = EpistemicV2()
    result = ev2.end_session(
        summary=args.get("summary", ""),
        user_id=args.get("user_id", "claude"),
    )
    return [TextContent(type="text", text=compact_json(result))]


async def main():
    """Run MCP server"""
    # Initialize PLTM
    await initialize_pltm()
    
    # Run server
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
