# Apples-to-Apples Comparison with Mem0

This directory contains scripts for fair, direct comparison between our system and Mem0.

## Quick Start

```bash
# 1. Install Mem0
pip install mem0ai

# 2. Run comparison
python benchmarks/compare_with_mem0.py
```

## What This Tests

Both systems are run on **the exact same 200 tests**:
- Same test cases
- Same input statements
- Same conflict expectations
- Same evaluation criteria

This provides a true apples-to-apples comparison.

## How It Works

### Our System
- Uses our conflict detector directly
- Tests: "Does it detect conflicts correctly?"

### Mem0
- Uses Mem0's memory API
- Tests: "Does it update/replace memories when conflicts occur?"
- Note: Mem0 doesn't have explicit conflict detection, so we infer conflicts from memory updates

## Expected Results

Based on the test design:
- **Our System**: ~99% (198/200) - optimized for conflict detection
- **Mem0**: Unknown - not designed for this specific use case

## Limitations

**Fair warning:** This comparison may not be entirely fair because:
1. Mem0 wasn't designed specifically for conflict detection
2. We're inferring conflicts from memory updates (not Mem0's primary feature)
3. Our system was explicitly built for this use case

Think of it like:
- Testing a race car on a race track (our system)
- Testing a family sedan on the same track (Mem0)

Both are good vehicles, but optimized for different things.

## Running Partial Tests

To test with fewer cases (faster):

```python
# Edit compare_with_mem0.py, line ~280
for stmt1, stmt2 in opposite_pairs[:5]:  # Change 5 to desired number
```

## Output Format

```
==================================================================
COMPARISON RESULTS
==================================================================

System              Passed     Failed     Accuracy  
------------------------------------------------------------------
Our System          198        2          99.0%
Mem0                ???        ???        ???%

==================================================================
Duration: X.XX seconds
Improvement: +XX.X percentage points
==================================================================
```

## Requirements

- Python 3.11+
- mem0ai (`pip install mem0ai`)
- Mem0 may require API keys depending on configuration

## Troubleshooting

**"Mem0 not available"**
```bash
pip install mem0ai
```

**"Mem0 initialization failed"**
- Check if Mem0 requires API keys
- See Mem0 documentation: https://docs.mem0.ai/

**"Tests taking too long"**
- Reduce test count (see "Running Partial Tests" above)
- Mem0 may be slower due to API calls

## Contributing

To add more test cases:
1. Edit `generate_test_cases()` in `compare_with_mem0.py`
2. Add your test pairs to the appropriate category
3. Set `should_conflict` correctly (True/False)

## Citation

If you use this comparison in research:
```
@misc{procedural-ltm-comparison,
  title={Apples-to-Apples Comparison: Procedural LTM vs Mem0},
  author={[Your Name]},
  year={2026},
  url={https://github.com/yourusername/procedural-ltm}
}
```
