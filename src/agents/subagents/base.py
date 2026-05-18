import uuid
from typing import Dict, Any, AsyncGenerator


class AntigravitySubAgent:
    """
    Base Class สำหรับ SubAgent ที่รันบน Antigravity Runtime
    เน้นความเร็ว (Stateless), ควบคุม Budget, และเชื่อมต่อ SSE Streaming
    """

    def __init__(self, task_name: str, max_tokens: int = 1500, max_depth: int = 3):
        self.task_id = str(uuid.uuid4())
        self.task_name = task_name

        # FinOps & Guardrails Limits
        self.max_tokens = max_tokens
        self.max_depth = max_depth
        self.current_tokens = 0
        self.current_depth = 0

        # Ephemeral Memory (Stateless - จะถูกทำลายทิ้งเมื่อจบงาน)
        self.ephemeral_memory: Dict[str, Any] = {}

    async def _enforce_guardrails(self, payload: Dict[str, Any] = None) -> None:
        """ตรวจสอบความปลอดภัยและขีดจำกัดทรัพยากร (Policy Enforcer & Circuit Breaker)"""
        # 1. FinOps Limits check
        if self.current_tokens > self.max_tokens:
            raise ResourceWarning(
                f"[FinOps Guard] {self.task_name} ใช้ Token เกินขีดจำกัด ({self.max_tokens})!"
            )

        # 2. Logic Guard / Recursion check
        if self.current_depth > self.max_depth:
            raise RecursionError(
                f"[Logic Guard] {self.task_name} ทำงานวนลูปเกินขีดจำกัด ({self.max_depth})!"
            )

        # 3. Thai Regulatory Check via PolicyEnforcer
        if payload:
            user_input = (
                payload.get("user_input")
                or payload.get("proposed_solution")
                or payload.get("query")
            )
            if user_input:
                try:
                    from src.governance.policy_enforcer import PolicyEnforcer
                    from src.protocols.agent_message import AgentMessage, MessageType

                    msg = AgentMessage(
                        sender_id=f"subagent_{self.task_name}",
                        message_type=MessageType.REASONING,
                        content={"text": str(user_input)},
                    )

                    enforcer = PolicyEnforcer()
                    await enforcer.enforce(msg)
                except (ImportError, Exception) as e:
                    # Allow graceful passing if services aren't fully initialized, but log or raise if policy violated
                    if "Policy denied" in str(e):
                        raise e

    async def execute(
        self, context_payload: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Core Execution แบบ Stateless และ Stream ผลลัพธ์กลับแบบ Real-time"""
        try:
            self.current_depth += 1
            await self._enforce_guardrails(context_payload)

            # 1. Stream สถานะเริ่มต้นกลับไปที่ Supervisor
            yield {
                "task_id": self.task_id,
                "status": "processing",
                "message": f"Starting task: {self.task_name}",
            }

            # 2. นำ Context ขึ้นมาประมวลผล (Working Memory)
            self.ephemeral_memory.update(context_payload)

            # (Mock) การประมวลผลของ Agent ย่อย เช่น ดึง Qdrant หรือสรุปข้อมูล
            insight = await self._process_task()

            # 3. Stream เฉพาะ "Key Insights" กลับไป (เพื่อประหยัด Token ของระบบหลัก)
            yield {"task_id": self.task_id, "status": "completed", "insight": insight}

        except Exception as e:
            yield {"task_id": self.task_id, "status": "failed", "error": str(e)}

        finally:
            # 4. ทำลายตัวเองเพื่อคืนทรัพยากรให้ระบบ (Zero-friction)
            self._teardown()

    async def _process_task(self) -> str:
        """ฟังก์ชันจำลองการทำงานเฉพาะจุดของ SubAgent"""
        self.current_tokens += 250  # จำลองการใช้ Token
        return f"Synthesized insight from {self.task_name}"

    def _teardown(self) -> None:
        """ล้างความจำและตัดการเชื่อมต่อทั้งหมด"""
        import logging

        logging.getLogger(__name__).info(
            f"[FinOps Telemetry] Agent '{self.task_name}' ({self.task_id}) consumed {self.current_tokens} tokens."
        )
        self.ephemeral_memory.clear()
        self.current_tokens = 0
        self.current_depth = 0
