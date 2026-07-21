# Product Requirements Document — Trixie v1 (Legacy Baseline)

**Document type:** Descriptive PRD (what exists today)
**Status:** Shipped / Deprecated — exists as reference for v2
**Date:** 2026-05-21

---

## 1. Overview

Trixie v1 is a voice-activated assistant that runs locally on a Windows PC. It listens for speech commands, routes them through a keyword dispatcher, calls a local Ollama server for AI responses, and speaks the answer back using text-to-speech. It is a single-machine, single-user, Windows-only application with no memory or agent capability.

---

## 2. What v1 Actually Does

### Voice command loop
- Captures microphone input via `SpeechRecognition` (Google STT — requires internet)
- Feeds transcribed text into a keyword router
- Speaks the response via `pyttsx3`

### Keyword routing (`autoutilities.py`)
Hard-coded `if/elif` chain — no NLP, no intent detection:

| Keyword in command | Action |
|---|---|
| `open <app>` | Launch app from hard-coded Windows path list |
| `search <query>` | `wikipedia.summary()` — 2 sentences |
| `what` / `why` / `explain` / `tell` | Prompt-engineer a suffix, send to Ollama |
| `program` | Ask `codellama` to generate a Python snippet |
| `image` | Send a hard-coded file path to `llava:13b` |
| `play` | Launch Spotify from hard-coded path |
| anything else | Route to `llama2` chat |

### Local LLM via Ollama (direct HTTP, no LangChain)
- `codellama` — code generation
- `llama2` — general chat
- `llava:13b` — image understanding (hard-coded image path)
- All calls via raw `requests.post("http://localhost:11434/api/...")`

### Application launcher
Hard-coded Windows paths in a dict:
```python
app_list = {
    'google':  'chrome.exe',
    'notepad': 'notepad.exe',
    'spotify': 'C:/Users/kumar/AppData/Roaming/Spotify/Spotify.exe',
    'brave':   'C:/Users/kumar/AppData/Local/BraveSoftware/...',
}
```

### Image upload server (`app.py`)
Standalone Flask server for uploading images — used by `autoutilities.py` to relay images to `llava`.

---

## 3. Architecture

```
main.py  (or entry point)
  ↓
SpeechRecognition  (Google STT — requires internet)
  ↓
autoutilities.py  (keyword if/elif dispatcher)
  ├── generate()   → POST /api/generate  (codellama, llava)
  ├── chat()       → POST /api/chat      (llama2)
  ├── open_app()   → subprocess.Popen (hardcoded Windows path)
  ├── search()     → wikipedia.summary()
  └── play()       → subprocess.Popen (Spotify)
  ↓
pyttsx3  (TTS — local, offline)
```

---

## 4. Dependencies

| Package | Purpose |
|---|---|
| `SpeechRecognition` | STT (uses Google's API) |
| `pyttsx3` | TTS |
| `PyAudio` | Microphone input |
| `requests` | Ollama HTTP calls |
| `wikipedia` | Wikipedia search |
| `Pillow` | Image handling |
| `pygments` | Terminal syntax highlighting |
| `flask`, `flask-cors` | Image upload server |

---

## 5. Known Limitations

| Limitation | Impact |
|---|---|
| Windows-only | Hard-coded `C:/Users/kumar/...` paths, `chrome.exe`, `notepad.exe` — runs nowhere else |
| Google STT | Requires internet; privacy issue; single point of failure |
| No memory | Every session is blank. Trixie forgets everything. |
| No tool calling | Pure keyword matching — no NLP, breaks on paraphrase |
| No context | Each LLM call is stateless — no conversation history |
| Single model per task | Hard-coded model per keyword, not user-configurable |
| No mobile/web | Desktop (Windows) only |
| Hard-coded username | Paths contain `kumar` — doesn't work for any other user |
| Image is a fixed path | Vision is broken unless that exact file exists |
| No error handling | Ollama failures return a random done_text from `utils.py` |
| No tests | Zero automated tests |
| No packaging | No installer, no CI, runs only from cloned repo |

---

## 6. Files in v1

| File | Role |
|---|---|
| `autoutilities.py` | All logic — keyword routing + all LLM calls |
| `utils.py` | `done_texts` list (fallback responses) |
| `app.py` | Flask image upload server |
| `upload_file.py` | Script to POST an image to the Flask server |
| `project_template.txt` | Unused planning note |
| `ToDo` | Handwritten TODO list |

---

## 7. What v1 Is Not

- Not an agent (no planning, no tool selection)
- Not cross-platform
- Not memory-enabled
- Not private (Google STT)
- Not installable
- Not testable

---

## 8. Why v2

v1 proves the concept: local LLM + voice + actions = useful. But the architecture hits a ceiling immediately. Every new feature requires adding another `elif`. There is no way to add memory, multi-step reasoning, or cross-platform support without a full rewrite.

v2 is that rewrite.
