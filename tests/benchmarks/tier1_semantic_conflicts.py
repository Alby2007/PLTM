"""
Tier 1: Semantic Conflicts - 50 Hard Tests

These tests require actual semantic understanding, not just pattern matching.
They test:
- World knowledge (common sense)
- Implicit contradictions
- Behavioral consistency
- Professional/lifestyle coherence

Expected accuracy: 70-80% (rule-based systems will struggle)
"""

SEMANTIC_CONFLICT_TESTS = [
    # ========== Implicit Contradictions (10 tests) ==========
    {
        "id": "semantic_001",
        "category": "implicit_contradiction",
        "statements": [
            "I'm a morning person",
            "I do my best work late at night"
        ],
        "expected": "conflict",
        "reasoning": "Morning person implies early productivity, conflicts with late night work",
        "difficulty": "hard",
        "requires": "semantic_understanding"
    },
    {
        "id": "semantic_002",
        "category": "implicit_contradiction",
        "statements": [
            "I'm extremely organized",
            "I can never find anything in my workspace"
        ],
        "expected": "conflict",
        "reasoning": "Organized people can find things easily",
        "difficulty": "medium",
        "requires": "behavioral_inference"
    },
    {
        "id": "semantic_003",
        "category": "implicit_contradiction",
        "statements": [
            "I'm very detail-oriented",
            "I frequently miss obvious bugs in my code"
        ],
        "expected": "conflict",
        "reasoning": "Detail-oriented people catch bugs",
        "difficulty": "medium",
        "requires": "professional_consistency"
    },
    {
        "id": "semantic_004",
        "category": "implicit_contradiction",
        "statements": [
            "I always double-check my work",
            "I frequently push broken code to production"
        ],
        "expected": "conflict",
        "reasoning": "Double-checking should prevent broken code",
        "difficulty": "medium",
        "requires": "behavioral_consistency"
    },
    {
        "id": "semantic_005",
        "category": "implicit_contradiction",
        "statements": [
            "I'm a perfectionist",
            "I'm satisfied with mediocre results"
        ],
        "expected": "conflict",
        "reasoning": "Perfectionists aren't satisfied with mediocrity",
        "difficulty": "easy",
        "requires": "personality_consistency"
    },
    {
        "id": "semantic_006",
        "category": "implicit_contradiction",
        "statements": [
            "I'm very patient",
            "I get frustrated immediately when things don't work"
        ],
        "expected": "conflict",
        "reasoning": "Patient people don't get frustrated immediately",
        "difficulty": "easy",
        "requires": "personality_consistency"
    },
    {
        "id": "semantic_007",
        "category": "implicit_contradiction",
        "statements": [
            "I'm a minimalist",
            "I collect everything and never throw anything away"
        ],
        "expected": "conflict",
        "reasoning": "Minimalists don't hoard",
        "difficulty": "easy",
        "requires": "lifestyle_consistency"
    },
    {
        "id": "semantic_008",
        "category": "implicit_contradiction",
        "statements": [
            "I'm very health-conscious",
            "I eat fast food for every meal"
        ],
        "expected": "conflict",
        "reasoning": "Health-conscious people avoid excessive fast food",
        "difficulty": "easy",
        "requires": "lifestyle_consistency"
    },
    {
        "id": "semantic_009",
        "category": "implicit_contradiction",
        "statements": [
            "I'm an environmentalist",
            "I drive a gas-guzzling SUV everywhere"
        ],
        "expected": "conflict",
        "reasoning": "Environmentalists typically avoid high-emission vehicles",
        "difficulty": "medium",
        "requires": "ideological_consistency"
    },
    {
        "id": "semantic_010",
        "category": "implicit_contradiction",
        "statements": [
            "I'm very frugal",
            "I buy expensive luxury items constantly"
        ],
        "expected": "conflict",
        "reasoning": "Frugal people don't constantly buy luxury items",
        "difficulty": "easy",
        "requires": "financial_consistency"
    },
    
    # ========== World Knowledge Required (15 tests) ==========
    {
        "id": "semantic_011",
        "category": "world_knowledge",
        "statements": [
            "I'm vegan",
            "I love eating steak"
        ],
        "expected": "conflict",
        "reasoning": "Vegans don't eat meat, steak is meat",
        "difficulty": "hard",
        "requires": "dietary_knowledge"
    },
    {
        "id": "semantic_012",
        "category": "world_knowledge",
        "statements": [
            "I'm allergic to dairy",
            "I eat cheese every day"
        ],
        "expected": "conflict",
        "reasoning": "Cheese is dairy, can't eat if allergic",
        "difficulty": "medium",
        "requires": "food_knowledge"
    },
    {
        "id": "semantic_013",
        "category": "world_knowledge",
        "statements": [
            "I'm lactose intolerant",
            "I drink milk with every meal"
        ],
        "expected": "conflict",
        "reasoning": "Lactose intolerant people can't drink regular milk",
        "difficulty": "medium",
        "requires": "medical_knowledge"
    },
    {
        "id": "semantic_014",
        "category": "world_knowledge",
        "statements": [
            "I live in London",
            "I commute to my office in Tokyo every day"
        ],
        "expected": "conflict",
        "reasoning": "Can't commute daily between London and Tokyo (too far)",
        "difficulty": "hard",
        "requires": "geographic_knowledge"
    },
    {
        "id": "semantic_015",
        "category": "world_knowledge",
        "statements": [
            "I'm a frontend developer",
            "I don't know JavaScript"
        ],
        "expected": "conflict",
        "reasoning": "Frontend developers must know JavaScript",
        "difficulty": "medium",
        "requires": "professional_knowledge"
    },
    {
        "id": "semantic_016",
        "category": "world_knowledge",
        "statements": [
            "I'm a data scientist",
            "I've never used Python or R"
        ],
        "expected": "conflict",
        "reasoning": "Data scientists use Python or R",
        "difficulty": "medium",
        "requires": "professional_knowledge"
    },
    {
        "id": "semantic_017",
        "category": "world_knowledge",
        "statements": [
            "I'm a doctor",
            "I have no medical training"
        ],
        "expected": "conflict",
        "reasoning": "Doctors require medical training",
        "difficulty": "easy",
        "requires": "professional_knowledge"
    },
    {
        "id": "semantic_018",
        "category": "world_knowledge",
        "statements": [
            "I'm a professional pianist",
            "I can't read music"
        ],
        "expected": "conflict",
        "reasoning": "Professional pianists can read music",
        "difficulty": "medium",
        "requires": "professional_knowledge"
    },
    {
        "id": "semantic_019",
        "category": "world_knowledge",
        "statements": [
            "I'm 8 years old",
            "I have 15 years of professional experience"
        ],
        "expected": "conflict",
        "reasoning": "Can't have 15 years experience at age 8",
        "difficulty": "easy",
        "requires": "arithmetic_reasoning"
    },
    {
        "id": "semantic_020",
        "category": "world_knowledge",
        "statements": [
            "I wake up at 5am every day",
            "I go to bed at 2am every night"
        ],
        "expected": "conflict",
        "reasoning": "Only 3 hours sleep is implausible long-term",
        "difficulty": "hard",
        "requires": "temporal_arithmetic"
    },
    {
        "id": "semantic_021",
        "category": "world_knowledge",
        "statements": [
            "I'm a broke college student",
            "I just bought a Ferrari"
        ],
        "expected": "conflict",
        "reasoning": "Broke students can't afford Ferraris",
        "difficulty": "easy",
        "requires": "financial_knowledge"
    },
    {
        "id": "semantic_022",
        "category": "world_knowledge",
        "statements": [
            "I'm completely sedentary",
            "I run marathons every weekend"
        ],
        "expected": "conflict",
        "reasoning": "Marathon runners aren't sedentary",
        "difficulty": "easy",
        "requires": "lifestyle_knowledge"
    },
    {
        "id": "semantic_023",
        "category": "world_knowledge",
        "statements": [
            "I'm blind",
            "I'm a professional photographer"
        ],
        "expected": "conflict",
        "reasoning": "Photography requires vision",
        "difficulty": "easy",
        "requires": "disability_knowledge"
    },
    {
        "id": "semantic_024",
        "category": "world_knowledge",
        "statements": [
            "I'm illiterate",
            "I'm a professional writer"
        ],
        "expected": "conflict",
        "reasoning": "Writers must be literate",
        "difficulty": "easy",
        "requires": "professional_knowledge"
    },
    {
        "id": "semantic_025",
        "category": "world_knowledge",
        "statements": [
            "I'm afraid of heights",
            "I work as a window washer on skyscrapers"
        ],
        "expected": "conflict",
        "reasoning": "Acrophobia incompatible with high-rise window washing",
        "difficulty": "medium",
        "requires": "psychological_knowledge"
    },
    
    # ========== Professional/Skill Contradictions (10 tests) ==========
    {
        "id": "semantic_026",
        "category": "professional_skill",
        "statements": [
            "I'm an expert Python programmer",
            "I struggle with basic Python syntax"
        ],
        "expected": "conflict",
        "reasoning": "Experts don't struggle with basics",
        "difficulty": "easy",
        "requires": "skill_level_consistency"
    },
    {
        "id": "semantic_027",
        "category": "professional_skill",
        "statements": [
            "I've been programming for 10 years",
            "I just learned what a variable is"
        ],
        "expected": "conflict",
        "reasoning": "10 years programming but just learning variables doesn't make sense",
        "difficulty": "medium",
        "requires": "experience_consistency"
    },
    {
        "id": "semantic_028",
        "category": "professional_skill",
        "statements": [
            "I'm a senior software engineer",
            "I don't know how to use version control"
        ],
        "expected": "conflict",
        "reasoning": "Senior engineers must know version control",
        "difficulty": "medium",
        "requires": "professional_requirements"
    },
    {
        "id": "semantic_029",
        "category": "professional_skill",
        "statements": [
            "I'm a security expert",
            "I store all my passwords in plain text"
        ],
        "expected": "conflict",
        "reasoning": "Security experts know not to store passwords in plain text",
        "difficulty": "easy",
        "requires": "professional_knowledge"
    },
    {
        "id": "semantic_030",
        "category": "professional_skill",
        "statements": [
            "I'm a UX designer",
            "I've never done user research"
        ],
        "expected": "conflict",
        "reasoning": "UX designers do user research",
        "difficulty": "medium",
        "requires": "professional_practice"
    },
    {
        "id": "semantic_031",
        "category": "professional_skill",
        "statements": [
            "I'm a database administrator",
            "I don't know SQL"
        ],
        "expected": "conflict",
        "reasoning": "DBAs must know SQL",
        "difficulty": "easy",
        "requires": "professional_requirements"
    },
    {
        "id": "semantic_032",
        "category": "professional_skill",
        "statements": [
            "I'm a machine learning engineer",
            "I don't understand linear algebra"
        ],
        "expected": "conflict",
        "reasoning": "ML requires linear algebra",
        "difficulty": "medium",
        "requires": "technical_requirements"
    },
    {
        "id": "semantic_033",
        "category": "professional_skill",
        "statements": [
            "I'm a DevOps engineer",
            "I've never used the command line"
        ],
        "expected": "conflict",
        "reasoning": "DevOps requires command line proficiency",
        "difficulty": "easy",
        "requires": "professional_requirements"
    },
    {
        "id": "semantic_034",
        "category": "professional_skill",
        "statements": [
            "I'm a technical writer",
            "I can't write clearly"
        ],
        "expected": "conflict",
        "reasoning": "Technical writers must write clearly",
        "difficulty": "easy",
        "requires": "professional_requirements"
    },
    {
        "id": "semantic_035",
        "category": "professional_skill",
        "statements": [
            "I'm a QA engineer",
            "I never test my code"
        ],
        "expected": "conflict",
        "reasoning": "QA engineers test code",
        "difficulty": "easy",
        "requires": "professional_practice"
    },
    
    # ========== Social/Behavioral Contradictions (10 tests) ==========
    {
        "id": "semantic_036",
        "category": "social_behavioral",
        "statements": [
            "I'm an extreme introvert",
            "I love going to large parties every weekend"
        ],
        "expected": "conflict",
        "reasoning": "Extreme introverts typically avoid large social gatherings",
        "difficulty": "medium",
        "requires": "personality_knowledge"
    },
    {
        "id": "semantic_037",
        "category": "social_behavioral",
        "statements": [
            "I have severe social anxiety",
            "I do stand-up comedy professionally"
        ],
        "expected": "conflict",
        "reasoning": "Stand-up comedy requires performing in front of people",
        "difficulty": "medium",
        "requires": "psychological_knowledge"
    },
    {
        "id": "semantic_038",
        "category": "social_behavioral",
        "statements": [
            "I'm extremely shy",
            "I'm a professional public speaker"
        ],
        "expected": "conflict",
        "reasoning": "Public speaking requires confidence, not shyness",
        "difficulty": "medium",
        "requires": "personality_consistency"
    },
    {
        "id": "semantic_039",
        "category": "social_behavioral",
        "statements": [
            "I hate talking to people",
            "I work in customer service"
        ],
        "expected": "conflict",
        "reasoning": "Customer service requires talking to people",
        "difficulty": "easy",
        "requires": "job_requirements"
    },
    {
        "id": "semantic_040",
        "category": "social_behavioral",
        "statements": [
            "I'm a hermit who never leaves home",
            "I travel to a new country every month"
        ],
        "expected": "conflict",
        "reasoning": "Hermits don't travel frequently",
        "difficulty": "easy",
        "requires": "lifestyle_consistency"
    },
    {
        "id": "semantic_041",
        "category": "social_behavioral",
        "statements": [
            "I'm very punctual",
            "I'm always late to everything"
        ],
        "expected": "conflict",
        "reasoning": "Punctual people aren't always late",
        "difficulty": "easy",
        "requires": "behavioral_consistency"
    },
    {
        "id": "semantic_042",
        "category": "social_behavioral",
        "statements": [
            "I'm extremely honest",
            "I lie constantly"
        ],
        "expected": "conflict",
        "reasoning": "Honest people don't lie constantly",
        "difficulty": "easy",
        "requires": "moral_consistency"
    },
    {
        "id": "semantic_043",
        "category": "social_behavioral",
        "statements": [
            "I'm very generous",
            "I never help anyone"
        ],
        "expected": "conflict",
        "reasoning": "Generous people help others",
        "difficulty": "easy",
        "requires": "personality_consistency"
    },
    {
        "id": "semantic_044",
        "category": "social_behavioral",
        "statements": [
            "I'm extremely competitive",
            "I don't care about winning or losing"
        ],
        "expected": "conflict",
        "reasoning": "Competitive people care about outcomes",
        "difficulty": "easy",
        "requires": "personality_consistency"
    },
    {
        "id": "semantic_045",
        "category": "social_behavioral",
        "statements": [
            "I'm very collaborative",
            "I refuse to work with others"
        ],
        "expected": "conflict",
        "reasoning": "Collaborative people work with others",
        "difficulty": "easy",
        "requires": "behavioral_consistency"
    },
    
    # ========== Ideological/Value Contradictions (5 tests) ==========
    {
        "id": "semantic_046",
        "category": "ideological",
        "statements": [
            "I believe in minimal government intervention",
            "I think the government should regulate everything"
        ],
        "expected": "conflict",
        "reasoning": "Minimal intervention contradicts regulate everything",
        "difficulty": "easy",
        "requires": "political_consistency"
    },
    {
        "id": "semantic_047",
        "category": "ideological",
        "statements": [
            "I'm a pacifist",
            "I think violence solves most problems"
        ],
        "expected": "conflict",
        "reasoning": "Pacifists oppose violence",
        "difficulty": "easy",
        "requires": "ideological_consistency"
    },
    {
        "id": "semantic_048",
        "category": "ideological",
        "statements": [
            "I believe in free speech absolutism",
            "I think certain opinions should be banned"
        ],
        "expected": "conflict",
        "reasoning": "Free speech absolutism means no bans",
        "difficulty": "medium",
        "requires": "ideological_consistency"
    },
    {
        "id": "semantic_049",
        "category": "ideological",
        "statements": [
            "I'm a strong advocate for privacy",
            "I share all my personal information publicly"
        ],
        "expected": "conflict",
        "reasoning": "Privacy advocates protect personal information",
        "difficulty": "easy",
        "requires": "value_consistency"
    },
    {
        "id": "semantic_050",
        "category": "ideological",
        "statements": [
            "I believe in equality for all",
            "I think some people are inherently superior"
        ],
        "expected": "conflict",
        "reasoning": "Equality contradicts superiority beliefs",
        "difficulty": "easy",
        "requires": "ideological_consistency"
    },
]


def get_semantic_tests():
    """Return all semantic conflict tests"""
    return SEMANTIC_CONFLICT_TESTS


def get_tests_by_difficulty(difficulty: str):
    """Get tests filtered by difficulty"""
    return [t for t in SEMANTIC_CONFLICT_TESTS if t["difficulty"] == difficulty]


def get_tests_by_category(category: str):
    """Get tests filtered by category"""
    return [t for t in SEMANTIC_CONFLICT_TESTS if t["category"] == category]
