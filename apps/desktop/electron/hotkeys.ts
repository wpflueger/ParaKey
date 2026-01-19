import { uIOhook } from "uiohook-napi";

export type HotkeyCallbacks = {
  onActivate: () => void;
  onDeactivate: () => void;
};

const CTRL_KEYS = new Set([29, 3613]);
const ALT_KEYS = new Set([56, 3640]);

export const registerHoldHotkey = ({ onActivate, onDeactivate }: HotkeyCallbacks): void => {
  let ctrlDown = false;
  let altDown = false;
  let active = false;

  const updateState = () => {
    const shouldBeActive = ctrlDown && altDown;
    if (shouldBeActive && !active) {
      active = true;
      onActivate();
    } else if (!shouldBeActive && active) {
      active = false;
      onDeactivate();
    }
  };

  uIOhook.on("keydown", (event) => {
    if (CTRL_KEYS.has(event.keycode)) {
      ctrlDown = true;
    }
    if (ALT_KEYS.has(event.keycode)) {
      altDown = true;
    }
    updateState();
  });

  uIOhook.on("keyup", (event) => {
    if (CTRL_KEYS.has(event.keycode)) {
      ctrlDown = false;
    }
    if (ALT_KEYS.has(event.keycode)) {
      altDown = false;
    }
    updateState();
  });

  uIOhook.start();
};

export const stopHotkeyListener = (): void => {
  uIOhook.removeAllListeners();
  uIOhook.stop();
};
