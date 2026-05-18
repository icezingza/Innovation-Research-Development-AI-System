import uuid
from typing import Any

from src.agents.base_agent import BaseAgent
from src.infrastructure.event_bus import RuntimeEvent, RuntimeEventBus

# Define local well-known topic constant
TOPIC_FORECAST_GENERATED = "forecast.generated"


class FuturistAgent(BaseAgent):
    """Cognitive agent designed for Technology Forecasting and Scenario Modeling.

    Operates in two modes:
      - Heuristic: No inference router. Uses robust rule-based baseline trend extrapolation.
      - LLM-augmented: Uses the Inference Router to construct three future scenarios
        (Optimistic, Pessimistic, Most Likely) along with timeline milestones
        and early emergence signals.

    Fulfills Phase 4 (Futurist Agent) and Phase 5 (Scenario Modeling) requirements.
    """

    def __init__(
        self,
        inference_router: Any | None = None,
        event_bus: RuntimeEventBus | None = None,
    ) -> None:
        super().__init__()
        self._inference = inference_router
        self._bus = event_bus

    async def perceive(self, context: dict[str, Any]) -> dict[str, Any]:
        """Extract the future forecasting target, prior trend data, and target timeframe."""
        question = str(context.get("question", ""))
        timeframe_years = int(context.get("timeframe_years", 10))
        prior_trends = list(context.get("prior_trends", []))

        return {
            "question": question,
            "timeframe_years": timeframe_years,
            "prior_trends": prior_trends,
        }

    async def reason(self, perception: dict[str, Any]) -> dict[str, Any]:
        """Perform scenario modeling and forecast the future path of the target technology."""
        question = perception["question"]
        years = perception["timeframe_years"]

        # Default rule-based heuristic scenarios
        scenarios = {
            "optimistic": f"Exponential growth of: '{question}' leading to widespread adaptation within {years} years.",
            "pessimistic": f"Regulatory hurdles and high cost slow down progress of: '{question}' significantly.",
            "most_likely": f"Gradual industry adoption of: '{question}', maturing in the latter half of the {years}-year cycle.",
        }
        timeline = [
            {
                "phase": "Early Adoption",
                "timeframe": "Years 1-3",
                "milestone": "Niche deployment in enterprise segments.",
            },
            {
                "phase": "Scaling & Maturity",
                "timeframe": "Years 4-7",
                "milestone": "Mass commoditization and price reduction.",
            },
            {
                "phase": "Ubiquitous Presence",
                "timeframe": f"Years 8-{years}",
                "milestone": "Seamless integration into daily life.",
            },
        ]
        signals = [
            "Increased academic citations",
            "Surging venture capital funding",
            "Talent migration towards sector",
        ]
        confidence = 0.65

        # If LLM capability is available, generate extremely realistic predictions
        if self._inference is not None and self._inference.enabled:
            prompt = (
                f"You are a visionary technological futurist and complexity scientist.\n"
                f"Analyze the future evolution of: '{question}' over a {years}-year horizon.\n"
                f"Generate a highly detailed, professional scenario forecast. Follow this JSON format precisely:\n"
                f"{{\n"
                f'  "optimistic": "Detail the best-case breakthrough scenario",\n'
                f'  "pessimistic": "Detail the worst-case stagnation/barrier scenario",\n'
                f'  "most_likely": "Detail the pragmatically balanced, highly probable scenario",\n'
                f'  "timeline": [\n'
                f'    {{"phase": "Phase name", "timeframe": "Years X-Y", "milestone": "Key breakthrough"}}\n'
                f"  ],\n"
                f'  "emergence_signals": ["Signal A", "Signal B"],\n'
                f'  "confidence_rating": 0.85\n'
                f"}}"
            )
            llm_output = await self._inference.complete(
                prompt=prompt,
                system=(
                    "You are a professional research agent specializing in technology forecasting, "
                    "complexity science, and scenario modeling. Respond ONLY with valid JSON matching the schema."
                ),
            )
            if llm_output:
                try:
                    import json

                    parsed = json.loads(llm_output.strip())
                    scenarios = {
                        "optimistic": parsed.get("optimistic", scenarios["optimistic"]),
                        "pessimistic": parsed.get(
                            "pessimistic", scenarios["pessimistic"]
                        ),
                        "most_likely": parsed.get(
                            "most_likely", scenarios["most_likely"]
                        ),
                    }
                    if "timeline" in parsed and isinstance(parsed["timeline"], list):
                        timeline = parsed["timeline"]
                    if "emergence_signals" in parsed and isinstance(
                        parsed["emergence_signals"], list
                    ):
                        signals = parsed["emergence_signals"]
                    confidence = float(parsed.get("confidence_rating", confidence))
                except Exception:
                    # Fallback to defaults if LLM outputs invalid JSON structure
                    pass

        return {
            "question": question,
            "target_horizon_years": years,
            "scenarios": scenarios,
            "timeline": timeline,
            "emergence_signals": signals,
            "confidence_rating": confidence,
        }

    async def act(self, reasoning: dict[str, Any]) -> dict[str, Any]:
        """Publish the future forecast event and output structured prediction results."""
        scenarios = reasoning["scenarios"]
        timeline = reasoning["timeline"]
        signals = reasoning["emergence_signals"]

        result = {
            "forecast_id": str(uuid.uuid4()),
            "question": reasoning["question"],
            "target_horizon_years": reasoning["target_horizon_years"],
            "scenarios": scenarios,
            "timeline": timeline,
            "emergence_signals": signals,
            "confidence_rating": reasoning["confidence_rating"],
        }

        # Wire communication dynamically through the Event Bus
        if self._bus is not None:
            await self._bus.publish(
                RuntimeEvent(
                    topic=TOPIC_FORECAST_GENERATED,
                    source_agent_id=self.agent_id,
                    payload={
                        "question": reasoning["question"],
                        "forecast_id": result["forecast_id"],
                        "most_likely_path": scenarios["most_likely"],
                        "confidence_rating": reasoning["confidence_rating"],
                    },
                )
            )

        return result
