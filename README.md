# KeyMuse

Speech-to-text dictation app for Windows. Press a hotkey, speak, release - text appears.

## Quick Start

### 1. Setup (one time)

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend\requirements.txt
pip install -r client\requirements.txt
pip install -r shared\requirements.txt
```

### 2. Run

```powershell
scripts\run_windows.ps1
```

The app loads the speech recognition model and starts listening for the hotkey.

- **Press Ctrl+Alt** to start recording
- **Release** to stop and insert text
- **Ctrl+C** to exit

## How It Works

KeyMuse runs as a single unified app:
1. Backend (speech recognition) runs in a background process (subprocess)
2. Client (hotkey detection, audio capture, text insertion) runs in the main thread
3. Uses NVIDIA Parakeet model for fast, accurate transcription

## Options

```powershell
# Use mock backend for testing (no GPU needed)
scripts\run_windows.ps1 --mode mock

# Verbose logging
scripts\run_windows.ps1 -v
```

## Build Executable

```powershell
.venv\Scripts\Activate.ps1
pip install pyinstaller
$env:PYTHONPATH = "shared\src;backend\src;client\src"
pyinstaller build.spec
```

Output: `dist\KeyMuse\KeyMuse.exe`

## Requirements

- Windows 10/11
- Python 3.11 or newer
- NVIDIA GPU with CUDA (for real-time transcription)
- ~2GB disk space for model
