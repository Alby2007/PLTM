"""
Hybrid Extractor - 3-Stage Extraction Pipeline

Stage 1: Rule-based (fast, covers 80% of simple cases)
Stage 2: LLM simple (semantic understanding for complex statements)
Stage 3: LLM complex (with examples for hardest cases)

This fixes the extraction bottleneck identified in the 300-test benchmark.
"""

from typing import List, Optional
import os
from loguru import logger

from src.extraction.rule_based import RuleBasedExtractor
from src.core.models import MemoryAtom, AtomType, Provenance, GraphType


class HybridExtractor:
    """
    3-stage extraction pipeline:
    1. Rule-based (fast, covers simple cases)
    2. LLM-based (semantic, covers complex cases)
    3. LLM with examples (hardest cases)
    """
    
    def __init__(self, llm_model: str = "claude-sonnet-4-20250514"):
        # Stage 1: Existing rule-based extractor
        self.rule_based = RuleBasedExtractor()
        
        # Stage 2/3: LLM for semantic extraction
        self.llm_model = llm_model
        self.llm_enabled = os.getenv("ANTHROPIC_API_KEY") is not None
        
        # Track which stage succeeded (for metrics)
        self.extraction_stats = {
            "rule_based": 0,
            "llm_simple": 0,
            "llm_complex": 0,
            "failed": 0
        }
        
        if not self.llm_enabled:
            logger.warning("ANTHROPIC_API_KEY not set - LLM extraction disabled")
    
    async def extract(self, message: str, user_id: str) -> List[MemoryAtom]:
        """
        Extract atoms using 3-stage pipeline
        
        Args:
            message: User message to extract from
            user_id: User identifier
            
        Returns:
            List of extracted MemoryAtom objects
        """
        # Stage 1: Try rule-based first (fast)
        atoms = self.rule_based.extract(message, user_id)
        
        if atoms:
            self.extraction_stats["rule_based"] += 1
            return atoms
        
        # If LLM not enabled, stop here
        if not self.llm_enabled:
            self.extraction_stats["failed"] += 1
            return []
        
        # Stage 2: Try LLM-based (semantic understanding)
        atoms = await self._extract_with_llm_simple(user_id, message)
        
        if atoms:
            self.extraction_stats["llm_simple"] += 1
            return atoms
        
        # Stage 3: Try LLM with examples (hard cases)
        atoms = await self._extract_with_llm_complex(user_id, message)
        
        if atoms:
            self.extraction_stats["llm_complex"] += 1
            return atoms
        
        # All stages failed
        self.extraction_stats["failed"] += 1
        logger.warning(f"Failed to extract atoms from: {message}")
        return []
    
    async def _extract_with_llm_simple(
        self,
        user_id: str,
        message: str
    ) -> List[MemoryAtom]:
        """
        Stage 2: Use LLM for semantic extraction
        """
        prompt = f"""Extract structured memory atoms from this statement.

Statement: "{message}"

Extract atoms in this format:
[subject] [predicate] [object]

Available predicates:
- Beliefs: believes_in, thinks, assumes
- Preferences: likes, dislikes, prefers, avoids
- Behaviors: does, refuses_to, always, never
- States: is, feels, currently
- Skills: can_do, expert_at, struggles_with
- Social: works_with, knows, reports_to
- Affiliations: works_at, member_of, part_of

Rules:
1. Subject is always "User" (referring to the speaker)
2. Use appropriate predicate from the list
3. Object is the thing being described
4. Extract ALL facts from the statement
5. Be as specific as possible

Examples:

Statement: "I love hiking in the mountains"
Output:
[User] [loves] [hiking in the mountains]

Statement: "I work at Google and I'm a senior engineer"
Output:
[User] [works_at] [Google]
[User] [is] [senior engineer]

Statement: "I believe in minimal government intervention"
Output:
[User] [believes_in] [minimal government intervention]

Statement: "I'm extremely competitive"
Output:
[User] [is] [extremely competitive]

Now extract from: "{message}"

Output (one atom per line):"""
        
        response = await self._call_llm(prompt, temperature=0.0)
        
        # Parse response into atoms
        atoms = self._parse_llm_output(user_id, response)
        
        return atoms
    
    async def _extract_with_llm_complex(
        self,
        user_id: str,
        message: str
    ) -> List[MemoryAtom]:
        """
        Stage 3: Use LLM with more examples for hard cases
        """
        prompt = f"""You are an expert at extracting structured knowledge from natural language.

Extract memory atoms from this statement: "{message}"

Format: [subject] [predicate] [object]

Available atom types and predicates:

BELIEF (opinions, worldviews):
- believes_in, thinks, assumes, doubts, trusts, distrusts

PREFERENCE (likes/dislikes):
- likes, dislikes, loves, hates, prefers, avoids, enjoys

BEHAVIOR (actions, habits):
- does, does_not, always, never, usually, rarely, refuses_to

STATE (current condition):
- is, is_not, feels, currently

SKILL (capabilities):
- can_do, cannot_do, expert_at, proficient_in, struggles_with

SOCIAL (relationships):
- knows, friends_with, reports_to, manages, mentors

AFFILIATION (organizations):
- works_at, studies_at, member_of, part_of

Complex examples:

"I don't care about winning or losing"
→ [User] [does_not_care_about] [winning or losing]

"I think violence solves most problems"
→ [User] [believes_in] [violence as solution to problems]

"I share all my personal information publicly"
→ [User] [does] [share personal information publicly]

"I refuse to work with others"
→ [User] [refuses_to] [work with others]

"I believe technology will save humanity"
→ [User] [believes_in] [technology saving humanity]

"I'm a morning person who hates coffee"
→ [User] [is] [morning person]
→ [User] [hates] [coffee]

Now extract from: "{message}"

Think step by step:
1. What is the main fact being stated?
2. What predicate best captures this?
3. What is the specific object?

Output (one atom per line, nothing else):"""
        
        response = await self._call_llm(prompt, temperature=0.0)
        
        atoms = self._parse_llm_output(user_id, response)
        
        return atoms
    
    def _parse_llm_output(
        self,
        user_id: str,
        llm_response: str
    ) -> List[MemoryAtom]:
        """
        Parse LLM output into MemoryAtom objects
        """
        atoms = []
        
        # Split by lines
        lines = llm_response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines or explanations
            if not line or not line.startswith('['):
                continue
            
            # Parse: [User] [predicate] [object]
            try:
                parts = []
                current = ""
                in_bracket = False
                
                for char in line:
                    if char == '[':
                        in_bracket = True
                        current = ""
                    elif char == ']':
                        in_bracket = False
                        if current:
                            parts.append(current.strip())
                    elif in_bracket:
                        current += char
                
                if len(parts) >= 3:
                    subject, predicate, obj = parts[0], parts[1], parts[2]
                    
                    # Infer atom type from predicate
                    atom_type = self._infer_atom_type(predicate)
                    
                    atom = MemoryAtom(
                        atom_type=atom_type,
                        subject=user_id,
                        predicate=predicate,
                        object=obj,
                        provenance=Provenance.USER_STATED,
                        graph=GraphType.UNSUBSTANTIATED,
                        confidence=0.9,  # High confidence for direct statements
                        strength=1.0
                    )
                    
                    atoms.append(atom)
                
            except Exception as e:
                logger.warning(f"Failed to parse line: {line}, error: {e}")
                continue
        
        return atoms
    
    def _infer_atom_type(self, predicate: str) -> AtomType:
        """
        Infer atom type from predicate
        """
        belief_predicates = ["believes_in", "thinks", "assumes", "doubts", "trusts", "distrusts"]
        preference_predicates = ["likes", "dislikes", "loves", "hates", "prefers", "avoids", "enjoys"]
        skill_predicates = ["can_do", "cannot_do", "expert_at", "proficient_in", "struggles_with"]
        affiliation_predicates = ["works_at", "studies_at", "member_of", "part_of"]
        state_predicates = ["is", "is_not", "feels", "currently"]
        
        if predicate in belief_predicates:
            return AtomType.BELIEF
        elif predicate in preference_predicates:
            return AtomType.PREFERENCE
        elif predicate in skill_predicates:
            return AtomType.SKILL
        elif predicate in affiliation_predicates:
            return AtomType.AFFILIATION
        elif predicate in state_predicates:
            return AtomType.STATE
        else:
            return AtomType.RELATION  # Default
    
    async def _call_llm(self, prompt: str, temperature: float = 0.0) -> str:
        """
        Call LLM (Claude Sonnet 4)
        """
        try:
            import anthropic
            
            client = anthropic.Anthropic()
            
            message = client.messages.create(
                model=self.llm_model,
                max_tokens=1000,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""
    
    def get_stats(self) -> dict:
        """
        Get extraction statistics
        """
        total = sum(self.extraction_stats.values())
        
        if total == 0:
            return self.extraction_stats
        
        return {
            "rule_based": f"{self.extraction_stats['rule_based']} ({self.extraction_stats['rule_based']/total*100:.1f}%)",
            "llm_simple": f"{self.extraction_stats['llm_simple']} ({self.extraction_stats['llm_simple']/total*100:.1f}%)",
            "llm_complex": f"{self.extraction_stats['llm_complex']} ({self.extraction_stats['llm_complex']/total*100:.1f}%)",
            "failed": f"{self.extraction_stats['failed']} ({self.extraction_stats['failed']/total*100:.1f}%)",
        }
