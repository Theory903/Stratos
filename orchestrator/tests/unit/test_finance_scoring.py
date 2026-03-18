from __future__ import annotations

from stratos_orchestrator.application.finance.scoring import FinanceScorer
from stratos_orchestrator.application.finance.trader import Trader
from stratos_orchestrator.application.finance.risk import RiskManager
from stratos_orchestrator.domain.entities import AnalystSignal, DebateMemo, TradeIntent


def _signal(analyst: str, score: float, confidence: float = 0.7) -> AnalystSignal:
    direction = "bullish" if score > 0.05 else "bearish" if score < -0.05 else "neutral"
    return AnalystSignal(
        analyst=analyst,
        instrument="AAPL",
        signal_score=score,
        confidence=confidence,
        direction=direction,
        thesis=f"{analyst} {direction}",
    )


def _debate() -> DebateMemo:
    return DebateMemo(
        bull_case="bull case",
        bear_case="bear case",
        synthesis="ResearchManager synthesis",
        verdict="hold_bias",
        confidence=0.5,
    )


def test_finance_scorer_profiles_crypto_and_india_equity() -> None:
    scorer = FinanceScorer()

    assert scorer.profile_for_instrument("X:BTCUSD").name == "crypto_swing"
    assert scorer.profile_for_instrument("INDEX:NIFTY50").name == "india_equity_swing"
    assert scorer.profile_for_instrument("AAPL").name == "equity_swing"


def test_trader_generates_buy_sell_and_hold_from_score_profiles() -> None:
    trader = Trader()

    buy_intent = trader.plan(
        "AAPL",
        [
            _signal("MarketAnalyst", 0.9),
            _signal("FundamentalsAnalyst", 0.8),
            _signal("NewsAnalyst", 0.6),
            _signal("SocialAnalyst", 0.2),
            _signal("MacroPolicyAnalyst", 0.2),
        ],
        _debate(),
    )
    sell_intent = trader.plan(
        "AAPL",
        [
            _signal("MarketAnalyst", -0.9),
            _signal("FundamentalsAnalyst", -0.7),
            _signal("NewsAnalyst", -0.8),
            _signal("SocialAnalyst", -0.3),
            _signal("MacroPolicyAnalyst", -0.2),
        ],
        _debate(),
    )
    hold_intent = trader.plan(
        "AAPL",
        [
            _signal("MarketAnalyst", 0.4),
            _signal("FundamentalsAnalyst", 0.3),
            _signal("NewsAnalyst", -0.4),
            _signal("SocialAnalyst", -0.3),
            _signal("MacroPolicyAnalyst", 0.0),
        ],
        _debate(),
    )

    assert buy_intent.action == "BUY"
    assert sell_intent.action == "SELL"
    assert hold_intent.action == "HOLD"


def test_conflict_penalty_reduces_raw_score_toward_neutral() -> None:
    scorer = FinanceScorer()
    signals = [
        _signal("MarketAnalyst", 0.8, confidence=0.9),
        _signal("FundamentalsAnalyst", 0.7, confidence=0.8),
        _signal("NewsAnalyst", -0.8, confidence=0.9),
        _signal("SocialAnalyst", -0.7, confidence=0.8),
        _signal("MacroPolicyAnalyst", 0.1, confidence=0.5),
    ]

    summary = scorer.score("AAPL", signals)

    assert summary.raw_score > summary.final_score
    assert summary.conflict_penalty > 0
    assert summary.disagreement_ratio > 0


def test_risk_manager_turns_hold_into_explainable_no_trade() -> None:
    trader = Trader()
    risk_manager = RiskManager()
    intent = trader.plan(
        "AAPL",
        [
            _signal("MarketAnalyst", 0.4),
            _signal("FundamentalsAnalyst", 0.3),
            _signal("NewsAnalyst", -0.4),
            _signal("SocialAnalyst", -0.3),
            _signal("MacroPolicyAnalyst", 0.0),
        ],
        _debate(),
    )

    verdict = risk_manager.review(
        "AAPL",
        {
            "portfolio_risk": {
                "estimated_daily_volatility": 0.02,
                "value_at_risk_95": 0.03,
                "concentration_risk": 0.1,
                "risk_flags": [],
                "regime": {"regime_label": "risk_on"},
            },
            "order_book": {"top_bid_price": 10},
        },
        intent,
        {"market_ready": True},
    )

    assert intent.action == "HOLD"
    assert verdict.allowed is False
    assert any("neutral" in reason.lower() for reason in verdict.kill_switch_reasons)


