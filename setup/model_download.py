"""
Trixie 2.0 — First-run model download & setup.

Strategy per platform:
  Desktop (Windows / macOS / Linux)
    → Install Ollama if missing
    → Start Ollama server
    → Pull gemma2:4b  (~2.7 GB, one-time download)

  Mobile (Android / iOS)
    → Download gemma-2-4b-it-Q4_K_M.gguf directly from HuggingFace (~2.7 GB)
    → Store in app-private data directory
    → Use llama-cpp-python for local inference

Model sources:
  Ollama model page : https://ollama.com/library/gemma2
  GGUF (HuggingFace): https://huggingface.co/bartowski/gemma-2-4b-it-GGUF
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

import requests

# ── Model config ───────────────────────────────────────────────────────────────

OLLAMA_MODEL = "gemma2:4b"

# Quantised GGUF for mobile / llama.cpp (Q4_K_M ≈ 2.7 GB — best quality/size tradeoff)
GGUF_URL = (
    "https://huggingface.co/bartowski/gemma-2-4b-it-GGUF"
    "/resolve/main/gemma-2-4b-it-Q4_K_M.gguf"
)
# Lighter option for low-RAM devices (Q2_K ≈ 1.6 GB, lower quality)
GGUF_URL_LIGHT = (
    "https://huggingface.co/bartowski/gemma-2-4b-it-GGUF"
    "/resolve/main/gemma-2-4b-it-Q2_K.gguf"
)
GGUF_FILENAME = "gemma-2-4b-it-Q4_K_M.gguf"

# Ollama desktop installers
OLLAMA_INSTALLER_URLS: dict[str, str] = {
    "Windows": "https://ollama.com/download/OllamaSetup.exe",
    "Darwin":  "https://ollama.com/download/Ollama-darwin.zip",
    # Linux uses the official install script
    "Linux":   "https://ollama.com/install.sh",
}

OLLAMA_API = "http://localhost:11434"


# ── Platform detection ─────────────────────────────────────────────────────────

def detect_platform() -> str:
    """Return one of: 'Windows', 'Darwin', 'Linux', 'Android', 'iOS'."""
    # Android: ANDROID_ROOT or ANDROID_DATA is set in the environment
    if os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA"):
        return "Android"
    # iOS (BeeWare/Briefcase sets BRIEFCASE_PLATFORM or SDK_NAME)
    sdk = os.environ.get("SDK_NAME", "")
    if "iphone" in sdk.lower() or os.environ.get("BRIEFCASE_PLATFORM") == "iOS":
        return "iOS"
    return platform.system()  # 'Windows', 'Darwin', 'Linux'


# ── Ollama helpers ─────────────────────────────────────────────────────────────

def is_ollama_running() -> bool:
    try:
        r = requests.get(f"{OLLAMA_API}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def is_model_available() -> bool:
    """Check whether gemma2:4b is already pulled in Ollama."""
    try:
        r = requests.get(f"{OLLAMA_API}/api/tags", timeout=3)
        if r.status_code == 200:
            names = [m["name"] for m in r.json().get("models", [])]
            return any(OLLAMA_MODEL.split(":")[0] in n for n in names)
    except Exception:
        pass
    return False


def start_ollama_server() -> bool:
    """Attempt to start the Ollama server in the background."""
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Wait up to 10 s for the server to respond
        for _ in range(10):
            time.sleep(1)
            if is_ollama_running():
                return True
    except FileNotFoundError:
        pass
    return False


def pull_model() -> bool:
    """Pull gemma2:4b via Ollama CLI. Streams progress to stdout."""
    print(f"[setup] Pulling {OLLAMA_MODEL} via Ollama — this may take a while …")
    result = subprocess.run(["ollama", "pull", OLLAMA_MODEL], check=False)
    return result.returncode == 0


# ── Ollama installation ────────────────────────────────────────────────────────

def _install_ollama_linux() -> bool:
    print("[setup] Installing Ollama on Linux …")
    result = subprocess.run(
        "curl -fsSL https://ollama.com/install.sh | sh",
        shell=True,
        check=False,
    )
    return result.returncode == 0


def _install_ollama_windows(tmp_dir: Path) -> bool:
    print("[setup] Downloading Ollama installer for Windows …")
    installer = tmp_dir / "OllamaSetup.exe"
    _download_file(OLLAMA_INSTALLER_URLS["Windows"], installer)
    print("[setup] Running Ollama installer (silent) …")
    result = subprocess.run([str(installer), "/S"], check=False)
    return result.returncode == 0


def _install_ollama_macos(tmp_dir: Path) -> bool:
    print("[setup] Downloading Ollama for macOS …")
    zip_path = tmp_dir / "Ollama-darwin.zip"
    _download_file(OLLAMA_INSTALLER_URLS["Darwin"], zip_path)
    print("[setup] Extracting Ollama.app …")
    subprocess.run(
        ["unzip", "-o", str(zip_path), "-d", str(tmp_dir)],
        check=False,
        stdout=subprocess.DEVNULL,
    )
    app_src = tmp_dir / "Ollama.app"
    app_dst = Path("/Applications/Ollama.app")
    if app_src.exists():
        if app_dst.exists():
            shutil.rmtree(app_dst)
        shutil.copytree(str(app_src), str(app_dst))
    # Launch Ollama so it registers as a background service
    subprocess.Popen(
        ["/Applications/Ollama.app/Contents/MacOS/Ollama"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True


def install_ollama(plat: str) -> bool:
    tmp_dir = Path.home() / ".trixie" / "setup"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    if plat == "Linux":
        return _install_ollama_linux()
    if plat == "Windows":
        return _install_ollama_windows(tmp_dir)
    if plat == "Darwin":
        return _install_ollama_macos(tmp_dir)
    return False


# ── GGUF download (mobile / llama.cpp) ────────────────────────────────────────

def get_mobile_model_dir() -> Path:
    """Return the platform-appropriate private data directory for the model."""
    plat = detect_platform()
    if plat == "Android":
        # Kivy / BeeWare sets ANDROID_PRIVATE; fall back to /data/data
        base = os.environ.get("ANDROID_PRIVATE", "/data/data/com.trixie.app")
        return Path(base) / "models"
    if plat == "iOS":
        # BeeWare Briefcase places app data under ~/Documents on iOS
        return Path.home() / "Documents" / "trixie" / "models"
    # Desktop fallback (for llama.cpp testing on desktop)
    return Path.home() / ".trixie" / "models"


def download_gguf(
    dest_dir: Path | None = None,
    light: bool = False,
    progress_cb: Callable[[int, int], None] | None = None,
) -> Path:
    """
    Download the Gemma GGUF model file.

    Args:
        dest_dir:    Where to save the file (defaults to mobile model dir).
        light:       Use the smaller Q2_K quantisation (~1.6 GB) instead of Q4_K_M.
        progress_cb: Optional callback(downloaded_bytes, total_bytes).

    Returns:
        Path to the downloaded .gguf file.
    """
    if dest_dir is None:
        dest_dir = get_mobile_model_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    url = GGUF_URL_LIGHT if light else GGUF_URL
    filename = Path(url).name
    dest = dest_dir / filename

    if dest.exists():
        print(f"[setup] Model already present: {dest}")
        return dest

    size_hint = "~1.6 GB" if light else "~2.7 GB"
    print(f"[setup] Downloading Gemma 4B GGUF ({size_hint}) …")
    print(f"[setup] Source : {url}")
    print(f"[setup] Dest   : {dest}")
    _download_file(url, dest, progress_cb=progress_cb)
    return dest


# ── Generic file downloader ────────────────────────────────────────────────────

def _download_file(
    url: str,
    dest: Path,
    progress_cb: Callable[[int, int], None] | None = None,
    chunk_size: int = 1 << 14,  # 16 KB
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        from tqdm import tqdm
        _has_tqdm = True
    except ImportError:
        _has_tqdm = False

    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))

        pbar = tqdm(total=total, unit="B", unit_scale=True, desc=dest.name) if _has_tqdm else None
        downloaded = 0

        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if progress_cb:
                    progress_cb(downloaded, total)
                if pbar:
                    pbar.update(len(chunk))

        if pbar:
            pbar.close()


# ── Top-level setup entry point ────────────────────────────────────────────────

def first_run_setup(
    model_dir: Path | None = None,
    light_model: bool = False,
    progress_cb: Callable[[int, int], None] | None = None,
) -> dict:
    """
    Run on first launch. Idempotent — safe to call multiple times.

    Returns:
        {
            "backend":    "ollama" | "llama_cpp",
            "model_path": str | None,   # set only for llama_cpp
            "ready":      bool,
        }
    """
    plat = detect_platform()
    print(f"[setup] Platform: {plat}")

    # ── Mobile path: download GGUF, use llama.cpp ─────────────────────────────
    if plat in ("Android", "iOS"):
        model_path = download_gguf(
            dest_dir=model_dir,
            light=light_model,
            progress_cb=progress_cb,
        )
        return {"backend": "llama_cpp", "model_path": str(model_path), "ready": True}

    # ── Desktop path: Ollama ──────────────────────────────────────────────────
    ollama_present = bool(shutil.which("ollama"))

    if not ollama_present:
        print("[setup] Ollama not found — installing …")
        ok = install_ollama(plat)
        if not ok:
            print("[setup] ERROR: Could not install Ollama automatically.")
            print("[setup] Please install manually: https://ollama.com/download")
            return {"backend": None, "model_path": None, "ready": False}

    if not is_ollama_running():
        print("[setup] Starting Ollama server …")
        if not start_ollama_server():
            print("[setup] ERROR: Ollama server did not start.")
            return {"backend": None, "model_path": None, "ready": False}

    if not is_model_available():
        ok = pull_model()
        if not ok:
            print(f"[setup] ERROR: Failed to pull {OLLAMA_MODEL}.")
            return {"backend": None, "model_path": None, "ready": False}

    print(f"[setup] {OLLAMA_MODEL} is ready via Ollama.")
    return {"backend": "ollama", "model_path": None, "ready": True}


if __name__ == "__main__":
    result = first_run_setup()
    print(f"\n[setup] Result: {result}")
