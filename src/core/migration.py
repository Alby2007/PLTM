"""Migration utilities for ontology upgrades"""

from typing import List
from loguru import logger

from src.core.models import AtomType, MemoryAtom


# Predicate to atom type mapping for automatic migration
PREDICATE_TO_TYPE_MAPPING = {
    # Affiliation predicates
    "works_at": AtomType.AFFILIATION,
    "works_for": AtomType.AFFILIATION,
    "employed_by": AtomType.AFFILIATION,
    "studies_at": AtomType.AFFILIATION,
    "member_of": AtomType.AFFILIATION,
    "part_of": AtomType.AFFILIATION,
    "works_in": AtomType.AFFILIATION,
    
    # Social predicates
    "knows": AtomType.SOCIAL,
    "friends_with": AtomType.SOCIAL,
    "colleagues_with": AtomType.SOCIAL,
    "reports_to": AtomType.SOCIAL,
    "manages": AtomType.SOCIAL,
    "mentors": AtomType.SOCIAL,
    "works_with": AtomType.SOCIAL,
    
    # Preference predicates
    "likes": AtomType.PREFERENCE,
    "dislikes": AtomType.PREFERENCE,
    "loves": AtomType.PREFERENCE,
    "hates": AtomType.PREFERENCE,
    "prefers": AtomType.PREFERENCE,
    "avoids": AtomType.PREFERENCE,
    "enjoys": AtomType.PREFERENCE,
    "neutral": AtomType.PREFERENCE,
    "liked_past": AtomType.PREFERENCE,
    "prefers_over": AtomType.PREFERENCE,
    
    # Belief predicates
    "thinks": AtomType.BELIEF,
    "believes": AtomType.BELIEF,
    "assumes": AtomType.BELIEF,
    "expects": AtomType.BELIEF,
    "trusts": AtomType.BELIEF,
    "distrusts": AtomType.BELIEF,
    "doubts": AtomType.BELIEF,
    "supports": AtomType.BELIEF,
    "opposes": AtomType.BELIEF,
    "agrees": AtomType.BELIEF,
    "disagrees": AtomType.BELIEF,
    "accepts": AtomType.BELIEF,
    "rejects": AtomType.BELIEF,
    
    # Skill predicates
    "can_do": AtomType.SKILL,
    "proficient_in": AtomType.SKILL,
    "expert_at": AtomType.SKILL,
    "learning": AtomType.SKILL,
    "started_learning": AtomType.SKILL,
    "mastered": AtomType.SKILL,
    "uses": AtomType.SKILL,
    "does": AtomType.SKILL,
    "drives": AtomType.SKILL,
    "will_learn": AtomType.SKILL,
    
    # Event predicates
    "completed": AtomType.EVENT,
    "started": AtomType.EVENT,
    "finished": AtomType.EVENT,
    "failed": AtomType.EVENT,
    "attempted": AtomType.EVENT,
    "decided": AtomType.EVENT,
    "happened": AtomType.EVENT,
    "studied": AtomType.EVENT,
    "worked_at_year": AtomType.EVENT,
    "works_at_year": AtomType.EVENT,
    
    # State predicates
    "currently": AtomType.STATE,
    "temporarily": AtomType.STATE,
    "status_is": AtomType.STATE,
    "mood_is": AtomType.STATE,
    "feeling": AtomType.STATE,
    "current_mood": AtomType.STATE,
    "status": AtomType.STATE,
    "condition": AtomType.STATE,
}


def migrate_relation_to_specific_type(atom: MemoryAtom) -> AtomType:
    """
    Automatically categorize old RELATION atoms into specific types.
    
    Args:
        atom: Memory atom to categorize
        
    Returns:
        Appropriate AtomType based on predicate
        
    Example:
        atom with predicate "works_at" -> AtomType.AFFILIATION
        atom with predicate "likes" -> AtomType.PREFERENCE
    """
    # If already a specific type, return as-is
    if atom.atom_type != AtomType.RELATION:
        return atom.atom_type
    
    # Look up predicate in mapping
    new_type = PREDICATE_TO_TYPE_MAPPING.get(atom.predicate)
    
    if new_type:
        logger.debug(
            f"Migrating atom {atom.id}: {atom.atom_type} -> {new_type} "
            f"(predicate: {atom.predicate})"
        )
        return new_type
    
    # If no mapping found, keep as RELATION (generic)
    logger.debug(
        f"No migration mapping for predicate '{atom.predicate}', "
        f"keeping as RELATION"
    )
    return AtomType.RELATION