def test_risk_manager_blocks_when_single_name_limit_is_already_breached() -> None:
    risk_manager = RiskManager()

    verdict = risk_manager.review(
        "AAPL",
        {
            "portfolio": {
                "constraints": {
                    "max_single_name_weight": 0.35,
                    "max_crypto_weight": 0.35,
                }
            },
            "portfolio_exposures": {
                "asset_class_exposure": {"equity": 0.9, "crypto": 0.1},
                "top_positions": [{"ticker": "AAPL", "weight": 0.42}],
            },
            "portfolio_risk": {
                "estimated_daily_volatility": 0.02,
                "value_at_risk_95": 0.03,
                "concentration_risk": 0.42,
                "risk_flags": [],
                "regime": {"regime_label": "risk_on"},
            },
            "order_book": {"top_bid_price": 10},
        },
        TradeIntent(
            instrument="AAPL",
            action="BUY",
            score=0.25,
            confidence=0.7,
            thesis="buy",
            entry_zone="entry",
            stop_loss="stop",
            take_profit="target",
            max_holding_period="10d",
        ),
        {"market_ready": True},
    )

    assert verdict.allowed is False
    assert any("single-name limit" in reason for reason in verdict.kill_switch_reasons)


def test_risk_manager_blocks_when_crypto_cap_is_exceeded() -> None:
    risk_manager = RiskManager()

    verdict = risk_manager.review(
        "X:BTCUSD",
        {
            "portfolio": {
                "constraints": {
                    "max_crypto_weight": 0.35,
                }
            },
            "portfolio_exposures": {
                "asset_class_exposure": {"crypto": 0.4},
                "top_positions": [],
            },
            "portfolio_risk": {
                "estimated_daily_volatility": 0.03,
                "value_at_risk_95": 0.04,
                "concentration_risk": 0.25,
                "risk_flags": [],
                "regime": {"regime_label": "risk_on"},
            },
            "order_book": {"top_bid_price": 10},
        },
        TradeIntent(
            instrument="X:BTCUSD",
            action="BUY",
            score=0.22,
            confidence=0.75,
            thesis="buy",
            entry_zone="entry",
            stop_loss="stop",
            take_profit="target",
            max_holding_period="7d",
        ),
        {"market_ready": True},
    )

    assert verdict.allowed is False
    assert any("Crypto exposure" in reason for reason in verdict.kill_switch_reasons)


def test_risk_manager_blocks_when_drawdown_limit_is_breached() -> None:
    risk_manager = RiskManager()

    verdict = risk_manager.review(
        "AAPL",
        {
            "portfolio": {
                "constraints": {
                    "max_drawdown_allowed": 0.1,
                }
            },
            "portfolio_exposures": {
                "asset_class_exposure": {"equity": 1.0},
                "top_positions": [],
            },
            "portfolio_risk": {
                "current_drawdown": 0.14,
                "estimated_daily_volatility": 0.02,
                "value_at_risk_95": 0.03,
                "concentration_risk": 0.2,
                "risk_flags": [],
                "regime": {"regime_label": "risk_on"},
            },
            "order_book": {"top_bid_price": 10},
        },
        TradeIntent(
            instrument="AAPL",
            action="BUY",
            score=0.3,
            confidence=0.7,
            thesis="buy",
            entry_zone="entry",
            stop_loss="stop",
            take_profit="target",
            max_holding_period="10d",
        ),
        {"market_ready": True},
    )

    assert verdict.allowed is False
    assert any("drawdown" in reason.lower() for reason in verdict.kill_switch_reasons)


def test_risk_manager_uses_conservative_sizing_in_risk_off_regime() -> None:
    risk_manager = RiskManager()

    verdict = risk_manager.review(
        "AAPL",
        {
            "portfolio": {
                "constraints": {
                    "max_single_name_weight": 0.5,
                    "max_crypto_weight": 0.35,
                }
            },
            "portfolio_exposures": {
                "asset_class_exposure": {"equity": 0.8},
                "top_positions": [{"ticker": "MSFT", "weight": 0.2}],
            },
            "portfolio_risk": {
                "estimated_daily_volatility": 0.02,
                "value_at_risk_95": 0.03,
                "concentration_risk": 0.2,
                "risk_flags": [],
                "regime": {"regime_label": "risk_off"},
            },
            "order_book": {"top_bid_price": 10},
        },
        TradeIntent(
            instrument="AAPL",
            action="BUY",
            score=0.3,
            confidence=0.7,
            thesis="buy",
            entry_zone="entry",
            stop_loss="stop",
            take_profit="target",
            max_holding_period="10d",
        ),
        {"market_ready": True},
    )

    assert verdict.allowed is True
    assert verdict.position_size_pct <= 0.01
    assert "ConservativeRisk" in verdict.rationale
