"""Debug script to identify experiment issues"""

import asyncio
import traceback
from src.pipeline.memory_pipeline import MemoryPipeline
from src.storage.sqlite_store import SQLiteGraphStore
from src.agents.lifelong_learning_agent import LifelongLearningAgent
from src.agents.multi_agent_workspace import SharedMemoryWorkspace
from src.agents.adaptive_prompts import AdaptivePromptSystem


async def process_message_fully(pipeline, user_id, message):
    """Helper to consume async generator"""
    async for update in pipeline.process_message(message, user_id):
        pass


async def main():
    store = SQLiteGraphStore(":memory:")
    await store.connect()
    pipeline = MemoryPipeline(store)
    
    print("="*70)
    print("TEST 1: Lifelong Learning Agent")
    print("="*70)
    try:
        user_id = "test_user_1"
        agent = LifelongLearningAgent(pipeline, user_id)
        await process_message_fully(pipeline, user_id, "I love Python")
        context = await agent.get_context("Tell me about programming")
        print(f"✅ SUCCESS: {agent.interaction_count} interactions")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
    
    print("\n" + "="*70)
    print("TEST 2: Multi-Agent Collaboration")
    print("="*70)
    try:
        workspace = SharedMemoryWorkspace(pipeline, workspace_id="test_workspace")
        await workspace.add_agent("researcher", "Research specialist", ["research", "analysis"])
        print(f"✅ SUCCESS: {len(workspace.agents)} agents")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
    
    print("\n" + "="*70)
    print("TEST 3: Adaptive Prompts")
    print("="*70)
    try:
        user_id = "test_user_3"
        prompt_system = AdaptivePromptSystem(pipeline, user_id)
        await process_message_fully(pipeline, user_id, "I prefer concise explanations")
        prompt = await prompt_system.generate_prompt(
            task="explain recursion"
        )
        print(f"✅ SUCCESS: Generated prompt")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
    
    await store.close()


if __name__ == "__main__":
    asyncio.run(main())
