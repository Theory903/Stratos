"""Application Use Case: Generate Memo.

Synthesizes execution results into a strategic memo.
"""

from __future__ import annotations

import json
from stratos_orchestrator.domain.entities import (
    ConfidenceBand,
    ExecutionPlan,
    StrategicMemo,
    TaskStatus,
)
from stratos_orchestrator.domain.ports import LLMProvider


class GenerateMemoUseCase:
    """Generate final strategic memo from plan results."""

    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def execute(self, plan: ExecutionPlan, regime: str = "normal", stability: float = 1.0) -> StrategicMemo:
        # Collect results
        results_context = []
        for task in plan.tasks:
            if task.status == TaskStatus.COMPLETED:
                results_context.append(
                    f"Tool: {task.tool_name}\nArgs: {task.arguments}\nResult: {json.dumps(task.result)}"
                )
            elif task.status == TaskStatus.FAILED:
                results_context.append(
                    f"Tool: {task.tool_name}\nArgs: {task.arguments}\nError: {task.error}"
                )

        system_prompt = (
            "You are a Chief Investment Officer. Synthesize the provided tool outputs into a "
            "comprehensive Strategic Memo.\n"
            "Format Requirement:\n"
            "- Recommendation: Clear, actionable advice.\n"
            "- Confidence Score: 0.0 to 1.0\n"
            "- Scenario Tree: List of possible future scenarios and their probabilities/impacts.\n"
            "- Worst Case: What could go wrong?\n"
            "- Risk Band: Low, Medium, High, Extreme.\n"
        )
        
        user_prompt = (
            f"Query: {plan.query}\n\n"
            "Execution Results:\n" + "\n---\n".join(results_context)
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        schema = {
            "title": "StrategicMemo",
            "type": "object",
            "properties": {
                "recommendation": {"type": "string"},
                "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "scenario_tree": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "worst_case": {"type": "string"},
                "risk_band": {"type": "string"},
            },
            "required": ["recommendation", "confidence_score", "scenario_tree", "worst_case", "risk_band"],
        }

        try:
            output = await self.llm.generate_structured(messages, schema)
            
            return StrategicMemo(
                query=plan.query,
                plan_summary=plan.reasoning or "Task summary pending.",
                tasks=plan.tasks,
                confidence_band=ConfidenceBand.from_score(output.get("confidence_score", 0.5)),
                risk_policy_status="PASS",
                recommendation=output.get("recommendation", "No recommendation generated."),
                worst_case=output.get("worst_case", "Unknown"),
                risk_band=output.get("risk_band", "Medium"),
                system_regime=regime,
                regime_stability=stability,
                scenario_tree=output.get("scenario_tree", []),
            )
        except Exception:
            # Fallback
            return StrategicMemo(
                query=plan.query,
                plan_summary=plan.reasoning or "Task summary pending.",
                tasks=plan.tasks,
                confidence_band=ConfidenceBand.from_score(0.0),
                risk_policy_status="FAILED",
                recommendation="Failed to generate memo due to LLM error.",
                worst_case="System failure",
                risk_band="Unknown",
                system_regime=regime,
                regime_stability=stability,
                scenario_tree=[],
            )
