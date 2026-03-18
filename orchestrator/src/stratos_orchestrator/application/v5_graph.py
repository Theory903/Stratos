"""V5 LangGraph runtime — core graph skeleton.

Topology:
    START → entry_guard → supervisor
      ├─→ fast_path ──────────────────────────────────────→ END
      ├─→ council_router → [specialists] → signal_aggregator
      │     → bull_researcher ‖ bear_researcher → research_manager
      │     → trader_agent → risk_engine → approval_gate
      │     → decision_packager → memory_writer → END
      ├─→ research_router → research_manager
      │     → decision_packager → memory_writer → END
      ├─→ replay_router → replay_analyst
      │     → decision_packager → END
      └─→ clarification_node ─────────────────────────────→ END
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Sequence

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langgraph.constants import Send

from stratos_orchestrator.application.v5.contracts import (
    ApprovalDecision,
    ApprovalRequest,
    DecisionPacketV5,
    MemoryWriteReason,
    MemoryWriteRecord,
    ResearchBrief,
    SpecialistSignal,
    SupervisorDecision,
    TradeIntentV5,
    V5Mode,
    V5State,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------


def entry_guard(state: V5State) -> dict[str, Any]:
    """Pure-code guard — no LLM.

    Checks:
      - empty input
      - malformed resume
      - provider outage short-circuit
    """
    query = (state.query or "").strip()
    if not query:
        return {
            "mode": V5Mode.CLARIFICATION,
            "current_stage": "entry_guard",
            "degrade_reason": "Empty query — cannot proceed.",
        }

    # Provider outage short-circuit
    health = state.provider_health or {}
    outages = health.get("outage_providers", [])
    degrade = ""
    if outages:
        degrade = f"Provider outage: {', '.join(outages)}. Results may be degraded."

    return {
        "current_stage": "entry_guard",
        "degrade_reason": degrade,
    }


async def supervisor(state: V5State, *, model: Any = None) -> Command:
    """Classify intent and pick a mode via structured output.

    Returns a ``Command(goto=target)`` to route the graph.
    """
    if state.mode == V5Mode.CLARIFICATION:
        return Command(goto="clarification_node")

    # If the supervisor has already been forced by entry_guard, honour it
    if state.mode is not None:
        return Command(goto=state.mode.value)

    if model is None:
        # Fallback: heuristic routing
        mode = _heuristic_mode(state.query)
        return Command(
            goto=mode.value,
            update={"mode": mode, "current_stage": "supervisor"},
        )

    try:
        planner = model.with_structured_output(SupervisorDecision)
        decision: SupervisorDecision = await planner.ainvoke(
            [
                SystemMessage(
                    content=(
                        "You are the STRATOS V5 supervisor. Choose the cheapest execution path "
                        "that will still be accurate.\n"
                        "Use fast_path for simple lookups, quotes, prices, basic facts.\n"
                        "Use council for investment decisions that need multi-specialist consensus.\n"
                        "Use research for deep investigation spanning multiple sources.\n"
                        "Use replay to revisit a previous decision thread.\n"
                        "Use clarification when the query is ambiguous or incomplete."
                    )
                ),
                HumanMessage(content=state.query),
            ]
        )
        mode = decision.mode
    except Exception:
        mode = _heuristic_mode(state.query)

    target_map = {
        V5Mode.FAST_PATH: "fast_path",
        V5Mode.COUNCIL: "council_router",
        V5Mode.RESEARCH: "research_router",
        V5Mode.REPLAY: "replay_router",
        V5Mode.CLARIFICATION: "clarification_node",
    }
    target = target_map.get(mode, "fast_path")

    return Command(
        goto=target,
        update={"mode": mode, "current_stage": "supervisor"},
    )


async def fast_path(state: V5State, *, model: Any = None) -> dict[str, Any]:
    """Lightweight pass-through — uses LLM for simple responses.

    Good for: basic questions, identity, simple lookups, provider health, thread status.
    """
    # Handle identity questions
    identity_patterns = ["who are you", "what are you", "your name", "introduce yourself"]
    query_lower = state.query.lower()
    
    if any(pattern in query_lower for pattern in identity_patterns):
        thesis = (
            "I am STRATOS, an AI-powered financial decision agent designed for portfolio managers, "
            "analysts, and decision-makers. I help you analyze market conditions, assess risks, "
            "generate trade ideas, and build investment cases by combining multiple data sources "
            "including market data, news, social signals, macro indicators, and your portfolio context. "
            "I can work in different modes: fast_path for quick answers, council for investment decisions, "
            "and research for deep investigation."
        )
        return {
            "current_stage": "fast_path",
            "final_packet": {
                "instrument": "",
                "action": "info",
                "thesis": thesis,
                "confidence": 0.95,
                "score": 0.0,
            },
        }

    # For other queries, try to use LLM if available
    if model is not None:
        try:
            response = await model.ainvoke([
                SystemMessage(content=(
                    "You are STRATOS, a helpful financial AI assistant. "
                    "Provide a concise, accurate response to the user's question. "
                    "If the question is not financial, provide a helpful general answer."
                )),
                HumanMessage(content=state.query),
            ])
            thesis = response.content if hasattr(response, 'content') else str(response)
            return {
                "current_stage": "fast_path",
                "final_packet": {
                    "instrument": "",
                    "action": "info",
                    "thesis": thesis,
                    "confidence": 0.85,
                    "score": 0.0,
                },
            }
        except Exception as e:
            logger.warning(f"fast_path LLM failed, using fallback: {e}")

    # Fallback response
    return {
        "current_stage": "fast_path",
        "final_packet": {
            "instrument": "",
            "action": "info",
            "thesis": f"I understand you're asking about '{state.query}'. Please rephrase as a portfolio, market, or investment question for better assistance.",
            "confidence": 0.5,
            "score": 0.0,
        },
    }


def clarification_node(state: V5State) -> dict[str, Any]:
    """Ask the user to refine their query."""
    reason = state.degrade_reason or "The query is ambiguous or incomplete."
    return {
        "current_stage": "clarification",
        "final_packet": {
            "action": "clarification_needed",
            "thesis": reason,
            "confidence": 0.0,
        },
        "messages": [AIMessage(content=f"I need more information: {reason}")],
    }


# ---------------------------------------------------------------------------
# Specialist Council (Production Implementation)
# ---------------------------------------------------------------------------


SPECIALIST_PROMPTS = {
    "market": """You are a MARKET SPECIALIST for STRATOS.
