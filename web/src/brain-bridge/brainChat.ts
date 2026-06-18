// brainChat — AI-3 (BODY) integration glue between the live chat and the BRAIN.
// Owned by AI-3 (its own folder; only imports AI-1's PUBLIC hook API).
//
// Three jobs, all offline-first + key-free:
//   1) observeTurn(): feed every real chat turn into the learner — it persists itself
//      via AI-1's async brainStore (IndexedDB for guests, Supabase when signed in),
//      so no snapshot mirroring here (that would clobber the fresh persisted brain).
//   2) localAnswer(): BRAIN-FIRST — covers(query) answers offline when the brain has
//      it; otherwise null → the chat tries web search, then the model. Default ON.
//   3) learnWebHits(): store web-search results back into the brain (region:web +
//      vocabulary) → self-improvement, so next time covers() answers it directly.
import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useBrainLearning, pickFacts, studyQuestion, type WebHit } from '../brain';
import { extractKeyContent } from '../autolearn';
import { streamChat } from '../lib/api';

const FLAG_KEY = 'auri.brain.localAnswer'; // '0' disables; anything else (default) = ON
const SELF_STUDY_KEY = 'auri.brain.selfStudy'; // '1' enables (DEFAULT OFF — makes model calls)
let selfStudyLoopActive = false; // module guard: one self-study loop even if useBrainChat mounts twice

/** Is the background self-study loop enabled? DEFAULT OFF (it calls the model on its
 *  own); set the flag to '1' to let the brain study via the model while idle. */
export function selfStudyEnabled(): boolean {
  try {
    return localStorage.getItem(SELF_STUDY_KEY) === '1';
  } catch {
    return false;
  }
}
export function setSelfStudyEnabled(on: boolean): void {
  try {
    localStorage.setItem(SELF_STUDY_KEY, on ? '1' : '0');
  } catch {
    /* storage blocked */
  }
}

/** Is the offline local-answer route enabled? DEFAULT ON — set the flag to '0' to
 *  turn it off and always use the model (Ollama/Groq/Gemini). */
export function localAnswerEnabled(): boolean {
  try {
    return localStorage.getItem(FLAG_KEY) !== '0';
  } catch {
    return true;
  }
}

/** Toggle the local-answer route (for a visible /brain or settings control). */
export function setLocalAnswerEnabled(on: boolean): void {
  try {
    localStorage.setItem(FLAG_KEY, on ? '1' : '0');
  } catch {
    /* storage blocked */
  }
}

export interface BrainChat {
  /** Feed one chat turn into the learner (it persists itself). Safe: never throws. */
  observeTurn: (userText: string, assistantText: string) => void;
  /** BRAIN-first answer (offline, no key) when covered; null → try web/model. */
  localAnswer: (query: string, memories: Parameters<typeof pickFacts>[0]) => string | null;
  /** Store web-search hits (+ optional page text, distilled) into the brain for
   *  self-improvement. Safe: never throws. */
  learnWebHits: (query: string, hits: WebHit[], pages?: string[]) => void;
  /** Hybrid H1 — the BRAIN KNOWLEDGE grounding block for a query, to prepend to the
   *  model's system message so a small Ollama model answers grounded in our brain.
   *  Empty string when the brain has nothing relevant. Safe: never throws. */
  groundContext: (query: string, memories: Parameters<typeof pickFacts>[0]) => string;
  /** Hybrid H2 — distil a MODEL answer into the brain (richer than observeTurn: stores
   *  a clean recallable Q→A + grows vocab). Use on the model path. Safe: never throws. */
  distill: (query: string, answer: string) => void;
}

export function useBrainChat(): BrainChat {
  const { observe, covers, learnWeb, ground, distill, studyTopic } = useBrainLearning();

  // Hybrid H4 — self-study loop: while idle, the brain picks a topic, the model
  // explains it, and the answer is distilled back in. DEFAULT OFF (makes model calls);
  // gentle (every 90s), capped per session, in-flight-guarded, never throws.
  const study = useRef({ inFlight: false, count: 0 });
  useEffect(() => {
    if (!selfStudyEnabled()) return;
    if (selfStudyLoopActive) return; // only ONE loop even if useBrainChat mounts twice
    selfStudyLoopActive = true;
    const MAX_PER_SESSION = 40;
    const id = window.setInterval(() => {
      const st = study.current;
      if (st.inFlight || st.count >= MAX_PER_SESSION) return;
      const topic = studyTopic();
      if (!topic) return;
      const q = studyQuestion(topic);
      st.inFlight = true;
      let acc = '';
      void streamChat(
        [
          { role: 'system', content: 'You are a concise, factual teacher. Answer in 2-4 sentences.' },
          { role: 'user', content: q },
        ],
        {
          onDelta: (d) => {
            acc += d;
          },
          onDone: () => {
            st.inFlight = false;
            st.count++;
            if (acc.trim().length > 12) {
              try {
                distill(q, acc); // learn what the model taught (H2)
              } catch {
                /* never break */
              }
            }
          },
          onError: () => {
            st.inFlight = false; // model unavailable → just skip this round
          },
        },
        undefined,
        { temperature: 0.3, maxTokens: 256 },
      );
    }, 90_000);
    return () => {
      window.clearInterval(id);
      selfStudyLoopActive = false;
    };
  }, [studyTopic, distill]);

  const observeTurn = useCallback(
    (userText: string, assistantText: string) => {
      try {
        observe(userText, assistantText); // grows + persists (AI-1's async brainStore)
      } catch {
        /* learning must NEVER break the chat */
      }
    },
    [observe],
  );

  const localAnswer = useCallback(
    (query: string, memories: Parameters<typeof pickFacts>[0]): string | null => {
      if (!localAnswerEnabled()) return null; // disabled → always use the model
      try {
        const facts = pickFacts(memories, query); // personal memory supplies the FACT
        const { covered, answer } = covers(query, facts); // brain-first: does it cover it?
        return covered && answer.trim() ? answer.trim() : null; // else → web/model
      } catch {
        return null;
      }
    },
    [covers],
  );

  const learnWebHits = useCallback(
    (query: string, hits: WebHit[], pages?: string[]) => {
      try {
        // Distil any fetched page text down to its query-relevant essence (AI-4's
        // extractKeyContent) so the brain learns the IMPORTANT content, not boilerplate.
        const keyPages = (pages ?? [])
          .map((p) => extractKeyContent(p, query, { maxSentences: 4, maxChars: 600 }))
          .filter((t) => t.trim().length > 0);
        learnWeb(query, hits, keyPages); // region:web docs + vocab → self-improvement
      } catch {
        /* never break the chat */
      }
    },
    [learnWeb],
  );

  const groundContext = useCallback(
    (query: string, memories: Parameters<typeof pickFacts>[0]): string => {
      try {
        return ground(query, memories);
      } catch {
        return ''; // grounding must NEVER break the chat
      }
    },
    [ground],
  );

  const distillTurn = useCallback(
    (query: string, answer: string) => {
      try {
        distill(query, answer); // learn the model's answer for an offline answer next time
      } catch {
        /* distillation must NEVER break the chat */
      }
    },
    [distill],
  );

  return useMemo(
    () => ({ observeTurn, localAnswer, learnWebHits, groundContext, distill: distillTurn }),
    [observeTurn, localAnswer, learnWebHits, groundContext, distillTurn],
  );
}
