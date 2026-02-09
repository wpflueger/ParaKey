import { useEffect, useMemo, useState } from "react";
import type { AppSettings, BackendStatus, DictationState, HotkeyPreset } from "./types";
import { getBridge } from "./bridge";
import "./App.css";

const DEFAULT_STATUS: BackendStatus = { ready: false, detail: "Initializing..." };

const formatHotkey = (preset: HotkeyPreset): string => {
  switch (preset) {
    case "ctrl+alt":
      return "Ctrl+Alt";
    case "ctrl+shift":
      return "Ctrl+Shift";
    case "alt+shift":
      return "Alt+Shift";
    case "win+alt":
      return "Win+Alt";
    default:
      return "Ctrl+Alt";
  }
};

const formatState = (state: DictationState): string => {
  switch (state) {
    case "RECORDING":
      return "Recording...";
    case "PROCESSING":
      return "Processing...";
    case "INSERTING":
      return "Inserting...";
    case "ERROR":
      return "Error";
    default:
      return "Idle";
  }
};

const statusTone = (state: DictationState): string => {
  switch (state) {
    case "RECORDING":
      return "tone-recording";
    case "PROCESSING":
    case "INSERTING":
      return "tone-processing";
    case "ERROR":
      return "tone-error";
    default:
      return "tone-idle";
  }
};