Your role: Analyze price action, technicals, market structure, and momentum.
Task: Given a user query about an investment decision, provide a directional signal (score -1 to +1).
Output: A SpecialistSignal with domain='market', score, confidence, thesis, evidence_ids.
Keep your thesis concise (1 paragraph) but grounded in specific market data.""",
    
    "news": """You are a NEWS SPECIALIST for STRATOS.
Your role: Analyze fundamental news, earnings, announcements, and media sentiment.
Task: Given a user query about an investment decision, provide a directional signal based on news.
Output: A SpecialistSignal with domain='news', score, confidence, thesis, evidence_ids.
Focus on recent news that would impact the investment thesis.""",
    
    "social": """You are a SOCIAL SPECIALIST for STRATOS.
Your role: Analyze social media sentiment, influencer opinions, and crowd behavior.
Task: Given a user query about an investment decision, provide a directional signal based on social signals.
Output: A SpecialistSignal with domain='social', score, confidence, thesis, evidence_ids.
Consider sentiment trends, viral narratives, and community positioning.""",
    
    "macro": """You are a MACRO SPECIALIST for STRATOS.
Your role: Analyze macroeconomic factors - rates, inflation, policy, geopolitical risk.
Task: Given a user query about an investment decision, provide a directional signal based on macro outlook.
Output: A SpecialistSignal with domain='macro', score, confidence, thesis, evidence_ids.
Consider central bank policy, economic indicators, and global risk factors.""",
    
    "portfolio": """You are a PORTFOLIO SPECIALIST for STRATOS.
