"""Chaos Agent API — manually trigger adversarial red-team runs and inspect learned rules."""

from fastapi import APIRouter, Depends, Request

from src.agents.chaos_agent import ChaosAgent, ChaosRunReport
from src.api.routes.auth import get_current_user
from src.security.chaos_rule_generator import ChaosRuleGenerator

router = APIRouter(prefix="/chaos", tags=["chaos"])


@router.post("/trigger", response_model=ChaosRunReport)
async def trigger_chaos_run(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> ChaosRunReport:
    """Run one full adversarial simulation against RegulatoryGuard.

    Attacks all prompts in the corpus, identifies misses, generates and persists
    new keyword rules from any missed prompts, and returns the full report.
    """
    audit_log = getattr(request.app.state, "audit_log", None)
    agent = ChaosAgent(audit_log=audit_log)
    return await agent.run()


@router.get("/corpus/learned")
async def get_learned_corpus(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return all rules learned by the ChaosAgent during past simulation runs."""
    generator = ChaosRuleGenerator()
    rules = generator.all_rules()
    return {"count": len(rules), "rules": rules}


@router.get("/corpus/stats")
async def get_corpus_stats(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return statistics about the current adversarial corpus and learned rules."""
    import yaml
    from pathlib import Path

    corpus_path = Path(__file__).resolve().parents[3] / "src" / "security" / "red_team_corpus.yaml"
    attack_count = 0
    control_count = 0
    if corpus_path.exists():
        with open(corpus_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        attack_count = len(data.get("attack_prompts", []))
        control_count = len(data.get("safe_controls", []))

    generator = ChaosRuleGenerator()
    learned_count = generator.rule_count()

    rules_path = Path(__file__).resolve().parents[3] / "src" / "security" / "rules"
    static_rule_files = len(list(rules_path.glob("*.yaml"))) if rules_path.exists() else 0

    return {
        "corpus": {
            "attack_prompts": attack_count,
            "safe_controls": control_count,
        },
        "rules": {
            "static_rule_files": static_rule_files,
            "learned_rules": learned_count,
        },
    }
