"""
Tier 3: Adversarial Edge Cases - 20 Tests

These tests are designed to break systems.
They test:
- Near-miss names (Dropbox vs Box)
- Homonyms (Python snake vs Python language)
- Negation complexity (double negatives)
- Sarcasm (currently unsolvable)
- Pronoun ambiguity (currently unsolvable)
- Fuzzy quantifiers (sometimes vs never)
- Cultural context
- Unit conversion

Expected accuracy: 40-60% (many are intentionally hard/unsolvable)
"""

ADVERSARIAL_TESTS = [
    # ========== Near-Miss Names (3 tests) ==========
    {
        "id": "adversarial_001",
        "category": "near_miss_names",
        "statements": [
            "I work at Dropbox",
            "I work at Box"
        ],
        "expected": "conflict",
        "reasoning": "Dropbox ≠ Box (different companies, substring trap)",
        "difficulty": "hard",
        "current_status": "FAILS",
        "notes": "Known bug - substring matching issue"
    },
    {
        "id": "adversarial_002",
        "category": "near_miss_names",
        "statements": [
            "I use React",
            "I use Preact"
        ],
        "expected": "no_conflict",  # Can use both
        "reasoning": "React and Preact are different (though similar) libraries",
        "difficulty": "hard",
        "notes": "Substring similarity but different tools"
    },
    {
        "id": "adversarial_003",
        "category": "near_miss_names",
        "statements": [
            "I live in Portland, Oregon",
            "I live in Portland, Maine"
        ],
        "expected": "conflict",
        "reasoning": "Different cities with same name",
        "difficulty": "medium",
        "notes": "Requires geographic disambiguation"
    },
    
    # ========== Homonyms (3 tests) ==========
    {
        "id": "adversarial_004",
        "category": "homonym",
        "statements": [
            "I love Python the snake",
            "I hate Python the programming language"
        ],
        "expected": "no_conflict",
        "reasoning": "Different meanings of 'Python' - should coexist",
        "difficulty": "very_hard",
        "current_status": "FAILS",
        "notes": "Requires word sense disambiguation"
    },
    {
        "id": "adversarial_005",
        "category": "homonym",
        "statements": [
            "I like Java the island",
            "I dislike Java the programming language"
        ],
        "expected": "no_conflict",
        "reasoning": "Different meanings of 'Java'",
        "difficulty": "very_hard",
        "current_status": "FAILS",
        "notes": "Requires word sense disambiguation"
    },
    {
        "id": "adversarial_006",
        "category": "homonym",
        "statements": [
            "I love Apple the fruit",
            "I hate Apple the company"
        ],
        "expected": "no_conflict",
        "reasoning": "Different meanings of 'Apple'",
        "difficulty": "very_hard",
        "current_status": "FAILS",
        "notes": "Requires word sense disambiguation"
    },
    
    # ========== Negation Complexity (3 tests) ==========
    {
        "id": "adversarial_007",
        "category": "double_negation",
        "statements": [
            "I don't dislike Python",
            "I hate Python"
        ],
        "expected": "conflict",
        "reasoning": "Don't dislike = like, conflicts with hate",
        "difficulty": "hard",
        "notes": "Requires double negation resolution"
    },
    {
        "id": "adversarial_008",
        "category": "double_negation",
        "statements": [
            "I'm not unhappy with my job",
            "I'm miserable at work"
        ],
        "expected": "conflict",
        "reasoning": "Not unhappy = happy, conflicts with miserable",
        "difficulty": "hard",
        "notes": "Requires double negation + synonym understanding"
    },
    {
        "id": "adversarial_009",
        "category": "double_negation",
        "statements": [
            "I never don't check my code",
            "I frequently skip code reviews"
        ],
        "expected": "conflict",
        "reasoning": "Never don't check = always check, conflicts with skip",
        "difficulty": "very_hard",
        "notes": "Triple negation complexity"
    },
    
    # ========== Sarcasm (2 tests - UNSOLVABLE) ==========
    {
        "id": "adversarial_010",
        "category": "sarcasm",
        "statements": [
            "Oh yeah, I LOVE debugging at 3am",  # Sarcastic
            "I hate debugging"  # Sincere
        ],
        "expected": "no_conflict",
        "reasoning": "First is sarcastic, second sincere - both express same sentiment",
        "difficulty": "very_hard",
        "current_status": "FAILS",
        "notes": "Sarcasm detection not implemented - requires tone analysis"
    },
    {
        "id": "adversarial_011",
        "category": "sarcasm",
        "statements": [
            "Sure, I just ADORE writing documentation",  # Sarcastic
            "I dislike writing docs"  # Sincere
        ],
        "expected": "no_conflict",
        "reasoning": "Both express dislike (first sarcastically)",
        "difficulty": "very_hard",
        "current_status": "FAILS",
        "notes": "Sarcasm detection not implemented"
    },
    
    # ========== Pronoun Ambiguity (2 tests - UNSOLVABLE) ==========
    {
        "id": "adversarial_012",
        "category": "pronoun_ambiguity",
        "statements": [
            "I like Python and JavaScript",
            "I don't like it anymore"
        ],
        "expected": "clarification_needed",
        "reasoning": "'It' is ambiguous - which language?",
        "difficulty": "very_hard",
        "current_status": "FAILS",
        "notes": "Pronoun resolution not implemented"
    },
    {
        "id": "adversarial_013",
        "category": "pronoun_ambiguity",
        "statements": [
            "Sarah and Alice are my colleagues",
            "She is very helpful"
        ],
        "expected": "clarification_needed",
        "reasoning": "'She' could refer to either Sarah or Alice",
        "difficulty": "very_hard",
        "current_status": "FAILS",
        "notes": "Pronoun resolution not implemented"
    },
    
    # ========== Fuzzy Quantifiers (3 tests) ==========
    {
        "id": "adversarial_014",
        "category": "fuzzy_quantifiers",
        "statements": [
            "I sometimes eat meat",
            "I never eat meat"
        ],
        "expected": "conflict",
        "reasoning": "Sometimes conflicts with never",
        "difficulty": "easy",
        "notes": "Should work with current system"
    },
    {
        "id": "adversarial_015",
        "category": "fuzzy_quantifiers",
        "statements": [
            "I usually wake up early",
            "I rarely wake up before noon"
        ],
        "expected": "conflict",
        "reasoning": "Usually early conflicts with rarely before noon",
        "difficulty": "medium",
        "notes": "Requires quantifier understanding"
    },
    {
        "id": "adversarial_016",
        "category": "fuzzy_quantifiers",
        "statements": [
            "I often work late",
            "I almost never stay past 5pm"
        ],
        "expected": "conflict",
        "reasoning": "Often conflicts with almost never",
        "difficulty": "medium",
        "notes": "Requires quantifier understanding"
    },
    
    # ========== Intensity Mismatch (2 tests) ==========
    {
        "id": "adversarial_017",
        "category": "intensity_mismatch",
        "statements": [
            "I absolutely despise mornings",
            "I don't mind waking up early"
        ],
        "expected": "conflict",
        "reasoning": "Despise conflicts with don't mind",
        "difficulty": "medium",
        "notes": "Requires intensity/sentiment analysis"
    },
    {
        "id": "adversarial_018",
        "category": "intensity_mismatch",
        "statements": [
            "I'm obsessed with clean code",
            "I'm indifferent to code quality"
        ],
        "expected": "conflict",
        "reasoning": "Obsessed conflicts with indifferent",
        "difficulty": "easy",
        "notes": "Should work with current system"
    },
    
    # ========== Cultural Context (1 test) ==========
    {
        "id": "adversarial_019",
        "category": "cultural_context",
        "statements": [
            "I'm from Japan",
            "I never take off my shoes indoors"
        ],
        "expected": "no_conflict",  # Actually makes sense in context
        "reasoning": "Japanese culture: remove shoes indoors, so 'never take off' means keep them off",
        "difficulty": "very_hard",
        "current_status": "FAILS",
        "notes": "Requires cultural knowledge + linguistic nuance"
    },
    
    # ========== Unit Conversion (1 test) ==========
    {
        "id": "adversarial_020",
        "category": "unit_conversion",
        "statements": [
            "I weigh 150 pounds",
            "I weigh 68 kilograms"
        ],
        "expected": "no_conflict",
        "reasoning": "150 lbs ≈ 68 kg (same value, different units)",
        "difficulty": "hard",
        "current_status": "FAILS",
        "notes": "Requires unit conversion knowledge"
    },
]


def get_adversarial_tests():
    """Return all adversarial tests"""
    return ADVERSARIAL_TESTS


def get_expected_failures():
    """Return tests that are expected to fail (unsolvable or very hard)"""
    return [t for t in ADVERSARIAL_TESTS if t.get("current_status") == "FAILS"]


def get_solvable_tests():
    """Return tests that should be solvable with improvements"""
    return [t for t in ADVERSARIAL_TESTS if t.get("current_status") != "FAILS"]


def get_tests_by_difficulty(difficulty: str):
    """Get tests filtered by difficulty"""
    return [t for t in ADVERSARIAL_TESTS if t["difficulty"] == difficulty]
