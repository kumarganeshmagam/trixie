"""
Trixie 2.0 — LangChain tool registry.

Gemma 4B picks tools from this list based on natural language — no keyword
matching. Every tool has a clear docstring because that docstring IS the
description the model sees when deciding whether to call the tool.
"""

from __future__ import annotations

import ast
import contextlib
import datetime
import io
import subprocess
from pathlib import Path

import wikipedia
from langchain_core.tools import tool


# ── Information tools ──────────────────────────────────────────────────────────

@tool
def search_wikipedia(query: str) -> str:
    """Search Wikipedia for factual information about a topic or concept."""
    try:
        return wikipedia.summary(query, sentences=3)
    except wikipedia.DisambiguationError as e:
        return f"Ambiguous query. Did you mean one of: {', '.join(e.options[:5])}?"
    except Exception as exc:
        return f"Could not find information about '{query}': {exc}"


@tool
def get_current_time() -> str:
    """Get the current date and time."""
    return datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")


# ── System tools ───────────────────────────────────────────────────────────────

@tool
def open_application(app_name: str) -> str:
    """
    Open a named application or file on the user's machine.
    Works cross-platform: use the app name (e.g. 'chrome', 'notepad',
    'spotify') or a full file path.
    """
    from platform.detector import open_file_or_app
    return open_file_or_app(app_name)


@tool
def read_file(path: str) -> str:
    """
    Read and return the contents of a file.
    Use ~ for the home directory. Returns an error if the file doesn't exist
    or is larger than 100 KB.
    """
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"File not found: {path}"
        if p.stat().st_size > 102_400:
            return f"File is too large (>{102_400 // 1024} KB) to read in full."
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"Error reading file: {exc}"


@tool
def write_file(path: str, content: str) -> str:
    """
    Write content to a file, creating it and any parent directories if needed.
    Overwrites if the file already exists. Use ~ for the home directory.
    """
    try:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content)} characters to {p}."
    except Exception as exc:
        return f"Error writing file: {exc}"


@tool
def run_python_code(code: str) -> str:
    """
    Execute a short Python code snippet and return its stdout output.
    Imports of os, subprocess, sys, shutil, and socket are blocked for safety.
    """
    _BLOCKED_MODULES = {"os", "subprocess", "sys", "shutil", "socket", "ctypes"}

    # Static safety check before executing
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"Syntax error: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod in _BLOCKED_MODULES:
                    return f"Blocked: import of '{alias.name}' is not permitted."
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            if mod in _BLOCKED_MODULES:
                return f"Blocked: import of '{node.module}' is not permitted."

    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            exec(compile(code, "<trixie_exec>", "exec"), {})  # noqa: S102
        return stdout.getvalue() or "(no output)"
    except Exception as exc:
        return f"Runtime error: {exc}"


# ── Memory tools ───────────────────────────────────────────────────────────────

@tool
def remember_fact(fact: str) -> str:
    """
    Store an important fact, note, or piece of information in Trixie's
    long-term memory. Use this when the user says 'remember that…' or
    shares something they'll want Trixie to know in future sessions.
    """
    from core.memory import store_episodic
    store_episodic(fact)
    return f"Stored in memory: {fact}"


@tool
def recall_facts(query: str) -> str:
    """
    Search Trixie's long-term memory for facts related to a query.
    Use this to answer questions like 'what do you know about X?' or
    when you need to retrieve something the user told Trixie earlier.
    """
    from core.memory import search_episodic
    results = search_episodic(query)
    if not results:
        return "No relevant memories found."
    return "From memory:\n" + "\n".join(f"• {r}" for r in results)


# ── Vision tool ────────────────────────────────────────────────────────────────

@tool
def look_at_screen() -> str:
    """
    Capture and describe the user's current screen in one sentence.
    Only works when the user has enabled vision. Returns 'Vision is off'
    if the user has not enabled it.
    """
    from core.vision import vision
    return vision.describe_context()


# ── Registry ───────────────────────────────────────────────────────────────────

ALL_TOOLS = [
    search_wikipedia,
    get_current_time,
    open_application,
    read_file,
    write_file,
    run_python_code,
    remember_fact,
    recall_facts,
    look_at_screen,
]
