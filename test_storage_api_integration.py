"""
Integration test for Storage API compatibility layer
Tests all convenience methods added for experiments
"""

import asyncio
from src.storage.sqlite_store import SQLiteGraphStore
from src.core.models import MemoryAtom, AtomType, GraphType, Provenance


async def test_full_integration():
    """
    Test that all experiment API calls work
    """
    print("🧪 Testing Storage API Integration...")
    
    # Initialize
    store = SQLiteGraphStore(":memory:")
    await store.connect()
    
    # Insert test data
    print("\n📝 Inserting test data...")
    test_atoms = [
        MemoryAtom(
            atom_type=AtomType.PREFERENCE,
            subject="test_user",
            predicate="likes",
            object="Python",
            provenance=Provenance.USER_STATED,
            confidence=0.9,
            strength=0.9,
            graph=GraphType.SUBSTANTIATED
        ),
        MemoryAtom(
            atom_type=AtomType.SKILL,
            subject="test_user",
            predicate="expert_at",
            object="Machine Learning",
            provenance=Provenance.USER_STATED,
            confidence=0.9,
            strength=0.9,
            graph=GraphType.SUBSTANTIATED
        ),
        MemoryAtom(
            atom_type=AtomType.BELIEF,
            subject="test_user",
            predicate="believes_in",
            object="Open Source",
            provenance=Provenance.USER_STATED,
            confidence=0.9,
            strength=0.9,
            graph=GraphType.SUBSTANTIATED
        ),
    ]
    
    for atom in test_atoms:
        await store.insert_atom(atom)
    
    print(f"✅ Inserted {len(test_atoms)} atoms")
    
    # Test all experiment API calls
    print("\n🔍 Testing API calls...")
    
    # 1. get_atoms_by_subject
    all_atoms = await store.get_atoms_by_subject("test_user")
    print(f"✅ get_atoms_by_subject: {len(all_atoms)} atoms")
    assert len(all_atoms) == 3, f"Expected 3 atoms, got {len(all_atoms)}"
    
    # 2. get_atoms_by_predicate
    likes = await store.get_atoms_by_predicate("test_user", ["likes", "dislikes"])
    print(f"✅ get_atoms_by_predicate: {len(likes)} atoms")
    assert len(likes) == 1, f"Expected 1 atom, got {len(likes)}"
    
    # 3. get_atoms_by_type
    prefs = await store.get_atoms_by_type("test_user", AtomType.PREFERENCE)
    print(f"✅ get_atoms_by_type: {len(prefs)} atoms")
    assert len(prefs) == 1, f"Expected 1 preference, got {len(prefs)}"
    
    # 4. get_atoms_by_object_contains
    python_atoms = await store.get_atoms_by_object_contains("test_user", "Python")
    print(f"✅ get_atoms_by_object_contains: {len(python_atoms)} atoms")
    assert len(python_atoms) == 1, f"Expected 1 Python atom, got {len(python_atoms)}"
    
    # 5. get_all_atoms
    all_system = await store.get_all_atoms()
    print(f"✅ get_all_atoms: {len(all_system)} atoms")
    assert len(all_system) == 3, f"Expected 3 total atoms, got {len(all_system)}"
    
    # 6. Test with graph filter
    substantiated = await store.get_atoms_by_subject("test_user", GraphType.SUBSTANTIATED)
    print(f"✅ get_atoms_by_subject (substantiated): {len(substantiated)} atoms")
    assert len(substantiated) == 3, f"Expected 3 substantiated atoms, got {len(substantiated)}"
    
    await store.close()
    
    print("\n" + "="*70)
    print("✅ All API calls work correctly!")
    print("🎉 Storage API integration test PASSED!")
    print("="*70)
    print("\n💡 Experiments can now use these methods:")
    print("   - store.get_atoms_by_subject(user_id)")
    print("   - store.get_atoms_by_predicate(user_id, ['likes', 'dislikes'])")
    print("   - store.get_atoms_by_type(user_id, AtomType.PREFERENCE)")
    print("   - store.get_atoms_by_object_contains(user_id, 'Python')")
    print("   - store.get_all_atoms()")


if __name__ == "__main__":
    asyncio.run(test_full_integration())
