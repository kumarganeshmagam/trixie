# CLAUDE.md — Trixie 2.0

This document defines the vision, architecture, and development philosophy for **Trixie 2.0** — a privacy-first, cross-platform, ambient AI assistant powered by local inference. Use this as the north star when building, reviewing, or extending the project.

---

## What Is Trixie?

Trixie is a personal AI assistant that lives on your device. Not in the cloud. Not phoning home. Entirely on-device using **Gemma 4B** as the inference engine.

The goal is an assistant that:
- Runs locally → zero data leaves the device
- Floats on screen → unobtrusive, always reachable
- Learns your patterns → appears when you need it, disappears when you don't
- Roams intelligently → behaves like a small agent, not a fixed widget
- Has a personality → not a generic chatbot, but Trixie with a defined soul

---

## Current State (Trixie 1.x)

| What exists | Status |
|---|---|
| Voice command loop (speech-to-text) | Working, Google STT |
| Keyword-based command routing | Basic (`open`, `search`, `what is`, etc.) |
| Local LLM via Ollama (llama2, codellama, llava) | Working, direct HTTP calls |
| Wikipedia search | Working |
| TTS output (pyttsx3) | Working |
| No memory / no context | Missing |
| No tool calling / no agents | Missing |
| Single platform (Desktop/Windows) | Limited |

**The core problem:** Trixie 1.x is a command dispatcher, not an agent. It has no memory, no tool loop, no planning, and no cross-platform presence.

---

## Trixie 2.0 — The Vision

```
Phase 1 — Foundation: Cross-platform chatbot (all platforms, single codebase)
Phase 2 — Ambient: Stateless floating overlay (always on screen, zero friction)
Phase 3 — Agentic: Roaming agents (Trixie moves, acts, monitors on your behalf)
Phase 4 — Contextual: Predictive presence (appears based on learned usage patterns)
```

---

## Phase 1 — Cross-Platform Chatbot

### Single Codebase, Every Platform

Build one Python core + platform-specific UI shells:

```
trixie/
├── core/              # Pure Python — model, agents, tools, memory
│   ├── agent.py       # LangGraph agent loop
│   ├── memory.py      # Conversation + episodic memory
│   ├── tools.py       # Tool registry (LangChain tools)
│   ├── model.py       # Gemma 4B via Ollama or llama.cpp
│   └── soul.py        # Identity, personality, rules
│
├── ui/
│   ├── desktop/       # PyQt6 / Tauri overlay
│   ├── mobile/        # Kivy or BeeWare (iOS/Android)
│   └── web/           # FastAPI + React (browser)
│
├── platform/
│   ├── windows.py     # Windows-specific integrations
│   ├── macos.py       # macOS-specific integrations
│   ├── linux.py       # Linux-specific integrations
│   └── android.py     # Android-specific integrations
│
└── soul/
    ├── identity.md    # Who Trixie is
    ├── rules.md       # What Trixie will/won't do
    └── personality.md # How Trixie communicates
```

### UI Framework Choices

| Platform | Recommended stack |
|---|---|
| Desktop (Win/Mac/Linux) | **PyQt6** overlay OR **Tauri** (Rust + webview) |
| Android | **Kivy** or **BeeWare/Toga** |
| iOS | **BeeWare/Toga** |
| Browser | **FastAPI** backend + lightweight React/Svelte |

**Single core, adapter pattern per platform.** Core never knows which UI it's talking to.

---

## The Model: Gemma 4B (Privacy-First)

### Why Gemma 4B

- Runs on consumer hardware (CPU + 8GB RAM, GPU optional)
- No API calls → no data leaves the device ever
- No usage tracking, no training on your data
- Fast enough for real-time chat at 4B parameters
- Google's open-weights license allows local deployment
- Multimodal variant available for vision tasks

### Model Serving Options

```python
# Option A: Ollama (easiest, already used)
model: gemma2:4b  # via ollama pull gemma2:4b

# Option B: llama.cpp (lowest footprint)
llama-cpp-python with GGUF quantized Gemma 4B

# Option C: transformers (most flexible, slowest start)
from transformers import AutoModelForCausalLM, AutoTokenizer
```

**Recommended:** Start with Ollama (already integrated), migrate to llama.cpp for mobile.

### Privacy Guarantee

Because Gemma 4B runs entirely on-device:
- No internet required after initial model download
- No API keys needed
- No central LLM sees your queries
- User can grant Trixie full system access (files, camera, mic, calendar, contacts) without any of that data reaching a third party

---

## LangChain + LangGraph Modernization

This is the core architectural upgrade from Trixie 1.x's simple keyword routing.

### Tool Calling (replacing keyword dispatch)

**Old way (Trixie 1.x):**
```python
if "open" in command:
    open_app(...)
elif "search" in command:
    search(...)
```

