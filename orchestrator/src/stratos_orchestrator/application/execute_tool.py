"""Application Use Case: Execute Tool.

Executes a single tool task.
"""

from __future__ import annotations

from stratos_orchestrator.domain.entities import AgentTask, TaskStatus
from stratos_orchestrator.domain.ports import ToolExecutor
from stratos_orchestrator.logging import get_logger

from stratos_orchestrator.domain.services.policy import PolicyGuard, PolicyValidationError

logger = get_logger(__name__)

class ExecuteToolUseCase:
    """Execute a specific tool with Governance Firewall (Subsystem G)."""

    def __init__(self, executor: ToolExecutor, guard: PolicyGuard | None = None) -> None:
        self.executor = executor
        self.guard = guard or PolicyGuard()

    async def execute(self, task: AgentTask, vix: float = 20.0, correlation: float = 0.5, stability: float = 1.0) -> AgentTask:
        # Update status
        task.status = TaskStatus.EXECUTING
        
        try:
            # Intercept with Governance Firewall
            if self.guard:
                # Update guard with current indicators for this execution
                self.guard.current_vix = vix
                self.guard.current_correlation = correlation
                self.guard.regime_stability = stability
                self.guard.validate_task(task)
                
            logger.info("executing_tool", tool=task.tool_name, args=task.arguments, regime=self.guard.get_system_regime() if self.guard else "N/A")
            result = await self.executor.execute(task.tool_name, task.arguments)
            task.result = result
            task.status = TaskStatus.COMPLETED
        except PolicyValidationError as e:
            logger.warning("risk_policy_violation", tool=task.tool_name, error=str(e))
            task.error = f"RISK POLICY VIOLATION: {str(e)}"
            task.status = TaskStatus.FAILED
        except Exception as e:
            logger.error("tool_failed", tool=task.tool_name, error=str(e))
            task.error = str(e)
            task.status = TaskStatus.FAILED
            
        return task
