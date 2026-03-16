# Fix Plan: Orchestrator Service NameError Issues

## Problem Summary

The orchestrator service is failing with `NameError` exceptions when handling requests:

1. **`NameError: name 'OrchestrateUseCase' is not defined`** in [`deps.py:64`](orchestrator/src/stratos_orchestrator/api/deps.py:64)
2. **`NameError: name 'HttpTool' is not defined`** in multiple tool files

## Root Cause Analysis

### Issue 1: Missing newline after import statement

In [`portfolio_tool.py`](orchestrator/src/stratos_orchestrator/adapters/tools/portfolio_tool.py) and [`geopolitics_tool.py`](orchestrator/src/stratos_orchestrator/adapters/tools/geopolitics_tool.py), the import statement and class definition are on consecutive lines without a blank line separator:

```python
# portfolio_tool.py (lines 5-7)
    
from stratos_orchestrator.adapters.tools.base import HttpTool
class PortfolioTool(HttpTool):  # <- No blank line between import and class
```

```python
# geopolitics_tool.py (lines 5-7)

from stratos_orchestrator.adapters.tools.base import HttpTool
class GeopoliticsTool(HttpTool):  # <- No blank line between import and class
```

While Python doesn't strictly require blank lines after imports, this can cause issues with some Python parsers and linters. More importantly, the error suggests the import is not being processed correctly.

### Issue 2: Potential circular import or module loading issue

The `OrchestrateUseCase` is properly imported in [`deps.py:12`](orchestrator/src/stratos_orchestrator/api/deps.py:12):
```python
from stratos_orchestrator.application.orchestrate import OrchestrateUseCase
```

And the class exists in [`orchestrate.py`](orchestrator/src/stratos_orchestrator/application/orchestrate.py). The error at runtime suggests a module loading order issue.

## Fix Plan

### Step 1: Fix formatting in portfolio_tool.py

Add a blank line after the import statement:

```python
# Before (lines 5-7):

from stratos_orchestrator.adapters.tools.base import HttpTool
class PortfolioTool(HttpTool):

# After:

from stratos_orchestrator.adapters.tools.base import HttpTool


class PortfolioTool(HttpTool):
```

### Step 2: Fix formatting in geopolitics_tool.py

Add a blank line after the import statement:

```python
# Before (lines 5-7):

from stratos_orchestrator.adapters.tools.base import HttpTool
class GeopoliticsTool(HttpTool):

# After:

from stratos_orchestrator.adapters.tools.base import HttpTool


class GeopoliticsTool(HttpTool):
```

### Step 3: Verify all tool files have consistent formatting

Ensure all tool files in `orchestrator/src/stratos_orchestrator/adapters/tools/` follow the same pattern with proper blank lines after imports.

### Step 4: Restart the orchestrator service

After making the changes, restart the Docker container:
```bash
docker-compose restart orchestrator
```

## Files to Modify

| File | Change |
|------|--------|
| [`portfolio_tool.py`](orchestrator/src/stratos_orchestrator/adapters/tools/portfolio_tool.py:6-7) | Add blank line after import |
| [`geopolitics_tool.py`](orchestrator/src/stratos_orchestrator/adapters/tools/geopolitics_tool.py:6-7) | Add blank line after import |

## Verification

After applying fixes, verify by:
1. Checking orchestrator logs for successful startup
2. Testing the `/orchestrate` and `/orchestrate/stream` endpoints
3. Confirming no `NameError` exceptions in logs