function App() {
  const [status, setStatus] = useState<BackendStatus>(DEFAULT_STATUS);
  const [dictationState, setDictationState] = useState<DictationState>("IDLE");
  const [history, setHistory] = useState<string[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [showLogs, setShowLogs] = useState(false);
  const [cachePath, setCachePath] = useState<string>("");
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [startupStatus, setStartupStatus] = useState("Preparing services...");
  const [lastLog, setLastLog] = useState<string | null>(null);

  useEffect(() => {
    const bridge = getBridge();

    const unsubLog = bridge.onBackendLog((line) => {
      setLogs((prev) => [...prev.slice(-200), line]);
      setLastLog(line);
    });
    const unsubStatus = bridge.onBackendStatus((payload) => {
      setStatus(payload);
      if (!payload.ready && payload.detail) {
        setStartupStatus(payload.detail);
      }
    });
    const unsubState = bridge.onDictationState((payload) => setDictationState(payload.state));
    const unsubTranscript = bridge.onTranscript((payload) => {
      setHistory((prev) => [payload.text, ...prev].slice(0, 10));
    });
    const unsubInstall = bridge.onInstallStatus((payload) => {
      setStatus({ ready: false, detail: payload.status });
    });
    const unsubError = bridge.onStartupError((payload) => {
      setErrorMessage(payload.message);
    });
    const unsubCache = bridge.onCachePath((payload) => setCachePath(payload.path));

    bridge.requestHistory().then(setHistory).catch(() => null);
    bridge.getSettings().then(setSettings).catch(() => null);
    bridge.requestCachePath().then(setCachePath).catch(() => null);

    return () => {
      unsubLog();
      unsubStatus();
      unsubState();
      unsubTranscript();
      unsubInstall();
      unsubError();
      unsubCache();
    };
  }, []);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showSettings) {
        setShowSettings(false);
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [showSettings]);

  const handleSaveSettings = async (next: AppSettings) => {
    await getBridge().saveSettings(next);
    setSettings(next);
    setShowSettings(false);
  };

  const recentHistory = useMemo(() => history.slice(0, 6), [history]);

  if (showLogs) {
    return (
      <div className="app logs">
        <header className="main-header">
          <div>
            <p className="eyebrow">ParaKey</p>
            <h1>Backend Logs</h1>
            <p className="subtle">Real-time backend output for debugging.</p>
          </div>
          <div className="header-actions">
            <button className="ghost" onClick={() => setShowLogs(false)}>
              Back
            </button>
            <button className="primary" onClick={() => setLogs([])}>
              Clear
            </button>
          </div>
        </header>
        <section className="log-panel full">
          <div className="log-header">
            <p>Backend Output</p>
            <span>{logs.length} lines</span>
          </div>
          <div className="log-body">
            {logs.length === 0 ? (
              <p className="log-empty">No backend output yet.</p>
            ) : (
              logs.map((line, index) => <p key={`${line}-${index}`}>{line}</p>)
            )}
          </div>
        </section>
      </div>
    );
  }

  if (!status.ready) {
    return (
      <div className="app startup">
        <header className="startup-header">
          <div>
            <p className="eyebrow">ParaKey</p>
            <h1>Preparing your dictation engine</h1>
          </div>
          <button className="ghost" onClick={() => getBridge().minimizeToTray()}>
            Minimize
          </button>
        </header>
        <section className="startup-body">
          <div className="status-card startup-card">
            <div className="status-line">
              <span className="dot" />
              <div>
                <p className="label">Startup</p>
                <p className="value">{startupStatus}</p>
              </div>
            </div>
            <div className="status-line">
              <span className="dot neutral" />
              <div>
                <p className="label">Model cache</p>
                <p className="value">{cachePath || "Detecting..."}</p>
              </div>
            </div>
            <div className="progress-bar">
              <span />
            </div>
            {lastLog && <p className="log-snippet">Last: {lastLog}</p>}
            <button className="ghost small" onClick={() => setShowLogs(true)}>
              View output logs
            </button>
          </div>
        </section>
        {errorMessage && (
          <div className="startup-error">{errorMessage}</div>
        )}
      </div>
    );
  }

  return (
    <div className="app main">
      <header className="main-header">
        <div>
          <p className="eyebrow">ParaKey</p>
          <h1>Dictation Control Center</h1>
          <p className="subtle">Press {formatHotkey(settings?.hotkey.preset ?? "ctrl+alt")} to dictate anywhere.</p>
        </div>
        <div className="header-actions">
          <button className="ghost" onClick={() => setShowLogs(true)}>
            View Logs
          </button>
          <button className="ghost" onClick={() => setShowSettings(true)}>
            Settings
          </button>
          <button className="primary" onClick={() => getBridge().minimizeToTray()}>
            Minimize to Tray
          </button>
        </div>
      </header>

      <section className="status-grid">
        <div className="status-card">
          <p className="label">Model</p>
          <p className="value">{status.ready ? "Ready" : "Not Ready"}</p>
          <span className={status.ready ? "pill" : "pill muted"}>{status.ready ? "Loaded" : "Unavailable"}</span>
        </div>
        <div className="status-card">
          <p className="label">Backend</p>
          <p className="value">{status.ready ? "Connected" : "Connecting"}</p>
          <span className={status.ready ? "pill" : "pill muted"}>{status.detail}</span>
        </div>
        <div className={`status-card ${statusTone(dictationState)}`}>
          <div className="status-line">
            <span className={`dot ${dictationState === "RECORDING" ? "recording" : ""}`} />
            <div>
              <p className="label">Dictation</p>
              <p className="value">{formatState(dictationState)}</p>
            </div>
          </div>
          <span className="pill">{formatHotkey(settings?.hotkey.preset ?? "ctrl+alt")}</span>
        </div>
      </section>

      <section className="history-panel">
        <div className="panel-header">
          <div>
            <h2>Recent transcripts</h2>
            <p>Tap copy to paste instantly.</p>
          </div>
          <button className="ghost" onClick={() => getBridge().requestHistory().then(setHistory)}>
            Refresh
          </button>
        </div>
        {recentHistory.length === 0 ? (
          <div className="empty-state">
            <p>No transcripts yet.</p>
            <p className="subtle">Hold {formatHotkey(settings?.hotkey.preset ?? "ctrl+alt")} and speak to start dictating.</p>
          </div>
        ) : (
          <div className="history-list">
            {recentHistory.map((item, index) => (
              <div className="history-item" key={`${item}-${index}`}>
                <p>{item}</p>
                <button
                  className="ghost small"
                  onClick={() => navigator.clipboard.writeText(item)}
                >
                  Copy
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {showSettings && settings && (
        <div className="modal-backdrop" onClick={() => setShowSettings(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <header>
              <h2>Settings</h2>
              <button className="ghost" onClick={() => setShowSettings(false)}>
                Close
              </button>
            </header>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                handleSaveSettings(settings);
              }}
            >
              <section>
                <h3>Hotkey</h3>
                <label>
                  Dictation shortcut
                  <select
                    value={settings.hotkey.preset}
                    onChange={(event) =>
                      setSettings({
                        ...settings,
                        hotkey: {
                          ...settings.hotkey,
                          preset: event.target.value as HotkeyPreset,
                        },
                      })
                    }
                  >
                    <option value="ctrl+alt">Ctrl + Alt</option>
                    <option value="ctrl+shift">Ctrl + Shift</option>
                    <option value="alt+shift">Alt + Shift</option>
                    <option value="win+alt">Win + Alt</option>
                  </select>
                </label>
                <p className="subtle">Hold the shortcut to record, release to transcribe.</p>
              </section>
              <section>
                <h3>Overlay</h3>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={settings.overlay.enabled}
                    onChange={(event) =>
                      setSettings({
                        ...settings,
                        overlay: { ...settings.overlay, enabled: event.target.checked },
                      })
                    }
                  />
                  Show overlay
                </label>
                <label>
                  Position
                  <select
                    value={settings.overlay.position}
                    onChange={(event) =>
                      setSettings({
                        ...settings,
                        overlay: {
                          ...settings.overlay,
                          position: event.target.value as AppSettings["overlay"]["position"],
                        },
                      })
                    }
                  >
                    <option value="top-left">Top left</option>
                    <option value="top-right">Top right</option>
                    <option value="bottom-left">Bottom left</option>
                    <option value="bottom-right">Bottom right</option>
                  </select>
                </label>
              </section>
              <section>
                <h3>General</h3>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={settings.startMinimized}
                    onChange={(event) =>
                      setSettings({
                        ...settings,
                        startMinimized: event.target.checked,
                      })
                    }
                  />
                  Start minimized
                </label>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={settings.showNotifications}
                    onChange={(event) =>
                      setSettings({
                        ...settings,
                        showNotifications: event.target.checked,
                      })
                    }
                  />
                  Show notifications
                </label>
              </section>
              <div className="modal-actions">
                <button className="ghost" type="button" onClick={() => setShowSettings(false)}>
                  Cancel
                </button>
                <button className="primary" type="submit">
                  Save
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
