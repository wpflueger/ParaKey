const MAX_HISTORY = 10;
let history: string[] = [];

export const addTranscript = (text: string): void => {
  history = [...history, text].slice(-MAX_HISTORY);
};

export const getHistory = (): string[] => [...history];

export const getLastTranscript = (): string | null => {
  if (history.length === 0) {
    return null;
  }
  return history[history.length - 1];
};

export const clearHistory = (): void => {
  history = [];
};
