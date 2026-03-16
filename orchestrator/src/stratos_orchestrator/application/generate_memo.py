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

    async def execute(
        self,
        plan: ExecutionPlan,
        regime: str = "normal",
        stability: float = 1.0,
        *,
        intent: str = "research",
        role: str = "pm",
    ) -> StrategicMemo:
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
            f"You are STRATOS, a senior investment operator writing for a {role.upper()} workflow. "
            f"The user intent is {intent}. Use only the provided tool outputs. "
            "Do not invent prices, percentages, timing, PnL, probabilities, or risk metrics that are not supported by the tool results. "
            "If evidence is thin, say that directly and lower confidence.\n"
            "Output discipline:\n"
            "- Decision: one short sentence, imperative, answer-first.\n"
            "- Summary: 2 sentences max, plain English, no hype.\n"
            "- Recommendation: one clear action paragraph, no repetition.\n"
            "- Key Findings: 3 to 5 bullets, each concise.\n"
            "- Historical Context: 0 to 3 bullets, only if supported.\n"
            "- Portfolio Impact: 0 to 4 bullets, only if there is a portfolio angle.\n"
            "- Recommended Actions: 2 to 4 concrete next steps.\n"
            "- Watch Items: 2 to 4 things to monitor next.\n"
            "- Data Quality: 2 to 4 bullets on freshness, missing coverage, pending data, or synthetic/internal signals.\n"
            "- Evidence Blocks: 2 to 4 title/detail objects using the strongest facts from tools.\n"
            "- Confidence Score: 0.0 to 1.0 and calibrated to evidence completeness.\n"
            "- Scenario Tree: up to 3 scenarios. Keep each scenario compact.\n"
            "- Worst Case: one sentence.\n"
            "- Risk Band: exactly one of Low, Medium, High, Extreme.\n"
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
                "decision": {"type": "string"},
                "recommendation": {"type": "string"},
                "summary": {"type": "string"},
                "key_findings": {"type": "array", "items": {"type": "string"}},
                "historical_context": {"type": "array", "items": {"type": "string"}},
                "portfolio_impact": {"type": "array", "items": {"type": "string"}},
                "recommended_actions": {"type": "array", "items": {"type": "string"}},
                "watch_items": {"type": "array", "items": {"type": "string"}},
                "data_quality": {"type": "array", "items": {"type": "string"}},
                "evidence_blocks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "detail": {"type": "string"},
                        },
                        "required": ["title", "detail"],
                    },
                },
                "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "scenario_tree": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "worst_case": {"type": "string"},
                "risk_band": {"type": "string"},
            },
            "required": [
                "decision",
                "summary",
                "recommendation",
                "key_findings",
                "historical_context",
                "portfolio_impact",
                "recommended_actions",
                "watch_items",
                "data_quality",
                "evidence_blocks",
                "confidence_score",
                "scenario_tree",
                "worst_case",
                "risk_band",
            ],
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
                intent=intent,
                role=role,
                decision=output.get("decision", ""),
                summary=output.get("summary", ""),
                key_findings=output.get("key_findings", []),
                historical_context=output.get("historical_context", []),
                portfolio_impact=output.get("portfolio_impact", []),
                recommended_actions=output.get("recommended_actions", []),
                watch_items=output.get("watch_items", []),
                data_quality=output.get("data_quality", []),
                evidence_blocks=output.get("evidence_blocks", []),
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
                intent=intent,
                role=role,
                decision="Hold until the agent can produce a grounded memo.",
                summary="Failed to generate structured summary.",
                key_findings=[],
                historical_context=[],
                portfolio_impact=[],
                recommended_actions=[],
                watch_items=[],
                data_quality=["Memo generation failed before evidence could be summarized."],
                evidence_blocks=[],
            )
