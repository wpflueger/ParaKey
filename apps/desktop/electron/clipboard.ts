import { clipboard } from "electron";
import { UiohookKey, uIOhook } from "uiohook-napi";

// eslint-disable-next-line no-control-regex
const CONTROL_PATTERN = /[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g;
const BIDI_PATTERN = new RegExp("[\\u200E\\u200F\\u202A-\\u202E\\u2066-\\u2069]", "g");

// Store previous clipboard content to restore after paste
let previousClipboardText: string | null = null;

export const sanitizeText = (text: string): string => {
  let sanitized = text.replace(CONTROL_PATTERN, "").replace(BIDI_PATTERN, "");
  sanitized = sanitized.normalize("NFC");
  sanitized = sanitized.replace(/\r\n/g, "\n").replace(/\r/g, "\n").replace(/\n/g, "\r\n");
  // Add trailing space for natural flow between consecutive dictations
  sanitized = sanitized.trimEnd() + " ";
  return sanitized;
};

export const setClipboardText = (text: string): void => {
  // Save current clipboard content before overwriting
  previousClipboardText = clipboard.readText();
  clipboard.writeText(text);
};

export const getClipboardText = (): string => clipboard.readText();

export const sendPaste = (): void => {
  // Small delay to ensure clipboard is ready and focus is restored
  setTimeout(() => {
    // Simulate Ctrl+V keystroke
    uIOhook.keyTap(UiohookKey.V, [UiohookKey.Ctrl]);
    // Restore previous clipboard content after paste
    setTimeout(() => {
      if (previousClipboardText !== null) {
        clipboard.writeText(previousClipboardText);
        previousClipboardText = null;
      } else {
        clipboard.clear();
      }
    }, 100);
  }, 50);
};

