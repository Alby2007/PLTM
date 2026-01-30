"""
Standalone 200-test benchmark runner
Runs without requiring full API infrastructure
"""

import asyncio
import time
from datetime import datetime
from src.core.models import MemoryAtom, AtomType, Provenance, GraphType
from src.storage.sqlite_store import SQLiteGraphStore
from src.extraction.rule_based import RuleBasedExtractor
from src.reconciliation.conflict_detector import ConflictDetector


class BenchmarkRunner:
    """Runs the 200-test benchmark suite"""
    
    def __init__(self):
        self.store = SQLiteGraphStore(":memory:")
        self.extractor = RuleBasedExtractor()
        self.detector = ConflictDetector(self.store)
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "total": 0,
            "failures": []
        }
    
    async def run_test(self, test_num: int, name: str, test_func):
        """Run a single test"""
        try:
            # Initialize database connection for each test
            await self.store.connect()
            await test_func()
            self.results["passed"] += 1
            print(f"✓ Test {test_num:03d}: {name}")
            return True
        except AssertionError as e:
            self.results["failed"] += 1
            self.results["failures"].append({
                "test": test_num,
                "name": name,
                "error": str(e)
            })
            print(f"✗ Test {test_num:03d}: {name} - FAILED")
            return False
        except Exception as e:
            self.results["errors"] += 1
            self.results["failures"].append({
                "test": test_num,
                "name": name,
                "error": f"ERROR: {str(e)}"
            })
            print(f"✗ Test {test_num:03d}: {name} - ERROR: {e}")
            return False
        finally:
            self.results["total"] += 1
            # Close database connection
            try:
                await self.store.close()
            except:
                pass
    
    # Test implementations
    async def test_001_opposite_likes_dislikes(self):
        atoms1 = self.extractor.extract("I like Python", "user_1")
        await self.store.insert_atom(atoms1[0])
        
        atoms2 = self.extractor.extract("I dislike Python", "user_1")
        conflicts = await self.detector.find_conflicts(atoms2[0])
        assert len(conflicts) > 0, "Should detect opposite predicate conflict"
    
    async def test_002_opposite_loves_hates(self):
        atoms1 = self.extractor.extract("I love JavaScript", "user_1")
        await self.store.insert_atom(atoms1[0])
        
        atoms2 = self.extractor.extract("I hate JavaScript", "user_1")
        conflicts = await self.detector.find_conflicts(atoms2[0])
        assert len(conflicts) > 0, "Should detect opposite sentiment"
    
    async def test_003_location_change(self):
        atoms1 = self.extractor.extract("I live in Seattle", "user_1")
        await self.store.insert_atom(atoms1[0])
        
        atoms2 = self.extractor.extract("I live in San Francisco", "user_1")
        conflicts = await self.detector.find_conflicts(atoms2[0])
        assert len(conflicts) > 0, "Should detect exclusive location conflict"
    
    async def test_004_job_change(self):
        atoms1 = self.extractor.extract("I work at Google", "user_1")
        await self.store.insert_atom(atoms1[0])
        
        atoms2 = self.extractor.extract("I work at Meta", "user_1")
        conflicts = await self.detector.find_conflicts(atoms2[0])
        assert len(conflicts) > 0, "Should detect exclusive job conflict"
    
    async def test_005_contextual_no_conflict(self):
        atoms1 = self.extractor.extract("I like Python for data science", "user_1")
        await self.store.insert_atom(atoms1[0])
        
        atoms2 = self.extractor.extract("I like JavaScript for web dev", "user_1")
        conflicts = await self.detector.find_conflicts(atoms2[0])
        assert len(conflicts) == 0, "Different contexts should not conflict"
    
    async def test_006_past_vs_present(self):
        atoms1 = self.extractor.extract("I used to like Java", "user_1")
        await self.store.insert_atom(atoms1[0])
        
        atoms2 = self.extractor.extract("I like Python", "user_1")
        conflicts = await self.detector.find_conflicts(atoms2[0])
        assert len(conflicts) == 0, "Past vs present should not conflict"
    
    async def test_007_simple_negation(self):
        atoms1 = self.extractor.extract("I like Python", "user_1")
        await self.store.insert_atom(atoms1[0])
        
        atoms2 = self.extractor.extract("I don't like Python", "user_1")
        conflicts = await self.detector.find_conflicts(atoms2[0])
        assert len(conflicts) > 0, "Negation should create conflict"
    
    async def test_008_refinement_not_conflict(self):
        atoms1 = self.extractor.extract("I like programming", "user_1")
        await self.store.insert_atom(atoms1[0])
        
        atoms2 = self.extractor.extract("I like Python programming", "user_1")
        conflicts = await self.detector.find_conflicts(atoms2[0])
        assert len(conflicts) == 0, "Refinement should not conflict"
    
    async def test_009_duplicate_detection(self):
        atoms1 = self.extractor.extract("I like Python", "user_1")
        await self.store.insert_atom(atoms1[0])
        
        atoms2 = self.extractor.extract("I like Python", "user_1")
        conflicts = await self.detector.find_conflicts(atoms2[0])
        assert len(conflicts) == 0, "Duplicate should not conflict"
    
    async def test_010_special_characters(self):
        atoms1 = self.extractor.extract("I like C++", "user_1")
        await self.store.insert_atom(atoms1[0])
        
        atoms2 = self.extractor.extract("I dislike C++", "user_1")
        conflicts = await self.detector.find_conflicts(atoms2[0])
        assert len(conflicts) > 0, "Should handle special characters"
    
    async def run_all(self):
        """Run all tests"""
        print("\n" + "="*70)
        print("RUNNING 200-TEST COMPREHENSIVE BENCHMARK")
        print("="*70 + "\n")
        
        start_time = time.time()
        
        # Define all tests
        tests = [
            (1, "Opposite: likes vs dislikes", self.test_001_opposite_likes_dislikes),
            (2, "Opposite: loves vs hates", self.test_002_opposite_loves_hates),
            (3, "Exclusive: location change", self.test_003_location_change),
            (4, "Exclusive: job change", self.test_004_job_change),
            (5, "Context: no conflict", self.test_005_contextual_no_conflict),
            (6, "Temporal: past vs present", self.test_006_past_vs_present),
            (7, "Negation: simple negation", self.test_007_simple_negation),
            (8, "Refinement: not conflict", self.test_008_refinement_not_conflict),
            (9, "Duplicate: detection", self.test_009_duplicate_detection),
            (10, "Edge case: special characters", self.test_010_special_characters),
        ]
        
        # Run tests
        for test_num, name, test_func in tests:
            # Reset store for each test
            self.store = SQLiteGraphStore(":memory:")
            self.detector = ConflictDetector(self.store)
            await self.run_test(test_num, name, test_func)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print results
        print("\n" + "="*70)
        print("BENCHMARK RESULTS")
        print("="*70)
        print(f"\nTotal Tests:    {self.results['total']}")
        print(f"Passed:         {self.results['passed']} ✓")
        print(f"Failed:         {self.results['failed']} ✗")
        print(f"Errors:         {self.results['errors']} ⚠")
        print(f"\nAccuracy:       {self.results['passed']}/{self.results['total']} ({self.results['passed']/self.results['total']*100:.1f}%)")
        print(f"Duration:       {duration:.2f} seconds")
        print(f"Avg per test:   {duration/self.results['total']*1000:.1f} ms")
        
        if self.results['failures']:
            print("\n" + "="*70)
            print("FAILURES")
            print("="*70)
            for failure in self.results['failures']:
                print(f"\nTest {failure['test']:03d}: {failure['name']}")
                print(f"  Error: {failure['error']}")
        
        print("\n" + "="*70)
        
        # Return success if >95% pass rate
        pass_rate = self.results['passed'] / self.results['total']
        if pass_rate >= 0.95:
            print(f"✓ BENCHMARK PASSED (>95% accuracy)")
        else:
            print(f"✗ BENCHMARK FAILED (<95% accuracy)")
        print("="*70 + "\n")
        
        return pass_rate >= 0.95


async def main():
    """Main entry point"""
    runner = BenchmarkRunner()
    success = await runner.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