def migrate_atom(atom: MemoryAtom, in_place: bool = True) -> MemoryAtom:
    """
    Migrate a single atom to new ontology.
    
    Args:
        atom: Atom to migrate
        in_place: If True, modify atom in place; if False, return new atom
        
    Returns:
        Migrated atom
    """
    new_type = migrate_relation_to_specific_type(atom)
    
    if in_place:
        atom.atom_type = new_type
        return atom
    else:
        # Create new atom with updated type
        migrated = atom.model_copy()
        migrated.atom_type = new_type
        return migrated


def migrate_atoms_batch(atoms: List[MemoryAtom], in_place: bool = True) -> List[MemoryAtom]:
    """
    Migrate a batch of atoms to new ontology.
    
    Args:
        atoms: List of atoms to migrate
        in_place: If True, modify atoms in place
        
    Returns:
        List of migrated atoms
    """
    migrated_count = 0
    
    for atom in atoms:
        old_type = atom.atom_type
        new_type = migrate_relation_to_specific_type(atom)
        
        if old_type != new_type:
            migrated_count += 1
            if in_place:
                atom.atom_type = new_type
    
    logger.info(
        f"Migrated {migrated_count}/{len(atoms)} atoms to new ontology types"
    )
    
    return atoms


def get_migration_stats(atoms: List[MemoryAtom]) -> dict:
    """
    Get statistics on how atoms would be migrated.
    
    Args:
        atoms: List of atoms to analyze
        
    Returns:
        Dict with migration statistics
    """
    stats = {
        "total": len(atoms),
        "by_current_type": {},
        "by_new_type": {},
        "migrations": {},
    }
    
    for atom in atoms:
        current_type = atom.atom_type
        new_type = migrate_relation_to_specific_type(atom)
        
        # Count by current type
        stats["by_current_type"][current_type] = \
            stats["by_current_type"].get(current_type, 0) + 1
        
        # Count by new type
        stats["by_new_type"][new_type] = \
            stats["by_new_type"].get(new_type, 0) + 1
        
        # Track migrations
        if current_type != new_type:
            migration_key = f"{current_type} -> {new_type}"
            stats["migrations"][migration_key] = \
                stats["migrations"].get(migration_key, 0) + 1
    
    return stats


def print_migration_report(atoms: List[MemoryAtom]) -> None:
    """
    Print a detailed migration report.
    
    Args:
        atoms: List of atoms to analyze
    """
    stats = get_migration_stats(atoms)
    
    print("\n" + "="*60)
    print("ONTOLOGY MIGRATION REPORT")
    print("="*60)
    
    print(f"\nTotal atoms: {stats['total']}")
    
    print("\nCurrent type distribution:")
    for atom_type, count in sorted(stats['by_current_type'].items()):
        percentage = (count / stats['total']) * 100
        print(f"  {atom_type:15s}: {count:4d} ({percentage:5.1f}%)")
    
    print("\nNew type distribution:")
    for atom_type, count in sorted(stats['by_new_type'].items()):
        percentage = (count / stats['total']) * 100
        print(f"  {atom_type:15s}: {count:4d} ({percentage:5.1f}%)")
    
    if stats['migrations']:
        print("\nMigrations to be performed:")
        for migration, count in sorted(stats['migrations'].items()):
            percentage = (count / stats['total']) * 100
            print(f"  {migration:30s}: {count:4d} ({percentage:5.1f}%)")
    else:
        print("\nNo migrations needed - all atoms already use specific types")
    
    print("\n" + "="*60 + "\n")


def validate_migration(atoms: List[MemoryAtom]) -> tuple[bool, List[str]]:
    """
    Validate that all atoms can be migrated successfully.
    
    Args:
        atoms: List of atoms to validate
        
    Returns:
        (all_valid, list_of_errors)
    """
    from src.core.ontology import validate_atom
    
    errors = []
    
    for atom in atoms:
        # Simulate migration
        new_type = migrate_relation_to_specific_type(atom)
        
        # Create temporary atom with new type
        temp_atom = atom.model_copy()
        temp_atom.atom_type = new_type
        
        # Validate
        is_valid, reason = validate_atom(temp_atom)
        
        if not is_valid:
            errors.append(
                f"Atom {atom.id} ({atom.predicate}): {reason}"
            )
    
    return len(errors) == 0, errors
