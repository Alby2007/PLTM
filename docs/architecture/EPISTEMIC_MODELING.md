# Epistemic Modeling in Procedural LTM

**Added**: January 31, 2026  
**Reason**: Community feedback on ambiguous belief attribution

---

## 🎯 The Problem

Previous implementation had ambiguous epistemic status:

```python
# AMBIGUOUS - Who believes this?
MemoryAtom(
    subject="Bob",
    predicate="will_get",
    object="job",
    epistemic_status="belief"  # ❌ Whose belief? User's? Bob's? Someone else's?
)
```

**Issue**: Can't distinguish between:
- "I think Bob will get a job" (user's belief)
- "Mary thinks Bob will get a job" (Mary's belief, reported by user)
- "Bob thinks he'll get a job" (Bob's belief, reported by user)

---

## ✅ The Solution

Explicit epistemic modeling with three fields:

```python
class MemoryAtom:
    # Epistemic modeling - WHO believes WHAT with WHAT certainty
    source_user: str              # WHO stated/observed this
    belief_holder: Optional[str]  # WHO holds the belief (if different)
    epistemic_distance: int       # How many levels removed (0=direct, 1=reported, etc.)
```

---

## 📚 Examples

### Direct Belief (User's Own Belief)

**Statement**: "I think Bob will get a job"

```python
MemoryAtom(
    subject="Bob",
    predicate="will_get",
    object="job",
    
    source_user="user_123",      # User stated this
    confidence=0.7,               # User is 70% certain
    belief_holder="user_123",     # User holds this belief
    epistemic_distance=0          # Direct belief
)
```

### Reported Belief (Someone Else's Belief)

**Statement**: "Mary thinks Bob will get a job"

```python
MemoryAtom(
    subject="Bob",
    predicate="will_get",
    object="job",
    
    source_user="user_123",       # User told us
    confidence=0.6,                # Lower (secondhand information)
    belief_holder="Mary",          # Mary holds this belief
    epistemic_distance=1           # One level removed (reported)
)
```

### Nested Belief (Third-Hand)

**Statement**: "Alice said that Mary thinks Bob will get a job"

```python
MemoryAtom(
    subject="Bob",
    predicate="will_get",
    object="job",
    
    source_user="user_123",       # User told us
    confidence=0.4,                # Even lower (third-hand)
    belief_holder="Mary",          # Mary holds the belief
    epistemic_distance=2           # Two levels removed (Alice → Mary → belief)
)
```

### Factual Statement (No Belief Holder)

**Statement**: "Bob got a job"

```python
MemoryAtom(
    subject="Bob",
    predicate="got",
    object="job",
    
    source_user="user_123",       # User stated this
    confidence=0.9,                # High certainty (factual)
    belief_holder=None,            # Not a belief, it's a fact
    epistemic_distance=0           # Direct observation/statement
)
```

---

## 🔍 Epistemic Distance Levels

| Distance | Meaning | Example | Confidence Impact |
|----------|---------|---------|-------------------|
| **0** | Direct | "I believe X" | No reduction |
| **1** | Reported | "Mary believes X" | -10% to -20% |
| **2** | Third-hand | "Alice said Mary believes X" | -20% to -40% |
| **3+** | Multi-level | "Bob heard Alice say Mary believes X" | -40% to -60% |

**Confidence degradation**: Each level of epistemic distance reduces confidence, reflecting uncertainty in transmission.

---

## 🎓 Knowledge Representation Theory

This approach is grounded in:

1. **Epistemic Logic** - Formal modeling of knowledge and belief
2. **Source Tracking** - Who said what, when
3. **Belief Attribution** - Distinguishing belief holders
4. **Confidence Calibration** - Adjusting certainty based on source distance

**Key Insight**: "I think X" and "Mary thinks X" are fundamentally different statements requiring different representations.

---

## 🔧 Implementation Details

### Default Values

```python
source_user: str = ""                    # Required (who told us)
belief_holder: Optional[str] = None      # Optional (defaults to source_user for beliefs)
epistemic_distance: int = 0              # Default to direct
```

### Inference Rules

```python
# If belief_holder is None, it's a factual statement
if atom.belief_holder is None:
    # Treat as fact, not belief
    pass

# If belief_holder == source_user, it's a direct belief
elif atom.belief_holder == atom.source_user:
    # User's own belief
    pass

# If belief_holder != source_user, it's a reported belief
else:
    # Someone else's belief, reported by user
    # Apply confidence reduction based on epistemic_distance
    adjusted_confidence = atom.confidence * (0.9 ** atom.epistemic_distance)
```

### Conflict Detection

```python
# Two beliefs about the same thing
atom1 = MemoryAtom(
    subject="Bob", predicate="will_get", object="job",
    belief_holder="user_123", confidence=0.7
)

atom2 = MemoryAtom(
    subject="Bob", predicate="will_not_get", object="job",
    belief_holder="Mary", confidence=0.6
)

# These DON'T conflict - different people can believe different things
# Only conflict if same belief_holder has contradictory beliefs
```

---

## 📊 Benefits

### 1. Unambiguous Attribution
- Clear who believes what
- No confusion about belief holders
- Explicit epistemic chains

### 2. Better Conflict Detection
- Can distinguish between:
  - User changing their mind (conflict)
  - User reporting someone else's belief (no conflict)
  - Multiple people with different beliefs (no conflict)

### 3. Confidence Calibration
- Automatically reduce confidence for reported beliefs
- Track epistemic distance for uncertainty quantification
- More accurate belief modeling

### 4. Richer Queries
```python
# Get all of user's beliefs
atoms = store.get_atoms_where(belief_holder="user_123")

# Get all reported beliefs (not user's own)
atoms = store.get_atoms_where(
    source_user="user_123",
    belief_holder_not="user_123"
)

# Get high-confidence direct beliefs
atoms = store.get_atoms_where(
    epistemic_distance=0,
    confidence_gte=0.8
)
```

---

## 🎯 Migration Guide

### For Existing Code

**Before:**
```python
atom = MemoryAtom(
    subject="Bob",
    predicate="will_get",
    object="job",
    # No epistemic modeling
)
```

**After:**
```python
atom = MemoryAtom(
    subject="Bob",
    predicate="will_get",
    object="job",
    source_user="user_123",      # Add this
    belief_holder="user_123",     # Add this for beliefs
    epistemic_distance=0          # Add this
)
```

### For New Code

Always specify:
1. `source_user` - Who told us this
2. `belief_holder` - Who believes it (if it's a belief)
3. `epistemic_distance` - How many levels removed

---

## 🙏 Credit

This improvement was suggested by community feedback pointing out the ambiguity in the original `epistemic_status` field.

**Original issue**: "epistemic_status='belief'" doesn't specify whose belief  
**Solution**: Explicit `belief_holder` and `epistemic_distance` fields  
**Result**: Unambiguous epistemic modeling

Good technical feedback that improved the system. Exactly the kind of precision knowledge representation needs.

---

## 📚 Further Reading

- **Epistemic Logic**: Hintikka, J. (1962). "Knowledge and Belief"
- **Belief Revision**: Gärdenfors, P. (1988). "Knowledge in Flux"
- **Source Tracking**: Wilensky, R. (1983). "Planning and Understanding"

---

**Status**: Implemented ✅  
**Last Updated**: January 31, 2026
