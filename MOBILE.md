# Trixie 2.0 — Mobile Packaging Guide

How to package and run Trixie on Android and iOS.

---

## Quick start

| Platform | Tool | Build machine |
|---|---|---|
| **Android** | Buildozer | Linux / macOS / WSL2 on Windows |
| **iOS** | BeeWare Briefcase | **macOS only** (Xcode required) |

---

## Device requirements

| Requirement | Minimum |
|---|---|
| RAM | 6 GB (8 GB recommended) |
| Free storage | 4 GB (3 GB model + 1 GB app data) |
| Android version | 8.0+ (API 26) |
| iOS version | 16+ |
| Architecture | arm64 (all phones since 2018) |

The model (~2.7 GB GGUF) is downloaded **once** on first launch over Wi-Fi
and stored in the app's private data directory. After that, everything runs
offline.

---

## Android — Buildozer

### 1. Set up the build machine

```bash
# Ubuntu 22.04 / Debian / WSL2
sudo apt-get install -y \
    git zip unzip openjdk-17-jdk \
    libffi-dev libssl-dev zlib1g-dev \
    autoconf automake libtool pkg-config \
    cmake ninja-build

pip install buildozer cython==0.29.37
```

### 2. Build the debug APK

```bash
# From the trixie/ project root:
buildozer android debug
```

First build takes **30–60 min** — it downloads the Android SDK, NDK, and
compiles `llama-cpp-python` for ARM64. Subsequent builds are ~5 min.

The APK lands in `bin/trixie-2.0.0-arm64-v8a-debug.apk`.

### 3. Install on your phone

**Option A — USB (fastest)**
```bash
# Enable USB Debugging on your phone, then:
adb install bin/trixie-*.apk
```

**Option B — Wi-Fi / file transfer**
Copy the APK to your phone and open it. Enable "Install from unknown sources"
in Settings → Apps → Special permissions.

**Option C — GitHub Actions (no build machine needed)**

Push to `main` or create a tag like `v2.0.0`. The
`.github/workflows/build-android.yml` workflow builds the APK automatically
and uploads it as a release artifact you can download and sideload.

### 4. Release APK (signed)

```bash
# Generate a keystore once:
keytool -genkey -v -keystore trixie.keystore \
        -alias trixie -keyalg RSA -keysize 2048 -validity 10000

# Add to buildozer.spec:
# android.keystore = trixie.keystore
# android.keystore_alias = trixie

buildozer android release
```

---

## iOS — BeeWare Briefcase

> **Requires macOS with Xcode 15+ installed.**

### 1. Install Briefcase

```bash
pip install briefcase
```

### 2. Create the Xcode project

```bash
briefcase create iOS
```

This generates an Xcode project under `iOS/Trixie/`.

### 3. Run on a simulator

```bash
briefcase run iOS
```

### 4. Run on a real device

```bash
# Plug in your iPhone, trust the Mac, then:
briefcase run iOS -d "Your iPhone Name"
```

You need a free or paid Apple Developer account. Free accounts can sideload
to your personal device for 7 days at a time; paid accounts ($99/yr) can
distribute via TestFlight or the App Store.

### 5. Build an IPA for TestFlight

```bash
briefcase build iOS
# → iOS/Trixie/build/Trixie.ipa
```

Upload to App Store Connect via Xcode Organizer or Transporter.

---

## What happens on first launch

```
App opens
  │
  ├─ ~/.trixie/.setup_complete exists?
  │     YES → load model, start chat
  │
  └─ NO → show download screen
          ├─ Platform = Android or iOS
          │    → download gemma-2-4b-it-Q4_K_M.gguf (~2.7 GB)
          │      from https://huggingface.co/bartowski/gemma-2-4b-it-GGUF
          │      to app private data dir
          └─ save .setup_complete → start chat
```

On Android the model is saved to:
```
/data/data/com.trixie.trixie/files/models/gemma-2-4b-it-Q4_K_M.gguf
```

On iOS:
```
~/Documents/trixie/models/gemma-2-4b-it-Q4_K_M.gguf
```

**The model is never re-downloaded** unless you clear app data or reinstall.

---

## Restoring Trixie on a new phone

Trixie's identity lives in `soul/` and `memory/`. Back them up once:

```bash
# On old phone / desktop:
python main.py
> /sync push https://github.com/you/trixie-memory

# On new phone (after first launch completes):
python main.py
> /sync pull https://github.com/you/trixie-memory
```

The repo should be **private**. The model is NOT synced (it's re-downloaded).
Only soul files and memories travel — ~1 MB total.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Build fails on `llama-cpp-python` | Run `buildozer android debug 2>&1 \| tail -50` for details; usually an NDK version mismatch — ensure `android.ndk = 25c` in buildozer.spec |
| App crashes on launch | Check logcat: `adb logcat \| grep python` |
| Out of memory during inference | Use the lighter model: change `light_model=True` in `setup/model_download.py` `first_run_setup()` — downloads Q2_K (~1.6 GB) instead of Q4_K_M |
| iOS: "untrusted developer" error | Settings → General → VPN & Device Management → trust your developer cert |
| Model download stalls | Check Wi-Fi, retry — download is resumable (partial file is kept) |
