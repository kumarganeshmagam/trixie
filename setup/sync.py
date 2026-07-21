"""
Trixie 2.0 — GitHub sync (soul + memory backup / restore).

Trixie's portable identity lives in two directories:
  soul/    → personality, rules, adaptations (small text files)
  memory/  → episodic facts, vector store, evolution log, decisions

Syncing to a *private* GitHub repo lets you restore Trixie exactly
as she was on any new device.

Rules:
  • Trixie CANNOT trigger sync automatically — always user-initiated.
  • The repo should be private (user's own account).
  • Credentials are never stored by Trixie; git uses the system keychain
    or a token the user passes explicitly.

Usage (CLI):
  /sync push https://github.com/you/trixie-memory
  /sync pull https://github.com/you/trixie-memory

Usage (Python):
  from setup.sync import sync_push, sync_pull
  sync_push("https://github.com/you/trixie-memory")
  sync_pull("https://github.com/you/trixie-memory")
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
SOUL_DIR = ROOT / "soul"
MEMORY_DIR = ROOT / "memory"

# Directories included in the sync — model files are excluded (re-downloaded)
SYNC_DIRS = [SOUL_DIR, MEMORY_DIR]
# Never sync large binary/vector-store files
GITIGNORE_PATTERNS = [
    "memory/semantic/",   # Chroma files — large, can be rebuilt from episodic
    "*.gguf",             # Model weights
    "__pycache__/",
    "*.pyc",
]


def sync_push(repo_url: str) -> None:
    """
    Push soul/ and memory/ to the user's private GitHub repo.

    Creates the repo structure if it doesn't exist locally as a git repo.
    Uses the system git credential store for authentication.
    """
    sync_dir = _prepare_sync_repo(repo_url)
    _copy_to_sync(sync_dir)
    _git(sync_dir, ["add", "."])
    _git(sync_dir, ["commit", "-m", "trixie sync: soul + memory backup",
                    "--allow-empty"])
    print("[sync] Pushing to GitHub …")
    result = _git(sync_dir, ["push", "-u", "origin", "main"], check=False)
    if result.returncode == 0:
        print("[sync] Push complete.")
    else:
        print("[sync] Push failed — check your credentials and repo URL.")


def sync_pull(repo_url: str) -> None:
    """
    Pull soul/ and memory/ from the user's private GitHub repo.

    Merges into the local directories. Existing files are overwritten.
    """
    sync_dir = _prepare_sync_repo(repo_url)

    print("[sync] Pulling from GitHub …")
    result = _git(sync_dir, ["pull", "origin", "main"], check=False)
    if result.returncode != 0:
        print("[sync] Pull failed — check your credentials and repo URL.")
        return

    _copy_from_sync(sync_dir)
    print("[sync] Pull complete — soul and memory restored.")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _prepare_sync_repo(repo_url: str) -> Path:
    sync_dir = Path.home() / ".trixie" / "sync_repo"
    sync_dir.mkdir(parents=True, exist_ok=True)

    git_dir = sync_dir / ".git"
    if not git_dir.exists():
        _git(sync_dir, ["init"])
        _git(sync_dir, ["remote", "add", "origin", repo_url])
        _write_gitignore(sync_dir)
        _git(sync_dir, ["add", ".gitignore"])
        _git(sync_dir, ["commit", "-m", "init", "--allow-empty"])
    else:
        # Update remote URL in case it changed
        _git(sync_dir, ["remote", "set-url", "origin", repo_url], check=False)

    return sync_dir


def _copy_to_sync(sync_dir: Path) -> None:
    for src in SYNC_DIRS:
        if not src.exists():
            continue
        dst = sync_dir / src.name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(str(src), str(dst), ignore=_ignore_patterns())


def _copy_from_sync(sync_dir: Path) -> None:
    for name in ("soul", "memory"):
        src = sync_dir / name
        if not src.exists():
            continue
        dst = ROOT / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(str(src), str(dst))


def _ignore_patterns():
    return shutil.ignore_patterns(
        "*.gguf", "*.bin", "__pycache__", "*.pyc", "chroma.sqlite3", "*.parquet"
    )


def _write_gitignore(sync_dir: Path) -> None:
    content = "\n".join(GITIGNORE_PATTERNS) + "\n"
    (sync_dir / ".gitignore").write_text(content, encoding="utf-8")


def _git(cwd: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        check=check,
        capture_output=not check,
    )
