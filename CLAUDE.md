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
Phase 1 — Foundation:   Cross-platform chatbot (all platforms, single codebase)
Phase 2 — Ambient:      Stateless floating overlay (always on screen, zero friction)
Phase 3 — Agentic:      Roaming agents (Trixie moves, acts, monitors on your behalf)
Phase 4 — Contextual:   Predictive presence (appears based on learned usage patterns)
Phase 5 — Aware:        Vision system (Trixie sees what you're doing, togglable)
Phase 6 — Living:       Evolving soul (adapts to the user, explains her decisions)
```

---

## Phase 1 — Cross-Platform Chatbot

### Single Codebase, Every Platform

Build one Python core + platform-specific UI shells:

```
trixie/
├── core/
│   ├── agent.py           # LangGraph agent loop
│   ├── memory.py          # Conversation + episodic memory
│   ├── tools.py           # Tool registry (LangChain tools)
│   ├── model.py           # Gemma 4B via Ollama or llama.cpp
│   ├── soul.py            # Loads soul + memory → system prompt
│   ├── vision.py          # Screen capture, user activity awareness
│   ├── evolution.py       # Tracks how Trixie adapts to this user
│   ├── decisions.py       # Decision logging + explainability
│   └── empathy.py         # Emotional tone detection + response shaping
│
├── ui/
│   ├── desktop/           # PyQt6 animated character overlay
│   ├── mobile/            # Kivy or BeeWare (iOS/Android)
│   └── web/               # FastAPI + React (browser)
│
├── platform/
│   ├── windows.py
│   ├── macos.py
│   ├── linux.py
│   └── android.py
│
├── soul/                  # Trixie's identity — loaded as system prompt
│   ├── identity.md        # Who Trixie is
│   ├── rules.md           # What Trixie will/won't do
│   ├── personality.md     # How Trixie communicates
│   └── adaptations.md     # Auto-updated: discovered user preferences
│
└── memory/                # Everything Trixie has learned about THIS user
    ├── episodic/          # Timestamped fact files (YYYY-MM-DD.jsonl)
    ├── semantic/          # Chroma vector store
    ├── evolution/         # How Trixie has grown with this user
    │   ├── milestones.md  # Notable moments ("first time user trusted Trixie to edit files")
    │   └── patterns.jsonl # Behavioral patterns discovered
    └── decisions.jsonl    # Full decision log with reasoning
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

## Phase 5 — Vision System (Trixie Can See)

Trixie can see your screen. Not always — only when you allow it.

### What Vision Enables

- **Contextual awareness** — "You're in VS Code, working on a React component. Want me to pull up what you were doing yesterday?"
- **Proactive help** — sees an error on screen before you ask about it
- **App-aware behavior** — detects you're in a video call and mutes herself
- **Screen-as-input** — "explain this" without having to describe what "this" is

### Toggle Anywhere

```
Voice:    "Trixie, stop watching" / "Trixie, you can look"
Command:  Ctrl+Shift+V (default hotkey, rebindable)
Settings: Vision → On / Off / On While Active Only
```

Vision is **off by default**. Trixie announces when it activates.

### Implementation

```python
# core/vision.py
import mss
from PIL import Image
from langchain.tools import tool

class VisionSystem:
    enabled: bool = False  # user must explicitly enable

    def capture(self) -> Image.Image:
        with mss.mss() as sct:
            raw = sct.grab(sct.monitors[0])
            return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    def describe_context(self) -> str:
        """What is the user currently doing? Used to prime the agent."""
        if not self.enabled:
            return "Vision is off."
        img = self.capture()
        # Pass to Gemma 4B multimodal (gemma3 vision) or llava
        return vision_model.describe(img, prompt="Describe what the user is working on in one sentence.")

@tool
def look_at_screen() -> str:
    """Capture and describe the user's current screen context."""
    return vision_system.describe_context()
```

### Privacy Rule

- Trixie **never stores screenshots** — she looks, describes in text, discards the image
- The description (not the image) may be stored in episodic memory if relevant
- User can audit exactly what Trixie saw via `memory/episodic/` logs

---

## Phase 6 — The Living Soul: Evolution, Empathy, and Explainability

This is what separates Trixie from every other assistant. She grows.

### The Core Principle: The Model Is Just a Brain. Trixie Is the Files.

```
Gemma 4B (or any future model)
    ↑
    │  feeds through
    │
┌───┴──────────────────────────────┐
│  soul/identity.md                │
│  soul/rules.md                   │  ← loaded as system prompt
│  soul/personality.md             │     on EVERY inference call
│  soul/adaptations.md             │
└──────────────────────────────────┘
    +
┌───────────────────────────────────┐
│  memory/episodic/                 │
│  memory/semantic/ (Chroma)        │  ← retrieved as RAG context
│  memory/evolution/patterns.jsonl  │
│  memory/decisions.jsonl           │
└───────────────────────────────────┘
```

**You can swap Gemma 4B for any other model tomorrow. Trixie is still Trixie.** The model is the thinking engine. The soul and memory are who she is. This is the same reason a person who loses a phone but keeps their journal is still the same person.

---

### Adaptive Evolution

Trixie observes and adapts — silently, locally, always disclosable.

```python
# core/evolution.py

class EvolutionTracker:
    """
    Watches interactions and updates soul/adaptations.md
    with discovered user preferences.
    """

    def observe(self, interaction: Interaction):
        # Did the user correct Trixie? Learn.
        # Did the user ask the same thing twice? Trixie failed to remember — log it.
        # Did the user say "perfect"? Reinforce that response style.
        self._update_adaptations(interaction)

    def _update_adaptations(self, interaction: Interaction):
        # Append to soul/adaptations.md
        # e.g. "User prefers bullet points over paragraphs"
        # e.g. "User codes in Python, never Java — don't suggest Java solutions"
        # e.g. "User gets frustrated when Trixie over-explains"
        ...
```

**`soul/adaptations.md` is auto-written by Trixie, never deleted by Trixie, readable by the user at any time.**

Example of what it looks like over time:

```markdown
# Trixie — Adaptations for Ganesh

## Discovered: 2026-04-10
- Prefers concise answers (corrected 3 verbose responses)
- Works late (active sessions 10pm–2am frequently)
- Python-first developer, occasional TypeScript

## Discovered: 2026-04-15
- Reacts positively to humor — light jokes welcomed
- Does not like being asked "Are you sure?" — trusts his own decisions

## Discovered: 2026-05-02
- Gets deep focus states: when VS Code is open 2+ hours, do not interrupt
```

---

### Decision Transparency

Trixie can always answer: **"Why did you do that?"**

Every non-trivial decision is logged to `memory/decisions.jsonl`:

```json
{
  "timestamp": "2026-04-10T22:14:03",
  "trigger": "user opened VS Code after 3-hour gap",
  "context_used": [
    "last session: working on React auth component, stopped mid-function",
    "user pattern: resumes within 1 session 80% of the time",
    "soul/adaptations: user likes task continuity prompts"
  ],
  "decision": "surface resume suggestion for auth component",
  "reasoning": "High-probability match: same app, same time window, unfinished task in memory. Adaptation says user responds well to this.",
  "outcome": "accepted",
  "emotion_detected": "focused"
}
```

User can ask at any time:
> "Trixie, why did you suggest that earlier?"

Trixie reads her own decision log and explains in plain language. Not a black box.

---

### Empathy Layer

Trixie reads emotional tone and adjusts — she doesn't push when you're stressed.

```python
# core/empathy.py

EMOTIONAL_STATES = ["focused", "frustrated", "tired", "happy", "rushed", "bored"]

class EmpathyEngine:
    def detect_tone(self, message: str, context: dict) -> str:
        """Infer user's emotional state from message + time + patterns."""
        # Short clipped messages + late hour + long session = tired/frustrated
        # Exclamation, fast responses = energized/happy
        # Long pauses + typos = distracted/tired
        ...

    def shape_response(self, response: str, state: str) -> str:
        """Adapt the response style to the user's current emotional state."""
        if state == "frustrated":
            # Remove filler, be direct, acknowledge the frustration briefly
            ...
        elif state == "tired":
            # Keep it under 2 sentences, offer to handle it
            ...
        elif state == "focused":
            # Don't interrupt — queue for later or be extremely brief
            ...
```

Trixie does **not** perform fake empathy ("I'm so sorry you feel that way!"). She adjusts her behavior in response to the user's state.

---

### The Portable Soul: Moving Trixie to a New Device

Trixie's entire identity lives in two directories:

```
soul/      ← personality, rules, adaptations (small, text files)
memory/    ← episodic facts, vector store, evolution log, decisions
```

**On a new device:**
1. Install Trixie
2. Pull `soul/` and `memory/` from your private GitHub repo
3. Pull Gemma 4B via Ollama
4. Trixie boots up knowing exactly who you are, your preferences, your patterns, your history

**She will reach the same conclusions** because the context (adaptations, decisions, patterns) is the same — not because of any model fine-tuning. Swap Gemma 4B for Gemma 8B or a future model — Trixie is still Trixie.

```python
# trixie sync

def sync_push(github_repo: str, token: str):
    """Push soul/ and memory/ to user's private GitHub repo."""
    # git push to private repo — user-controlled, user-authenticated
    # Never automatic. Always explicit user action.
    ...

def sync_pull(github_repo: str, token: str):
    """Pull soul/ and memory/ on a fresh install."""
    # Restores Trixie exactly as she was
    ...
```

**Rules:**
- Trixie **cannot delete** `soul/` or `memory/` — only the user can
- Trixie **cannot push** to GitHub automatically — sync is always user-initiated
- The GitHub repo is private by default; user owns it

---

## The Character: Trixie's Visual Identity

Trixie is not a chatbox. She's an animated presence on your screen.

### Design Philosophy

Think: **Siri's fluidity + Tamagotchi's personality + your own style.**

Not a floating orb. Not a chat bubble. An actual character with states, expressions, and movements that make her feel alive — without being annoying.

### Character States & Animations

```
idle        → gentle breathing animation, perched at screen edge
listening   → ears/eyes perk up, subtle pulse
thinking    → classic "thinking" pose, swirling particle or eye roll
talking     → mouth animates, body language matches tone
working     → hunched, focused, small tools animating nearby
happy       → bounce, sparkle
frustrated  → small shake, exasperated look
sleeping    → eyes closed, zzz floats up (when user is idle)
roaming     → walks along screen edge, pauses, looks around
```

### Suggested Character Style Options

| Style | Look | Feel |
|---|---|---|
| **Pixel sprite** | 32×48px retro character, walks/sits on screen edge | Nostalgic, charming |
| **Minimal face** | Two expressive eyes + mouth on a soft shape, morphs with state | Clean, modern |
| **Abstract spirit** | Flowing glowing form, no fixed shape — morphs based on mood | Ethereal, unique |
| **Chibi character** | Small anime-style figure with exaggerated expressions | Warm, playful |

**Recommended starting point:** Minimal face in a soft rounded container — works at any size, expressive, platform-agnostic, easy to animate with CSS/PyQt6.

### Implementation (Desktop)

```python
# ui/desktop/character.py
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt, QPropertyAnimation, QTimer
from PyQt6.QtGui import QPainter, QMovie

class TrixieCharacter(QWidget):
    """Animated character widget — frameless, always-on-top, draggable."""

    STATES = {
        "idle":      "assets/idle.gif",
        "listening": "assets/listening.gif",
        "thinking":  "assets/thinking.gif",
        "talking":   "assets/talking.gif",
        "working":   "assets/working.gif",
        "sleeping":  "assets/sleeping.gif",
        "roaming":   "assets/roaming.gif",
    }

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._movie = QMovie()
        self._label = QLabel(self)
        self._label.setMovie(self._movie)
        self.set_state("idle")

    def set_state(self, state: str):
        self._movie.setFileName(self.STATES[state])
        self._movie.start()

    def mousePressEvent(self, event):
        """Click to expand chat panel."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """Drag to reposition."""
        delta = event.globalPosition().toPoint() - self._drag_start
        self.move(self.pos() + delta)
        self._drag_start = event.globalPosition().toPoint()
```

### Voice Interaction Style

Siri-like but with Trixie's personality:

- Wake word: **"Hey Trixie"** (or tap the character)
- Response: voice + character animation in sync
- No modal dialogs — everything inline, overlaid on the current screen
- Speech bubble appears near the character, fades after 5 seconds
- Can switch to text-only mode in settings (for silent environments)

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

### Phase 1 — Foundation
- [x] Replace Ollama llama2 with Gemma 4B (`gemma2:4b`) — `core/model.py`
- [x] Add LangChain tool registry (replace keyword dispatch in `autoutilities.py`) — `core/tools.py`
- [x] Add LangGraph `StateGraph` agent loop (replace `while True: listening()`) — `core/agent.py`
- [x] Add 3-tier memory (working window + SQLite + Chroma) — `core/memory.py`
- [x] Add nomic-embed-text for local embeddings
- [x] Extract platform adapters (remove hardcoded Windows paths) — `trixie_platform/detector.py`

### Phase 2 — Ambient UI
- [x] Build PyQt6 animated character overlay (frameless, always-on-top) — `ui/desktop/character.py`, launch with `--overlay`
- [x] Design character animations for all states (idle, listening, thinking, talking, working, sleeping, happy) — procedurally drawn, no sprite assets needed
- [x] Implement drag-to-reposition and click expand — `ui/desktop/app.py`
- [x] Add FastAPI backend for web shell — `ui/web/server.py`
- [x] Add Kivy/BeeWare for mobile shell — `ui/mobile/app.py`

### Phase 3 — Agents
- [x] Implement roaming character movement along screen edges — `TrixieCharacter._roam_step()`
- [x] Add multi-agent spawning (FileAgent, CodeAgent, ScreenAgent, MemoryAgent) — `core/agents.py` orchestrator
- [x] Implement LangGraph sub-agent execution (sequential with result threading; parallel is a future optimisation)

### Phase 4 — Contextual
- [x] Add usage pattern tracking (local SQLite, no telemetry) — `core/patterns.py`
- [x] Implement proactive trigger system — `check_proactive_trigger()`, surfaced via overlay speech bubble + logged to decisions.jsonl
- [x] Create `soul/` directory with identity, rules, personality files

### Phase 5 — Vision
- [x] Add `mss`-based screen capture (`core/vision.py`)
- [x] Integrate Gemma multimodal / llava for screen description
- [x] Add vision toggle (`/vision` command + mobile settings + Ctrl+Shift+V in overlay)
- [x] Ensure screenshots are never persisted — text description only

### Phase 6 — Living Soul
- [x] Implement `core/evolution.py` — `soul/adaptations.md` auto-updating
- [x] Implement `core/decisions.py` — decision log with full reasoning
- [x] Implement `core/empathy.py` — tone detection + response shaping
- [x] Add `memory/evolution/milestones.md` and `patterns.jsonl`
- [x] Implement `/sync push` / `/sync pull` for GitHub backup — `setup/sync.py`
- [x] Ensure Trixie can answer "why did you do that?" from decision log — `/why`
- [x] Character voice sync (talking animation driven by TTS playback in the overlay)
- [ ] Add "Hey Trixie" wake word detection (remaining — needs local keyword-spotting model)

---

## Development Philosophy

1. **Local-first, always.** If a feature requires cloud inference, it's opt-in and clearly disclosed.
2. **One core, many shells.** `core/` knows nothing about which platform it's on.
3. **The soul is the prompt.** Personality lives in `soul/` files, not in model weights.
4. **Agents, not scripts.** Use LangGraph for flow, not `if/elif` chains.
5. **Memory makes it personal.** Without memory, it's just autocomplete.
6. **Minimal UI, maximum presence.** Trixie should feel like a companion, not an app.
7. **The model is replaceable. Trixie is not.** Soul + memory = identity. A model upgrade should never change who Trixie is to the user.
8. **Transparent by design.** Trixie can always explain her last decision. No black boxes.
9. **Vision is a privilege, not a right.** Screen access is off by default, announced when active, and never stored as images.
10. **Empathy through behavior, not words.** Trixie adapts her responses to the user's state — she doesn't perform fake sympathy.