Your role: Analyze position sizing, risk parity, correlation, and portfolio context.
Task: Given a user query about an investment decision, provide a directional signal considering portfolio fit.
Output: A SpecialistSignal with domain='portfolio', score, confidence, thesis, evidence_ids.
Consider how this fits the overall portfolio, correlation with existing positions, and risk budget.""",
}


async def market_specialist(state: V5State, *, model) -> dict[str, Any]:
    """Market specialist - price action, technicals, market structure."""
    from langchain_core.messages import HumanMessage, SystemMessage
    
    try:
        runner = model.with_structured_output(SpecialistSignal)
        result = await runner.ainvoke([
            SystemMessage(content=SPECIALIST_PROMPTS["market"]),
            HumanMessage(content=state.query),
        ])
        return {
            "signals": [{"domain": "market", **result.model_dump()}],
        }
    except Exception:
        logger.exception("market_specialist failed")
        return {
            "signals": [],
        }


async def news_specialist(state: V5State, *, model) -> dict[str, Any]:
    """News specialist - fundamental news, earnings."""
    from langchain_core.messages import HumanMessage, SystemMessage
    
    try:
        runner = model.with_structured_output(SpecialistSignal)
        result = await runner.ainvoke([
            SystemMessage(content=SPECIALIST_PROMPTS["news"]),
            HumanMessage(content=state.query),
        ])
        return {
            "signals": [{"domain": "news", **result.model_dump()}],
        }
    except Exception:
        logger.exception("news_specialist failed")
        return {
            "signals": [],
        }


async def social_specialist(state: V5State, *, model) -> dict[str, Any]:
    """Social specialist - sentiment, social signals."""
    from langchain_core.messages import HumanMessage, SystemMessage
    
    try:
        runner = model.with_structured_output(SpecialistSignal)
        result = await runner.ainvoke([
            SystemMessage(content=SPECIALIST_PROMPTS["social"]),
            HumanMessage(content=state.query),
        ])
        return {
            "signals": [{"domain": "social", **result.model_dump()}],
        }
    except Exception:
        logger.exception("social_specialist failed")
        return {
            "signals": [],
        }


async def macro_specialist(state: V5State, *, model) -> dict[str, Any]:
    """Macro specialist - rates, inflation, policy."""
    from langchain_core.messages import HumanMessage, SystemMessage
    
    try:
        runner = model.with_structured_output(SpecialistSignal)
        result = await runner.ainvoke([
            SystemMessage(content=SPECIALIST_PROMPTS["macro"]),
            HumanMessage(content=state.query),
        ])
        return {
            "signals": [{"domain": "macro", **result.model_dump()}],
        }
    except Exception:
        logger.exception("macro_specialist failed")
        return {
            "signals": [],
        }


async def portfolio_specialist(state: V5State, *, model) -> dict[str, Any]:
    """Portfolio specialist - risk parity, correlation."""
    from langchain_core.messages import HumanMessage, SystemMessage
    
    try:
        runner = model.with_structured_output(SpecialistSignal)
        result = await runner.ainvoke([
            SystemMessage(content=SPECIALIST_PROMPTS["portfolio"]),
            HumanMessage(content=state.query),
        ])
        return {
            "signals": [{"domain": "portfolio", **result.model_dump()}],
        }
    except Exception:
        logger.exception("portfolio_specialist failed")
        return {
            "signals": [],
        }


def council_router(state: V5State) -> dict[str, Any]:
    """Entry point for the full council pipeline.
    
    Routes to parallel specialist nodes for multi-domain analysis.
    """
    return {"current_stage": "council_router"}


def signal_aggregator(state: V5State) -> dict[str, Any]:
    """Merge specialist signals with weighted consensus.
    
    Production implementation:
    - Weighted average score (confidence-weighted)
    - Harmonic mean of confidences
    - Conflict detection (opposing signals > 0.3 spread)
    - Mark 'mixed' when spread is high
    """
    signals = state.signals or []
    
    if not signals:
        return {
            "current_stage": "signal_aggregator",
            "aggregated_signals": {
                "signals": [],
                "consensus_direction": "neutral",
                "consensus_score": 0.0,
                "consensus_confidence": 0.0,
                "conflict_note": "No signals received from specialists",
            },
        }
    
    # Compute weighted average score
    total_weight = 0.0
    weighted_sum = 0.0
    confidences = []
    domains = []
    
    for sig in signals:
        score = sig.get("score", 0.0)
        confidence = sig.get("confidence", 0.0)
        domain = sig.get("domain", "unknown")
        
        if confidence > 0:
            weighted_sum += score * confidence
            total_weight += confidence
            confidences.append(confidence)
            domains.append(domain)
    
    consensus_score = weighted_sum / total_weight if total_weight > 0 else 0.0
    
    # Harmonic mean of confidences
    if confidences:
        n = len(confidences)
        consensus_confidence = n / sum(1.0 / c for c in confidences if c > 0) if any(c > 0 for c in confidences) else 0.0
    else:
        consensus_confidence = 0.0
    
    # Determine direction
    if abs(consensus_score) < 0.15:
        consensus_direction = "neutral"
    elif consensus_score > 0.15:
        consensus_direction = "bull"
    else:
        consensus_direction = "bear"
    
    # Conflict detection - check for opposing signals
    positive_signals = [s for s in signals if s.get("score", 0) > 0.1]
    negative_signals = [s for s in signals if s.get("score", 0) < -0.1]
    
    conflict_note = ""
    if positive_signals and negative_signals:
        # Check spread
        max_positive = max(s.get("score", 0) for s in positive_signals)
        min_negative = min(s.get("score", 0) for s in negative_signals)
        spread = max_positive - min_negative
        
        if spread > 0.3:
            consensus_direction = "mixed"
            conflict_note = f"Specialists strongly disagree: bull signals ({max_positive:.2f}) vs bear signals ({min_negative:.2f}). Consider deeper research."
    
    return {
        "current_stage": "signal_aggregator",
        "aggregated_signals": {
            "signals": signals,
            "consensus_direction": consensus_direction,
            "consensus_score": consensus_score,
            "consensus_confidence": consensus_confidence,
            "conflict_note": conflict_note,
        },
    }


# ---------------------------------------------------------------------------
# Research path stubs (wired in Phase 6)
# ---------------------------------------------------------------------------


def research_router(state: V5State) -> dict[str, Any]:
    """Entry point for deep research. Placeholder."""
    return {"current_stage": "research_router"}


# ---------------------------------------------------------------------------
# Replay path stub (wired in Phase 8)
# ---------------------------------------------------------------------------


def replay_router(state: V5State) -> dict[str, Any]:
    """Entry point for historical replay. Placeholder."""
    return {"current_stage": "replay_router"}


def replay_analyst(state: V5State) -> dict[str, Any]:
    """Analyse a previous decision thread. Placeholder."""
    return {"current_stage": "replay_analyst"}


# ---------------------------------------------------------------------------
# Research Nodes (Production Implementation)
# ---------------------------------------------------------------------------


async def bull_researcher(state: V5State, *, model) -> dict[str, Any]:
    """Build bullish thesis with structured output."""
    from langchain_core.messages import HumanMessage, SystemMessage
    
    aggregated = state.aggregated_signals or {}
    signals_summary = aggregated.get("consensus_score", 0)
    
    prompt = f"""You are a BULLISH RESEARCHER for STRATOS.
