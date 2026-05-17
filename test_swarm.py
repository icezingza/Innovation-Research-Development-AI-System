import asyncio
import logging
import sys

from src.infrastructure.event_bus import RuntimeEventBus
from src.agents.hypothesis_agent import HypothesisAgent
from src.agents.critique_agent import CritiqueAgent
from src.agents.synthesis_agent import SynthesisAgent
from src.orchestration.agent_coordinator import AgentCoordinator, CoordinatorConfig
from src.inference.router import InferenceRouter

# Configure logging to see the swarm in action
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("test_swarm")


async def run_test():
    logger.info("Initializing Swarm components...")

    # 1. Setup Infrastructure
    bus = RuntimeEventBus()

    # 2. Setup Inference (Empty router -> will use heuristic fallbacks)
    # This ensures the test runs even without API keys
    router = InferenceRouter(providers=[])

    # 3. Setup Specialized Agents
    hyp_agents = [
        HypothesisAgent(event_bus=bus, inference_router=router),
        HypothesisAgent(event_bus=bus, inference_router=router),
    ]
    crit_agents = [CritiqueAgent(event_bus=bus, inference_router=router)]
    synth_agent = SynthesisAgent(event_bus=bus, inference_router=router)

    # 4. Initialize Coordinator
    coordinator = AgentCoordinator(
        event_bus=bus,
        hypothesis_agents=hyp_agents,
        critique_agents=crit_agents,
        synthesis_agent=synth_agent,
        inference_router=router,
        config=CoordinatorConfig(max_sub_questions=2, run_critique=True),
    )

    goal = "Impact of artificial general intelligence on global economy"
    logger.info(f"Starting Swarm coordination for goal: '{goal}'")

    try:
        result = await coordinator.coordinate(goal)

        print("\n" + "=" * 50)
        print("SWARM COORDINATION RESULT")
        print("=" * 50)
        print(f"Session ID: {result.session_id}")
        print(f"Goal: {result.goal}")
        print(f"Duration: {result.duration_seconds}s")
        print(f"Events Published: {result.events_published}")

        print("\n[Sub-questions]")
        for i, q in enumerate(result.sub_questions):
            print(f"  {i + 1}. {q}")

        print("\n[Hypotheses Generated]")
        for i, h in enumerate(result.hypotheses):
            print(f"  - {h.get('statement')}")

        print("\n[Critiques]")
        for i, c in enumerate(result.critiques):
            print(f"  - {c.get('critique')}")

        print("\n[Final Synthesis]")
        print(f"  Conclusion: {result.synthesis.get('conclusion')}")
        print(f"  Confidence: {result.synthesis.get('confidence')}")
        print("=" * 50 + "\n")

        logger.info("Swarm coordination test completed successfully!")

    except Exception as e:
        logger.exception(f"Swarm coordination failed: {e}")


if __name__ == "__main__":
    asyncio.run(run_test())
