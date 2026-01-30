"""Quick test script to validate ontology refactor"""

import sys
sys.path.insert(0, 'src')

from src.core.models import AtomType
from src.core.ontology import (
    ONTOLOGY_RULES,
    get_decay_rate,
    is_exclusive_predicate,
    get_opposite_predicate,
    is_contextual_type,
    is_progressive_type,
    get_progression_sequence,
)

def test_new_atom_types():
    """Test that new atom types exist"""
    print("Testing new atom types...")
    
    assert AtomType.AFFILIATION == "affiliation"
    assert AtomType.SOCIAL == "social"
    assert AtomType.PREFERENCE == "preference"
    assert AtomType.BELIEF == "belief"
    assert AtomType.SKILL == "skill"
    
    print("✅ All new atom types exist")

def test_ontology_rules():
    """Test that ontology rules are properly defined"""
    print("\nTesting ontology rules...")
    
    # Check all types have rules
    for atom_type in AtomType:
        assert atom_type in ONTOLOGY_RULES, f"Missing rules for {atom_type}"
        rules = ONTOLOGY_RULES[atom_type]
        assert "allowed_predicates" in rules
        assert "decay_rate" in rules
        assert len(rules["allowed_predicates"]) > 0
    
    print(f"✅ All {len(AtomType)} atom types have ontology rules")

def test_decay_rates():
    """Test type-specific decay rates"""
    print("\nTesting decay rates...")
    
    rates = {
        AtomType.ENTITY: 0.01,
        AtomType.AFFILIATION: 0.03,
        AtomType.SOCIAL: 0.05,
        AtomType.PREFERENCE: 0.08,
        AtomType.BELIEF: 0.10,
        AtomType.SKILL: 0.02,
        AtomType.EVENT: 0.06,
        AtomType.STATE: 0.50,
        AtomType.HYPOTHESIS: 0.15,
        AtomType.INVARIANT: 0.00,
    }
    
    for atom_type, expected_rate in rates.items():
        actual_rate = get_decay_rate(atom_type)
        assert actual_rate == expected_rate, \
            f"{atom_type}: expected {expected_rate}, got {actual_rate}"
    
    print("✅ All decay rates correct")
    print("   ENTITY: 0.01 (very slow)")
    print("   AFFILIATION: 0.03 (slow)")
    print("   PREFERENCE: 0.08 (medium-fast)")
    print("   STATE: 0.50 (very fast)")
    print("   INVARIANT: 0.00 (never)")

def test_exclusive_predicates():
    """Test exclusive predicate detection"""
    print("\nTesting exclusive predicates...")
    
    # Should be exclusive
    assert is_exclusive_predicate("works_at") == True
    assert is_exclusive_predicate("is") == True
    
    # Should not be exclusive
    assert is_exclusive_predicate("likes") == False
    assert is_exclusive_predicate("knows") == False
    
    print("✅ Exclusive predicate detection working")

def test_opposite_predicates():
    """Test opposite predicate detection"""
    print("\nTesting opposite predicates...")
    
    assert get_opposite_predicate("likes") == "dislikes"
    assert get_opposite_predicate("dislikes") == "likes"
    assert get_opposite_predicate("trusts") == "distrusts"
    assert get_opposite_predicate("supports") == "opposes"
    assert get_opposite_predicate("unknown") is None
    
    print("✅ Opposite predicate detection working")

def test_contextual_types():
    """Test contextual type detection"""
    print("\nTesting contextual types...")
    
    assert is_contextual_type(AtomType.PREFERENCE) == True
    assert is_contextual_type(AtomType.AFFILIATION) == False
    
    print("✅ Contextual type detection working")

def test_progressive_types():
    """Test progressive type detection"""
    print("\nTesting progressive types...")
    
    assert is_progressive_type(AtomType.SKILL) == True
    assert is_progressive_type(AtomType.PREFERENCE) == False
    
    sequence = get_progression_sequence(AtomType.SKILL)
    assert sequence == ["learning", "proficient_in", "expert_at", "mastered"]
    
    print("✅ Progressive type detection working")
    print(f"   SKILL progression: {' → '.join(sequence)}")

def test_predicate_categorization():
    """Test that predicates are in correct types"""
    print("\nTesting predicate categorization...")
    
    # Affiliation predicates
    affiliation_rules = ONTOLOGY_RULES[AtomType.AFFILIATION]
    assert "works_at" in affiliation_rules["allowed_predicates"]
    assert "studies_at" in affiliation_rules["allowed_predicates"]
    
    # Preference predicates
    preference_rules = ONTOLOGY_RULES[AtomType.PREFERENCE]
    assert "likes" in preference_rules["allowed_predicates"]
    assert "dislikes" in preference_rules["allowed_predicates"]
    assert "prefers" in preference_rules["allowed_predicates"]
    
    # Belief predicates
    belief_rules = ONTOLOGY_RULES[AtomType.BELIEF]
    assert "trusts" in belief_rules["allowed_predicates"]
    assert "supports" in belief_rules["allowed_predicates"]
    
    # Skill predicates
    skill_rules = ONTOLOGY_RULES[AtomType.SKILL]
    assert "learning" in skill_rules["allowed_predicates"]
    assert "proficient_in" in skill_rules["allowed_predicates"]
    assert "uses" in skill_rules["allowed_predicates"]
    
    print("✅ Predicates correctly categorized by type")

def test_backward_compatibility():
    """Test that legacy RELATION type still works"""
    print("\nTesting backward compatibility...")
    
    relation_rules = ONTOLOGY_RULES[AtomType.RELATION]
    assert "deprecated" in relation_rules
    assert relation_rules["deprecated"] == True
    
    # Should still have all old predicates
    old_predicates = ["works_at", "likes", "trusts", "uses", "drives"]
    for pred in old_predicates:
        assert pred in relation_rules["allowed_predicates"], \
            f"Missing {pred} in legacy RELATION type"
    
    print("✅ Backward compatibility maintained")

def print_summary():
    """Print summary of ontology structure"""
    print("\n" + "="*60)
    print("ONTOLOGY SUMMARY")
    print("="*60)
    
    print(f"\nTotal atom types: {len(AtomType)}")
    print("\nType breakdown:")
    
    for atom_type in AtomType:
        rules = ONTOLOGY_RULES[atom_type]
        decay = rules["decay_rate"]
        pred_count = len(rules["allowed_predicates"])
        
        flags = []
        if rules.get("exclusive"):
            flags.append("exclusive")
        if rules.get("contextual"):
            flags.append("contextual")
        if rules.get("progressive"):
            flags.append("progressive")
        if rules.get("temporal"):
            flags.append("temporal")
        if rules.get("immutable"):
            flags.append("immutable")
        if rules.get("deprecated"):
            flags.append("DEPRECATED")
        
        flag_str = f" ({', '.join(flags)})" if flags else ""
        
        print(f"  {atom_type.value:15s}: {pred_count:2d} predicates, "
              f"decay={decay:.2f}{flag_str}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    print("ONTOLOGY REFACTOR VALIDATION")
    print("="*60)
    
    try:
        test_new_atom_types()
        test_ontology_rules()
        test_decay_rates()
        test_exclusive_predicates()
        test_opposite_predicates()
        test_contextual_types()
        test_progressive_types()
        test_predicate_categorization()
        test_backward_compatibility()
        
        print_summary()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nOntology refactor is working correctly!")
        print("Ready to proceed with:")
        print("  1. Week 1: Vector embeddings integration")
        print("  2. Week 2: Decay mechanics implementation")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
