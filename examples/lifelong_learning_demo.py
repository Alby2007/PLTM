"""
Lifelong Learning Agent Demo

This example demonstrates how an AI agent improves over time by
accumulating personalized knowledge through the memory system.

Run this to see:
1. Agent with no memory (baseline)
2. Agent learning from interactions
3. Agent becoming increasingly personalized
4. Improvement metrics over time
"""

import asyncio
from datetime import datetime

from src.storage.graph_store import SQLiteGraphStore
from src.extraction.rule_based import RuleBasedExtractor
from src.reconciliation.conflict_detector import ConflictDetector
from src.pipeline.orchestrator import MemoryPipeline
from src.agents import LifelongLearningAgent, LifelongLearningExperiment


async def mock_llm(prompt: str) -> str:
    """
    Mock LLM for demonstration purposes.
    In production, replace with actual LLM call (OpenAI, Anthropic, etc.)
    """
    # Simple mock that just echoes the prompt structure
    if "Python" in prompt:
        return "I can help you with Python! Based on what I know about you, I'll provide relevant examples."
    elif "JavaScript" in prompt:
        return "I can help you with JavaScript! Let me provide some guidance."
    else:
        return "I'm here to help! Let me know what you need."


async def run_demo():
    """Run the lifelong learning agent demonstration"""
    
    print("=" * 80)
    print("LIFELONG LEARNING AGENT DEMO")
    print("=" * 80)
    print()
    
    # Initialize memory system (existing components - no modifications!)
    store = SQLiteGraphStore("demo_lifelong_learning.db")
    await store.connect()
    
    extractor = RuleBasedExtractor()
    detector = ConflictDetector(store)
    
    pipeline = MemoryPipeline(
        store=store,
        extractor=extractor,
        detector=detector
    )
    
    # Initialize lifelong learning agent
    agent = LifelongLearningAgent(
        memory_pipeline=pipeline,
        user_id="demo_user",
        learning_enabled=True
    )
    
    # Initialize experiment framework
    experiment = LifelongLearningExperiment(agent)
    
    print("✅ Agent initialized with zero memories")
    print()
    
    # Simulate a series of interactions over time
    interactions = [
        # Week 1: Learning preferences
        ("I prefer Python over JavaScript", True),
        ("I like concise code", True),
        ("I work on machine learning projects", True),
        
        # Week 2: Learning expertise
        ("I'm experienced with neural networks", True),
        ("I use PyTorch for deep learning", True),
        ("I prefer functional programming style", True),
        
        # Week 3: Learning projects
        ("I'm building a recommendation system", True),
        ("I work at a startup", True),
        ("I like to use type hints in Python", True),
        
        # Week 4: More context
        ("I prefer async/await over callbacks", True),
        ("I like using dataclasses", True),
        ("I'm interested in LLM applications", True),
    ]
    
    print("📚 Running 12 interactions to accumulate knowledge...")
    print()
    
    for i, (message, task_success) in enumerate(interactions, 1):
        print(f"Interaction {i}/12: \"{message}\"")
        
        # Run interaction
        result = await experiment.run_interaction(
            message=message,
            llm_callable=mock_llm,
            task_success=task_success
        )
        
        print(f"  → Context used: {result['context_count']} memories")
        print(f"  → Learnings stored: {result['learnings_stored']}")
        print()
        
        # Show progress every 3 interactions
        if i % 3 == 0:
            stats = agent.get_stats()
            print(f"  📊 Progress: {stats['learnings_extracted']} total learnings extracted")
            print()
    
    print("=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print()
    
    # Show agent stats
    stats = agent.get_stats()
    print("Agent Statistics:")
    print(f"  Total Interactions:        {stats['interaction_count']}")
    print(f"  Learnings Extracted:       {stats['learnings_extracted']}")
    print(f"  Avg Learnings/Interaction: {stats['avg_learnings_per_interaction']:.2f}")
    print()
    
    # Show user profile
    profile = await agent.get_user_profile()
    print("User Profile (Accumulated Knowledge):")
    print(f"  Total Memories:    {profile['total_memories']}")
    print(f"  Preferences:       {len(profile['preferences'])}")
    print(f"  Expertise:         {len(profile['expertise'])}")
    print(f"  Affiliations:      {len(profile['affiliations'])}")
    print()
    
    if profile['preferences']:
        print("  Sample Preferences:")
        for pref in profile['preferences'][:3]:
            print(f"    - {pref}")
        print()
    
    # Show improvement metrics
    print("Improvement Metrics:")
    metrics = experiment.get_improvement_metrics()
    if 'error' not in metrics:
        print(f"  Context Growth:    {metrics['baseline_context_count']:.1f} → {metrics['current_context_count']:.1f} memories")
        print(f"  Growth:            +{metrics['context_growth']:.1f} memories")
    print()
    
    # Demonstrate personalized response
    print("=" * 80)
    print("PERSONALIZED RESPONSE DEMO")
    print("=" * 80)
    print()
    
    test_message = "Help me with a Python project"
    print(f"User: \"{test_message}\"")
    print()
    
    # Get context
    context = await agent.get_context(test_message, limit=10)
    print(f"Agent retrieved {len(context)} relevant memories:")
    for ctx in context[:5]:
        print(f"  - {ctx['statement']} (confidence: {ctx['confidence']:.0%})")
    print()
    
    # Generate response
    result = await agent.respond(test_message, mock_llm, extract_learnings=False)
    print(f"Agent response: \"{result['response']}\"")
    print(f"(Used {result['context_count']} memories for personalization)")
    print()
    
    # Cleanup
    await store.close()
    
    print("=" * 80)
    print("✅ Demo complete!")
    print()
    print("Key Takeaways:")
    print("  1. Agent starts with zero knowledge")
    print("  2. Learns from every interaction")
    print("  3. Accumulates personalized context")
    print("  4. Responses become increasingly relevant")
    print("  5. No modifications to existing memory system!")
    print("=" * 80)


async def run_experiment_simulation():
    """
    Simulate a 90-day experiment to measure improvement over time.
    
    This demonstrates the research potential of the lifelong learning agent.
    """
    
    print("=" * 80)
    print("90-DAY LIFELONG LEARNING EXPERIMENT SIMULATION")
    print("=" * 80)
    print()
    
    # Initialize
    store = SQLiteGraphStore("experiment_lifelong_learning.db")
    await store.connect()
    
    extractor = RuleBasedExtractor()
    detector = ConflictDetector(store)
    pipeline = MemoryPipeline(store=store, extractor=extractor, detector=detector)
    
    agent = LifelongLearningAgent(pipeline, "experiment_user", learning_enabled=True)
    experiment = LifelongLearningExperiment(agent)
    
    # Simulate 90 days of interactions (1 per day)
    print("Simulating 90 days of daily interactions...")
    print()
    
    for day in range(1, 91):
        message = f"Day {day}: I'm working on my project"
        await experiment.run_interaction(
            message=message,
            llm_callable=mock_llm,
            task_success=True
        )
        
        if day % 10 == 0:
            stats = agent.get_stats()
            print(f"Day {day}: {stats['learnings_extracted']} learnings, {stats['context_retrievals']} context retrievals")
    
    print()
    print("=" * 80)
    print("EXPERIMENT RESULTS")
    print("=" * 80)
    print()
    
    # Generate report
    report = experiment.generate_report()
    print(report)
    
    # Cleanup
    await store.close()
    
    print("Experiment data saved for analysis!")
    print()


if __name__ == "__main__":
    print()
    print("Choose demo:")
    print("1. Quick demo (12 interactions)")
    print("2. 90-day experiment simulation")
    print()
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        asyncio.run(run_experiment_simulation())
    else:
        asyncio.run(run_demo())
