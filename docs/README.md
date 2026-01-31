# Documentation Index

Complete guide to the Procedural LTM system documentation.

---

## 📚 Quick Navigation

### Getting Started
- **[Main README](../README.md)** - Project overview and quick start
- **[Reproduction Guide](../REPRODUCE.md)** - Step-by-step setup (5 minutes)
- **[Contributing Guide](../CONTRIBUTING.md)** - How to contribute

### Core Documentation
- **[Architecture](architecture/TECHNICAL_DESIGN.md)** - System design and components
- **[Benchmark Results](benchmarks/COMPREHENSIVE_RESULTS.md)** - 300-test validation results
- **[Deployment Guide](deployment/GUIDE.md)** - Production deployment (Docker, K8s)
- **[Testing Guide](testing/GUIDE.md)** - Running and writing tests
- **[Test Structure](testing/TEST_STRUCTURE.md)** - Where all 300+ tests live

### Applications
- **[Experiments Quickstart](experiments/QUICKSTART.md)** - 7 novel AI applications
  - Lifelong Learning Agent
  - Multi-Agent Workspace
  - Temporal Reasoning
  - Personalized Tutor
  - Contextual Copilot
  - Memory-Aware RAG
  - Adaptive Prompts

### Development Archive
- **[Archive](archive/)** - Historical development docs, weekly progress, phase summaries

---

## 🎯 Documentation by Use Case

### "I want to understand what this is"
1. Read [Main README](../README.md)
2. Check [Common Misconceptions](../README.md#-common-misconceptions)
3. Review [Architecture](architecture/TECHNICAL_DESIGN.md)

### "I want to run it myself"
1. Follow [Reproduction Guide](../REPRODUCE.md)
2. Run benchmarks: `python run_200_test_benchmark.py`
3. Try experiments: `python test_all_experiments_simple.py`

### "I want to deploy to production"
1. Read [Deployment Guide](deployment/GUIDE.md)
2. Choose: Docker Compose (local) or Kubernetes (production)
3. Set up monitoring (Prometheus + Grafana)

### "I want to contribute"
1. Read [Contributing Guide](../CONTRIBUTING.md)
2. Check [Test Structure](testing/TEST_STRUCTURE.md)
3. Pick an area from contribution priorities

### "I want to verify the claims"
1. Read [Benchmark Results](benchmarks/COMPREHENSIVE_RESULTS.md)
2. Run: `python run_300_comprehensive_benchmark.py`
3. Check [Test Structure](testing/TEST_STRUCTURE.md) for test locations

---

## 📊 Test Documentation

**Important:** If someone asks "where are the 300 tests?", point them to:
- **[Test Structure Guide](testing/TEST_STRUCTURE.md)** - Complete breakdown
- `tests/benchmarks/` - 102 pytest tests
- `run_200_test_benchmark.py` - Standalone runner (99% accuracy)
- `run_300_comprehensive_benchmark.py` - Comprehensive runner (86% accuracy)

**Verify yourself:**
```bash
# Count tests
python -m pytest tests/benchmarks/ --collect-only
# Shows: 102 tests collected

# Run benchmarks
python run_200_test_benchmark.py  # 198/200 passing
python run_300_comprehensive_benchmark.py  # 258/300 passing
```

---

## 🏗️ Architecture Documentation

### System Components
- **Storage Layer**: SQLite/PostgreSQL dual-graph architecture
- **Extraction**: Rule-based + LLM hybrid
- **Conflict Detection**: 4-stage semantic matching + multi-hop reasoning
- **Jury System**: Multi-judge deliberation (Safety, Memory, Time, Consensus)
- **Temporal**: Decay mechanics and supersession
- **Observability**: Prometheus metrics, Grafana dashboards

### Key Innovations
1. **Multi-hop reasoning** - Detects transitive conflicts
2. **Dual-graph architecture** - Substantiated + historical
3. **Grammar-constrained judges** - No hallucinations
4. **Context-aware reconciliation** - Same fact, different contexts

---

## 📈 Benchmark Documentation

### Test Suites
- **200-test core**: 99% accuracy (pattern matching)
- **50 semantic tests**: 86% accuracy (world knowledge)
- **30 multi-hop tests**: 85%+ accuracy (transitive reasoning)
- **20 adversarial tests**: 10% accuracy (research-level)

### Comparison with SOTA
- **vs Mem0**: +19.1 percentage points (86% vs 66.9%)
- **Latency**: 14x faster (3.5ms vs 50ms)
- **Infrastructure**: Production-ready vs research prototype

---

## 🚀 Deployment Documentation

### Deployment Options
1. **Local Development**: SQLite + Docker Compose
2. **Small Scale**: Single instance, PostgreSQL
3. **Production**: Kubernetes cluster, auto-scaling
4. **Enterprise**: Multi-region, sharding, CDN

### Monitoring
- Prometheus metrics at `/metrics`
- Grafana dashboards in `monitoring/grafana/`
- Health checks: `/health`, `/ready`

---

## 🎓 Learning Path

**Recommended reading order:**

1. **Day 1**: Main README + Reproduction Guide
2. **Day 2**: Architecture + Benchmark Results
3. **Day 3**: Experiments Quickstart + Try demos
4. **Day 4**: Deployment Guide + Set up local
5. **Day 5**: Contributing Guide + Pick a task

---

## 🔄 Documentation Updates

### Recent Changes
- **Jan 31, 2026**: Reorganized docs into `/docs/` structure
- **Jan 31, 2026**: Added Test Structure guide
- **Jan 31, 2026**: Created comprehensive benchmark results
- **Jan 31, 2026**: Added deployment guide consolidation

### Maintenance
- Documentation is kept in sync with code
- All examples are tested and working
- Benchmarks are re-run before major releases

---

## 📞 Getting Help

### Documentation Issues
- **Missing info?** Open an issue
- **Unclear section?** Start a discussion
- **Found error?** Submit a PR

### Technical Support
1. Check relevant documentation section
2. Search existing GitHub issues
3. Open new issue with details

---

## 🎯 Quick Reference

| Need | Documentation | Command |
|------|---------------|---------|
| **Setup** | [REPRODUCE.md](../REPRODUCE.md) | `pip install -r requirements.txt` |
| **Test** | [TEST_STRUCTURE.md](testing/TEST_STRUCTURE.md) | `python run_200_test_benchmark.py` |
| **Deploy** | [GUIDE.md](deployment/GUIDE.md) | `docker-compose up -d` |
| **Contribute** | [CONTRIBUTING.md](../CONTRIBUTING.md) | `git checkout -b feature/name` |
| **Verify** | [COMPREHENSIVE_RESULTS.md](benchmarks/COMPREHENSIVE_RESULTS.md) | `python run_300_comprehensive_benchmark.py` |

---

**Last Updated**: January 31, 2026  
**Status**: Complete and up-to-date ✅
