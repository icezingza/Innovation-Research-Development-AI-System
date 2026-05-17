import asyncio
import logging
from typing import Any, Dict

# นำเข้าโมดูลหลักตามโครงสร้างสถาปัตยกรรมระบบ
from src.governance.policy_enforcer import PolicyEnforcer, PolicyDecision
from src.protocols.agent_message import AgentMessage, MessageType
from src.telemetry.runtime_metrics import runtime_events
from src.telemetry.tracing import tracer

logger = logging.getLogger(__name__)


class CognitivePipeline:
    """Coordinates agent execution through a governed async pipeline."""

    def __init__(self, agents: Any = None, policy_enforcer: PolicyEnforcer = None):
        if isinstance(agents, list):
            self.agents_list = agents
            self.agents = {}
            for agent in agents:
                if hasattr(agent, "agent_id"):
                    self.agents[agent.agent_id] = agent
                else:
                    self.agents[str(agent)] = agent
        else:
            self.agents = agents or {}
            self.agents_list = (
                list(self.agents.values()) if isinstance(self.agents, dict) else []
            )

        self.policy_enforcer = policy_enforcer or PolicyEnforcer()

    async def run(self, context: Dict[str, Any]) -> list[AgentMessage]:
        """รันกระบวนการของเอเจนต์ทั้งหมดใน Pipeline และคืนค่าเป็นรายการของ AgentMessage"""
        messages = []

        # 1. รันระบบ 5 สเตจดั้งเดิมผ่าน process() พร้อมผ่าน governance check
        # (ซึ่งจะเก็บข้อมูลผลลัพธ์ลงใน context)
        await self.process(context)

        # 2. รันและรวบรวมคำตอบ (AgentMessage) จากเอเจนต์ทั้งหมด
        for agent in self.agents_list:
            if hasattr(agent, "run"):
                try:
                    response = await agent.run(context)
                    if isinstance(response, AgentMessage):
                        messages.append(response)
                    elif hasattr(response, "content"):
                        messages.append(
                            AgentMessage(
                                sender_id=getattr(agent, "agent_id", "agent"),
                                content=response.content,
                                message_type=MessageType.ACTION,
                            )
                        )
                    else:
                        messages.append(
                            AgentMessage(
                                sender_id=getattr(agent, "agent_id", "agent"),
                                content=str(response),
                                message_type=MessageType.ACTION,
                            )
                        )
                except Exception as e:
                    logger.error(
                        f"Error running agent {getattr(agent, 'agent_id', 'unknown')}: {e}"
                    )

        return messages

    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """รันกระบวนการ Cognitive ทั้ง 5 สเตจแบบ Async และมีการควบคุม Governance"""
        session_id = context.get("session_id", "default-session")

        # ใช้ tracer ครอบคลุมการทำงานเพื่อทำ Distributed Tracing
        with tracer.start_as_current_span("cognitive_pipeline_process") as span:
            span.set_attribute("session_id", session_id)
            logger.info(f"[{session_id}] เริ่มต้นกระบวนการ Governing Async Pipeline")

            # 1. Semantic Understanding
            context = await self._semantic_understanding_stage(context, session_id)

            # 2. Reasoning
            context = await self._reasoning_stage(context, session_id)

            # 3. Hypothesis Generation (รองรับ Parallel สำหรับหลาย Agent)
            context = await self._hypothesis_generation_stage(context, session_id)

            # 4. Feedback Analysis & Critique
            context = await self._feedback_analysis_stage(context, session_id)

            # 5. Memory Update & Synced Record
            context = await self._memory_update_stage(context, session_id)

            logger.info(f"[{session_id}] เสด็จสิ้น Cognitive Pipeline สำเร็จ")
            return context

    async def _enforce_governance(
        self, context: Dict[str, Any], stage_name: str
    ) -> bool:
        """ตรวจสอบความปลอดภัยผ่าน Policy Enforcer ก่อนเริ่มรันสเตจ"""
        if not self.policy_enforcer:
            return True
        # รับค่า PolicyResult จาก enforcer โดยใช้ evaluate ตามคลาส PolicyEnforcer
        decision = await self.policy_enforcer.evaluate(
            AgentMessage(
                sender_id="pipeline_governor",
                content={**context, "stage": stage_name},
                message_type=MessageType.PERCEPTION,
            )
        )
        return (
            decision.decision == PolicyDecision.ALLOW
        )  # คืนค่า True หากผ่านเกณฑ์นโยบายความปลอดภัย

    # ==========================================
    # STAGE REFACTORING (ASYNC / GOVERNED)
    # ==========================================

    async def _semantic_understanding_stage(
        self, context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """สเตจ 1: ดึง Intent และตีความบริบทแบบ Async"""
        if not await self._enforce_governance(context, "semantic_understanding"):
            raise PermissionError("Stage semantic_understanding blocked by policy.")

        logger.debug(f"[{session_id}] Stage 1: Semantic Understanding")
        if "semantic" in self.agents:
            # รันผ่านระบบ Agent Message Contract
            response = await self.agents["semantic"].run(context)
            context["semantic_output"] = (
                response.content if hasattr(response, "content") else response
            )
        return context

    async def _reasoning_stage(
        self, context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """สเตจ 2: คิดวิเคราะห์เชิงตรรกะเหตุและผล"""
        if not await self._enforce_governance(context, "reasoning"):
            raise PermissionError("Stage reasoning blocked by policy.")

        logger.debug(f"[{session_id}] Stage 2: Reasoning")
        if "reasoning" in self.agents:
            response = await self.agents["reasoning"].run(context)
            context["reasoning_output"] = (
                response.content if hasattr(response, "content") else response
            )
        return context

    async def _hypothesis_generation_stage(
        self, context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """สเตจ 3: สร้างสมมติฐานแบบขนาน (Parallel Processing)"""
        if not await self._enforce_governance(context, "hypothesis_generation"):
            raise PermissionError("Stage hypothesis_generation blocked by policy.")

        logger.debug(f"[{session_id}] Stage 3: Hypothesis Generation")

        # ค้นหาข้อมูลย่อยหรือแตกชุดคำถามย่อยเพื่อประมวลผลขนานกัน
        if "hypothesis_pool" in self.agents:
            agents_pool = self.agents["hypothesis_pool"]  # List ของ Hypothesis Agents
            tasks = [agent.run(context) for agent in agents_pool]

            # รันแบบขนานกันจริงผ่าน asyncio.gather
            results = await asyncio.gather(*tasks)
            context["hypotheses"] = [
                r.content if hasattr(r, "content") else r for r in results
            ]
        return context

    async def _feedback_analysis_stage(
        self, context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """สเตจ 4: ตรวจสอบย้อนกลับ (Critique & Reflection) เพื่อหาจุดบกพร่อง"""
        if not await self._enforce_governance(context, "feedback_analysis"):
            raise PermissionError("Stage feedback_analysis blocked by policy.")

        logger.debug(f"[{session_id}] Stage 4: Feedback Analysis")
        if "critique" in self.agents:
            response = await self.agents["critique"].run(context)
            context["critiques"] = (
                response.content if hasattr(response, "content") else response
            )
        return context

    async def _memory_update_stage(
        self, context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """สเตจ 5: ซิงค์บันทึกเหตุการณ์ลงฐานความจำระบบ"""
        if not await self._enforce_governance(context, "memory_update"):
            raise PermissionError("Stage memory_update blocked by policy.")

        logger.debug(f"[{session_id}] Stage 5: Memory Update")
        if "memory" in self.agents:
            await self.agents["memory"].run(context)

        # ยิงสถานะ Event Metric เพื่อแจ้งระบบภายนอกผ่าน Telemetry
        if hasattr(runtime_events, "emit"):
            runtime_events.emit(
                "pipeline_completed", {"session_id": session_id, "status": "success"}
            )

        return context
