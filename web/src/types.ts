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
}
