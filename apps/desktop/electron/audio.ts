import type { AudioFrame } from "./grpc-client";

export type AudioStreamOptions = {
  sampleRateHz: number;
  channels: number;
  frameMs: number;
  deviceIndex?: number | null;
};

export type AudioStreamController = {
  start: () => void;
  stop: () => void;
  onFrame: (callback: (frame: AudioFrame) => void) => void;
};

export const createAudioStream = async (
  options: AudioStreamOptions,
): Promise<AudioStreamController> => {
  let portAudioModule: typeof import("naudiodon");
  try {
    portAudioModule = await import("naudiodon");
  } catch (error) {
    throw new Error(
      "Audio capture library failed to load. Rebuild native modules (naudiodon) for Electron.",
      { cause: error as Error },
    );
  }
  const portAudio = portAudioModule as unknown as {
    AudioIO: new (options: {
      inOptions: {
        channelCount: number;
        sampleFormat: number;
        sampleRate: number;
        deviceId?: number;
        closeOnError: boolean;
      };
    }) => { on: (event: string, handler: (data: Buffer) => void) => void; start: () => void; quit: () => void };
    SampleFormat16Bit: number;
  };
  const frameSamples = Math.round((options.sampleRateHz * options.frameMs) / 1000);
  const frameBytes = frameSamples * options.channels * 2;

  const input = new portAudio.AudioIO({
    inOptions: {
      channelCount: options.channels,
      sampleFormat: portAudio.SampleFormat16Bit,
      sampleRate: options.sampleRateHz,
      deviceId: options.deviceIndex ?? -1,
      closeOnError: true,
    },
  });

  let sequence = BigInt(0);
  let onFrame: ((frame: AudioFrame) => void) | null = null;
  // Remainder buffer holds only the leftover bytes (< one frame) after
  // extracting complete frames. This is always small, avoiding the O(n^2)
  // cost of concatenating the entire accumulated buffer on every chunk.
  let remainder = Buffer.alloc(0);

  const flushBuffer = () => {
    // Send any remaining audio data, padding with silence if needed
    if (remainder.length > 0 && onFrame) {
      const paddedFrame = Buffer.alloc(frameBytes);
      remainder.copy(paddedFrame, 0, 0, remainder.length);
      onFrame({
        audio: paddedFrame,
        sample_rate_hz: options.sampleRateHz,
        channels: options.channels,
        sequence: sequence++,
        end_of_stream: false,
      });
      remainder = Buffer.alloc(0);
    }
  };

  input.on("data", (chunk: Buffer) => {
    // Only concat if there are leftover bytes from the previous chunk.
    // The remainder is always < frameBytes, so this concat is bounded.
    const data = remainder.length > 0 ? Buffer.concat([remainder, chunk]) : chunk;
    let offset = 0;
    while (offset + frameBytes <= data.length) {
      const frame = data.subarray(offset, offset + frameBytes);
      offset += frameBytes;
      if (onFrame) {
        onFrame({
          audio: frame,
          sample_rate_hz: options.sampleRateHz,
          channels: options.channels,
          sequence: sequence++,
          end_of_stream: false,
        });
      }
    }
    // Keep only the leftover bytes (always < frameBytes)
    remainder = offset < data.length ? data.subarray(offset) : Buffer.alloc(0);
  });

  return {
    start: () => input.start(),
    stop: () => {
      // Flush any remaining buffered audio before stopping
      flushBuffer();
      input.quit();
    },
    onFrame: (callback) => {
      onFrame = callback;
    },
  };
};
