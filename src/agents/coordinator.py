import json
from typing import AsyncGenerator
from enum import Enum

from src.agents.subagents.graph_diver import GraphDeepDiverSubAgent
from src.agents.subagents.guardrail_resolver import ConflictResolverSubAgent
from src.agents.subagents.simulation_prep import SimulationDataPrepSubAgent
from src.agents.subagents.red_team_guard import RedTeamGuardSubAgent
from src.agents.subagents.meta_learner import MetaLearnerSubAgent
from src.agents.subagents.circuit_breaker import CircuitBreakerSubAgent


class SwarmIndustry(str, Enum):
    FINTECH = "fintech"
    LEGAL = "legal"
    HEALTH = "health"


SWARM_CONFIGS = {
    SwarmIndustry.FINTECH: {
        "max_recursion_depth": 3,
        "require_red_team": True,
        "simulation_scenario": "digital_bank_run",
    },
    SwarmIndustry.LEGAL: {
        "max_recursion_depth": 5,
        "require_red_team": False,
        "simulation_scenario": "contract_breach_litigation",
    },
    SwarmIndustry.HEALTH: {
        "max_recursion_depth": 4,
        "require_red_team": True,
        "simulation_scenario": "pandemic_supply_chain_collapse",
    },
}


class AgentCoordinator:
    """หัวหน้าทีมควบคุม SubAgents แบบ Industry Swarm และพ่นข้อมูลแบบ Streaming (SSE)"""

    def __init__(self, tenant_id: str, memory=None, inference=None, embedding=None):
        self.tenant_id = tenant_id
        self.memory = memory
        self.inference = inference
        self.embedding = embedding

    async def coordinate_research(
        self, query: str, industry: str = "fintech"
    ) -> AsyncGenerator[str, None]:

        # Load Swarm Config
        try:
            swarm_ind = SwarmIndustry(industry.lower())
            config = SWARM_CONFIGS[swarm_ind]
        except ValueError:
            swarm_ind = SwarmIndustry.FINTECH
            config = SWARM_CONFIGS[swarm_ind]

        qdrant = self.memory.vector_store if self.memory else None
        neo4j = self.memory.graph_store if self.memory else None

        yield json.dumps(
            {
                "status": "init",
                "msg": f"🌐 เริ่มต้นระบบ {swarm_ind.value.upper()} Swarm Template...",
            }
        )

        # --- Phase 0: Red Teaming (Prompt Injection Guard) ---
        if config["require_red_team"]:
            yield json.dumps(
                {"status": "phase_0", "msg": "🛡️ เริ่มตรวจสอบความปลอดภัย AI Red Teaming..."}
            )
            guard = RedTeamGuardSubAgent(
                task_name=f"guard_{swarm_ind.value}",
                inference=self.inference,
                qdrant=qdrant,
                neo4j=neo4j,
            )
            is_safe = True

            async for chunk in guard.execute({"user_input": query}):
                yield json.dumps({"status": "phase_0_stream", "chunk": chunk})
                if chunk.get("status") == "blocked":
                    is_safe = False

            if not is_safe:
                yield json.dumps(
                    {
                        "status": "aborted",
                        "msg": "🚨 ระบบระงับการทำงานเนื่องจากพบความเสี่ยงด้านความปลอดภัย (Prompt Injection)",
                    }
                )
                return

        # --- Phase 1: Knowledge Retrieval ---
        yield json.dumps(
            {
                "status": "phase_1",
                "msg": "🔍 กระจายลูกน้องหน่วย Deep-Diver ลงพื้นที่ Neo4j/Qdrant...",
            }
        )

        retriever = GraphDeepDiverSubAgent(
            task_name=f"retriever_{swarm_ind.value}",
            qdrant=qdrant,
            neo4j=neo4j,
            embedding_provider=self.embedding,
        )

        knowledge_insight = None
        async for chunk in retriever.execute(
            {"query": query, "domain": swarm_ind.value}
        ):
            yield json.dumps({"status": "phase_1_stream", "chunk": chunk})
            if chunk.get("status") == "completed":
                knowledge_insight = chunk.get("insight")

        yield json.dumps({"status": "phase_1_complete", "data": knowledge_insight})

        # --- Phase 1.5: Circuit Breaker Check ---
        mock_depth = len(query.split()) // 10  # Arbitrary depth for simulation

        yield json.dumps(
            {
                "status": "phase_1_5",
                "msg": "⚡ ตรวจสอบ Circuit Breaker ป้องกันการวนลูป (Max Recursion)...",
            }
        )
        breaker = CircuitBreakerSubAgent(
            task_name=f"breaker_{swarm_ind.value}",
            inference=self.inference,
            qdrant=qdrant,
            neo4j=neo4j,
        )

        async for chunk in breaker.execute(
            {
                "recursion_depth": mock_depth,
                "max_depth": config["max_recursion_depth"],
                "user_input": query,
            }
        ):
            yield json.dumps({"status": "phase_1_5_stream", "chunk": chunk})
            if chunk.get("status") == "circuit_broken":
                yield json.dumps(
                    {
                        "status": "phase_1_5_complete",
                        "msg": "📉 เปิดใช้งาน Bayesian Optimization ตัดจบวงจรสำเร็จ",
                    }
                )

        # --- Phase 2: Conflict & Compliance ---
        yield json.dumps(
            {"status": "phase_2", "msg": "⚖️ กำลังตรวจสอบความขัดแย้งและ Compliance..."}
        )
        resolver = ConflictResolverSubAgent(
            task_name=f"resolver_{swarm_ind.value}",
            inference=self.inference,
            qdrant=qdrant,
            neo4j=neo4j,
        )

        compliance_check = None
        async for chunk in resolver.execute(
            {"proposed_solution": str(knowledge_insight), "background_facts": []}
        ):
            yield json.dumps({"status": "phase_2_stream", "chunk": chunk})
            if chunk.get("status") == "cleared":
                compliance_check = chunk.get("resolved_insight")

        yield json.dumps({"status": "phase_2_complete", "data": compliance_check})

        # --- Phase 3: Simulation Prep ---
        yield json.dumps(
            {
                "status": "phase_3",
                "msg": f"🧪 กำลังเตรียม Payload ({config['simulation_scenario']}) สำหรับ Mesa Simulation Engine...",
            }
        )
        sim_prep = SimulationDataPrepSubAgent(
            task_name=f"sim_{swarm_ind.value}", inference=self.inference
        )

        sim_payload = None
        async for chunk in sim_prep.execute(
            {
                "scenario_type": config["simulation_scenario"],
                "severity": "high",
                "research_insight": str(compliance_check),
            }
        ):
            yield json.dumps({"status": "phase_3_stream", "chunk": chunk})
            if chunk.get("status") == "simulation_ready":
                sim_payload = chunk.get("mesa_payload")

        yield json.dumps({"status": "phase_3_complete", "final_sim_ready": sim_payload})

        # --- Phase 4: Meta-Learning ---
        yield json.dumps(
            {
                "status": "phase_4",
                "msg": "🧠 อัปเดต Speculative Knowledge Graphs และ Weights กลับสู่ระบบ (Meta-Learning)...",
            }
        )

        meta = MetaLearnerSubAgent(
            task_name=f"meta_{swarm_ind.value}",
            neo4j=neo4j,
            inference=self.inference,
            qdrant=qdrant,
        )

        async for chunk in meta.execute(
            {
                "feedback": "Successfully created simulation payload without crashes.",
                "performance_metrics": {"tokens": 1200},
            }
        ):
            yield json.dumps({"status": "phase_4_stream", "chunk": chunk})

        yield json.dumps(
            {"status": "all_phases_complete", "final_sim_ready": sim_payload}
        )
