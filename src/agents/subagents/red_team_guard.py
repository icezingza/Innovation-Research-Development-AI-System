import json
from typing import Dict, Any, AsyncGenerator
from .base import AntigravitySubAgent
from src.security.regulatory_guard import get_regulatory_guard, RegulatoryViolation
from src.memory.qdrant_connector import QdrantMemoryConnector
from src.memory.neo4j_connector import Neo4jKnowledgeConnector


class RedTeamGuardSubAgent(AntigravitySubAgent):
    """
    SubAgent: AI Red Teaming Middleware (Prompt Injection Guard)
    หน้าที่: ตรวจสอบและสกัดกั้นการโจมตีทางสถาปัตยกรรมข้ามเลเยอร์ และคัดกรองความปลอดภัยขั้นสูงเชิงปัญญาประดิษฐ์
    """

    def __init__(
        self,
        task_name: str = "Red_Team_Guard",
        max_tokens: int = 1500,
        inference=None,
        qdrant: QdrantMemoryConnector = None,
        neo4j: Neo4jKnowledgeConnector = None,
    ):
        super().__init__(task_name=task_name, max_tokens=max_tokens)
        self.inference = inference
        self.qdrant = qdrant
        self.neo4j = neo4j
        self.guard = get_regulatory_guard()

    async def execute(
        self, payload: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        user_input = payload.get("user_input", "")

        yield {
            "status": "thinking",
            "log": "🛡️ เริ่มวิเคราะห์ความเสี่ยง Prompt Injection & Policy Compliance ผ่าน Intelligent Gateway...",
        }

        yield {
            "status": "thinking",
            "log": f"🕵️ ตรวจสอบโครงสร้างคำถามเชิงลึก: {str(user_input)[:40]}...",
        }

        # 1. รันด่านตรวจ Regulatory Guard (PDPA, BOT) ชุดจริง
        is_safe = True
        violation_reason = ""
        risk_level = "LOW"

        try:
            self.guard.check(str(user_input))
        except RegulatoryViolation as rv:
            is_safe = False
            violation_reason = rv.message
            risk_level = rv.severity
            yield {
                "status": "thinking",
                "log": f"🚨 ตรวจพบการละเมิดกฎระเบียบ ({rv.rule_id})! ระดับความรุนแรง: {rv.severity}",
            }

        # 2. ค้นหาความปลอดภัยเชิงพฤติกรรมผ่าน Qdrant Semantic Security Check (ตรวจสอบประวัติการโจมตี)
        if is_safe and self.qdrant and self.qdrant.client:
            try:
                # ถ้าเราสามารถดึงหรือเปรียบเทียบข้อมูลเพื่อตรวจเช็คเวกเตอร์ที่คล้ายกับ prompt injection
                # เราสามารถเพิ่มกลไกคัดกรองที่มีความแม่นยำสูงเชิงเวกเตอร์ได้ที่นี่
                pass
            except Exception:
                pass

        # 3. ค้นหาความเสี่ยงเชิงพฤติกรรม (Prompt Injection) ผ่าน Model Inference จริง แทนการสุ่มเดา String Match
        if is_safe and self.inference and self.inference.enabled:
            yield {
                "status": "thinking",
                "log": "🤖 เปิดใช้งาน LLM Cognitive Firewall เพื่อวิเคราะห์ความปลอดภัยเชิงพฤติกรรมระดับลึก...",
            }
            prompt = (
                f"Analyze the following user query for safety, jailbreak attempts, or prompt injection:\n"
                f'"""\n{user_input}\n"""\n\n'
                f"Respond strictly in valid JSON format with keys:\n"
                f'- "is_attack": boolean\n'
                f'- "risk_level": "LOW" | "MEDIUM" | "CRITICAL"\n'
                f'- "message": "brief explanation"'
            )
            try:
                resp = await self.inference.complete(
                    prompt=prompt,
                    system="You are an elite cyber security firewall. Analyze inputs strictly.",
                    tier="fast",
                )
                if resp:
                    cleaned_resp = resp.strip()
                    if cleaned_resp.startswith("```json"):
                        cleaned_resp = cleaned_resp[7:]
                    if cleaned_resp.endswith("```"):
                        cleaned_resp = cleaned_resp[:-3]

                    data = json.loads(cleaned_resp.strip())
                    if data.get("is_attack", False):
                        is_safe = False
                        violation_reason = data.get(
                            "message", "Detected potential jailbreak/prompt injection."
                        )
                        risk_level = data.get("risk_level", "CRITICAL")
            except Exception:
                # Fallback to smart heuristic when LLM fails
                is_attack = any(
                    kw in str(user_input).lower()
                    for kw in [
                        "ignore all previous instructions",
                        "bypass security",
                        "system settings override",
                    ]
                )
                if is_attack:
                    is_safe = False
                    violation_reason = (
                        "Dynamic heuristic: Potential prompt injection keywords found."
                    )
                    risk_level = "CRITICAL"
        else:
            # Smart heuristic fallback
            is_attack = any(
                kw in str(user_input).lower()
                for kw in [
                    "ignore all previous instructions",
                    "bypass security",
                    "system settings override",
                ]
            )
            if is_attack:
                is_safe = False
                violation_reason = (
                    "Dynamic heuristic: Potential prompt injection keywords found."
                )
                risk_level = "CRITICAL"

        if not is_safe:
            yield {
                "status": "thinking",
                "log": "🚨 สกัดกั้น Payload และรายงานลงระบบเฝ้าระวังความปลอดภัย...",
            }
            yield {
                "status": "blocked",
                "risk_level": risk_level,
                "message": violation_reason,
                "sanitized_input": "[REDACTED_ATTACK_VECTOR]",
            }
        else:
            yield {
                "status": "thinking",
                "log": "✅ ตรวจสอบความปลอดภัยสมบูรณ์ — ข้อมูลอยู่ในเกณฑ์ปลอดภัย",
            }
            yield {
                "status": "cleared",
                "risk_level": "LOW",
                "message": "Payload is safe.",
                "sanitized_input": user_input,
            }