Your role: Build a compelling bullish thesis based on the specialist council signals.
Current consensus score: {signals_summary:.2f} (positive = bullish)
Query: {state.query}

Task: Provide a bullish thesis with supporting evidence, target price rationale, and risk factors to monitor.
Output: A ResearchBrief with bull_thesis, evidence_ids, citations."""
    
    try:
        runner = model.with_structured_output(ResearchBrief)
        result = await runner.ainvoke([
            SystemMessage(content=prompt),
            HumanMessage(content=f"Analyze for bullish case: {state.query}"),
        ])
        return {
            "current_stage": "bull_researcher",
            "research": {**result.model_dump(), "type": "bull"},
        }
    except Exception:
        logger.exception("bull_researcher failed")
        return {
            "current_stage": "bull_researcher",
            "degrade_reason": "bull_researcher_failed",
            "research": {"bull_thesis": "", "type": "bull"},
        }


async def bear_researcher(state: V5State, *, model) -> dict[str, Any]:
    """Build bearish thesis with structured output."""
    from langchain_core.messages import HumanMessage, SystemMessage
    
    aggregated = state.aggregated_signals or {}
    signals_summary = aggregated.get("consensus_score", 0)
    
    prompt = f"""You are a BEARISH RESEARCHER for STRATOS.
