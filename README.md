# KeyMuse
Speech to text app

## Quick Start (Windows)

Requires Python 3.11+ on Windows.

### First-time setup
```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
pip install -r client\requirements.txt
pip install -r shared\requirements.txt
```

### Run the app (single entrypoint, two managed processes)
```powershell
scripts\run_windows.ps1
```

This starts the backend service in a managed subprocess and then launches
the client in the same console for a single-app experience on Windows.

## Quick Start (WSL)

Requires Python 3.11+ and [pyenv](https://github.com/pyenv/pyenv) with [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv).

### First-time setup
```bash
make setup
direnv allow  # optional, auto-sets PYTHONPATH
```

### Run the app
In one terminal:
```bash
make backend
```

In another terminal:
```bash
make client
```

### Available commands
```bash
make help           # Show all commands
make setup          # Set up both virtualenvs
make backend        # Run backend server
make client         # Run client app
make test           # Run all tests
make clean          # Clean __pycache__
```

## VS Code Development

1. Open the workspace in VS Code
2. Press **F5** and select "Backend + Client" to run both with debugging
3. Or use **Ctrl+Shift+P** → "Tasks: Run Task" to run individual components

## Manual Setup (alternative)

If you prefer not to use the Makefile:

```bash
export PYTHONPATH="$PWD/shared/src"

# Backend (terminal 1)
pyenv virtualenv 3.12.3 keymuse-backend
cd backend && pyenv local keymuse-backend
pip install -r requirements.txt
python -m keymuse_backend.server

# Client (terminal 2)
pyenv virtualenv 3.12.3 keymuse-client
cd client && pyenv local keymuse-client
pip install -r requirements.txt
python -m keymuse_client.app
```

## Tests
```bash
make test
# Or manually:
PYTHONPATH=$PWD/shared/src pytest backend/tests client/tests
```

## Backend model
The backend now defaults to the NVIDIA Parakeet TDT model (`nvidia/parakeet-tdt-0.6b-v3`) and
requires a CUDA-capable GPU with CUDA-enabled PyTorch installed. To run the mock backend
instead, set `KEYMUSE_MODE=mock` before starting the backend.

## Windows Build (two managed processes)
Build the app on Windows (not WSL):

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
pip install -r client\requirements.txt
pip install -r shared\requirements.txt
$env:PYTHONPATH="shared\src;backend\src;client\src"
pytest client\tests -m "windows_only"
pyinstaller client\src\keymuse_client\launcher.py --onefile --noconsole
```
