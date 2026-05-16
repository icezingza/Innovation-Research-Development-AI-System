"""
Thai Regulatory Guardrail - Policy Enforcement Engine
ป้องกันการตอบที่สุ่มเสี่ยงผิดกฎหมายไทย (PDPA, ธปท., กลต.)
"""

import re
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class RegulatoryViolation(Exception):
    """ยกเมื่อข้อความละเมิดกฎระเบียบ"""
    def __init__(self, rule_id: str, message: str, severity: str = "HIGH"):
        self.rule_id = rule_id
        self.message = message
        self.severity = severity
        super().__init__(f"[{severity}] {rule_id}: {message}")

class RegulatoryGuard:
    def __init__(self, rules_path: str = None):
        if rules_path is None:
            rules_path = Path(__file__).parent / "rules"
        self.rules_path = Path(rules_path)
        self.rules: List[Dict] = []
        self._load_rules()

    def _load_rules(self):
        """โหลดกฎทั้งหมดจากไฟล์ YAML"""
        if not self.rules_path.exists():
            logger.warning(f"Rules directory not found: {self.rules_path}")
            return
            
        for rule_file in sorted(self.rules_path.glob("*.yaml")):
            with open(rule_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and "rules" in data:
                    self.rules.extend(data["rules"])
                    logger.info(f"Loaded {len(data['rules'])} rules from {rule_file.name}")

    def check(self, text: str, context: Optional[Dict] = None) -> bool:
        """
        ตรวจสอบข้อความว่าผิดกฎหรือไม่
        - ถ้าผิด → raise RegulatoryViolation
        - ถ้าผ่าน → return True
        """
        violations = []

        for rule in self.rules:
            if not rule.get("enabled", True):
                continue

            # ตรวจ Pattern Match
            if "patterns" in rule:
                for pattern in rule["patterns"]:
                    flags = re.IGNORECASE if rule.get("case_sensitive", False) == False else 0
                    if re.search(pattern, text, flags):
                        violations.append(rule)
                        break

            # ตรวจ Keyword Match
            if "keywords" in rule:
                for keyword in rule["keywords"]:
                    if keyword.lower() in text.lower():
                        violations.append(rule)
                        break

            # ตรวจ Forbidden Phrases
            if "forbidden_phrases" in rule:
                for phrase in rule["forbidden_phrases"]:
                    if phrase.lower() in text.lower():
                        violations.append(rule)
                        break

        if violations:
            # เรียงตาม severity → ส่ง violation ที่รุนแรงที่สุด
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            worst = min(violations, key=lambda v: severity_order.get(v.get("severity", "LOW"), 99))

            raise RegulatoryViolation(
                rule_id=worst["id"],
                message=worst.get("message", "Content violates regulatory rules"),
                severity=worst.get("severity", "HIGH")
            )

        return True

    def get_applicable_rules(self, domain: str) -> List[Dict]:
        """ดึงกฎที่เกี่ยวข้องกับโดเมนที่กำหนด (finance, health, legal)"""
        return [r for r in self.rules if domain in r.get("domains", []) or "all" in r.get("domains", [])]

# Singleton instance
_regulatory_guard_instance = None

def get_regulatory_guard() -> RegulatoryGuard:
    global _regulatory_guard_instance
    if _regulatory_guard_instance is None:
        _regulatory_guard_instance = RegulatoryGuard()
    return _regulatory_guard_instance