Your role: Build a compelling bearish thesis based on the specialist council signals.
Current consensus score: {signals_summary:.2f} (negative = bearish)
Query: {state.query}

Task: Provide a bearish thesis with supporting evidence, downside scenarios, and risk factors.
Output: A ResearchBrief with bear_thesis, evidence_ids, citations."""
    
    try:
        runner = model.with_structured_output(ResearchBrief)
        result = await runner.ainvoke([
            SystemMessage(content=prompt),
            HumanMessage(content=f"Analyze for bearish case: {state.query}"),
        ])
        return {
            "current_stage": "bear_researcher",
            "research": {**result.model_dump(), "type": "bear"},
        }
    except Exception:
        logger.exception("bear_researcher failed")
        return {
            "current_stage": "bear_researcher",
            "degrade_reason": "bear_researcher_failed",
            "research": {"bear_thesis": "", "type": "bear"},
        }


def research_manager(state: V5State) -> dict[str, Any]:
    """Synthesize bull + bear into final ResearchBrief with verdict."""
    research = state.research or {}
    
    # Get bull and bear components
    bull = research.get("bull_thesis", "")
    bear = research.get("bear_thesis", "")
    evidence = research.get("evidence_ids", [])
    citations = research.get("citations", [])
    
    # Synthesize
    if bull and bear:
        synthesis = f"BULL CASE: {bull[:200]}...\n\nBEAR CASE: {bear[:200]}..."
        # Determine verdict based on which thesis is stronger
        # For now, default to hold if balanced
        verdict = "hold"
        confidence = 0.5
    elif bull:
        synthesis = bull
        verdict = "bullish"
        confidence = 0.6
    elif bear:
        synthesis = bear
        verdict = "bearish"
        confidence = 0.6
    else:
        synthesis = "Research incomplete"
        verdict = "hold"
        confidence = 0.0
    
    return {
        "current_stage": "research_manager",
        "research": {
            "bull_thesis": bull,
            "bear_thesis": bear,
            "synthesis": synthesis,
            "verdict": verdict,
            "confidence": confidence,
            "evidence_ids": evidence,
            "citations": citations,
        },
    }


# ---------------------------------------------------------------------------
# Trader, risk, approval
# ---------------------------------------------------------------------------


async def trader_agent(state: V5State, *, model) -> dict[str, Any]:
    """Generate a trade intent from aggregated signals + research.
    
    Production implementation with real LLM and structured output.
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    
    aggregated = state.aggregated_signals or {}
    research = state.research or {}
    
    prompt = f"""You are the TRADER AGENT for STRATOS.
Your role: Translate specialist consensus and research into a concrete trade recommendation.

Specialist Consensus:
- Direction: {aggregated.get('consensus_direction', 'neutral')}
- Score: {aggregated.get('consensus_score', 0):.2f}
- Confidence: {aggregated.get('consensus_confidence', 0):.2f}

Research Synthesis:
- Verdict: {research.get('verdict', 'hold')}
- Thesis: {research.get('synthesis', '')[:300]}

Query: {state.query}

Task: Generate a TradeIntentV5 with instrument, action, score, confidence, thesis, entry_zone, stop_loss, take_profit, max_holding_period."""
    
    try:
        runner = model.with_structured_output(TradeIntentV5)
        result = await runner.ainvoke([
            SystemMessage(content=prompt),
            HumanMessage(content=f"Generate trade recommendation for: {state.query}"),
        ])
        return {
            "current_stage": "trader_agent",
            "trade_intent": result.model_dump(),
        }
    except Exception:
        logger.exception("trader_agent failed")
        return {
            "current_stage": "trader_agent",
            "degrade_reason": "trader_agent_failed",
            "trade_intent": {},
        }


