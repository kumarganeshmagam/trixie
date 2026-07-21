"""
Trixie 2.0 — Web UI (FastAPI + Server-Sent Events).

Runs on localhost only — this is NOT a cloud service.
All inference still happens on-device via Ollama / llama.cpp.

Start:
    python main.py --web        # opens http://localhost:7860
    python main.py --web --port 8080
"""

from __future__ import annotations

import asyncio
import json
import sys
import webbrowser
from pathlib import Path
from typing import AsyncGenerator

# ── FastAPI ────────────────────────────────────────────────────────────────────
try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, StreamingResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("[web] FastAPI not installed. Run: pip install fastapi uvicorn")
    sys.exit(1)

ROOT = Path(__file__).parent.parent.parent
app = FastAPI(title="Trixie", docs_url=None, redoc_url=None)

_agent = None  # set by run()


# ── API models ─────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

class MemoryRequest(BaseModel):
    fact: str


# ── HTML chat UI (served inline — no separate frontend build needed) ───────────

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trixie</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0f0f0f; color: #e8e8e8; font-family: system-ui, sans-serif;
         display: flex; flex-direction: column; height: 100vh; }
  #header { background: #1a1a1a; padding: 14px 20px; display: flex;
             align-items: center; gap: 12px; border-bottom: 1px solid #2a2a2a; }
  #header h1 { font-size: 1.1rem; color: #7c6af7; }
  #status  { font-size: 0.75rem; color: #888; margin-left: auto; }
  #chat    { flex: 1; overflow-y: auto; padding: 16px; display: flex;
             flex-direction: column; gap: 10px; }
  .bubble  { max-width: 72%; padding: 10px 14px; border-radius: 14px;
             font-size: 0.9rem; line-height: 1.5; white-space: pre-wrap; }
  .user    { background: #2a1e3a; align-self: flex-end; border-bottom-right-radius: 4px; }
  .trixie  { background: #1e2a3a; align-self: flex-start; border-bottom-left-radius: 4px; }
  .thinking{ color: #888; font-style: italic; }
  #input-row { padding: 12px 16px; background: #1a1a1a; border-top: 1px solid #2a2a2a;
               display: flex; gap: 10px; }
  #msg     { flex: 1; background: #252525; border: 1px solid #333; border-radius: 10px;
             color: #e8e8e8; padding: 10px 14px; font-size: 0.9rem; outline: none;
             resize: none; height: 44px; }
  #send    { background: #7c6af7; color: #fff; border: none; border-radius: 10px;
             padding: 0 20px; cursor: pointer; font-size: 0.9rem; }
  #send:hover { background: #6b5ce7; }
  #toolbar { display: flex; gap: 8px; padding: 6px 16px; background: #1a1a1a; }
  .tool-btn{ background: #1e1e1e; border: 1px solid #333; color: #888;
             border-radius: 8px; padding: 4px 10px; font-size: 0.75rem; cursor: pointer; }
  .tool-btn:hover { color: #e8e8e8; border-color: #555; }
</style>
</head>
<body>
<div id="header">
  <h1>Trixie</h1>
  <span id="status">Ready</span>
</div>
<div id="chat"></div>
<div id="toolbar">
  <button class="tool-btn" onclick="sendCmd('/memory')">Memory</button>
  <button class="tool-btn" onclick="sendCmd('/why')">Why?</button>
  <button class="tool-btn" onclick="sendCmd('/reset')">Reset</button>
  <button class="tool-btn" onclick="toggleVision()">Vision: OFF</button>
</div>
<div id="input-row">
  <textarea id="msg" placeholder="Message Trixie…" onkeydown="onKey(event)"></textarea>
  <button id="send" onclick="send()">Send</button>
</div>
<script>
let visionOn = false;

function addBubble(text, role) {
  const div = document.createElement('div');
  div.className = 'bubble ' + role;
  div.textContent = text;
  const chat = document.getElementById('chat');
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function setStatus(t) { document.getElementById('status').textContent = t; }

async function send() {
  const inp = document.getElementById('msg');
  const text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  addBubble(text, 'user');
  const thinking = addBubble('Trixie is thinking…', 'trixie thinking');
  setStatus('Thinking…');
  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await res.json();
    thinking.className = 'bubble trixie';
    thinking.textContent = data.response;
  } catch(e) {
    thinking.textContent = 'Error: ' + e.message;
  }
  setStatus('Ready');
}

async function sendCmd(cmd) {
  addBubble(cmd, 'user');
  const thinking = addBubble('…', 'trixie thinking');
  const res = await fetch('/command', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: cmd})
  });
  const data = await res.json();
  thinking.className = 'bubble trixie';
  thinking.textContent = data.response;
}

async function toggleVision() {
  visionOn = !visionOn;
  const btn = document.querySelector('[onclick="toggleVision()"]');
  btn.textContent = 'Vision: ' + (visionOn ? 'ON' : 'OFF');
  await fetch('/vision', {method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({on: visionOn})});
}

function onKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
}

// Greet on load
addBubble("Hey! I'm Trixie. How can I help?", 'trixie');
</script>
</body>
</html>
"""


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(_HTML)


@app.post("/chat")
async def chat(req: ChatRequest):
    global _agent
    if _agent is None:
        return {"response": "Model is still loading — please wait a moment."}
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, _agent.chat, req.message)
    return {"response": response}


@app.post("/command")
async def command(req: ChatRequest):
    """Handle /slash commands."""
    cmd = req.message.strip()
    if cmd == "/reset":
        if _agent: _agent.reset_working_memory()
        return {"response": "Working memory cleared."}
    if cmd == "/memory":
        from core.memory import get_recent_episodic
        facts = get_recent_episodic(10)
        return {"response": "\n".join(facts) if facts else "No memories stored yet."}
    if cmd == "/why":
        from core.decisions import explain_last_decision
        return {"response": explain_last_decision()}
    return {"response": f"Unknown command: {cmd}"}


@app.post("/vision")
async def vision_toggle(req: dict):
    from core.vision import vision
    msg = vision.enable() if req.get("on") else vision.disable()
    return {"response": msg}


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": _agent is not None}


# ── Startup ────────────────────────────────────────────────────────────────────

def _load_agent():
    global _agent
    state_file = Path.home() / ".trixie" / ".setup_complete"

    if not state_file.exists():
        from setup.model_download import first_run_setup
        result = first_run_setup()
        if not result.get("ready"):
            print("[web] ERROR: Model setup failed.")
            return
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(str(result), encoding="utf-8")
    else:
        import ast
        result = ast.literal_eval(state_file.read_text(encoding="utf-8"))

    from core.model import get_llm
    from core.agent import TrixieAgent
    llm = get_llm(backend=result.get("backend", "ollama"),
                  model_path=result.get("model_path"))
    _agent = TrixieAgent(llm)
    print("[web] Trixie agent loaded.")


def run(host: str = "127.0.0.1", port: int = 7860):
    """Start the web server and open the browser."""
    import threading
    threading.Thread(target=_load_agent, daemon=True).start()

    # Parse --port from CLI args
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            try: port = int(sys.argv[i + 1])
            except ValueError: pass

    url = f"http://{host}:{port}"
    print(f"[web] Trixie web UI → {url}")
    print("[web] Press Ctrl+C to stop.")

    # Open browser after a short delay so server is ready
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")
