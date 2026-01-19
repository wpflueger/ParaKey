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
  let buffer = Buffer.alloc(0);

  const flushBuffer = () => {
    // Send any remaining audio data, padding with silence if needed
    if (buffer.length > 0 && onFrame) {
      // Pad the remaining buffer with silence to make a complete frame
      const paddedFrame = Buffer.alloc(frameBytes);
      buffer.copy(paddedFrame, 0, 0, buffer.length);
      // Rest of paddedFrame is already zeros (silence)
      onFrame({
        audio: paddedFrame,
        sample_rate_hz: options.sampleRateHz,
        channels: options.channels,
        sequence: sequence++,
        end_of_stream: false,
      });
      buffer = Buffer.alloc(0);
    }
  };

  input.on("data", (chunk: Buffer) => {
    buffer = Buffer.concat([buffer, chunk]);
    while (buffer.length >= frameBytes) {
      const frame = buffer.subarray(0, frameBytes);
      buffer = buffer.subarray(frameBytes);
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
