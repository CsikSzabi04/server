// Central config. Importing this module also loads .env (via dotenv side-effect),
// so it must be the first project import in any entrypoint.
import 'dotenv/config';

function parseList(v: string | undefined): string[] {
  if (!v) return [];
  return v
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

function parseInteger(v: string | undefined, fallback: number): number {
  const n = Number.parseInt(v ?? '', 10);
  return Number.isFinite(n) ? n : fallback;
}

function parseBool(v: string | undefined, fallback: boolean): boolean {
  if (v == null) return fallback;
  return ['1', 'true', 'yes', 'on'].includes(v.trim().toLowerCase());
}

function parseFloatEnv(v: string | undefined, fallback: number): number {
  const n = Number.parseFloat(v ?? '');
  return Number.isFinite(n) ? n : fallback;
}

// Short + action-oriented on purpose: long "admit when unsure" style prompts
// make small (2-3B) models over-refuse. This keeps them helpful and on-task.
const DEFAULT_SYSTEM_PROMPT =
  'Te Auri vagy, egy gyors és segítőkész AI-asszisztens. Válaszolj magyarul, tömören, ' +
  'barátságosan és lényegre törően. Ha a felhasználó más nyelven ír, azon a nyelven válaszolj.';

export const config = {
  port: parseInteger(process.env.PORT, 8787),
  // Multiple keys supported for rotation (comma separated).
  apiKeys: parseList(process.env.AURI_API_KEY).filter((k) => k && k !== 'auri_sk_CHANGE_ME'),
  // Trailing slash stripped so we can safely append paths.
  ollamaUrl: (process.env.OLLAMA_URL ?? 'http://localhost:11434').replace(/\/+$/, ''),
  ollamaModel: process.env.OLLAMA_MODEL ?? 'llama3.2:3b',
  allowedOrigins: parseList(process.env.ALLOWED_ORIGINS),
  rateLimitPerMin: parseInteger(process.env.RATE_LIMIT_PER_MIN, 60),
  ollamaTimeoutMs: parseInteger(process.env.OLLAMA_TIMEOUT_MS, 60_000),
  logPrompts: parseBool(process.env.LOG_PROMPTS, false),
  maxMessages: parseInteger(process.env.MAX_MESSAGES, 100),
  maxPromptChars: parseInteger(process.env.MAX_PROMPT_CHARS, 24_000),

  // ── Inference quality + speed (Ollama generation) ──
  // Keep the model loaded in RAM between requests -> no cold start.
  ollamaKeepAlive: process.env.OLLAMA_KEEP_ALIVE ?? '30m',
  // Bigger context = remembers more (smarter), but slower prefill / more RAM.
  ollamaNumCtx: parseInteger(process.env.OLLAMA_NUM_CTX, 4096),
  // Default cap on generated tokens when the request omits max_tokens.
  ollamaNumPredict: parseInteger(process.env.OLLAMA_NUM_PREDICT, 768),
  // 0 = let Ollama auto-detect.
  ollamaNumThread: parseInteger(process.env.OLLAMA_NUM_THREAD, 0),
  ollamaNumBatch: parseInteger(process.env.OLLAMA_NUM_BATCH, 0),
  // Sampling defaults (used only when the request doesn't override them).
  temperature: parseFloatEnv(process.env.OLLAMA_TEMPERATURE, 0.7),
  topP: parseFloatEnv(process.env.OLLAMA_TOP_P, 0.9),
  topK: parseInteger(process.env.OLLAMA_TOP_K, 40),
  repeatPenalty: parseFloatEnv(process.env.OLLAMA_REPEAT_PENALTY, 1.1),
  // Persona / instruction injected when the request has no system message.
  // Set AURI_SYSTEM_PROMPT="" to disable the injection.
  systemPrompt: process.env.AURI_SYSTEM_PROMPT ?? DEFAULT_SYSTEM_PROMPT,
  // Concurrency gate for CPU-bound inference (avoid thrashing under load).
  maxConcurrency: parseInteger(process.env.OLLAMA_MAX_CONCURRENCY, 2),
  queueLimit: parseInteger(process.env.OLLAMA_QUEUE_LIMIT, 24),
  // Preload the model on boot so the first real request is fast.
  warmupOnBoot: parseBool(process.env.WARMUP_ON_BOOT, true),

  // ── Piper text-to-speech (local, free). Paths are resolved against the
  //    server's working directory. Defaults point at the PublicFreeAI install. ──
  piperEnabled: parseBool(process.env.PIPER_ENABLED, true),
  piperBin: process.env.PIPER_BIN ?? '../PublicFreeAI/Piper/piper/piper.exe',
  piperVoice: process.env.PIPER_VOICE ?? '../PublicFreeAI/Piper/voices/hu_HU-anna-medium.onnx',
  piperTimeoutMs: parseInteger(process.env.PIPER_TIMEOUT_MS, 30_000),
  piperMaxChars: parseInteger(process.env.PIPER_MAX_CHARS, 1_200),
} as const;

export function hasApiKeys(): boolean {
  return config.apiKeys.length > 0;
}
