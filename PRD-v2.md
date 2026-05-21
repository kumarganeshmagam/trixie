# Product Requirements Document — Trixie v2.0 (Build from Scratch)

**Document type:** Prescriptive PRD (what to build)
**Status:** Active — use this as the north star for a new session
**Date:** 2026-05-21

---

## 1. Product Vision

Trixie is a privacy-first AI assistant that lives entirely on your device. No cloud inference. No API keys. No data leaving the machine. She is not an app you open — she is a presence on your screen that grows, adapts, and remembers who you are across every device you ever own.

**One sentence:** Trixie is a local-first, cross-platform, agentic AI assistant with a persistent soul, three-tier memory, and an animated ambient UI — all running entirely on Gemma 4B with zero cloud dependency.

---

## 2. Core Principles (non-negotiable)

1. **Local-first.** All inference on-device. Gemma 4B via Ollama (desktop) or llama.cpp GGUF (mobile). No API calls to any cloud LLM.
2. **One core, many shells.** `core/` has zero platform imports. UI shells adapt to platform. The core never knows what UI it is talking to.
3. **The soul is the prompt.** Personality lives in `soul/*.md` files. Swapping the underlying model never changes who Trixie is.
4. **Memory makes it personal.** Three tiers: working (RAM), episodic (SQLite), semantic (Chroma + local embeddings).
5. **Agents, not scripts.** LangGraph `StateGraph` for all control flow. No `if/elif` keyword dispatch.
6. **Transparent by design.** Trixie can always explain her last decision. Every non-trivial action is logged.
7. **Vision is a privilege.** Screen access is off by default, announced when active, never stored as images.
8. **The model is replaceable. Trixie is not.** `soul/` + `memory/` = identity. A model upgrade must never change who Trixie is to the user.

---

## 3. Target Platforms

| Platform | UI | Model backend |
|---|---|---|
| Windows / macOS / Linux | CLI (default) + Web UI (`--web`) + PyQt6 overlay (Phase 2) | Ollama → `gemma2:4b` |
| Android | Kivy app (auto-download GGUF on first run) | llama-cpp-python + GGUF |
| iOS | BeeWare/Briefcase app | llama-cpp-python + GGUF |
| Browser | FastAPI backend + inline HTML chat | Same as host platform |

Single Python codebase. Platform detection via `trixie_platform/detector.py`.

---

## 4. Project Structure (start fresh with this layout)

```
trixie/
├── core/
│   ├── __init__.py
│   ├── agent.py          # LangGraph ReAct loop
│   ├── decisions.py      # Decision logger (memory/decisions.jsonl)
│   ├── empathy.py        # Emotion detection + response shaping
│   ├── evolution.py      # Interaction observer → soul/adaptations.md
│   ├── memory.py         # 3-tier memory (working + episodic + semantic)
│   ├── model.py          # Unified LLM interface (Ollama / llama.cpp)
│   ├── soul.py           # Loads soul/*.md → system prompt
│   ├── tools.py          # LangChain @tool registry
│   └── vision.py         # Screen capture (mss) — off by default
│
├── ui/
│   ├── __init__.py
│   ├── desktop/
│   │   └── __init__.py   # (Phase 2: PyQt6 animated overlay)
│   ├── mobile/
│   │   ├── __init__.py
│   │   └── app.py        # Kivy app (Android/iOS)
│   └── web/
│       ├── __init__.py
│       └── server.py     # FastAPI + inline HTML chat UI
│
├── trixie_platform/
│   ├── __init__.py
│   └── detector.py       # current() → 'Windows'|'Darwin'|'Linux'|'Android'|'iOS'
│                         # open_file_or_app(target) cross-platform
│
├── setup/
│   ├── __init__.py
│   ├── model_download.py # first_run_setup() — Ollama or GGUF download
│   └── sync.py           # sync_push/pull (soul + memory to private GitHub repo)
│
├── soul/
│   ├── identity.md       # Who Trixie is
│   ├── rules.md          # Always/Never rules
│   ├── personality.md    # Communication style
│   └── adaptations.md    # Auto-written by Trixie, never deleted by Trixie
│
├── memory/
│   └── evolution/
│       ├── milestones.md # Notable growth moments
│       └── patterns.jsonl
│
├── .github/
│   └── workflows/
│       ├── build-android.yml
│       ├── build-ios.yml
│       └── build-desktop.yml
│
├── main.py               # Unified entry point
├── buildozer.spec        # Android packaging
├── pyproject.toml        # BeeWare Briefcase (iOS + desktop)
├── requirements.txt
└── CLAUDE.md             # Architecture north star (already exists)
```