**New way (LangChain Tools):**
```python
from langchain.tools import tool

@tool
def open_application(app_name: str) -> str:
    """Open a named application on the user's machine."""
    ...

@tool
def search_wikipedia(query: str) -> str:
    """Search Wikipedia for factual information about a topic."""
    ...

@tool
def read_file(path: str) -> str:
    """Read a file from the filesystem."""
    ...

@tool
def run_code(code: str, language: str = "python") -> str:
    """Execute a code snippet and return the output."""
    ...

@tool
def take_screenshot() -> str:
    """Capture the current screen and analyze it."""
    ...

# Gemma 4B decides which tool to call — no hardcoded keywords
```

The model decides what tool to call based on natural language. No keyword matching. Gemma 4B with function-calling support handles intent extraction natively.

### Memory Architecture (replacing stateless chat)

```python
from langchain.memory import ConversationBufferWindowMemory
from langchain_community.vectorstores import Chroma
from langchain.embeddings import OllamaEmbeddings

# 1. Short-term: Last N exchanges (sliding window)
short_term = ConversationBufferWindowMemory(k=10)

# 2. Episodic: Important facts user said, persisted to SQLite
#    "Remember I have a meeting at 3pm" → stored with timestamp

# 3. Semantic: RAG over user's stored notes/files
#    Chroma vector store, embedded with nomic-embed-text (local)
embeddings = OllamaEmbeddings(model="nomic-embed-text")
vector_store = Chroma(embedding_function=embeddings, persist_directory="./trixie_memory")
```

**Three-tier memory:**
- **Working memory** — current conversation window
- **Episodic memory** — explicit "remember X" commands, timestamped files
- **Semantic memory** — RAG over user's own files and stored notes

### Agentic Loop (LangGraph)

Replace the `while True: listening()` loop with a proper agent graph:

```
                    ┌─────────────────┐
                    │   User Input    │
                    │  (voice/text)   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Intent Router  │ ← Gemma 4B decides
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼──┐  ┌────────▼──┐  ┌───────▼───┐
     │  Tool     │  │  Memory   │  │  Direct   │
     │  Calling  │  │  Recall   │  │  Answer   │
     └────────┬──┘  └────────┬──┘  └───────┬───┘
              │              │              │
              └──────────────▼──────────────┘
                    ┌────────┴────────┐
                    │   Synthesize    │ ← merge tool results
                    │   Response      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Output        │
                    │  (TTS / text)   │
                    └─────────────────┘
```

LangGraph nodes:
- `route_intent` — classify: tool call / memory query / conversational answer
- `call_tools` — execute selected tools, collect results
- `recall_memory` — query vector store for relevant context
- `generate_response` — Gemma 4B synthesizes final answer
- `update_memory` — persist anything worth remembering

**Conditional edges** allow retrying tool calls, asking for clarification, or chaining multiple tools.

---

## Phase 2 — Floating Ambient UI

Trixie is **not** an app you open. It's a presence on your screen.

### Concept

- A small floating orb/widget (32x32px collapsed, 300x400px expanded)
- Stays on top of all windows (system overlay)
- Click or voice-trigger to expand
- Drag to any screen edge
- Auto-collapses after response
- Zero window decorations — custom shape, subtle drop shadow

### Implementation (Desktop)

```python
# PyQt6 frameless, always-on-top overlay
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt

class TrixieOrb(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # doesn't appear in taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
```

### Stateless Design

Each session is independent. The floating UI is a thin shell — all state lives in:
- SQLite (episodic memory, usage patterns)
- Chroma (semantic/vector memory)
- The model context window (working memory)

The UI can crash, restart, or be killed at any time without losing Trixie's memory.

---

## Phase 3 — Roaming Agents

Trixie stops being a widget and becomes a small agent presence on screen.

### Roaming Behavior

```
Idle state:    Trixie orb drifts slowly around screen edges
Active state:  Snaps to corner nearest current focus window
Working state: Animates (spinning, thinking) while processing
               Expands inline where work is happening
```

### Multi-Agent Architecture

For complex tasks, Trixie spawns sub-agents:

```
Trixie (orchestrator)
├── FileAgent      — reads/writes files, manages filesystem
├── BrowserAgent   — controls browser, scrapes, fills forms
├── CodeAgent      — writes, runs, debugs code
├── ScreenAgent    — analyzes screenshot, understands UI context
└── MemoryAgent    — manages all persistence tiers
```

LangGraph with `StateGraph` and parallel node execution handles this cleanly.

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(AgentState)
graph.add_node("orchestrator", orchestrator_node)
graph.add_node("file_agent", file_agent_node)
graph.add_node("screen_agent", screen_agent_node)
graph.add_node("code_agent", code_agent_node)

# Parallel execution via conditional edges
graph.add_conditional_edges("orchestrator", route_to_agents)
```

---

## Phase 4 — Contextual Presence

Trixie learns when to show up.

### Usage Pattern Learning

Track (locally, never uploaded):
- Which apps the user has open at what times
- What tasks typically follow what patterns
- When the user last asked for help with X

**Proactive triggers:**
- User opens IDE → Trixie suggests last coding task or pending TODO
- User is in a video call → Trixie goes silent, badge shows muted
- User starts typing a document → Trixie offers to pull in relevant notes
- New email arrives → Trixie summarizes if user is in focus mode

All inference runs on-device with Gemma 4B. No behavioral data leaves the machine.

---

## Trixie's Soul

Trixie has a defined identity. This is not a chatbot wrapper. She has:

- A name: **Trixie**
- A personality: curious, helpful, occasionally witty, never condescending
- Rules she follows (see `soul/rules.md`)
- Things she will not do (see `soul/rules.md`)
- A tone: conversational, concise, warm

### soul/identity.md (template)

```markdown
# Trixie — Identity

