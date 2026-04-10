"""
Trixie 2.0 — LangGraph agent loop.

Graph (ReAct pattern):

    user input
        │
        ▼
  ┌─────────────┐      tool calls?      ┌──────────────┐
  │     llm     │ ─── yes ──────────── ▶│  tool_node   │
  │  (Gemma 4B) │ ◀── tool results ─── │ (executes    │
  └─────────────┘                       │  all tools)  │
        │ no tool calls                 └──────────────┘
        ▼
      END  →  response returned to caller

Pre-graph:
  1. detect_emotion   — infers user state (frustrated / tired / etc.)
  2. retrieve_context — fetches relevant episodic + semantic memory
  3. build_system_prompt — loads soul + injects context + emotion hint

Post-graph:
  1. update_working_memory — stores user + assistant messages
  2. observe (evolution)   — logs interaction for adaptation tracking
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from core.empathy import detect_emotion, shape_response_instruction
from core.evolution import Interaction, observe
from core.memory import WorkingMemory, retrieve_context
from core.soul import build_system_prompt
from core.tools import ALL_TOOLS


# ── Agent state ────────────────────────────────────────────────────────────────

class TrixieState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    emotion: str
    memory_context: str


# ── Graph nodes ────────────────────────────────────────────────────────────────

def _llm_node(state: TrixieState, llm_with_tools):
    """Call the LLM with soul-enriched system prompt + conversation history."""
    emotion_hint = shape_response_instruction(state.get("emotion", "neutral"))
    system_text = build_system_prompt(
        memory_context=state.get("memory_context", ""),
        emotion=state.get("emotion", "neutral"),
    )
    if emotion_hint:
        system_text += f"\n\n{emotion_hint}"

    messages = [SystemMessage(content=system_text)] + list(state["messages"])
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def _route(state: TrixieState) -> str:
    """If the last message has tool calls, run them; otherwise finish."""
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


# ── Graph builder ──────────────────────────────────────────────────────────────

def build_graph(llm):
    """
    Compile and return the Trixie LangGraph.

    Args:
        llm: A LangChain chat model (ChatOllama or LlamaCpp).
    """
    llm_with_tools = llm.bind_tools(ALL_TOOLS)
    tool_node = ToolNode(ALL_TOOLS)

    graph = StateGraph(TrixieState)
    graph.add_node("llm", lambda s: _llm_node(s, llm_with_tools))
    graph.add_node("tools", tool_node)

    graph.set_entry_point("llm")
    graph.add_conditional_edges("llm", _route, {"tools": "tools", END: END})
    graph.add_edge("tools", "llm")

    return graph.compile()


# ── High-level agent wrapper ───────────────────────────────────────────────────

class TrixieAgent:
    """
    Stateful wrapper around the compiled LangGraph.

    Handles:
      • Working memory (sliding-window conversation buffer)
      • Emotion detection  (before every turn)
      • Memory retrieval   (before every turn)
      • Evolution tracking (after every turn)
    """

    def __init__(self, llm) -> None:
        self._graph = build_graph(llm)
        self._working_memory = WorkingMemory()

    def chat(self, user_input: str) -> str:
        """
        Process one user turn and return Trixie's response text.

        Side-effects:
          • Updates working memory
          • Logs the interaction via evolution.observe()
        """
        # ── Pre-turn enrichment ────────────────────────────────────────────────
        emotion_signal = detect_emotion(user_input)
        emotion = emotion_signal.state
        memory_context = retrieve_context(user_input)

        # Rebuild message list from working memory
        history: list[BaseMessage] = []
        for msg in self._working_memory.messages():
            if msg["role"] == "user":
                history.append(HumanMessage(content=msg["content"]))
            else:
                history.append(AIMessage(content=msg["content"]))
        history.append(HumanMessage(content=user_input))

        # ── Run the graph ──────────────────────────────────────────────────────
        result = self._graph.invoke(
            TrixieState(
                messages=history,
                emotion=emotion,
                memory_context=memory_context,
            )
        )

        # ── Extract response ───────────────────────────────────────────────────
        last = result["messages"][-1]
        response_text = last.content if hasattr(last, "content") else str(last)

        # ── Post-turn updates ──────────────────────────────────────────────────
        self._working_memory.add("user", user_input)
        self._working_memory.add("assistant", response_text)

        observe(
            Interaction(
                user_message=user_input,
                trixie_response=response_text,
                outcome="unknown",   # caller can update via evolution.observe()
                emotion=emotion,
            )
        )

        return response_text

    def reset_working_memory(self) -> None:
        """Clear the in-session conversation buffer (long-term memory is unaffected)."""
        self._working_memory.clear()
