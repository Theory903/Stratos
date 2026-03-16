"""Policy analysis tool."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class PolicyTool(HttpTool):
    """Tool for analyzing financial policy and regulations."""

    @property
    def name(self) -> str:
        return "policy_analyze"

    @property
    def description(self) -> str:
        return (
            "Search for and analyze relevant financial policy documents. "
            "Useful for understanding regulatory constraints."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Policy query/topic (e.g., 'Basel III capital requirements')",
                },
                "limit": {
                    "type": "integer",
                    "default": 3,
                },
            },
            "required": ["query"],
        }

    async def execute(self, arguments: dict) -> dict:
        query = arguments["query"]
        limit = arguments.get("limit", 3)

        try:
            # Determine sentiment of query first?
            # Or just RAG search
            docs = await self._request("POST", "/rag/search", json={"query": query, "limit": limit})
            return {"relevant_policies": docs}
        except Exception as e:
            return {"error": f"Failed to analyze policy: {e}"}
