import { credentials, makeGenericClientConstructor } from "@grpc/grpc-js";
import type { ClientWritableStream } from "@grpc/grpc-js";

export type HealthStatus = {
  ready: boolean;
  mode: string;
  detail: string;
};

export type DictationEvent = {
  partial?: { text: string };
  final?: { text: string; from_cache: boolean };
  status?: { mode: string; detail: string };
  error?: { code: string; message: string };
};

export type AudioFrame = {
  audio: Buffer;
  sample_rate_hz: number;
  channels: number;
  sequence: bigint;
  end_of_stream: boolean;
};

type GrpcDictationClient = {
  GetHealth: (payload: Record<string, never>, callback: (error: Error | null, response: HealthStatus) => void) => void;
  StreamAudio: () => ClientWritableStream<AudioFrame>;
};

const encodeJson = (payload: unknown): Buffer => Buffer.from(JSON.stringify(payload), "utf-8");

const decodeJson = (data: Buffer): Record<string, unknown> => {
  if (!data || data.length === 0) {
    return {};
  }
  return JSON.parse(data.toString("utf-8")) as Record<string, unknown>;
};

const serializeAudioFrame = (frame: AudioFrame): Buffer =>
  encodeJson({
    audio: frame.audio.toString("base64"),
    sample_rate_hz: frame.sample_rate_hz,
    channels: frame.channels,
    sequence: frame.sequence.toString(),
    end_of_stream: frame.end_of_stream,
  });

const deserializeDictationEvent = (data: Buffer): DictationEvent => {
  const payload = decodeJson(data);
  return {
    partial: typeof payload.partial === "object" && payload.partial
      ? { text: String((payload.partial as Record<string, unknown>).text ?? "") }
      : undefined,
    final: typeof payload.final === "object" && payload.final
      ? {
          text: String((payload.final as Record<string, unknown>).text ?? ""),
          from_cache: Boolean((payload.final as Record<string, unknown>).from_cache),
        }
      : undefined,
    status: typeof payload.status === "object" && payload.status
      ? {
          mode: String((payload.status as Record<string, unknown>).mode ?? ""),
          detail: String((payload.status as Record<string, unknown>).detail ?? ""),
        }
      : undefined,
    error: typeof payload.error === "object" && payload.error
      ? {
          code: String((payload.error as Record<string, unknown>).code ?? ""),
          message: String((payload.error as Record<string, unknown>).message ?? ""),
        }
      : undefined,
  };
};

const deserializeHealthStatus = (data: Buffer): HealthStatus => {
  const payload = decodeJson(data);
  return {
    ready: Boolean(payload.ready),
    mode: String(payload.mode ?? ""),
    detail: String(payload.detail ?? ""),
  };
};

export type DictationClient = {
  GetHealth: (payload: Record<string, never>) => Promise<HealthStatus>;
  StreamAudio: () => ClientWritableStream<AudioFrame>;
};

export const createDictationClient = (host: string, port: number): DictationClient => {
  const methods = {
    StreamAudio: {
      path: "/parakey.dictation.v1.DictationService/StreamAudio",
      requestStream: true,
      responseStream: true,
      requestSerialize: serializeAudioFrame,
      requestDeserialize: () => ({}) as AudioFrame,
      responseSerialize: encodeJson,
      responseDeserialize: deserializeDictationEvent,
    },
    GetHealth: {
      path: "/parakey.dictation.v1.DictationService/GetHealth",
      requestStream: false,
      responseStream: false,
      requestSerialize: () => encodeJson({}),
      requestDeserialize: () => ({}),
      responseSerialize: encodeJson,
      responseDeserialize: deserializeHealthStatus,
    },
  } as const;

  const ClientCtor = makeGenericClientConstructor(methods, "DictationService") as unknown as new (
    address: string,
    creds: ReturnType<typeof credentials.createInsecure>,
  ) => GrpcDictationClient;

  const client = new ClientCtor(`${host}:${port}`, credentials.createInsecure());

  return {
    GetHealth: (payload: Record<string, never>) =>
      new Promise((resolve, reject) => {
        client.GetHealth(payload, (error, response) => {
          if (error) {
            reject(error);
            return;
          }
          resolve(response);
        });
      }),
    StreamAudio: () => client.StreamAudio(),
  };
};

export const streamAudio = (
  client: DictationClient,
  onEvent: (event: DictationEvent) => void,
  onError: (error: Error) => void,
): ClientWritableStream<AudioFrame> => {
  const stream = client.StreamAudio();
  stream.on("data", (event: DictationEvent) => onEvent(event));
  stream.on("error", (error: Error) => onError(error));
  return stream;
};
