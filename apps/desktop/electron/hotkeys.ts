import { uIOhook } from "uiohook-napi";
import type { HotkeyPreset } from "./settings";

export type HotkeyCallbacks = {
  onActivate: () => void;
  onDeactivate: () => void;
};

// Map of modifier key base codes to all their variants (left/right)
const MODIFIER_VARIANTS: Record<number, Set<number>> = {
  29: new Set([29, 3613]),     // Ctrl (left: 29, right: 3613)
  42: new Set([42, 3638]),     // Shift (left: 42, right: 3638)
  56: new Set([56, 3640]),     // Alt (left: 56, right: 3640)
  3675: new Set([3675, 3676]), // Win (left: 3675, right: 3676)
};

let key1Codes: Set<number> = new Set();
let key2Codes: Set<number> = new Set();

const updateHotkeyConfig = (preset: HotkeyPreset) => {

  switch (preset) {
    case "ctrl+alt":
      key1Codes = MODIFIER_VARIANTS[29]; // Ctrl
      key2Codes = MODIFIER_VARIANTS[56]; // Alt
      break;
    case "ctrl+shift":
      key1Codes = MODIFIER_VARIANTS[29]; // Ctrl
      key2Codes = MODIFIER_VARIANTS[42]; // Shift
      break;
    case "alt+shift":
      key1Codes = MODIFIER_VARIANTS[56]; // Alt
      key2Codes = MODIFIER_VARIANTS[42]; // Shift
      break;
    case "win+alt":
      key1Codes = MODIFIER_VARIANTS[3675]; // Win
      key2Codes = MODIFIER_VARIANTS[56];   // Alt
      break;
  }
};

export const setHotkeyPreset = (preset: HotkeyPreset): void => {
  updateHotkeyConfig(preset);
};

export const registerHoldHotkey = (
  { onActivate, onDeactivate }: HotkeyCallbacks,
  preset: HotkeyPreset = "ctrl+alt",
): void => {
  updateHotkeyConfig(preset);

  let key1Down = false;
  let key2Down = false;
  let active = false;

  const updateState = () => {
    const shouldBeActive = key1Down && key2Down;
    if (shouldBeActive && !active) {
      active = true;
      onActivate();
    } else if (!shouldBeActive && active) {
      active = false;
      onDeactivate();
    }
  };

  uIOhook.on("keydown", (event) => {
    if (key1Codes.has(event.keycode)) {
      key1Down = true;
    }
    if (key2Codes.has(event.keycode)) {
      key2Down = true;
    }
    updateState();
  });

  uIOhook.on("keyup", (event) => {
    if (key1Codes.has(event.keycode)) {
      key1Down = false;
    }
    if (key2Codes.has(event.keycode)) {
      key2Down = false;
    }
    updateState();
  });

  uIOhook.start();
};

export const stopHotkeyListener = (): void => {
  uIOhook.removeAllListeners();
  uIOhook.stop();
};
