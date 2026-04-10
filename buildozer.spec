[app]

# App identity
title = Trixie
package.name = trixie
package.domain = com.trixie

# Source
source.dir = .
source.include_exts = py,png,jpg,jpeg,gif,kv,atlas,md,jsonl,json,db,txt
source.include_patterns = soul/*,memory/evolution/*,assets/*
source.exclude_dirs = tests,bin,.git,__pycache__,.trixie
source.exclude_patterns = *.gguf,*.bin,*.so,autoutilities.py,app.py,upload_file.py

version = 2.0.0

# Entry point
entrypoint = ui/mobile/app.py

# ── Requirements ──────────────────────────────────────────────────────────────
# Note: llama-cpp-python is compiled from source by Buildozer using the
# Android NDK. This adds ~10 min to the first build but only once.
requirements =
    python3==3.11,
    kivy==2.3.0,
    kivymd,
    requests,
    tqdm,
    Pillow,
    wikipedia,
    langchain,
    langchain-community,
    langchain-ollama,
    langgraph,
    chromadb,
    llama-cpp-python

# ── Android config ────────────────────────────────────────────────────────────
android.permissions =
    android.permission.INTERNET,
    android.permission.READ_EXTERNAL_STORAGE,
    android.permission.WRITE_EXTERNAL_STORAGE,
    android.permission.RECORD_AUDIO

# ARM64 only — covers all modern Android phones (2018+)
android.arch = arm64-v8a

android.api = 33
android.minapi = 26
android.ndk = 25c
android.sdk = 33
android.ndk_api = 26

android.accept_sdk_license = True
android.allow_backup = True

# Large heap — needed for Gemma 4B inference
android.manifest.application_arguments = android:largeHeap="true"

# ── iOS config (via Briefcase — see pyproject.toml) ───────────────────────────
# iOS builds are handled by Briefcase, not Buildozer.
# Run: briefcase create iOS && briefcase run iOS

# ── Build ─────────────────────────────────────────────────────────────────────
orientation = portrait
fullscreen = 0
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
