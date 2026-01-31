# Contributing to Procedural LTM

Thank you for your interest in contributing!

---

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/Alby2007/LLTM.git
cd LLTM

# Install dependencies
pip install -r requirements.txt

# Run tests to verify setup
python -m pytest tests/ -v

# Expected: 200+ tests passing
```

### 2. Verify Installation

```bash
# Run core benchmark (should get 99% accuracy)
python run_200_test_benchmark.py

# Run comprehensive suite (should get 86% accuracy)
python run_300_comprehensive_benchmark.py

# Run multi-hop tests (should get 100%)
python -m pytest tests/test_multihop_reasoning.py -v
```

---

## 📁 Project Structure

```
LLTM/
├── src/                    # Core system code
│   ├── agents/            # AI agents (lifelong learning, tutor, etc.)
│   ├── core/              # Core models and ontology
│   ├── extraction/        # Fact extraction (rule-based + LLM)
│   ├── jury/              # Multi-judge deliberation system
│   ├── observability/     # Monitoring and metrics
│   ├── pipeline/          # Memory processing pipeline
│   ├── reconciliation/    # Conflict detection and resolution
│   ├── storage/           # Database layer (SQLite, PostgreSQL)
│   └── temporal/          # Time-based decay and supersession
├── tests/                 # Test suite
│   ├── benchmarks/        # 102 benchmark tests
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── docs/                  # Documentation
│   ├── architecture/      # Technical design
│   ├── benchmarks/        # Benchmark results
│   ├── deployment/        # Deployment guides
│   ├── experiments/       # Application demos
│   └── testing/           # Testing guides
├── examples/              # Usage examples
├── k8s/                   # Kubernetes configs
└── monitoring/            # Prometheus/Grafana configs
```

---

## 🧪 Running Tests

### All Tests
```bash
python -m pytest tests/ -v
```

### Specific Test Suites
```bash
# Benchmark tests (102 tests)
python -m pytest tests/benchmarks/ -v

# Multi-hop reasoning (6 tests)
python -m pytest tests/test_multihop_reasoning.py -v

# Storage API tests
python -m pytest tests/test_storage_api.py -v

# Experiment tests
python test_all_experiments_simple.py
```

### Test Coverage
```bash
python -m pytest tests/ --cov=src --cov-report=html
```

---

## 📝 Code Style

### Python Style Guide
- Follow PEP 8
- Use type hints
- Write docstrings for public APIs
- Keep functions focused and small

### Example
```python
from typing import List, Optional
from src.core.models import MemoryAtom

async def process_atoms(
    atoms: List[MemoryAtom],
    filter_type: Optional[str] = None
) -> List[MemoryAtom]:
    """
    Process a list of memory atoms.
    
    Args:
        atoms: List of atoms to process
        filter_type: Optional type filter
        
    Returns:
        Filtered and processed atoms
    """
    # Implementation
    pass
```

---

## 🔧 Development Workflow

### 1. Create a Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Write code
- Add tests
- Update documentation

### 3. Run Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Check code style
black src/ tests/
ruff check src/ tests/
```

### 4. Commit
```bash
git add .
git commit -m "feat: add your feature description"
```

### 5. Push and Create PR
```bash
git push origin feature/your-feature-name
# Then create PR on GitHub
```

---

## 🎯 Contribution Areas

### High Priority
- [ ] Expand world knowledge rules (currently 20, target 100+)
- [ ] Improve multi-hop reasoning (85% → 95%)
- [ ] Add more semantic conflict patterns
- [ ] Optimize 3-hop graph traversal
- [ ] Domain-specific ontologies (medical, legal, etc.)

### Medium Priority
- [ ] Additional storage backends (MongoDB, Redis)
- [ ] Enhanced monitoring dashboards
- [ ] More experiment applications
- [ ] Performance optimizations
- [ ] Documentation improvements

### Research Opportunities
- [ ] Adversarial robustness (currently 10%)
- [ ] Adaptive rule learning from feedback
- [ ] Graph neural networks for reasoning
- [ ] Semantic embeddings for fuzzy matching
- [ ] Confidence calibration for chains

---

## 📚 Documentation

### Where to Add Documentation

**Code Documentation:**
- Docstrings in source files
- Type hints for all functions
- Inline comments for complex logic

**User Documentation:**
- `docs/` directory for guides
- `README.md` for overview
- `REPRODUCE.md` for quick start

**API Documentation:**
- `docs/api/` for API reference
- Examples in `examples/`

---

## 🐛 Reporting Issues

### Bug Reports
Include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages and logs

### Feature Requests
Include:
- Use case description
- Proposed solution
- Alternative approaches considered

---

## ✅ Pull Request Checklist

Before submitting a PR:

- [ ] Tests pass: `python -m pytest tests/ -v`
- [ ] Code formatted: `black src/ tests/`
- [ ] Type hints added
- [ ] Docstrings written
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)
- [ ] No breaking changes (or clearly documented)

---

## 🎓 Learning Resources

### Understanding the System
1. **Start**: Read `README.md`
2. **Architecture**: `docs/architecture/TECHNICAL_DESIGN.md`
3. **Benchmarks**: `docs/benchmarks/COMPREHENSIVE_RESULTS.md`
4. **Code**: Explore `src/` directory

### Key Concepts
- **Dual-graph architecture**: Substantiated vs historical
- **Multi-judge deliberation**: SafetyJudge, MemoryJudge, etc.
- **Conflict resolution**: Opposite predicates, exclusive predicates
- **Multi-hop reasoning**: Transitive conflict detection
- **Temporal supersession**: Newer facts override older

---

## 💬 Community

### Getting Help
- GitHub Issues: Bug reports and questions
- Discussions: Feature ideas and general chat
- Email: [your-email] for private inquiries

### Code of Conduct
- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Follow the project's technical standards

---

## 🎉 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in academic papers (if applicable)

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Questions?** Open an issue or start a discussion!

**Last Updated**: January 31, 2026