---

## 5. Model: Gemma 4B

### Desktop
- Ollama running locally: `gemma2:4b`
- First-run: check if Ollama is installed → install if not → `ollama pull gemma2:4b`
- Embeddings: `nomic-embed-text` (local, via Ollama)

### Mobile (Android / iOS)
- GGUF quantized: `gemma-2-4b-it-Q4_K_M.gguf` (~2.7 GB) — primary
- Light fallback: `gemma-2-4b-it-Q2_K.gguf` (~1.5 GB) — for low-storage devices
- Source: `https://huggingface.co/bartowski/gemma-2-4b-it-GGUF`
- Downloaded on first launch, progress bar UI, saves to app data directory
- Embeddings: sentence-transformers `all-MiniLM-L6-v2` (ONNX, CPU-friendly)

### Model abstraction (`core/model.py`)
```python
def get_llm(backend: str = "ollama", model_path: str | None = None):
    if backend == "ollama":
        return ChatOllama(model="gemma2:4b", temperature=0.7)
    else:
        return LlamaCpp(model_path=model_path, n_ctx=4096, temperature=0.7)
```

---

## 6. Soul System

### Files loaded on every inference call
```
soul/identity.md    — who Trixie is, core traits
soul/rules.md       — always/never constraints
soul/personality.md — communication style, banned phrases
soul/adaptations.md — auto-discovered user preferences (appended by Trixie)
```

### System prompt construction (`core/soul.py`)
```python
def build_system_prompt(memory_context: str, emotion: str) -> str:
    identity   = Path("soul/identity.md").read_text()
    rules      = Path("soul/rules.md").read_text()
    personality = Path("soul/personality.md").read_text()
    adaptations = Path("soul/adaptations.md").read_text()

    prompt = f"{identity}\n\n{rules}\n\n{personality}\n\n{adaptations}"

    if memory_context:
        prompt += f"\n\n## Relevant Memory\n{memory_context}"

    if emotion != "neutral":
        prompt += f"\n\n## Current User State\n{emotion}"

    return prompt
```

### soul/identity.md (content)
- Name: Trixie, Version: 2.0, Pronouns: she/her
- Core traits: Curious, Helpful, Private, Honest, Brief, Consistent
- Character description: warm but not clingy, confident but not arrogant, occasionally witty
- Memory commitment: remembers across devices and sessions forever

### soul/rules.md (content)
- **Always:** run on-device; announce system actions; stop and ask when unsure; respect "don't remember this"
- **Never:** send data to remote servers; store screenshots; delete soul/ or memory/ files; pretend to have done something it hasn't; activate vision silently

### soul/personality.md (content)
- Banned phrases: "Certainly!", "Great question!", "As an AI...", "I'd be happy to!", "Of course!"
- Adapts tone to emotion (direct when frustrated, brief when tired, normal when focused)
- Concise by default — depth on request only
- Code answers use inline blocks, not prose descriptions

### soul/adaptations.md (auto-written)
- Trixie appends to this file when she discovers a user preference
- Format: `## Discovered: YYYY-MM-DD\n- Preference: ...\n- Reason: ...`
- User can read and edit; Trixie never deletes entries

---

## 7. Three-Tier Memory (`core/memory.py`)

### Tier 1 — Working memory (RAM, per-session)
- Sliding window: last 20 messages
- Cleared on `/reset` or app restart
- Class: `WorkingMemory` with `add()`, `messages()`, `clear()`

