[app]

title = Trixie
package.name = trixie
package.domain = com.trixie

# ── Source ────────────────────────────────────────────────────────────────────
source.dir = .
# Entry point — Buildozer always looks for main.py; our main.py auto-detects
# that it's on Android and delegates to the Kivy UI.
source.include_exts = py,png,jpg,jpeg,gif,kv,md,jsonl,json,txt
source.include_patterns = soul/**,memory/evolution/**
source.exclude_dirs  = .git,__pycache__,bin,.trixie,tests,ui/web,ui/desktop
source.exclude_patterns = *.gguf,*.bin,autoutilities.py,app.py,upload_file.py

version = 2.0.0

# ── Requirements ─────────────────────────────────────────────────────────────
# llama-cpp-python is compiled from source via the custom p4a recipe.
# First build: ~45 min. Subsequent builds: ~5 min (cached).
requirements =
    python3==3.11,
    kivy==2.3.0,
    requests,
    tqdm,
    Pillow,
    wikipedia,
    langchain,
    langchain-community,
    langgraph,
    chromadb,
    llama-cpp-python

# Path to custom p4a recipes (adds llama-cpp-python Android build support)
p4a.local_recipes = .p4a_recipes

# ── Android ───────────────────────────────────────────────────────────────────
android.permissions =
    android.permission.INTERNET,
    android.permission.READ_EXTERNAL_STORAGE,
    android.permission.WRITE_EXTERNAL_STORAGE,
    android.permission.RECORD_AUDIO

android.arch = arm64-v8a
android.api = 33
android.minapi = 26
android.ndk = 25c
android.sdk = 33
android.ndk_api = 26
android.accept_sdk_license = True
android.allow_backup = True

# Large heap — Gemma 4B needs ~4–6 GB RAM
android.meta_data = android:largeHeap=true

# ── Build ─────────────────────────────────────────────────────────────────────
orientation = portrait
fullscreen = 0
log_level = 2

[buildozer]
log_level = 2
warn_on_root = 1