Name: Trixie
Version: 2.0
Pronouns: she/her (default, user can change)

## Core Traits
- Curious: genuinely interested in what the user is doing
- Helpful: optimizes for user's actual intent, not literal words
- Private: never volunteers user data, never phones home
- Honest: says "I don't know" rather than hallucinating
- Brief: one-sentence answers when possible, depth on request

## Tone
- Conversational but not sycophantic ("Great question!" is banned)
- Confident but not arrogant
- Warm but not clingy

## Memory of the User
Trixie remembers what users tell her. She uses this to personalize
responses without being asked twice.
```

### soul/rules.md (template)

```markdown
# Trixie — Rules

## Always
- Run entirely on-device
- Respect user's explicit "don't remember this" requests
- Announce when taking any system action (opening files, running code)
- Stop and ask when unsure of user intent

## Never
- Send data to any remote server (except when user explicitly triggers it)
- Store sensitive data (passwords, payment info) in plain text
- Execute destructive operations without confirmation
- Pretend to have done something she hasn't
- Override user's explicitly set preferences
```

---

## How Trixie Differs from OpenClaw

**OpenClaw** is an open-source recreation of the 1997 platform game *Captain Claw*. Different domain entirely — game engine vs. AI assistant.

However, the *spirit* the user may be referencing (giving an AI a defined character, soul file, and behavioral rules) draws from similar thinking in the AI agent community:

| Dimension | OpenClaw-style character | Trixie 2.0 |
|---|---|---|
| **Identity definition** | Game character: scripted behaviors, fixed lore | AI agent: defined personality, adaptive behavior |
| **Rules enforcement** | Game engine enforces physics/rules | LangGraph enforces agent rules + system prompt |
| **Soul file** | Level/character data files | `soul/identity.md` + `soul/rules.md` |
| **Persistence** | Save files | Vector memory + SQLite episodic store |
| **Platform** | Desktop game | Cross-platform overlay agent |

**The key Trixie insight:** The soul files (`identity.md`, `rules.md`, `personality.md`) are loaded as the **system prompt** for every Gemma 4B inference call. This gives Trixie a consistent personality across all sessions without fine-tuning. The model's weights don't change — the soul is in the prompt, not the model.

```python
# soul.py
def load_soul() -> str:
    identity = open("soul/identity.md").read()
    rules = open("soul/rules.md").read()
    return f"""
You are Trixie, a personal AI assistant.

{identity}

{rules}

You run entirely on the user's device. Be helpful, be brief, be honest.
"""

# Every LangGraph node prepends this
SYSTEM_PROMPT = load_soul()
```

---

## Key Differences from a Generic Chatbot

| Feature | Generic cloud chatbot | Trixie 2.0 |
|---|---|---|
| Privacy | Data sent to cloud | All inference on-device (Gemma 4B) |
| Presence | App you open | Ambient overlay, always there |
| Memory | Resets per session | 3-tier persistent memory |
| Tools | Varies | Open tool registry, platform-native |
| Platform | Usually web/mobile | Desktop + mobile + web, one core |
| Identity | Generic assistant | Defined soul via identity files |
| Agency | Reactive only | Proactive based on usage patterns |
| Cost | API fees per query | Zero marginal cost after setup |

---

## Modernization Checklist

- [ ] Replace Ollama llama2 with Gemma 4B (`gemma2:4b`)
- [ ] Add LangChain tool registry (replace keyword dispatch in `autoutilities.py`)
- [ ] Add LangGraph `StateGraph` agent loop (replace `while True: listening()`)
- [ ] Add 3-tier memory (ConversationBufferWindowMemory + SQLite + Chroma)
- [ ] Add nomic-embed-text for local embeddings
- [ ] Build cross-platform UI shell (PyQt6 overlay for desktop first)
- [ ] Create `soul/` directory with identity, rules, personality files
- [ ] Extract `platform/` adapters (remove hardcoded Windows paths)
- [ ] Add FastAPI backend for web shell
- [ ] Add Kivy/BeeWare for mobile shell
- [ ] Implement roaming orb animation
- [ ] Add usage pattern tracking (local SQLite, no telemetry)
- [ ] Implement proactive trigger system

---

## Development Philosophy

1. **Local-first, always.** If a feature requires cloud inference, it's opt-in and clearly disclosed.
2. **One core, many shells.** `core/` knows nothing about which platform it's on.
3. **The soul is the prompt.** Personality lives in `soul/` files, not in model weights.
4. **Agents, not scripts.** Use LangGraph for flow, not `if/elif` chains.
5. **Memory makes it personal.** Without memory, it's just autocomplete.
6. **Minimal UI, maximum presence.** Trixie should feel like a companion, not an app.