### Tier 2 — Episodic memory (SQLite, persistent)
- Stores facts the user explicitly tells Trixie ("remember that I...")
- Also stores inferred important facts (Trixie decides what's worth keeping)
- Schema: `id, timestamp, fact TEXT, tags TEXT, embedding BLOB`
- Functions: `store_episodic(fact, tags)`, `search_episodic(query, limit)`, `get_recent_episodic(limit)`
- DB path: `memory/episodic.db`

### Tier 3 — Semantic memory (Chroma vector store, persistent)
- Indexes user notes, files, and conversation summaries
- Local embeddings via `nomic-embed-text` (Ollama) or `all-MiniLM-L6-v2` (mobile)
- Functions: `store_semantic(text)`, `search_semantic(query, k)`
- Persist path: `memory/semantic/`

### Memory retrieval
```python
def retrieve_context(query: str) -> str:
    episodic = search_episodic(query, limit=5)
    semantic = search_semantic(query, k=3)
    # Combine, deduplicate, format as context string
```

---

## 8. LangGraph Agent Loop (`core/agent.py`)

### ReAct pattern
```
user input
    │
    ▼
[pre-turn]
  detect_emotion(user_input) → emotion: str
  retrieve_context(user_input) → memory_context: str
  build_system_prompt(memory_context, emotion) → system_prompt: str
    │
    ▼
StateGraph:
  llm_node → tool_calls? → tool_node → llm_node → ... → END
    │
    ▼
[post-turn]
  update_working_memory(user_input, response)
  observe(interaction) → evolution tracking
```

### State schema
```python
class TrixieState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    emotion: str
    memory_context: str
```

### Graph nodes
- `llm` — calls `llm.bind_tools(ALL_TOOLS)` with soul system prompt prepended
- `tools` — `ToolNode(ALL_TOOLS)` — executes all requested tools in parallel
- Conditional edge from `llm`: if last message has tool_calls → `tools`, else → `END`
- Edge from `tools` → `llm` (loop until no more tool calls)

---

## 9. Tool Registry (`core/tools.py`)

All tools use LangChain `@tool` decorator. Gemma 4B selects tools from natural language — no keyword matching.

| Tool | Description |
|---|---|
| `search_wikipedia(query)` | Wikipedia 2-sentence summary |
| `get_current_time()` | Current date/time |
| `open_application(app_name)` | Cross-platform app/file opener |
| `read_file(path)` | Read text file (path must exist) |
| `write_file(path, content)` | Write text to file |
| `run_python_code(code)` | Execute Python snippet, return stdout/stderr |
| `remember_fact(fact, tags)` | Store to episodic memory |
| `recall_facts(query)` | Search episodic + semantic memory |
| `look_at_screen()` | Describe screen (only if vision is enabled) |

`ALL_TOOLS = [search_wikipedia, get_current_time, open_application, read_file, write_file, run_python_code, remember_fact, recall_facts, look_at_screen]`

---

## 10. Platform Detection (`trixie_platform/detector.py`)

```python
def current() -> str:
    # Returns: 'Windows' | 'Darwin' | 'Linux' | 'Android' | 'iOS'

def open_file_or_app(target: str) -> str:
    # Windows: os.startfile(target) or subprocess ['start', target]
    # macOS:   subprocess ['open', target]
    # Linux:   subprocess ['xdg-open', target]
    # Android: intent via Kivy/Android API
    # iOS:     UIApplication.openURL
```

**Critical:** Name this package `trixie_platform` (not `platform`) — `platform` shadows the Python stdlib module.

---

## 11. Empathy Engine (`core/empathy.py`)

### Emotion states
`frustrated` | `tired` | `rushed` | `happy` | `focused` | `neutral`

### Detection heuristics
- Short, clipped messages + late hour + long session → `tired`
- Repeated questions / corrections → `frustrated`
- Exclamation marks + short responses + daytime → `happy`
- `asap`, `quick`, `hurry`, `now` in message → `rushed`
- Long focused session, minimal small talk → `focused`

### Response shaping (injected into system prompt)
- `frustrated` → be direct, skip filler, acknowledge briefly
- `tired` → keep under 2 sentences, offer to handle it
- `rushed` → bullet points, no preamble
- `focused` → minimal interruption, queue questions
- `happy` / `neutral` → normal Trixie personality

```python
@dataclass
class EmotionSignal:
    state: str
    confidence: float
    signals: list[str]

def detect_emotion(message: str, now: datetime | None = None) -> EmotionSignal
def shape_response_instruction(emotion: str) -> str
```

---

## 12. Evolution Tracker (`core/evolution.py`)

Watches interactions and updates `soul/adaptations.md`.

```python
@dataclass
class Interaction:
    user_message: str
    trixie_response: str
    outcome: str          # 'accepted' | 'corrected' | 'ignored' | 'unknown'
    emotion: str

def observe(interaction: Interaction) -> None:
    # Detects patterns:
    #   - User corrected Trixie's response → learn the preference
    #   - User asked the same thing twice → Trixie failed to remember
    #   - User said "perfect" / positive → reinforce this style
    # Appends to soul/adaptations.md
    # Appends to memory/evolution/patterns.jsonl

def record_milestone(milestone: str) -> None:
    # Appends to memory/evolution/milestones.md
```

---

## 13. Decision Logger (`core/decisions.py`)

Every non-trivial action Trixie takes is logged with full reasoning.

```python
def log_decision(
    trigger: str,
    decision: str,
    reasoning: str,
    context_used: list[str],
    outcome: str = "pending",
    emotion: str = "neutral",
) -> None:
    # Appends JSON line to memory/decisions.jsonl

def explain_last_decision() -> str:
    # Reads last entry from memory/decisions.jsonl
    # Returns human-readable explanation for /why command
```

Log format:
```json
{
  "timestamp": "2026-05-21T22:14:03",
  "trigger": "user opened VS Code after 3-hour gap",
  "context_used": ["last session: working on React auth component"],
  "decision": "surface resume suggestion for auth component",
  "reasoning": "High-probability match: same app, same time window, unfinished task in memory.",
  "outcome": "accepted",
  "emotion": "focused"
}
```

---

## 14. Vision System (`core/vision.py`)

**Off by default. Announced when activated. Images never written to disk.**

```python
class VisionSystem:
    enabled: bool = False

    def enable(self) -> str    # returns confirmation message
    def disable(self) -> str
    def toggle(self) -> str

    def capture_jpeg_b64(self) -> str | None:
        # Uses mss to capture screen 0
        # Encodes to JPEG base64 in memory
        # Image data NEVER written to any file

    def describe_context(self, llm) -> str:
        # Calls capture_jpeg_b64()
        # Passes base64 image to Gemma vision (or llava fallback)
        # Returns text description only
        # Image data discarded immediately after description

vision = VisionSystem()  # module-level singleton
```

Toggle methods:
- CLI: `/vision on` / `/vision off`
- Web: POST `/vision` toggle endpoint
- Mobile: Settings modal toggle
- (Phase 2) Desktop: voice "Trixie, stop watching" / hotkey `Ctrl+Shift+V`

---

## 15. GitHub Sync (`setup/sync.py`)

User-initiated only. Never automatic.

```python
def sync_push(repo_url: str) -> None:
    # git add soul/ memory/
    # git commit -m "Trixie soul + memory backup YYYY-MM-DD"
    # git push to user's private repo

def sync_pull(repo_url: str) -> None:
    # git pull from user's private repo
    # restores soul/ and memory/ on new device
```

**Rules:**
- Never runs automatically
- Only the user can initiate sync
- Target repo must be private (Trixie warns if not)
- Trixie cannot push code — only `soul/` and `memory/` directories

---

## 16. Entry Point (`main.py`)

```python
# Platform detection → route to right UI shell
if _is_mobile():         # ANDROID_ROOT or BRIEFCASE_PLATFORM=iOS
    from ui.mobile.app import run; run()
elif "--web" in sys.argv:
    from ui.web.server import run as web_run; web_run()
else:
    # CLI loop with first-run setup check
```

CLI commands:
| Command | Action |
|---|---|
| `/reset` | Clear working memory |
| `/memory` | Show last 10 episodic memories |
| `/why` | Explain last decision |
| `/vision on\|off` | Toggle screen capture |
| `/sync push\|pull <repo>` | GitHub backup/restore |
| `exit` / `quit` / `bye` | Graceful exit with farewell |

---

## 17. Web UI (`ui/web/server.py`)

FastAPI + inline HTML (no separate frontend build step).

### Endpoints
| Method | Path | Description |
|---|---|---|
| GET | `/` | Serves full chat UI (inline HTML, dark theme, bubble layout) |
| POST | `/chat` | `{"message": str}` → `{"response": str}` — runs agent.chat() in executor |
| POST | `/command` | `{"command": "/reset"\|"/memory"\|"/why"}` → `{"result": str}` |
| POST | `/vision` | `{"action": "toggle"\|"on"\|"off"}` → `{"status": str}` |
| GET | `/health` | `{"status": "ok"}` |

Launch: `python main.py --web` → auto-opens `http://localhost:7860` in default browser.

---

## 18. Mobile UI (`ui/mobile/app.py`)

Kivy app for Android and iOS.

### Screens
1. **DownloadScreen** — first-run GGUF download with progress bar; blocks until ready
2. **ChatScreen** — main chat:
   - `ChatBubble` widget: user right (blue), Trixie left (dark grey)
   - `MessageList`: `ScrollView` + `GridLayout`, auto-scrolls to latest
   - `TextInput` + send button at bottom
   - Trixie response runs in background thread (no UI freeze)
3. **SettingsModal** — popup with: vision toggle, `/memory`, `/why`, `/reset`

### First-run flow
```
App launch
  → DownloadScreen (if no GGUF in app data dir)
      → download GGUF with tqdm progress
      → verify size
  → ChatScreen
      → greeting message
```

---

## 19. First-Run Setup (`setup/model_download.py`)

```python
def first_run_setup(
    force_gguf: bool = False,
    light_model: bool = False,
    progress_callback: Callable[[float], None] | None = None,
) -> dict:
    # Returns: {"backend": "ollama"|"gguf", "model_path": str|None, "ready": bool}
    #
    # Desktop: ensure Ollama installed → ollama pull gemma2:4b
    # Mobile/force_gguf: download GGUF to platform-appropriate directory
    #   - Android: /data/data/<app>/files/
    #   - iOS: ~/Documents/
    #   - Desktop: ~/.trixie/models/
```

---

## 20. Android Packaging (`buildozer.spec`)

Key settings:
```ini
[app]
title = Trixie
package.name = trixie
package.domain = com.trixie.assistant
source.main = main.py
requirements = python3,kivy,requests,tqdm,langchain,langchain-community,langchain-ollama,langgraph,chromadb,llama-cpp-python,Pillow
android.arch = arm64-v8a
android.api = 33
android.minapi = 26
android.ndk = 25c
p4a.local_recipes = .p4a_recipes
```

Custom p4a recipe for `llama-cpp-python` (written via `shell: python` in the workflow — NOT a bash heredoc):
- `CMAKE_ARGS=-DLLAMA_ANDROID=1 -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-26`

---

## 21. iOS Packaging (`pyproject.toml`)

```toml
[tool.briefcase.app.trixie.iOS]
requires = [
    "kivy",
    "langchain>=0.2.0",
    "langchain-community>=0.2.0",
    "langgraph>=0.1.0",
    "llama-cpp-python>=0.2.0",
    "requests",
    "tqdm",
    "Pillow",
]
```

Build: `briefcase create iOS && briefcase build iOS` (on GitHub's `macos-latest` runner — Xcode 15 is pre-installed, no local Mac required).

Distribution options:
- Free (7-day): AltStore or Sideloadly
- Paid ($99/yr Apple Developer): TestFlight / App Store

---

## 22. CI/CD (GitHub Actions)

All three workflows must trigger on:
```yaml
on:
  push:
    branches: [main]
    tags: ["v*"]
  pull_request:
    branches: [main]
  workflow_dispatch:
```

### build-android.yml
- Runner: `ubuntu-22.04`
- Steps: system deps → buildozer + cython → write p4a recipe (via `shell: python`) → `buildozer -v android debug`
- Caches: `~/.buildozer` and `~/.android` (keyed by buildozer.spec hash)
- Timeout: 120 minutes

### build-ios.yml
- Runner: `macos-latest` (Xcode 15 built in)
- Steps: Python → briefcase 0.3.17 → `briefcase create iOS` → `briefcase build iOS`
- Optional: import signing cert from GitHub Secrets for TestFlight
- Timeout: 90 minutes

### build-desktop.yml
- Runner matrix: `ubuntu-22.04`, `windows-latest`, `macos-latest`
- Steps: Python → pip (no llama-cpp-python for desktop) → PyInstaller spec → `pyinstaller trixie.spec`
- PyInstaller spec: `shell: python` (not a bash heredoc) to avoid delimiter issues
- Collects: `langchain`, `langchain_community`, `langgraph` (dynamic imports)
- Artifacts: `trixie-linux.zip`, `trixie-windows.zip`, `trixie-macos.zip`
- Timeout: 45 minutes

---

## 23. Dependencies (`requirements.txt`)

```
# LLM / Agent
langchain>=0.2.0
langchain-community>=0.2.0
langchain-ollama>=0.1.0
langgraph>=0.1.0

# Vector store
chromadb>=0.5.0

# HTTP
requests>=2.31.0
tqdm>=4.66.0

# Voice
pyttsx3~=2.90
SpeechRecognition>=3.10.0
PyAudio~=0.2.11

# Vision
mss>=9.0.0
Pillow>=10.2.0

# Utilities
wikipedia~=1.4.0
python-decouple~=3.8

# Web UI
fastapi>=0.110.0
uvicorn>=0.29.0

# Mobile (uncomment for Android/iOS builds)
# llama-cpp-python>=0.2.0
```

---

## 24. Phase Roadmap

| Phase | Feature | Status |
|---|---|---|
| 1 | Core agent (LangGraph + LangChain tools) | ✅ Built |
| 1 | 3-tier memory (working + SQLite + Chroma) | ✅ Built |
| 1 | Soul system (identity/rules/personality/adaptations files) | ✅ Built |
| 1 | Cross-platform CLI entry point | ✅ Built |
| 1 | Web UI (FastAPI --web flag) | ✅ Built |
| 1 | Mobile UI (Kivy, Android + iOS) | ✅ Built |
| 1 | First-run model download (Ollama + GGUF) | ✅ Built |
| 1 | GitHub sync push/pull | ✅ Built |
| 1 | Vision system (mss, off by default) | ✅ Built |
| 1 | Empathy engine (emotion detection) | ✅ Built |
| 1 | Evolution tracker (adaptations.md auto-update) | ✅ Built |
| 1 | Decision logger (/why command) | ✅ Built |
| 1 | GitHub Actions CI (Android + iOS + Desktop) | ✅ Built |
| 2 | PyQt6 animated character overlay (desktop) | 🔲 Planned |
| 2 | Character sprites/animations (idle/thinking/talking/etc.) | 🔲 Planned |
| 2 | Drag-to-reposition, auto-collapse | 🔲 Planned |
| 3 | Multi-agent spawning (FileAgent, BrowserAgent, CodeAgent) | 🔲 Planned |
| 3 | Roaming character movement along screen edges | 🔲 Planned |
| 4 | Usage pattern tracking (proactive triggers) | 🔲 Planned |
| 4 | App-context awareness (VS Code open → suggest last task) | 🔲 Planned |
| 6 | Wake word detection ("Hey Trixie") | 🔲 Planned |
| 6 | Voice animation sync (character state driven by TTS) | 🔲 Planned |

---

## 25. Critical Implementation Notes

### DO NOT repeat v1 mistakes
- No hard-coded usernames or file paths
- No keyword `if/elif` dispatch — all intent through LLM tool selection
- No hardcoded Windows-only paths — use `trixie_platform/detector.py`
- No naming a package `platform` — it shadows Python stdlib

### Heredoc trap (previously broke CI)
Never write p4a recipes or PyInstaller specs via bash heredoc inside YAML — the YAML indentation adds leading spaces to the end delimiter, which bash cannot match, silently breaking the entire shell script. Always use `shell: python` to write files programmatically.

### Mobile vs Desktop model split
- Desktop: Ollama manages models, Trixie just calls it
- Mobile: must download GGUF directly; no Ollama on Android/iOS
- `first_run_setup()` returns `{"backend": "ollama"|"gguf", "model_path": ..., "ready": bool}` and is called once at startup

### Trixie cannot delete soul/ or memory/
Enforce in code: `evolution.py` and `decisions.py` must only append, never delete. `soul/adaptations.md` is append-only. The user deletes if they choose to.

### Vision privacy guarantee
`capture_jpeg_b64()` must NEVER write image data to disk or any log. Only the text description returned by the vision model may be stored (in episodic memory, only if Trixie deems it relevant).

---

## 26. What a New Session Should Do

1. **Create the directory structure** exactly as in Section 4
2. **Write `soul/*.md` files** with the content defined in Section 6
3. **Implement `core/` modules** in this order: `model.py` → `soul.py` → `memory.py` → `tools.py` → `empathy.py` → `evolution.py` → `decisions.py` → `vision.py` → `agent.py`
4. **Implement `trixie_platform/detector.py`** (must be named `trixie_platform`, not `platform`)
5. **Implement `setup/model_download.py`** and `setup/sync.py`
6. **Implement `ui/web/server.py`** (FastAPI, inline HTML, no separate build step)
7. **Implement `ui/mobile/app.py`** (Kivy, DownloadScreen + ChatScreen + SettingsModal)
8. **Write `main.py`** (mobile detect → web flag → CLI loop)
9. **Write CI workflows** (all three, all with `pull_request` trigger, use `shell: python` for file writing — never bash heredoc)
10. **Write `buildozer.spec`** and `pyproject.toml`
11. **Smoke test:** `python main.py --web` should start a FastAPI server, open browser, and show the chat UI

**Start from an empty repo. Do not port v1 code. v1 is reference only.**
