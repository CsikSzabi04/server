import type { Role } from './lib/api';

export interface UIMessage {
  id: string;
  role: Role;
  content: string;
  streaming?: boolean;
  error?: boolean;
  /** Where an assistant reply came from: the local brain (offline), a web search, the
   *  model, or 'brain-model' = the model answering GROUNDED in the brain's knowledge. */
  source?: 'brain' | 'model' | 'web' | 'brain-model';
  /** User turns: pasted / dropped / photographed images (data: URLs) — memory only,
   *  never saved to the conversation history or the BRAIN. */
  images?: string[];
  /** Hidden: what the text model saw for an image turn (the locally read picture + the
   *  question) — later turns reuse it instead of re-sending the picture. */
  modelContent?: string;
}
