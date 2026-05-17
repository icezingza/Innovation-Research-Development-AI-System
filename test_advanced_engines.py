import asyncio
from src.reasoning.divergent_engine import DivergentThinkingEngine
from src.intelligence.literature import LiteratureIntelligenceComponent
from src.infrastructure.simulator import ExperimentSimulator, SimulationConfig
from src.civilization.world_model import WorldModelingEngine

# Dummy Event Bus to intercept publications
class DummyEventBus:
    async def publish(self, topic: str, payload: dict):
        print(f"   📡 [EventBus] Published to '{topic}': {len(payload.get('paths', []))} paths generated.")

async def test_divergent_thinking():
    print("\n[1] --- Testing DivergentThinkingEngine ---")
    bus = DummyEventBus()
    engine = DivergentThinkingEngine(event_bus=bus)
    paths = await engine.generate_divergent_paths("Mitigating flux noise in SQUID-based devices", num_paths=3)
    for p in paths:
        print(f"    ↳ Path: {p['path']} (Confidence: {p['confidence']:.2f})")

async def test_literature_intelligence():
    print("\n[2] --- Testing LiteratureIntelligenceComponent ---")
    lit_engine = LiteratureIntelligenceComponent(memory=None)
    result = await lit_engine.synthesize_domain("Quantum Error Correction", "Magic State Distillation overhead")
    print(f"    ↳ Summary: {result.summary}")
    print(f"    ↳ Citations: {result.citation_count} | Confidence: {result.confidence}")

async def test_experiment_simulator():
    print("\n[3] --- Testing ExperimentSimulator ---")
    config = SimulationConfig(duration_steps=1000, noise_model="depolarizing", error_rate=0.01)
    simulator = ExperimentSimulator(config=config)
    result = await simulator.run_simulation("Dynamic decoupling reduces TLS noise by 40%", {"pulse_sequence": "CPMG"})
    print(f"    ↳ Validation Score: {result.validation_score}")
    print(f"    ↳ Findings:")
    for f in result.findings:
        print(f"        - {f}")

async def test_world_modeling():
    print("\n[4] --- Testing WorldModelingEngine ---")
    world_model = WorldModelingEngine(neo4j_connector=None)
    result = await world_model.update_state("Room temperature superconductor LK-99 officially debunked by Nature", "Materials Science")
    print(f"    ↳ Status: {result['status']} | Domain: {result['domain']}")
    print(f"    ↳ Event: {result['event']} | Severity: {result['impact_severity']}")
    print(f"    ↳ Internal DB State: {world_model.current_state}")

async def main():
    print("🚀 Starting Advanced Engines Integration Test (NamoNexus v5.0.0)...")
    await test_divergent_thinking()
    await test_literature_intelligence()
    await test_experiment_simulator()
    await test_world_modeling()
    print("\n✅ All Advanced Engines executed successfully without errors!")

if __name__ == "__main__":
    asyncio.run(main())
