"""Domain service for enforcing institutional risk policies (Subsystem G)."""

from __future__ import annotations

import json
from pathlib import Path
from stratos_orchestrator.domain.entities import AgentTask, RiskPolicy
from stratos_orchestrator.logging import get_logger

logger = get_logger(__name__)

class PolicyValidationError(Exception):
    """Raised when a tool call violates risk policy."""
    pass

class PolicyGuard:
    """Unoverrideable firewall for LLM tool-calling with ADR (Subsystem G)."""

    def __init__(
        self, 
        policy: RiskPolicy | None = None, 
        config_path: Path | None = None,
        current_vix: float = 20.0,
        current_correlation: float = 0.5,
        regime_stability: float = 1.0,
        kill_switch_active: bool = False
    ) -> None:
        self.policy = policy or self._load_policy(config_path)
        self.current_vix = current_vix
        self.current_correlation = current_correlation
        self.regime_stability = regime_stability
        self.kill_switch_active = kill_switch_active
        self.adr_active = self._check_adr_trigger()

    def _load_policy(self, path: Path | None) -> RiskPolicy:
        if path and path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                    return RiskPolicy(**data)
            except Exception:
                logger.error("failed_to_load_policy", path=str(path))
        return RiskPolicy()

    def _check_adr_trigger(self) -> bool:
        """Check if crisis thresholds are breached."""
        vix_breached = self.current_vix > self.policy.vix_crisis_threshold
        corr_breached = self.current_correlation > self.policy.corr_spike_threshold
        
        if vix_breached or corr_breached:
            logger.warning("ADR_TRIGGERED", vix=self.current_vix, corr=self.current_correlation)
            return True
        return False

    def get_system_regime(self) -> str:
        """Return the current system regime label based on multi-indicator triggers."""
        # Crisis triggers
        vix_crisis = self.current_vix > self.policy.vix_crisis_threshold
        corr_crisis = self.current_correlation > self.policy.corr_spike_threshold
        
        if vix_crisis or corr_crisis:
            return "crisis"
            
        # Stress triggers
        if self.current_vix > 25.0 or self.current_correlation > 0.7:
            return "stressed"
            
        return "normal"

    def get_effective_limits(self) -> dict[str, float]:
        """Return the current risk ceilings, adjusted for ADR and Stability."""
        regime = self.get_system_regime()
        mult = 1.0
        if regime == "crisis":
            mult = self.policy.crisis_mult
        elif regime == "stressed":
            mult = self.policy.stressed_mult
            
        # Add Stability Penalty (Subsystem A.5)
        # If stability is below 0.7, we apply a linear penalty down to 0.5x
        stability_mult = 1.0
        if self.regime_stability < 0.7:
            # Simple linear glue: at 0.7 stability -> 1.0 mult, at 0.0 stability -> 0.5 mult
            stability_mult = 0.5 + (0.5 * (self.regime_stability / 0.7))
            logger.info("STABILITY_PENALTY_APPLIED", stability=self.regime_stability, mult=stability_mult)
            
        total_mult = mult * stability_mult
            
        return {
            "max_allocation": self.policy.max_allocation * total_mult,
            "max_leverage": self.policy.max_leverage * total_mult,
            "max_sector_concentration": self.policy.max_sector_concentration * total_mult,
            "max_net_exposure": self.policy.max_net_exposure * total_mult,
        }

    def validate_task(self, task: AgentTask) -> None:
        """Validate a proposed task against the dynamic Multi-Dimensional Policy.
        
        Raises PolicyValidationError if violated.
        """
        if self.kill_switch_active:
            logger.critical("KILL_SWITCH_ENGAGED", tool=task.tool_name)
            raise PolicyValidationError("Risk Kill-Switch is engaged. All executions halted.")

        limits = self.get_effective_limits()
        regime = self.get_system_regime()
        reason = f"ADR ACTION ({regime.upper()})" if regime != "normal" else "Hard Constraint"
        
        # 1. Allocation Limit (Subsystem G.1)
        if "allocation" in task.arguments or "weight" in task.arguments:
            for key in ["allocation", "weight"]:
                val = task.arguments.get(key)
                if isinstance(val, (int, float)) and val > limits["max_allocation"]:
                    raise PolicyValidationError(
                        f"Allocation of {val} violates ceiling of {limits['max_allocation']} ({reason})"
                    )

        # 2. Leverage Limit (Subsystem G.2)
        if "leverage" in task.arguments:
            lev = task.arguments.get("leverage")
            if isinstance(lev, (int, float)) and lev > limits["max_leverage"]:
                raise PolicyValidationError(
                    f"Leverage of {lev} violates ceiling of {limits['max_leverage']} ({reason})"
                )

        # 3. Multi-Dimensional: Sector Concentration
        if "sector_weights" in task.arguments:
            sectors = task.arguments.get("sector_weights")
            if isinstance(sectors, dict):
                for sector, weight in sectors.items():
                    if weight > limits["max_sector_concentration"]:
                        raise PolicyValidationError(
                            f"Sector '{sector}' concentration {weight} violates limit of {limits['max_sector_concentration']} ({reason})"
                        )

        # 4. Multi-Dimensional: Net Exposure
        if "net_exposure" in task.arguments:
            exp = task.arguments.get("net_exposure")
            if isinstance(exp, (int, float)) and abs(exp) > limits["max_net_exposure"]:
                raise PolicyValidationError(
                    f"Net exposure {exp} violates limit of {limits['max_net_exposure']} ({reason})"
                )

        logger.info("policy_check_passed", tool=task.tool_name, regime=regime)
