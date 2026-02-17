# WisprTool — by FuturMinds

A free, local voice-to-text tool that transcribes your speech and types it anywhere — browser, VS Code, Notepad, Slack, or any other application. No cloud subscription required.

If you want to learn how to build tools like this yourself, 
subscribe to [FuturMinds](https://www.youtube.com/channel/UCzsmpPhpoweC6itJd_oAt3w).

---

## Features

| Feature | Description |
|---|---|
| **Global hotkey** | Hold a configurable key combo to record; release to transcribe and paste |
| **Local transcription** | Uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — fully offline, no API costs |
| **Filler removal** | Automatically strips *um, uh, you know, like, basically* |
| **Smart corrections** | Backtracks on *"actually"* / *"I mean"* — deletes the last word or sentence |
| **Numbered lists** | Converts *"first… second… third…"* into `1. 2. 3.` |
| **Smart punctuation** | Converts dictated words like *"comma"*, *"period"*, *"new line"* |
| **AI rewriting** | Optional polish via Gemini, OpenAI, or Claude — with custom style/tone instructions |
| **Transcription history** | Last 100 transcriptions with copy-on-click |
| **Cross-platform** | Windows 10/11 and macOS |

---

## ⬇️ Download & Use Instantly (No Setup Required)

**Don't want to deal with Python or code? Just download and run.**

👉 **[Download WisprTool.exe](/releases/latest)** — Windows 10/11, no installation needed.

1. Download `WhisperTool.exe` from the link above
2. Double-click to run
3. Hold **Alt + Ctrl**, speak, release — text pastes wherever your cursor is

> First launch downloads the Whisper model (~104 MB) once. Everything after that is instant.

Want to see how this was built from scratch in 20 minutes?
📺 **[Watch the full build on YouTube](YOUR_VIDEO_LINK)**

---

## Quick Start

### Windows

1. Install [Python 3.10+](https://www.python.org/downloads/) (check "Add to PATH")
2. Double-click `install.bat` — installs all dependencies
3. Double-click `run.bat` — launches WisprTool
4. Hold **Alt + Ctrl** (default), speak, release — text is pasted at your cursor

### macOS

1. Install [Python 3](https://www.python.org/downloads/) or via Homebrew: `brew install python3`
2. Open Terminal in the project folder and run:
   ```bash
   chmod +x run.command
   pip3 install -r requirements.txt
   ```
3. Double-click `run.command` — launches WisprTool
4. **Grant permissions** when prompted:
   - **Accessibility** — for global hotkey detection
     System Settings → Privacy & Security → Accessibility → add Python/WisprTool
   - **Microphone** — for recording
     System Settings → Privacy & Security → Microphone → allow
5. Hold **Alt + Ctrl** (default), speak, release — text is pasted at your cursor

> **First run** downloads the Whisper `base` model (~150 MB). Subsequent runs are instant.

---

## Using the Prebuilt Executable (Windows)

If you received a `WisprTool.exe` file:

1. Place it in any folder
2. Double-click to run — no Python or installation needed
3. On first run, the Whisper model downloads to `%USERPROFILE%\.cache\huggingface\`
4. Settings are saved as `config.json` in the same folder as the exe

Share the single `WisprTool.exe` file with anyone on Windows. They need no additional software.

---

## How to Use

1. **Position your cursor** in any text field in any application
2. **Hold the hotkey** (default: Alt + Ctrl) — a circular animated overlay appears
3. **Speak** — the waveform responds to your voice
4. **Release the hotkey** — a loading spinner shows while transcribing
5. Your **text is pasted** at the cursor automatically

### Changing the Hotkey

1. Click **Change** next to the hotkey display
2. Press and hold your desired modifier keys (e.g., Ctrl + Shift)
3. Release — the new hotkey is saved automatically

### AI Rewriting

1. Tick **Enable AI rewriting** in the AI Rewriting section
2. Choose a provider: **Gemini**, **OpenAI**, or **Claude**
3. Paste your API key
4. Optionally add style/tone instructions, e.g. *"Professional and concise"*
5. Click **Apply Settings** to save (you'll see a green confirmation)
6. Every transcription is now automatically polished by the AI before pasting

If the AI call fails, the error message appears in red below the Apply button.

---

## Building from Source

### Windows

```bash
# 1. Install build dependencies
pip install pyinstaller

# 2. Run the build script
build.bat
```

The exe is created at `dist\WisprTool.exe`.

### macOS

```bash
# 1. Install build dependencies
pip3 install pyinstaller

# 2. Make the script executable and run it
chmod +x build.sh
./build.sh
```

The binary is created at `dist/WisprTool`.

> **macOS app signing**: Unsigned macOS binaries may be blocked by Gatekeeper. Right-click → Open the first time, or run:
> ```bash
> xattr -dr com.apple.quarantine dist/WisprTool
> ```

---

## Project Structure

```
wisprTool/
├── main.py              # Main application (UI, audio, transcription, AI)
├── text_processor.py    # Text post-processing (fillers, backtrack, lists, punctuation)
├── requirements.txt     # Python dependencies
│
├── install.bat          # Windows: install dependencies
├── run.bat              # Windows: launch without console window
├── run.command          # macOS: launch script
├── build.bat            # Windows: build single .exe
├── build.sh             # macOS: build single binary
│
├── VERSION              # Current version (read by the app at runtime)
├── CHANGELOG.md         # Release history
├── README.md            # This file
├── .gitignore           # Git ignore rules
│
└── config.json          # Auto-created at runtime (not committed)
```

---

## Configuration

Settings are saved automatically to `config.json`. You can also edit it manually:

```json
{
  "hotkey": ["alt", "ctrl"],
  "model_size": "base",
  "language": "en",
  "remove_fillers": true,
  "backtrack": true,
  "numbered_lists": true,
  "smart_punctuation": true,
  "ai_rewrite": false,
  "ai_provider": "Gemini",
  "ai_api_keys": {
    "Gemini": "",
    "OpenAI": "",
    "Claude": ""
  },
  "ai_style": ""
}
```

**Model sizes** (larger = more accurate but slower):
`tiny` · `base` *(default)* · `small` · `medium` · `large-v3`

**Language**: Set to `en` for English, or leave empty for auto-detect.

---

## AI Provider Setup

### Gemini
1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Create an API key and paste it in WisprTool

### OpenAI
1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create an API key and paste it in WisprTool

### Claude (Anthropic)
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an API key and paste it in WisprTool

---

## Dependencies

| Package | Purpose |
|---|---|
| `faster-whisper` | Local speech-to-text (Whisper model, CTranslate2 backend) |
| `sounddevice` | Microphone audio capture |
| `numpy` | Audio data processing |
| `pynput` | Cross-platform global hotkey detection |
| `pyperclip` | Clipboard read/write |
| `pyautogui` | Simulate Ctrl+V / Cmd+V paste |

All AI API calls use Python's built-in `urllib` — no extra HTTP library needed.

---

## Versioning & Releases

WisprTool uses [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).

**Where the version lives:**
- `VERSION` file at the project root — single source of truth
- Shown in the app title bar: *"WhisperTool v1.0.0 (by FuturMinds)"*
- Bundled into the exe automatically by the build scripts

**To cut a new release:**

```bash
# 1. Update the VERSION file
echo "1.1.0" > VERSION

# 2. Update CHANGELOG.md with new entries under ## [1.1.0]

# 3. Commit, tag, push
git add VERSION CHANGELOG.md
git commit -m "Release v1.1.0"
git tag -a v1.1.0 -m "Release v1.1.0 — <short summary>"
git push origin master --tags

# 4. Build the exe (Windows) or binary (macOS)
build.bat        # Windows
./build.sh       # macOS

# 5. Upload dist/WisprTool.exe as a GitHub Release asset
gh release create v1.1.0 dist/WisprTool.exe --title "v1.1.0" --notes "See CHANGELOG.md"
```

**Version bumping guide:**
- `PATCH` (1.0.0 → 1.0.1) — bug fixes, minor tweaks
- `MINOR` (1.0.0 → 1.1.0) — new features, backward compatible
- `MAJOR` (1.0.0 → 2.0.0) — breaking changes to config or behavior

All past releases are documented in [CHANGELOG.md](CHANGELOG.md).

---

## Troubleshooting

**No text is pasted**
- Make sure your cursor is in a text field *before* releasing the hotkey
- On Mac, verify Accessibility permission is granted

**"Permission denied" on microphone**
- Mac: System Settings → Privacy → Microphone → allow Python or WisprTool
- Windows: Settings → Privacy → Microphone → allow desktop apps

**Hotkey not detected**
- Mac: Accessibility permission is required for `pynput` to detect keys globally
- Try running as administrator on Windows if using a restricted account

**AI rewriting fails**
- Double-check your API key
- Verify you have credits/quota on the provider's dashboard

**First run is slow**
- The Whisper model (~150 MB for `base`) downloads once on first use


## Feature Requests

Drop feature requests as GitHub Issues — the most upvoted ones get built in the next version.

If this saved you $12/month, a GitHub star takes 2 seconds and helps others find it.