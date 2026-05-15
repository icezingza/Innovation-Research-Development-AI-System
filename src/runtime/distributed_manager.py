import logging
import os
from typing import Any, Dict, Optional

# ดึงระบบอินฟราสตรักเจอร์ Event Bus และ Worker Pool มาสเกลคลาวด์
from src.infrastructure.redis_event_bus import RedisEventBus
from src.runtime.worker_pool import WorkerPool
from src.orchestration.agent_coordinator import AgentCoordinator

logger = logging.getLogger(__name__)

class DistributedScalingManager:
    """ผู้บริหารจัดการอินฟราสตรักเจอร์และการกระจายโหลดงานเอเจนต์ข้ามคลัสเตอร์คลาวด์"""

    def __init__(
        self,
        coordinator: AgentCoordinator,
        redis_url: Optional[str] = None,
        max_parallel_workers: int = 10
    ):
        self.coordinator = coordinator
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.max_parallel_workers = max_parallel_workers
        self.redis_bus: Optional[RedisEventBus] = None
        self.worker_pool: Optional[WorkerPool] = None
        self._is_scaled_up = False

    async def initialize_distributed_cluster(self) -> None:
        """เชื่อมต่อระบบเข้ากับโครงข่าย Redis และเปิดการทำงานของ Worker Nodes"""
        logger.info("กำลังผูก Cognitive Pipeline เข้ากับระบบกระจายโหลดส่วนกลาง...")
        
        try:
            # 1. ติดตั้งและเริ่มระบบ Redis Event Bus สำหรับรับส่งข้อมูลข้ามโหนด
            self.redis_bus = RedisEventBus(redis_url=self.redis_url)
            await self.redis_bus.connect()
            
            # เชื่อมต่อ Event Bus ตัวกลางเข้ากับ Agent Coordinator ตัวหลัก
            self.coordinator.event_bus = self.redis_bus
            logger.info("✅ เชื่อมต่อ Redis Event Bus ข้ามคลัสเตอร์สำเร็จ")

            # 2. ปรับแต่งโครงสร้างคลังประมวลผลให้พร้อมรับโหลดขนาดใหญ่ (Worker Pool Scaling)
            self.worker_pool = WorkerPool(max_workers=self.max_parallel_workers)
            await self.worker_pool.start()
            logger.info(f"🚀 สตาร์ท Worker Pool สำเร็จ รองรับสูงสุด {self.max_parallel_workers} Workers ขนานกัน")
            
            self._is_scaled_up = True
            
        except Exception as e:
            logger.error(f"❌ ไม่สามารถเริ่มต้นระบบกระจายโหลดได้: {str(e)}")
            raise e

    async def dispatch_scale_task(self, goal: str, session_id: str) -> Dict[str, Any]:
        """ยิงงานวิจัยเข้าสู่คลัสเตอร์คลาวด์แบบกระจายคิวการคิด"""
        if not self._is_scaled_up:
            raise RuntimeError("กรุณาเรียก initialize_distributed_cluster ก่อนเริ่มกระจายงานค่ะ")

        logger.info(f"[{session_id}] บรรจุเป้าหมายลงคิวงานประมวลผลข้ามเครื่อง: {goal}")

        # ใช้ Worker Pool ขนส่ง Task การคิดของ Coordinator ไปยังทรัพยากรว่างบนโหนด
        task_future = await self.worker_pool.submit(
            self.coordinator.coordinate,
            goal=goal,
            session_id=session_id
        )
        
        # รอรับผลการประมวลผลที่ผ่านการคัดกรองร่วมกันมาแล้ว
        result = await task_future
        return result

    async def shutdown_cluster(self) -> None:
        """เคลียร์คิวและปิดการเชื่อมต่อทรัพยากรทั้งหมดเพื่อประหยัด Token และงบคลาวด์"""
        logger.info("กำลังเคลียร์สถานะระบบกระจายโหลด...")
        
        if self.worker_pool:
            await self.worker_pool.stop()
        if self.redis_bus:
            await self.redis_bus.disconnect()
            
        self._is_scaled_up = False
        logger.info("🔒 ปิดการทำงานคลัสเตอร์แบบกระจายตัวเรียบร้อยค่ะ")