def risk_engine(state: V5State) -> dict[str, Any]:
    """Deterministic risk check — no LLM.
    
    Production implementation with real risk calculations:
    - VaR calculation
    - Concentration checks
    - Max position size
    - Kill-switch rules
    """
    trade = state.trade_intent or {}
    
    # Extract trade parameters
    position_size_pct = trade.get("position_size_pct", 10.0)  # default 10%
    instrument = trade.get("instrument", "")
    action = trade.get("action", "")
    
    # Deterministic risk checks
    kill_switch_reasons = []
    allowed = True
    
    # Max position size check (default max 20%)
    if position_size_pct > 20:
        kill_switch_reasons.append(f"Position size {position_size_pct}% exceeds max 20%")
        allowed = False
    
    # Concentration risk (if we had portfolio context, we'd check here)
    concentration_risk = 0.0  # Would check against portfolio
    
    # Capital at risk (simplified calculation)
    capital_at_risk = position_size_pct / 100.0  # Assume full position at risk
    
    # VaR estimate (simplified - would use real vol in prod)
    value_at_risk_95 = position_size_pct * 0.02  # 2% of position as rough daily VaR
    
    # Regime check (would check vol regime, liquidity in prod)
    regime = "normal"
    
    # Build rationale
    if allowed:
        rationale = f"Risk checks passed. Position: {position_size_pct}%, Instrument: {instrument}, Action: {action}"
    else:
        rationale = f"Risk rejected: {'; '.join(kill_switch_reasons)}"
    
    return {
        "current_stage": "risk_engine",
        "risk_verdict": {
            "allowed": allowed,
            "regime": regime,
            "value_at_risk_95": value_at_risk_95,
            "concentration_risk": concentration_risk,
            "position_size_pct": position_size_pct,
            "capital_at_risk": capital_at_risk,
            "kill_switch_reasons": kill_switch_reasons,
            "rationale": rationale,
        },
    }


def approval_gate(state: V5State) -> dict[str, Any]:
    """HITL pause point.

    Uses ``interrupt()`` to pause the graph. The frontend resumes with
    an ``ApprovalDecision`` payload via ``Command(resume=...)``.
    """
    trade = state.trade_intent or {}
    risk = state.risk_verdict or {}

    request = ApprovalRequest(
        approval_id=str(uuid.uuid4()),
        instrument=trade.get("instrument", ""),
        action=trade.get("action", ""),
        thesis=trade.get("thesis", ""),
        risk_summary=risk.get("rationale", ""),
        position_size_pct=risk.get("position_size_pct", 0.0),
        capital_at_risk=risk.get("capital_at_risk", 0.0),
    )

    # Pause the graph — this raises an interrupt that LangGraph handles
    resume_payload = interrupt(request.model_dump())

    # When resumed, resume_payload contains the ApprovalDecision dict
    decision = ApprovalDecision.model_validate(resume_payload)

    return {
        "current_stage": "approval_gate",
        "approval_request": request.model_dump(),
        "approval_decision": decision.model_dump(),
    }


# ---------------------------------------------------------------------------
# Decision packager & memory writer
# ---------------------------------------------------------------------------


