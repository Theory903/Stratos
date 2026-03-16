"""Test PlanTasks use case."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from stratos_orchestrator.application.plan_tasks import PlanTasksUseCase
from stratos_orchestrator.domain.entities import AgentTask, TaskStatus
from stratos_orchestrator.domain.ports import LLMProvider, ToolExecutor

@pytest.mark.asyncio
async def test_plan_tasks_success():
    # Arrange
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.generate_structured = AsyncMock(return_value={
        "reasoning": "Test reasoning",
        "tasks": [
            {"tool_name": "mock_tool", "arguments": {"arg": 1}}
        ]
    })
    
    mock_tools = MagicMock(spec=ToolExecutor)
    mock_tools.get_schemas.return_value = [{"name": "mock_tool", "description": "desc", "parameters": {}}]
    
    use_case = PlanTasksUseCase(mock_llm, mock_tools)
    
    # Act
    plan = await use_case.execute("Test query")
    
    # Assert
    assert plan.query == "Test query"
    assert plan.reasoning == "Test reasoning"
    assert len(plan.tasks) == 1
    assert plan.tasks[0].tool_name == "mock_tool"
    assert plan.tasks[0].arguments == {"arg": 1}
    assert plan.tasks[0].status == TaskStatus.PENDING

@pytest.mark.asyncio
async def test_plan_tasks_handles_error():
    # Arrange
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.generate_structured = AsyncMock(side_effect=Exception("LLM Fail"))
    
    mock_tools = MagicMock(spec=ToolExecutor)
    mock_tools.get_schemas.return_value = []
    
    use_case = PlanTasksUseCase(mock_llm, mock_tools)
    
    # Act
    plan = await use_case.execute("Test query")
    
    # Assert
    assert "Failed to plan" in plan.reasoning
    assert len(plan.tasks) == 0
