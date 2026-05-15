import logging
from typing import Any, Dict, Optional

# นำเข้าโครงสร้าง Inference Provider เดิมของระบบ
from src.inference.base_provider import BaseProvider
from src.inference.ollama_provider import OllamaProvider
from src.governance.audit_log import GovernanceAuditLog

logger = logging.getLogger(__name__)

class ResilientInferenceRouter:
    """Router ควบคุมการเรียกใช้ LLM พร้อมระบบสลับช่องสัญญาณสำรอง (Fallback) อัตโนมัติ"""

    def __init__(
        self, 
        primary_provider: BaseProvider, 
        fallback_provider: OllamaProvider,
        audit_logger: Optional[GovernanceAuditLog] = None
    ):
        self.primary = primary_provider
        self.fallback = fallback_provider
        self.audit_logger = audit_logger

    async def generate_with_fallback(
        self, 
        prompt: str, 
        session_id: str,
        system_instruction: Optional[str] = None, 
        **kwargs: Any
    ) -> str:
        """เรียกใช้งาน API หลัก หากเกิดปัญหาจะสลับมาใช้ Local Ollama ทันทีเพื่อความทนทานของระบบ"""
        try:
            logger.debug(f"[{session_id}] กำลังส่งคำสั่งไปยัง Primary Provider ({self.primary.__class__.__name__})")
            
            # เรียกใช้งาน Cloud API หลัก
            return await self.primary.complete(
                prompt=prompt, 
                system=system_instruction or "", 
                **kwargs
            )
            
        except Exception as primary_error:
            # ดักจับ Error ทุกรูปแบบ (Timeout, Rate Limit, API Down)
            logger.error(f"❌ [{session_id}] Primary Provider ล่มชั่วคราว: {str(primary_error)}")
            
            # บันทึกประวัติความผิดพลาดลงระบบ Audit เพื่อนำไปวิเคราะห์สถิติภายหลัง
            if self.audit_logger and hasattr(self.audit_logger, "log_fallback_event"):
                await self.audit_logger.log_fallback_event(session_id, str(primary_error))

            logger.warning(f"🔄 [{session_id}] กำลังเปิดใช้งานโครงข่ายสำรอง: เปลี่ยนเส้นทางไป Local Ollama ค่ะ")
            
            try:
                # สลับโหลดงานมาให้ Local Ollama ประมวลผลแทน (Resilience Mode)
                fallback_result = await self.fallback.complete(
                    prompt=prompt, 
                    system=system_instruction or "", 
                    **kwargs
                )
                logger.info(f"✅ [{session_id}] ดึงข้อมูลผ่าน Local Ollama Fallback สำเร็จ ระบบรันต่อได้ไม่หยุดชะงัก")
                return fallback_result
                
            except Exception as fallback_error:
                # กรณีฉุกเฉินระดับวิกฤต (Local Service ปิดอยู่ หรือ Memory เต็ม)
                logger.critical(f"🚨 [CRITICAL] [{session_id}] โครงข่ายสำรอง Ollama ล่มเช่นกัน: {str(fallback_error)}")
                raise RuntimeError(f"Inference Pipeline Failed entirely. Primary: {primary_error}, Fallback: {fallback_error}")