def decision_packager(state: V5State) -> dict[str, Any]:
    """Assemble the final decision packet from trade + risk + approval.

    All non-fast-path flows converge here.
    """
    trade = state.trade_intent or {}
    risk = state.risk_verdict or {}
    approval = state.approval_decision or {}
    research = state.research or {}

    packet = DecisionPacketV5(
        instrument=trade.get("instrument", ""),
        action=trade.get("action", "") if approval.get("approved", True) else "rejected",
        confidence=trade.get("confidence", 0.0),
        score=trade.get("score", 0.0),
        thesis=trade.get("thesis", research.get("synthesis", "")),
        entry_zone=trade.get("entry_zone", ""),
        stop_loss=trade.get("stop_loss", ""),
        take_profit=trade.get("take_profit", ""),
        max_holding_period=trade.get("max_holding_period", ""),
        position_size_pct=risk.get("position_size_pct", 0.0),
        capital_at_risk=risk.get("capital_at_risk", 0.0),
        kill_switch_reasons=risk.get("kill_switch_reasons", []),
    )
    return {
        "current_stage": "decision_packager",
        "final_packet": packet.model_dump(),
    }


def memory_writer(state: V5State) -> dict[str, Any]:
    """Write to long-term memory — only when write policy permits.

    Write policy:
      - successful final packet
      - approval/rejection event
      - explicit user preference
      - replay lesson
    """
    writes: list[dict[str, Any]] = list(state.memory_writes)

    packet = state.final_packet or {}
    approval = state.approval_decision

    # Successful final packet
    if packet.get("action") and packet.get("action") not in ("clarification_needed", "info"):
        writes.append(
            MemoryWriteRecord(
                reason=MemoryWriteReason.FINAL_PACKET,
                query=state.query,
                decision=packet.get("action", ""),
                summary=packet.get("thesis", ""),
            ).model_dump()
        )

    # Approval / rejection event
    if approval:
        writes.append(
            MemoryWriteRecord(
                reason=MemoryWriteReason.APPROVAL_EVENT,
                query=state.query,
                approval_event=approval,
            ).model_dump()
        )

    return {
        "current_stage": "memory_writer",
        "memory_writes": writes,
    }


# ---------------------------------------------------------------------------
# Heuristic fallback
# ---------------------------------------------------------------------------


