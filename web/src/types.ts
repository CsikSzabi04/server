import type { Role } from './lib/api';

export interface UIMessage {
  id: string;
  role: Role;
  content: string;
  streaming?: boolean;
  error?: boolean;
}
