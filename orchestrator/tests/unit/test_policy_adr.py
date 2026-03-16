import pytest
from stratos_orchestrator.domain.entities import AgentTask, RiskPolicy
from stratos_orchestrator.domain.services.policy import PolicyGuard, PolicyValidationError

def test_policy_guard_normal_conditions():
    policy = RiskPolicy(max_allocation=0.35, vix_crisis_threshold=30.0)
    # Normal IX (20)
    guard = PolicyGuard(policy=policy, current_vix=20.0)
    
    task = AgentTask(
        tool_name="portfolio_allocate",
        arguments={"allocation": 0.30},
        status="pending"
    )
    
    # Should pass
    guard.validate_task(task)

def test_policy_guard_adr_trigger_vix():
    policy = RiskPolicy(max_allocation=0.40, vix_crisis_threshold=30.0, crisis_mult=0.5)
    # Crisis VIX (40) -> Effective max_allocation should be 0.20
    guard = PolicyGuard(policy=policy, current_vix=40.0)
    
    task = AgentTask(
        tool_name="portfolio_allocate",
        arguments={"allocation": 0.30},
        status="pending"
    )
    
    # Should fail due to ADR clamping
    with pytest.raises(PolicyValidationError) as excinfo:
        guard.validate_task(task)
    
    assert "violates ceiling of 0.2" in str(excinfo.value)
    assert "ADR ACTION" in str(excinfo.value)

def test_policy_guard_adr_trigger_correlation():
    policy = RiskPolicy(max_leverage=1.2, corr_spike_threshold=0.8, crisis_mult=0.5)
    # Stressed Correlation (0.9) -> Effective max_leverage should be 0.6
    guard = PolicyGuard(policy=policy, current_correlation=0.9)
    
    task = AgentTask(
        tool_name="trade_execution",
        arguments={"leverage": 1.0},
        status="pending"
    )
    
    # Should fail due to ADR clamping
    with pytest.raises(PolicyValidationError) as excinfo:
        guard.validate_task(task)
    
    assert "violates ceiling of 0.6" in str(excinfo.value)

def test_policy_guard_sector_concentration():
    policy = RiskPolicy(max_sector_concentration=0.5, crisis_mult=0.5)
    # Stressed (VIX 35) -> Limit becomes 0.25 (using crisis_mult for simplicity in this test)
    guard = PolicyGuard(policy=policy, current_vix=40.0) 
    
    task = AgentTask(
        tool_name="portfolio_allocate",
        arguments={"sector_weights": {"tech": 0.40}},
        status="pending"
    )
    
    with pytest.raises(PolicyValidationError) as excinfo:
        guard.validate_task(task)
    assert "Sector 'tech' concentration 0.4 violates limit of 0.25" in str(excinfo.value)

def test_policy_guard_net_exposure():
    policy = RiskPolicy(max_net_exposure=1.0, crisis_mult=0.5)
    # Crisis -> Limit becomes 0.5
    guard = PolicyGuard(policy=policy, current_vix=40.0)
    
    task = AgentTask(
        tool_name="portfolio_allocate",
        arguments={"net_exposure": 0.75},
        status="pending"
    )
    
    with pytest.raises(PolicyValidationError) as excinfo:
        guard.validate_task(task)
    assert "Net exposure 0.75 violates limit of 0.5" in str(excinfo.value)

def test_policy_guard_effective_limits():
    policy = RiskPolicy(
        max_allocation=0.35, 
        max_leverage=1.2, 
        max_sector_concentration=0.5,
        crisis_mult=0.5
    )
    
    # Normal
    guard_normal = PolicyGuard(policy=policy, current_vix=20.0)
    assert guard_normal.get_effective_limits()["max_allocation"] == 0.35
    
    # ADR (Crisis)
    guard_adr = PolicyGuard(policy=policy, current_vix=40.0)
    assert guard_adr.get_effective_limits()["max_allocation"] == 0.175
    assert guard_adr.get_effective_limits()["max_sector_concentration"] == 0.25

def test_policy_guard_kill_switch():
    policy = RiskPolicy()
    guard = PolicyGuard(policy=policy, kill_switch_active=True)
    
    task = AgentTask(
        tool_name="portfolio_allocate",
        arguments={"allocation": 0.01},
        status="pending"
    )
    
    with pytest.raises(PolicyValidationError) as excinfo:
        guard.validate_task(task)
    assert "Risk Kill-Switch is engaged" in str(excinfo.value)
