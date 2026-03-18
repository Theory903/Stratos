"""Finance decision-engine modules."""

from stratos_orchestrator.application.finance.analysts import (
    FundamentalsAnalyst,
    MacroPolicyAnalyst,
    MarketAnalyst,
    NewsAnalyst,
    SocialAnalyst,
)
from stratos_orchestrator.application.finance.context import FinanceContextLoader, FreshnessGate
from stratos_orchestrator.application.finance.debate import BearResearcher, BullResearcher, ResearchManager
from stratos_orchestrator.application.finance.feedback import FinanceFeedbackMemory
from stratos_orchestrator.application.finance.packager import DecisionPackager
from stratos_orchestrator.application.finance.quant import QuantAnalyst
from stratos_orchestrator.application.finance.resolver import InstrumentResolver
from stratos_orchestrator.application.finance.risk import AggressiveRiskProfile, ConservativeRiskProfile, NeutralRiskProfile, RiskManager
from stratos_orchestrator.application.finance.scoring import FinanceScorer, ScoreSummary, ScoringProfile
from stratos_orchestrator.application.finance.supervisor import FinanceSupervisor, FinanceSupervisorPlan
from stratos_orchestrator.application.finance.trader import Trader

__all__ = [
    "AggressiveRiskProfile",
    "BearResearcher",
    "BullResearcher",
    "ConservativeRiskProfile",
    "DecisionPackager",
    "FinanceFeedbackMemory",
    "FinanceContextLoader",
    "FinanceSupervisor",
    "FinanceSupervisorPlan",
    "FreshnessGate",
    "FinanceScorer",
    "FundamentalsAnalyst",
    "InstrumentResolver",
    "MacroPolicyAnalyst",
    "MarketAnalyst",
    "NeutralRiskProfile",
    "NewsAnalyst",
    "QuantAnalyst",
    "ResearchManager",
    "RiskManager",
    "ScoreSummary",
    "ScoringProfile",
    "SocialAnalyst",
    "Trader",
]
