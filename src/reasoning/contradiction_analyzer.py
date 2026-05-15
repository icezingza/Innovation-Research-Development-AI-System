import time

from pydantic import BaseModel

from src.telemetry.runtime_metrics import reasoning_latency
from src.telemetry.tracing import tracer


class Contradiction(BaseModel):
    statement_a: str
    statement_b: str
    contradiction_type: str
    severity: float


class ContradictionReport(BaseModel):
    statements: list[str]
    contradictions: list[Contradiction]
    is_consistent: bool


class ContradictionAnalyzer:
    """Detects logical contradictions in sets of statements."""

    _NEGATION_PAIRS: list[tuple[str, str]] = [
        ("is", "is not"),
        ("can", "cannot"),
        ("will", "will not"),
        ("always", "never"),
        ("all", "none"),
        ("must", "must not"),
        ("true", "false"),
        ("exists", "does not exist"),
    ]

    async def analyze(self, statements: list[str]) -> ContradictionReport:
        with tracer.start_as_current_span("reasoning.analyze_contradictions"):
            start = time.monotonic()
            contradictions = self._find_contradictions(statements)
            reasoning_latency.observe(time.monotonic() - start)
            return ContradictionReport(
                statements=statements,
                contradictions=contradictions,
                is_consistent=len(contradictions) == 0,
            )

    def _find_contradictions(self, statements: list[str]) -> list[Contradiction]:
        found: list[Contradiction] = []
        lowered = [s.lower() for s in statements]
        for i in range(len(lowered)):
            for j in range(i + 1, len(lowered)):
                contradiction_type = self._check_pair(lowered[i], lowered[j])
                if contradiction_type:
                    found.append(
                        Contradiction(
                            statement_a=statements[i],
                            statement_b=statements[j],
                            contradiction_type=contradiction_type,
                            severity=0.8,
                        )
                    )
        return found

    def _check_pair(self, a: str, b: str) -> str | None:
        for positive, negative in self._NEGATION_PAIRS:
            if positive in a and negative in b:
                return f"direct_negation({positive!r} vs {negative!r})"
            if negative in a and positive in b:
                return f"direct_negation({negative!r} vs {positive!r})"
        # Shared subject with opposing negation
        a_words = set(a.split())
        b_words = set(b.split())
        shared = a_words & b_words - {"a", "the", "is", "are", "of", "in"}
        if len(shared) >= 2 and ("not" in a_words) != ("not" in b_words):
            return "implicit_negation"
        return None
