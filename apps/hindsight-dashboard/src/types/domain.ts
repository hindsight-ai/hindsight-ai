// Central shared domain types to reduce scattered inline interfaces.
// Incrementally refined during migration; some fields marked optional until confirmed.

export type ID = string;
export type Maybe<T> = T | null | undefined;

// Memory Block as used in UI (superset of API minimal type)
export interface UIMemoryKeyword { id: ID; keyword: string; keyword_text?: string; }
export interface UIMemoryBlock {
  id: ID;
  agent_id?: ID;
  conversation_id?: ID;
  content?: string;
  created_at?: string;
  timestamp?: string;
  feedback_score?: number | null;
  retrieval_count?: number | null;
  errors?: string;
  lessons_learned?: string;
  external_history_link?: string;
  metadata_col?: Record<string, any> | null;
  archived?: boolean;
  keywords?: UIMemoryKeyword[];
}

export interface AgentRef { agent_id: ID; agent_name?: string; visibility_scope?: string; }

// Keyword suggestion structure (normalizing possible API variations)
export interface KeywordSuggestionResult { memory_block_id: ID; keyword: string; keyword_text?: string; confidence?: number; applied?: boolean; }

// Optimization suggestion (simplified for typing pass)
export interface OptimizationSuggestion { suggestion_id: ID; type: string; status?: string; priority?: string; memory_block_ids?: ID[]; created_at?: string; rationale?: string; }

// Generic progress payloads
export interface BatchProgress { processed: number; total: number; }

// Common callback shapes
export type VoidFn = () => void;
export type ProgressCallback = (p: BatchProgress) => void;
