"""
Trixie 2.0 — Model interface.

Abstracts over two inference backends:

  ollama    → ChatOllama via langchain-ollama
              Used on desktop (Windows / macOS / Linux).
              Requires Ollama running locally on port 11434.

  llama_cpp → LlamaCpp via langchain-community
              Used on mobile (Android / iOS) or any device without Ollama.
              Requires the GGUF file downloaded by setup/model_download.py.

Usage:
    from core.model import get_llm
    llm = get_llm(backend="ollama")
"""

from __future__ import annotations

OLLAMA_MODEL = "gemma2:4b"
OLLAMA_BASE_URL = "http://localhost:11434"


def get_llm(backend: str = "ollama", model_path: str | None = None):
    """
    Return a LangChain chat model instance.

    Args:
        backend:    "ollama" (default) or "llama_cpp"
        model_path: Path to the .gguf file — required when backend="llama_cpp"
    """
    if backend == "ollama":
        return _ollama_llm()
    if backend == "llama_cpp":
        if not model_path:
            raise ValueError("model_path is required for the llama_cpp backend")
        return _llama_cpp_llm(model_path)
    raise ValueError(f"Unknown backend: {backend!r}. Choose 'ollama' or 'llama_cpp'.")


def _ollama_llm():
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.7,
        num_ctx=4096,
    )


def _llama_cpp_llm(model_path: str):
    from langchain_community.llms import LlamaCpp

    return LlamaCpp(
        model_path=model_path,
        temperature=0.7,
        max_tokens=2048,
        n_ctx=4096,
        n_batch=512,
        verbose=False,
        # Use GPU layers if available — 0 means CPU-only
        n_gpu_layers=int(__import__("os").environ.get("TRIXIE_GPU_LAYERS", "0")),
    )


def check_ollama_ready() -> bool:
    """Return True if Ollama is running and gemma2:4b is available."""
    try:
        import requests

        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if r.status_code == 200:
            names = [m["name"] for m in r.json().get("models", [])]
            return any(OLLAMA_MODEL.split(":")[0] in n for n in names)
    except Exception:
        pass
    return False
