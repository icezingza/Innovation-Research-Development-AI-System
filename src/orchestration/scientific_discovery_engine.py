import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

# นำเข้าระบบประสานงานและโครงสร้างคลังข้อมูลเดิมของระบบ
from src.orchestration.agent_coordinator import AgentCoordinator
from src.infrastructure.event_bus import RuntimeEventBus, RuntimeEvent
from src.memory.research_memory import ResearchMemory

logger = logging.getLogger(__name__)


class DiscoveryTask(BaseModel):
    """โมเดลข้อมูลโจทย์วิจัยทางวิทยาศาสตร์"""

    task_id: str
    scientific_goal: str
    domain: str
    iterations: int = 3  # จำนวนรอบในการพัฒนาสมมติฐาน (Evolution Generation)


class ScientificDiscoveryEngine:
    """Engine ควบคุมลูปวิจัยและวิเคราะห์การค้นพบทางวิทยาศาสตร์อัตโนมัติ"""

    def __init__(
        self,
        coordinator: AgentCoordinator,
        event_bus: RuntimeEventBus,
        memory_store: Optional[ResearchMemory] = None,
    ):
        self.coordinator = coordinator
        self.event_bus = event_bus
        self.memory_store = memory_store
        self._active_loops: Dict[str, bool] = {}

    async def execute_discovery_loop(self, task: DiscoveryTask) -> Dict[str, Any]:
        """เริ่มลูปการวิจัย ค้นหา และวิพากษ์สมมติฐานแบบอัตโนมัติตาม Generation"""
        session_id = f"discovery-{task.task_id}"
        self._active_loops[session_id] = True

        logger.info(
            f"[{session_id}] เริ่มต้นลูปวิจัยโดเมน: {task.domain} เป้าหมาย: {task.scientific_goal}"
        )

        current_goal = task.scientific_goal
        discovery_history: List[Dict[str, Any]] = []

        # ทำกระบวนการวิจัยแบบวิวัฒนาการสมมติฐาน (Hypothesis Evolution Loop)
        for gen in range(1, task.iterations + 1):
            if not self._active_loops.get(session_id, False):
                logger.warning(f"[{session_id}] ลูปวิจัยถูกสั่งหยุดก่อนกำหนด")
                break

            logger.info(
                f"[{session_id}] เริ่มการประมวลผล Generation {gen}/{task.iterations}"
            )

            # เรียกใช้ Swarm Agents ผ่าน Coordinator ครบ Loop (Goal -> Sub-questions -> Parallel Hypotheses -> Critique -> Synthesis)
            result = await self.coordinator.coordinate(
                goal=current_goal, session_id=f"{session_id}-gen-{gen}"
            )

            # บันทึกประวัติและผลลัพธ์ของการค้นพบในรอบนั้น ๆ
            gen_report = {
                "generation": gen,
                "hypotheses_generated": result.hypotheses,
                "critiques_received": result.critiques,
                "synthesis_outcome": result.synthesis,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            discovery_history.append(gen_report)

            # ยิง Event แจ้งเตือนระบบการทำดัชนีความรู้ (Knowledge Civilization Engine)
            await self._emit_discovery_event(
                session_id, "generation_completed", gen_report
            )

            # ปรับปรุงเป้าหมายหรือคำถามในรอบถัดไปโดยอิงจาก Feedback ในรอบก่อน (Self-Improvement Loop)
            if result.synthesis and "next_research_question" in result.synthesis:
                current_goal = result.synthesis["next_research_question"]
                logger.info(
                    f"[{session_id}] ปรับเปลี่ยนทิศทางวิจัย Gen {gen + 1} เป็น: {current_goal}"
                )
            else:
                # กรณีคัดกรองแล้วพบว่าสมมติฐานนิ่งหรืออิ่มตัวแล้ว ให้จบสเตจการค้นพบ
                logger.info(f"[{session_id}] สมมติฐานและผลลัพธ์เริ่มนิ่ง สิ้นสุดลูปอัตโนมัติ")
                break

        final_discovery = {
            "task_id": task.task_id,
            "session_id": session_id,
            "final_synthesis": discovery_history[-1]["synthesis_outcome"]
            if discovery_history
            else {},
            "history": discovery_history,
        }

        # บันทึกข้อมูลระยะยาวลงคลังความรู้ระบบ (ถ้ามี)
        if self.memory_store:
            # สมมติว่ามี method save_discovery หรือคล้ายกันใน ResearchMemory
            if hasattr(self.memory_store, "save_discovery"):
                await self.memory_store.save_discovery(final_discovery)

        return final_discovery

    async def stop_loop(self, session_id: str) -> None:
        """สั่งหยุดลูปการค้นพบที่กำลังทำงานอยู่"""
        if session_id in self._active_loops:
            self._active_loops[session_id] = False
            logger.info(f"[{session_id}] ส่งสัญญาณหยุดทำงานเรียบร้อยค่ะ")

    async def _emit_discovery_event(
        self, session_id: str, event_type: str, payload: dict
    ) -> None:
        """ยิง Event เข้า Bus ส่วนกลางเพื่อส่งพิกัดการทำงานให้ระบบ Telemetry / Dashboard"""
        if self.event_bus:
            await self.event_bus.publish(
                RuntimeEvent(
                    topic=f"scientific_discovery:{event_type}",
                    source_agent_id="scientific_discovery_engine",
                    payload={"session_id": session_id, "data": payload},
                )
            )
