"""V5 Graph Runtime — LangGraph-native orchestration for V5 specialist council.

Production-hardened with:
    - Stable SSE wire format
    - approval_required event on interrupt
    - final_output event on completion
    - Streamable resume path
    - Proper thread hydration via graph.aget_state()
    - Full metadata in all events (thread_id, run_id, mode, stage)
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import TYPE_CHECKING, Any, AsyncGenerator

from stratos_orchestrator.application.v5 import (
    V5State,
    build_model,
    build_v5_graph,
    create_checkpointer,
    create_store,
)
from stratos_orchestrator.application.v5.contracts import (
    ApprovalDecision,
    ApprovalRequest,
    DecisionPacketV5,
    V5Mode,
)
from stratos_orchestrator.config import Settings

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.store.base import BaseStore

from stratos_orchestrator.application.v5.tool_sets import (
    build_council_tools,
    build_fast_path_tools,
    build_replay_tools,
    build_research_tools,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 120


class V5GraphRuntime:
    """Strict LangGraph runtime for STRATOS v5 specialist council."""

    def __init__(
        self,
        *,
        settings: Settings,
        tools_registry: Any = None,
        checkpointer: "BaseCheckpointSaver | None" = None,
        store: "BaseStore | None" = None,
        model: Any = None,
    ) -> None:
        self._settings = settings
        self._tools_registry = tools_registry
        self._checkpointer = checkpointer or create_checkpointer(settings)
        self._store = store or create_store(settings)
        self._model = model or build_model(settings)
        self._graph = None
        self._timeout = DEFAULT_TIMEOUT

    async def _ensure_graph(self):
        """Lazily build and compile the graph."""
        if self._graph is None:
            self._graph = build_v5_graph(
                checkpointer=self._checkpointer,
                store=self._store,
                model=self._model,
            )
        return self._graph

    async def execute(
        self,
        *,
        query: str,
        thread_id: str,
        user_id: str,
        workspace_id: str,
        mode: V5Mode | None = None,
        approval_response: ApprovalDecision | None = None,
    ) -> tuple[DecisionPacketV5, dict[str, Any]]:
        """Non-streaming execution — returns final packet and trace."""
        initial_state = self._build_initial_state(
            query=query,
            thread_id=thread_id,
            user_id=user_id,
            workspace_id=workspace_id,
            mode=mode,
        )

        graph = await self._ensure_graph()
        config = {"configurable": {"thread_id": thread_id}}

        if approval_response is not None:
            from langgraph.types import Command
            input_data = Command(resume={"approval": approval_response})
        else:
            input_data = initial_state

        try:
            final_state = await asyncio.wait_for(
                graph.ainvoke(input_data, config=config),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Execution timed out after {self._timeout}s")

        if "__interrupt__" in final_state:
            return self._interrupted_result(final_state)

        packet = DecisionPacketV5.model_validate(final_state["final_packet"])
        trace = final_state.get("trace", {})
        return packet, trace

    async def stream(
        self,
        *,
        query: str,
        thread_id: str,
        user_id: str,
        workspace_id: str,
        mode: V5Mode | None = None,
        approval_response: ApprovalDecision | None = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming execution — yields SSE-formatted strings.

        Yields SSE strings in format: "event: {type}\ndata: {json}\n\n"
        """
        run_id = str(uuid.uuid4())
        
        initial_state = self._build_initial_state(
            query=query,
            thread_id=thread_id,
            user_id=user_id,
            workspace_id=workspace_id,
            mode=mode,
        )

        graph = await self._ensure_graph()
        config = {"configurable": {"thread_id": thread_id}}

        if approval_response is not None:
            from langgraph.types import Command
            input_data = Command(resume={"approval": approval_response})
        else:
            input_data = initial_state

        # Emit initial events with full metadata
        yield self._sse_event("status", {"message": "Initializing STRATOS v5 graph runtime...", "run_id": run_id})
        yield self._sse_event("context", {
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "mode": mode.value if mode else "auto",
            "run_id": run_id,
        })

        last_node = None
        interrupt_emitted = False
        final_output_emitted = False

        try:
            async for event in graph.astream_events(input_data, config=config, version="v2"):
                event_name = event.get("event")
                node_name = event.get("name", "")
                
                # Track current node for metadata
                if event_name == "on_chain_start":
                    last_node = node_name

                # node_start event
                if event_name == "on_chain_start":
                    yield self._sse_event("node_start", {
                        "node": node_name,
                        "run_id": event.get("run_id"),
                        "thread_id": thread_id,
                        "stage": node_name,
                    })

                # node_complete event
                elif event_name == "on_chain_end":
                    yield self._sse_event("node_complete", {
                        "node": node_name,
                        "run_id": event.get("run_id"),
                        "thread_id": thread_id,
                        "stage": last_node,
                    })
                    
                    # Emit final_output when decision_packager completes
                    if node_name == "decision_packager" and not final_output_emitted:
                        output = event.get("data", {}).get("output", {})
                        if output:
                            yield self._sse_event("final_output", {
                                "packet": output,
                                "thread_id": thread_id,
                                "run_id": run_id,
                            })
                            final_output_emitted = True

                # token streaming
                elif event_name == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        # AIMessageChunk has a content attribute, not a dict
                        content = getattr(chunk, "content", None)
                        if content:
                            yield self._sse_event("token", {
                                "content": content,
                                "run_id": run_id,
                                "thread_id": thread_id,
                            })

                # tool events
                elif event_name == "on_tool_start":
                    yield self._sse_event("tool_start", {
                        "tool": event.get("name"),
                        "run_id": event.get("run_id"),
                        "thread_id": thread_id,
                    })
                elif event_name == "on_tool_end":
                    yield self._sse_event("tool_end", {
                        "tool": event.get("name"),
                        "run_id": event.get("run_id"),
                        "thread_id": thread_id,
                    })

                # Detect interrupt from task result
                elif event_name == "on_task_completed":
                    # Check if there's an interrupt in the result
                    pass  # Interrupts handled via state inspection

        except asyncio.TimeoutError:
            yield self._sse_event("error", {
                "message": f"Execution timed out after {self._timeout}s",
                "run_id": run_id,
                "thread_id": thread_id,
            })
            return

        except Exception as exc:
            logger.exception("V5 stream failed")
            yield self._sse_event("error", {
                "message": str(exc),
                "run_id": run_id,
                "thread_id": thread_id,
            })
            return

        # If no final_output was emitted (e.g., fast_path), fetch final state
        if not final_output_emitted:
            try:
                final_state = await graph.aget_state(config)
                if final_state and final_state.values:
                    values = final_state.values
                    if values.get("final_packet"):
                        yield self._sse_event("final_output", {
                            "packet": values["final_packet"],
                            "thread_id": thread_id,
                            "run_id": run_id,
                        })
            except Exception as e:
                logger.warning(f"Could not fetch final state: {e}")

    async def stream_with_state_check(
        self,
        *,
        query: str,
        thread_id: str,
        user_id: str,
        workspace_id: str,
        mode: V5Mode | None = None,
        approval_response: ApprovalDecision | None = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming with explicit interrupt detection via state inspection.
        
        This method runs astream and periodically checks the graph state
        to detect interrupts and emit appropriate events.
        """
        run_id = str(uuid.uuid4())
        
        initial_state = self._build_initial_state(
            query=query,
            thread_id=thread_id,
            user_id=user_id,
            workspace_id=workspace_id,
            mode=mode,
        )

        graph = await self._ensure_graph()
        config = {"configurable": {"thread_id": thread_id}}

        if approval_response is not None:
            from langgraph.types import Command
            input_data = Command(resume={"approval": approval_response})
        else:
            input_data = initial_state

        # Emit initial events
        yield self._sse_event("status", {"message": "Initializing STRATOS v5 graph runtime...", "run_id": run_id})
        yield self._sse_event("context", {
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "mode": mode.value if mode else "auto",
            "run_id": run_id,
        })

        interrupt_emitted = False
        final_output_emitted = False
        
        try:
            # Use astream (not astream_events) to get state updates
            logger.info("V5 stream: starting astream")
            async for state in graph.astream(input_data, config=config):
                logger.info(f"V5 stream: got state: {state.keys() if state else 'None'}")
                # Check for interrupt
                if "__interrupt__" in state and not interrupt_emitted:
                    interrupt_data = state.get("__interrupt__", {})
                    approval_req = interrupt_data.get("approval_request")
                    if approval_req:
                        yield self._sse_event("approval_required", {
                            "approval_request": approval_req,
                            "thread_id": thread_id,
                            "run_id": run_id,
                        })
                        interrupt_emitted = True
                    
                    # Also check for approval_request in state
                    if state.get("approval_request") and not interrupt_emitted:
                        yield self._sse_event("approval_required", {
                            "approval_request": state["approval_request"],
                            "thread_id": thread_id,
                            "run_id": run_id,
                        })
                        interrupt_emitted = True

                # Check for final output from decision_packager
                if state.get("final_packet") and not final_output_emitted:
                    yield self._sse_event("final_output", {
                        "packet": state["final_packet"],
                        "thread_id": thread_id,
                        "run_id": run_id,
                    })
                    final_output_emitted = True

                # Emit node progress from current_stage
                current_stage = state.get("current_stage", "")
                if current_stage:
                    yield self._sse_event("node_progress", {
                        "stage": current_stage,
                        "thread_id": thread_id,
                        "run_id": run_id,
                    })

        except asyncio.TimeoutError:
            yield self._sse_event("error", {
                "message": f"Execution timed out after {self._timeout}s",
                "run_id": run_id,
                "thread_id": thread_id,
            })

        except Exception as exc:
            logger.exception("V5 stream failed")
            yield self._sse_event("error", {
                "message": str(exc),
                "run_id": run_id,
                "thread_id": thread_id,
            })

    async def resume(
        self,
        *,
        thread_id: str,
        approval_response: ApprovalDecision,
    ) -> tuple[DecisionPacketV5, dict[str, Any]]:
        """Resume from an interrupt with approval decision."""
        from langgraph.types import Command

        graph = await self._ensure_graph()
        config = {"configurable": {"thread_id": thread_id}}

        input_data = Command(resume={"approval": approval_response})

        try:
            final_state = await asyncio.wait_for(
                graph.ainvoke(input_data, config=config),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Resume timed out after {self._timeout}s")

        if "__interrupt__" in final_state:
            return self._interrupted_result(final_state)

        packet = DecisionPacketV5.model_validate(final_state["final_packet"])
        trace = final_state.get("trace", {})
        return packet, trace

    async def resume_stream(
        self,
        *,
        thread_id: str,
        approval_response: ApprovalDecision,
    ) -> AsyncGenerator[str, None]:
        """Stream from an interrupt resume with approval decision."""
        from langgraph.types import Command

        run_id = str(uuid.uuid4())
        
        graph = await self._ensure_graph()
        config = {"configurable": {"thread_id": thread_id}}

        input_data = Command(resume={"approval": approval_response})

        yield self._sse_event("status", {"message": "Resuming from approval...", "run_id": run_id})
        yield self._sse_event("context", {
            "thread_id": thread_id,
            "approval_id": approval_response.approval_id,
            "approved": approval_response.approved,
            "run_id": run_id,
        })

        final_output_emitted = False
        
        try:
            async for state in graph.astream(input_data, config=config):
                # Check for final output
                if state.get("final_packet") and not final_output_emitted:
                    yield self._sse_event("final_output", {
                        "packet": state["final_packet"],
                        "thread_id": thread_id,
                        "run_id": run_id,
                    })
                    final_output_emitted = True

                # Emit stage progress
                current_stage = state.get("current_stage", "")
                if current_stage:
                    yield self._sse_event("node_progress", {
                        "stage": current_stage,
                        "thread_id": thread_id,
                        "run_id": run_id,
                    })

        except asyncio.TimeoutError:
            yield self._sse_event("error", {
                "message": f"Resume timed out after {self._timeout}s",
                "run_id": run_id,
                "thread_id": thread_id,
            })

        except Exception as exc:
            logger.exception("V5 stream failed")
            yield self._sse_event("error", {
                "message": str(exc),
                "run_id": run_id,
                "thread_id": thread_id,
            })

        # Signal stream complete
        yield self._sse_event("stream_complete", {
            "run_id": run_id,
            "thread_id": thread_id,
        })

    async def get_thread_state(self, thread_id: str) -> dict[str, Any] | None:
        """Get current state of a thread from checkpointer.
        
        Returns full thread state including:
        - current_stage
        - mode
        - query
        - specialist_signals
        - aggregated_signals
        - research_brief
        - trade_intent
        - risk_verdict
        - approval_request
        - final_packet
        """
        graph = await self._ensure_graph()
        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Use graph.aget_state() for proper state retrieval
            state = await graph.aget_state(config)
            
            if state is None:
                return None

            # Extract channel values
            if hasattr(state, "values") and state.values:
                values = state.values
            elif hasattr(state, "channel_values"):
                values = dict(state.channel_values)
            else:
                values = {}

            # Build comprehensive state response
            thread_state = {
                "thread_id": thread_id,
                "next": state.next if hasattr(state, "next") else None,
            }
            
            # Add all state values
            for key, value in values.items():
                if value is not None:
                    # Serialize Pydantic models
                    if hasattr(value, "model_dump"):
                        thread_state[key] = value.model_dump()
                    elif hasattr(value, "dict"):
                        thread_state[key] = value.dict()
                    else:
                        thread_state[key] = value

            return thread_state

        except Exception:
            logger.exception("Failed to get thread state")
            return None

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _build_initial_state(
        self,
        query: str,
        thread_id: str,
        user_id: str,
        workspace_id: str,
        mode: V5Mode | None = None,
    ) -> V5State:
        """Build initial V5State for the graph."""
        return V5State(
            query=query,
            thread_id=thread_id,
            user_id=user_id,
            workspace_id=workspace_id,
            mode=mode,
            current_stage="entry_guard",
            signals=[],
            aggregated_signals=None,
            research=None,
            trade_intent=None,
            risk_verdict=None,
            final_packet=None,
        )

    def _sse_event(self, event_type: str, data: Any) -> str:
        """Format event for SSE wire format.
        
        Returns: "event: {type}\ndata: {json}\n\n"
        """
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    def _interrupted_result(self, final_state: dict[str, Any]) -> tuple[DecisionPacketV5, dict[str, Any]]:
        """Handle interrupt — return ApprovalRequest for HITL."""
        # Try multiple sources for approval request
        approval_req = None
        
        # Check __interrupt__ key
        interrupt_data = final_state.get("__interrupt__", {})
        if interrupt_data:
            approval_req = interrupt_data.get("approval_request")
        
        # Check approval_request in state
        if not approval_req:
            approval_req = final_state.get("approval_request")

        # Try to parse as ApprovalRequest
        approval_req_dict = {}
        if approval_req and isinstance(approval_req, dict):
            approval_req_dict = approval_req
            try:
                approval_req = ApprovalRequest(**approval_req)
            except Exception:
                pass

        trace = {
            "status": "interrupted",
            "approval_request": approval_req_dict,
        }

        thesis = ""
        if approval_req_dict:
            thesis = approval_req_dict.get("thesis", "Approval required")

        empty_packet = DecisionPacketV5(
            action="pending_approval",
            confidence=0.0,
            score=0.0,
            thesis=thesis,
        )

        return empty_packet, trace


# ---------------------------------------------------------------------------
# Factory for dependency injection
# ---------------------------------------------------------------------------


def create_v5_runtime(settings: Settings) -> V5GraphRuntime:
    """Factory to create V5GraphRuntime instance."""
    return V5GraphRuntime(settings=settings)