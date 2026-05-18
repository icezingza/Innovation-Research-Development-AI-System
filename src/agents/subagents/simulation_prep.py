from typing import Dict, Any
from .base import AntigravitySubAgent


class SimulationDataPrepSubAgent(AntigravitySubAgent):
    """
    SubAgent เบอร์ 3: เตรียมตัวแปรและสภาพแวดล้อมจำลอง (World Model)
    หน้าที่: เตรียมตัวแปรและสภาพแวดล้อมจำลอง เพื่อทดสอบ Swarm
    """

    def __init__(
        self,
        task_name: str = "Mesa_Simulation_Prep",
        max_tokens: int = 2500,
        inference=None,
    ):
        super().__init__(task_name=task_name, max_tokens=max_tokens, max_depth=3)
        self.inference = inference
        self.default_scenarios = [
            "digital_bank_run",
            "supply_chain_collapse",
            "sudden_policy_shift",
        ]

    async def _process_task(self) -> Dict[str, Any]:
        """Override core logic เพื่อสร้างชุดข้อมูลสำหรับ Mesa Engine"""

        target_scenario = self.ephemeral_memory.get("scenario_type", "digital_bank_run")
        severity_level = self.ephemeral_memory.get("severity", "high")
        research_insight = self.ephemeral_memory.get("research_insight", "")

        self.current_tokens += 100

        # 1. ใช้ LLM ออกแบบพารามิเตอร์โลกจำลองเพื่อให้ผลลัพธ์ละเอียดและสมจริงที่สุด
        simulation_payload = None
        if self.inference and self.inference.enabled:
            prompt = (
                f"Design a highly detailed simulation scenario for Mesa Engine.\n"
                f"Scenario: {target_scenario}\n"
                f"Severity: {severity_level}\n"
                f"Research Context: {research_insight}\n\n"
                f"Format output as a valid JSON object representing the simulation configuration. "
                f"Include key parameters like agent count, event probabilities, network policies, "
                f"and expected outcomes."
            )
            try:
                resp = await self.inference.complete(
                    prompt=prompt,
                    system="You are a principal systems simulation architect. Output valid JSON only.",
                    tier="fast",
                )
                if resp:
                    import json

                    cleaned_resp = resp.strip()
                    if cleaned_resp.startswith("```json"):
                        cleaned_resp = cleaned_resp[7:]
                    if cleaned_resp.endswith("```"):
                        cleaned_resp = cleaned_resp[:-3]
                    simulation_payload = json.loads(cleaned_resp.strip())
            except Exception:
                pass

        if not simulation_payload:
            # Fallback to local heuristic
            simulation_payload = await self._generate_crisis_parameters(
                target_scenario, severity_level
            )

        # 2. จัดเตรียม Output ในรูปแบบที่พร้อมยิงเข้า Ray Cluster
        ray_job_id = await self._submit_to_ray_cluster(simulation_payload)

        return {
            "status": "simulation_ready",
            "scenario": target_scenario,
            "mesa_payload": simulation_payload,
            "ray_job_id": ray_job_id,
            "instruction": "Deploy to Ray Cluster for Swarm Stress Testing",
        }

    async def _submit_to_ray_cluster(self, payload: Dict[str, Any]) -> str:
        """ยิง Payload ผ่าน HTTP API ไปยัง Ray Cluster Head Node (Mock)"""
        import uuid

        job_id = f"ray-job-{uuid.uuid4().hex[:8]}"
        self.current_tokens += 50
        return job_id

    async def _generate_crisis_parameters(
        self, scenario: str, severity: str
    ) -> Dict[str, Any]:
        """ฟังก์ชันคำนวณและเตรียมค่าตัวแปรวิกฤต (Mock Data Generation)"""
        self.current_tokens += 400

        agent_count = 10000 if severity == "high" else 5000

        if scenario == "digital_bank_run":
            return {
                "environment": "Thai_Financial_Sector",
                "num_agents": agent_count,
                "panic_spread_rate": 0.85,
                "liquidity_drop_rate": 0.40,
                "bot_intervention_policy": "delayed",
            }
        elif scenario == "supply_chain_collapse":
            return {
                "environment": "SME_Digital_Commerce",
                "num_agents": agent_count,
                "default_probability": 0.65,
                "cascade_effect_multiplier": 1.5,
            }
        else:
            return {
                "environment": "General_Simulation",
                "num_agents": agent_count,
                "scenario": scenario,
            }
