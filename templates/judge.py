import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.inference.router import InferenceRouter
from src.inference.base_provider import CompletionRequest

logger = logging.getLogger(__name__)


class SynthesisJudgeScore(BaseModel):
    """ผลการประเมินความถูกต้องของบทสรุปงานวิจัยโดย LLM-as-a-Judge"""

    accuracy_score: float = Field(
        ..., ge=0, le=1, description="ความถูกต้องเชิงข้อเท็จจริงเทียบกับสมมติฐานต้นทาง"
    )
    comprehensiveness_score: float = Field(
        ..., ge=0, le=1, description="ความครบถ้วนของเนื้อหา"
    )
    contradiction_resolution_score: float = Field(
        ..., ge=0, le=1, description="การจัดการข้อขัดแย้งที่ถูกตรวจพบ"
    )
    overall_score: float = Field(..., ge=0, le=1, description="คะแนนรวมเชิงคุณภาพ")
    rationale: str = Field(..., description="เหตุผลประกอบการให้คะแนนอย่างละเอียด")
    missing_insights: List[str] = Field(
        default_factory=list, description="ประเด็นสำคัญที่ตกหล่นไป"
    )
    detected_hallucinations: List[str] = Field(
        default_factory=list, description="ข้อมูลที่ไม่มีแหล่งอ้างอิงหรือสร้างขึ้นเอง"
    )


class CognitiveJudge:
    """
    NamoNexus Sovereign Auditor: ทำหน้าที่ประเมินคุณภาพของ SynthesisStatement
    เพื่อให้มั่นใจว่าระบบไม่เกิด Hallucination และตอบโจทย์เป้าหมายการวิจัย
    """

    def __init__(self, router: InferenceRouter, judge_model: Optional[str] = None):
        self.router = router
        self.judge_model = judge_model or "gpt-4o"  # แนะนำให้ใช้โมเดลตัวท็อปสำหรับการตัดสิน

    def _build_prompt(
        self, goal: str, hypotheses: List[Dict], critiques: List[Dict], synthesis: Dict
    ) -> str:
        """สร้าง Prompt สำหรับการตัดสิน (Judgement Prompt)"""
        hyp_context = "\n".join(
            [
                f"- {h.get('statement')} (Conf: {h.get('confidence')})"
                for h in hypotheses
            ]
        )
        crit_context = "\n".join(
            [
                f"- {c.get('contradictions_detected')}"
                for c in critiques
                if c.get("contradictions_detected")
            ]
        )

        return f"""
        You are the 'Sovereign Auditor' of the NamoNexus Research Engine. 
        Your task is to perform a rigorous audit of a research synthesis.

        [RESEARCH GOAL]
        {goal}

        [SOURCE HYPOTHESES]
        {hyp_context}

        [PEER CRITIQUES / CONTRADICTIONS]
        {crit_context}

        [GENERATED SYNTHESIS]
        {synthesis.get("synthesis_statement")}

        CRITICAL INSTRUCTIONS:
        1. Compare the synthesis against the hypotheses. Does it ignore any key findings?
        2. Check the critiques. Did the synthesis resolve or acknowledge the identified contradictions?
        3. Identify any 'Hallucinations' (claims made in the synthesis that are not present in any hypothesis).
        4. Provide an overall score based on scientific integrity.

        Respond strictly in JSON format matching the schema of SynthesisJudgeScore.
        """

    async def evaluate_synthesis(
        self, goal: str, hypotheses: List[Dict], critiques: List[Dict], synthesis: Dict
    ) -> SynthesisJudgeScore:
        """ประเมิน SynthesisStatement และคืนค่าเป็นคะแนนเชิงโครงสร้าง"""

        prompt = self._build_prompt(goal, hypotheses, critiques, synthesis)

        request = CompletionRequest(
            prompt=prompt,
            system="You are an expert scientific auditor specialized in reasoning trace analysis. Output JSON only.",
            temperature=0.1,  # ใช้ temp ต่ำเพื่อความแม่นยำ
            model=self.judge_model,
        )

        try:
            response = await self.router.complete(request)
            # รองรับทั้งการคืนค่าเป็น JSON string หรือ Dict
            data = (
                json.loads(response.content)
                if isinstance(response.content, str)
                else response.content
            )

            judge_result = SynthesisJudgeScore(**data)

            logger.info(
                "synthesis_audit_complete",
                extra={
                    "overall_score": judge_result.overall_score,
                    "hallucinations_found": len(judge_result.detected_hallucinations),
                },
            )
            return judge_result

        except Exception as e:
            logger.error(f"Failed to execute LLM-as-a-Judge: {str(e)}")
            # Fallback score ในกรณีที่ Judge ล่ม เพื่อไม่ให้ระบบหยุดทำงาน
            return SynthesisJudgeScore(
                accuracy_score=0.5,
                comprehensiveness_score=0.5,
                contradiction_resolution_score=0.5,
                overall_score=0.5,
                rationale=f"Audit failed due to error: {str(e)}",
            )
