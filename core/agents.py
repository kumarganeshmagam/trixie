"""
Trixie 2.0 — Multi-agent orchestration (Phase 3).

For complex tasks Trixie delegates to specialised sub-agents, each of which
is a small LangGraph ReAct loop with a focused tool subset and its own
role instruction:

    Trixie (orchestrator)
    ├── FileAgent    — reads/writes files
    ├── CodeAgent    — writes and runs code
    ├── ScreenAgent  — looks at the screen (vision must be on)
    └── MemoryAgent  — stores and recalls long-term memory

The orchestrator is itself an LLM node: it reads the user request, decides
which sub-agents are needed (possibly several), runs them, then synthesises
a single answer. Every delegation is logged to memory/decisions.jsonl.

For simple requests the main single-graph agent (core/agent.py) is enough;
the orchestrator is for multi-step work ("read that file, fix the bug in
it, and remember what changed").
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from core.decisions import log_decision
from core.tools import (
    look_at_screen,
    open_application,
    read_file,
    recall_facts,
    remember_fact,
    run_python_code,
    search_wikipedia,
    write_file,
)


# ── Sub-agent definitions ──────────────────────────────────────────────────────

@dataclass
class SubAgentSpec:
    name: str
    role: str
    tools: list = field(default_factory=list)


SUB_AGENTS: dict[str, SubAgentSpec] = {
    "file_agent": SubAgentSpec(
        name="FileAgent",
        role=(
            "You are Trixie's FileAgent. You handle reading and writing files "
            "on the user's machine. Do exactly what the task asks, then report "
            "what you did in one or two sentences."
        ),
        tools=[read_file, write_file, open_application],
    ),
    "code_agent": SubAgentSpec(
        name="CodeAgent",
        role=(
            "You are Trixie's CodeAgent. You write and execute Python code to "
            "solve the task. Run the code to verify it works, then report the "
            "result concisely."
        ),
        tools=[run_python_code, read_file, write_file],
    ),
    "screen_agent": SubAgentSpec(
        name="ScreenAgent",
        role=(
            "You are Trixie's ScreenAgent. You look at the user's screen "
            "(only if vision is enabled) and describe or analyse what is "
            "there. If vision is off, say so and stop."
        ),
        tools=[look_at_screen],
    ),
    "memory_agent": SubAgentSpec(
        name="MemoryAgent",
        role=(
            "You are Trixie's MemoryAgent. You store facts into long-term "
            "memory and recall them. Confirm what was stored or found."
        ),
        tools=[remember_fact, recall_facts, search_wikipedia],
    ),
}


# ── Sub-agent graph (small ReAct loop) ─────────────────────────────────────────

class _SubState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]


def _build_sub_graph(llm, spec: SubAgentSpec):
    llm_with_tools = llm.bind_tools(spec.tools)

    def llm_node(state: _SubState):
        messages = [SystemMessage(content=spec.role)] + list(state["messages"])
        return {"messages": [llm_with_tools.invoke(messages)]}

    def route(state: _SubState) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    graph = StateGraph(_SubState)
    graph.add_node("llm", llm_node)
    graph.add_node("tools", ToolNode(spec.tools))
    graph.set_entry_point("llm")
    graph.add_conditional_edges("llm", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "llm")
    return graph.compile()


# ── Orchestrator ───────────────────────────────────────────────────────────────

_PLAN_PROMPT = (
    "You are Trixie's orchestrator. Given the user's request, decide which "
    "specialist agents are needed and what each should do.\n\n"
    "Available agents:\n"
    "  file_agent   — read/write files, open apps\n"
    "  code_agent   — write and run Python code\n"
    "  screen_agent — describe the user's screen (vision)\n"
    "  memory_agent — store/recall long-term memory, look up facts\n\n"
    "Respond with ONE line per delegation, in execution order, formatted as:\n"
    "  agent_name: task description\n"
    "Use only the agent names above. Use as few agents as possible — often "
    "just one. No other text."
)


class Orchestrator:
    """
    Plans a request into sub-agent tasks, runs each sub-agent in order
    (results are threaded into the next task), and synthesises one answer.
    """

    def __init__(self, llm) -> None:
        self._llm = llm
        self._sub_graphs = {
            key: _build_sub_graph(llm, spec) for key, spec in SUB_AGENTS.items()
        }

    def _plan(self, request: str) -> list[tuple[str, str]]:
        response = self._llm.invoke(
            [SystemMessage(content=_PLAN_PROMPT), HumanMessage(content=request)]
        )
        steps: list[tuple[str, str]] = []
        for line in str(response.content).splitlines():
            if ":" not in line:
                continue
            name, task = line.split(":", 1)
            name = name.strip().lower().replace("-", "_")
            if name in SUB_AGENTS and task.strip():
                steps.append((name, task.strip()))
        return steps or [("memory_agent", request)]

    def run(self, request: str) -> str:
        steps = self._plan(request)

        log_decision(
            trigger=f"complex request: {request[:120]}",
            decision="delegate to sub-agents: "
            + ", ".join(f"{SUB_AGENTS[n].name}({t[:40]})" for n, t in steps),
            reasoning="Orchestrator planned the request into specialist tasks.",
            context_used=[f"{len(steps)} step plan"],
        )

        results: list[str] = []
        for name, task in steps:
            context = ("\nEarlier results:\n" + "\n".join(results)) if results else ""
            out = self._sub_graphs[name].invoke(
                {"messages": [HumanMessage(content=task + context)]}
            )
            last = out["messages"][-1]
            results.append(f"[{SUB_AGENTS[name].name}] {last.content}")

        if len(results) == 1:
            return results[0].split("] ", 1)[-1]

        synthesis = self._llm.invoke(
            [
                SystemMessage(
                    content="You are Trixie. Combine the sub-agent results below "
                    "into one concise answer for the user. Don't mention the agents."
                ),
                HumanMessage(content=f"Request: {request}\n\n" + "\n\n".join(results)),
            ]
        )
        return str(synthesis.content)


def looks_complex(message: str) -> bool:
    """
    Heuristic: does this request likely need multi-agent orchestration?
    Multi-step phrasing ("and then", multiple verbs across domains) → yes.
    """
    lower = message.lower()
    connectors = sum(lower.count(c) for c in (" and ", " then ", " after that", ";"))
    domains = sum(
        any(w in lower for w in words)
        for words in (
            ("file", "read", "write", "save", "open"),
            ("code", "script", "run", "execute", "program"),
            ("screen", "looking", "see"),
            ("remember", "recall", "memory"),
        )
    )
    return connectors >= 1 and domains >= 2