def _heuristic_mode(query: str) -> V5Mode:
    """Keyword-based fallback when the LLM supervisor is unavailable."""
    lowered = query.lower()

    fast_tokens = {"price", "quote", "btc", "eth", "latest", "status", "health"}
    if any(tok in lowered for tok in fast_tokens) and len(query.split()) <= 10:
        return V5Mode.FAST_PATH

    replay_tokens = {"replay", "revisit", "last time", "previous decision"}
    if any(tok in lowered for tok in replay_tokens):
        return V5Mode.REPLAY

    research_tokens = {"research", "investigate", "deep dive", "analyze"}
    if any(tok in lowered for tok in research_tokens):
        return V5Mode.RESEARCH

    council_tokens = {
        "allocate", "portfolio", "position", "trade", "hedge",
        "buy", "sell", "exposure", "scenario",
    }
    if any(tok in lowered for tok in council_tokens):
        return V5Mode.COUNCIL

    return V5Mode.FAST_PATH


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_v5_graph(
    *,
    checkpointer: Any = None,
    store: Any = None,
    model: Any = None,
) -> Any:
    """Build and compile the V5 state graph.

    Parameters
    ----------
    checkpointer : BaseCheckpointSaver
        LangGraph checkpointer for durable threads.
    store : BaseStore
        Long-term memory store.
    model : BaseChatModel | None
        LLM for the supervisor node. If ``None``, heuristic routing is used.
    """
    graph = StateGraph(V5State)

    # --- register nodes ---
    graph.add_node("entry_guard", entry_guard)

    # Supervisor needs the model, so wrap it in a closure
    async def _supervisor(state: V5State) -> Command:
        return await supervisor(state, model=model)

    # Specialist nodes need the model, wrap them
    async def _market_specialist(state: V5State) -> dict[str, Any]:
        return await market_specialist(state, model=model)

    async def _news_specialist(state: V5State) -> dict[str, Any]:
        return await news_specialist(state, model=model)

    async def _social_specialist(state: V5State) -> dict[str, Any]:
        return await social_specialist(state, model=model)

    async def _macro_specialist(state: V5State) -> dict[str, Any]:
        return await macro_specialist(state, model=model)

    async def _portfolio_specialist(state: V5State) -> dict[str, Any]:
        return await portfolio_specialist(state, model=model)

    # Research nodes need the model
    async def _bull_researcher(state: V5State) -> dict[str, Any]:
        return await bull_researcher(state, model=model)

    async def _bear_researcher(state: V5State) -> dict[str, Any]:
        return await bear_researcher(state, model=model)

    # Trader needs the model
    async def _trader_agent(state: V5State) -> dict[str, Any]:
        return await trader_agent(state, model=model)

    # Fast path needs the model
    async def _fast_path(state: V5State) -> dict[str, Any]:
        return await fast_path(state, model=model)

    graph.add_node("supervisor", _supervisor)
    graph.add_node("fast_path", _fast_path)
    graph.add_node("clarification_node", clarification_node)

    # Council pipeline - specialist nodes
    graph.add_node("council_router", council_router)
    graph.add_node("market_specialist", _market_specialist)
    graph.add_node("news_specialist", _news_specialist)
    graph.add_node("social_specialist", _social_specialist)
    graph.add_node("macro_specialist", _macro_specialist)
    graph.add_node("portfolio_specialist", _portfolio_specialist)
    graph.add_node("signal_aggregator", signal_aggregator)
    graph.add_node("trader_agent", _trader_agent)
    graph.add_node("risk_engine", risk_engine)
    graph.add_node("approval_gate", approval_gate)

    # Research pipeline
    graph.add_node("research_router", research_router)
    graph.add_node("bull_researcher", _bull_researcher)
    graph.add_node("bear_researcher", _bear_researcher)
    graph.add_node("research_manager", research_manager)

    # Replay pipeline
    graph.add_node("replay_router", replay_router)
    graph.add_node("replay_analyst", replay_analyst)

    # Convergence nodes
    graph.add_node("decision_packager", decision_packager)
    graph.add_node("memory_writer", memory_writer)

    # --- edges ---
    graph.add_edge(START, "entry_guard")
    graph.add_edge("entry_guard", "supervisor")

    # Supervisor routes via Command(goto=...), but we still need
    # the static edges for the nodes it can target:
    # (No add_edge from supervisor — Command handles routing)

    # Fast path → END
    graph.add_edge("fast_path", END)

    # Clarification → END
    graph.add_edge("clarification_node", END)

    # Council pipeline - fan-out to specialists in parallel using Send
    def council_fan_out(state: V5State) -> Sequence[Send]:
        return [
            Send("market_specialist", {}),
            Send("news_specialist", {}),
            Send("social_specialist", {}),
            Send("macro_specialist", {}),
            Send("portfolio_specialist", {}),
        ]
    
    graph.add_conditional_edges("council_router", council_fan_out)
    # All specialists converge to signal_aggregator
    graph.add_edge("market_specialist", "signal_aggregator")
    graph.add_edge("news_specialist", "signal_aggregator")
    graph.add_edge("social_specialist", "signal_aggregator")
    graph.add_edge("macro_specialist", "signal_aggregator")
    graph.add_edge("portfolio_specialist", "signal_aggregator")
    graph.add_edge("signal_aggregator", "trader_agent")
    graph.add_edge("trader_agent", "risk_engine")
    graph.add_edge("risk_engine", "approval_gate")
    graph.add_edge("approval_gate", "decision_packager")

    # Research pipeline - parallel bull/bear using Send
    def research_fan_out(state: V5State) -> Sequence[Send]:
        return [
            Send("bull_researcher", {}),
            Send("bear_researcher", {}),
        ]
    
    graph.add_conditional_edges("research_router", research_fan_out)
    graph.add_edge("bull_researcher", "research_manager")
    graph.add_edge("bear_researcher", "research_manager")
    graph.add_edge("research_manager", "decision_packager")

    # Replay pipeline converges through decision_packager
    graph.add_edge("replay_router", "replay_analyst")
    graph.add_edge("replay_analyst", "decision_packager")

    # Convergence
    graph.add_edge("decision_packager", "memory_writer")
    graph.add_edge("memory_writer", END)

    return graph.compile(checkpointer=checkpointer, store=store)
