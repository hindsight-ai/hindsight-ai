import axios, { AxiosInstance } from 'axios';

// Define interfaces for the data models based on architecture_memoire_agent_en.md
export interface CreateMemoryBlockPayload {
  agent_id: string; // UUID
  conversation_id: string; // UUID
  content: string; // Main content of the memory block
  errors?: string;
  lessons_learned: string;
  metadata?: Record<string, any>; // JSON
}

export interface MemoryBlock {
  memory_id: string; // UUID (mapped from API field `id`)
  agent_id: string; // UUID
  conversation_id: string; // UUID
  timestamp: string; // TIMESTAMP
  content: string;
  errors: string | null;
  lessons_learned: string;
  metadata: Record<string, any> | null; // mapped from API `metadata_col`
  feedback_score: number;
  created_at: string; // TIMESTAMP
  updated_at: string; // TIMESTAMP
}

export interface Agent {
  agent_id: string; // UUID
  agent_name: string;
  created_at: string; // TIMESTAMP
  updated_at: string; // TIMESTAMP
}

export interface CreateAgentPayload {
  agent_name: string;
}

export interface RetrieveMemoriesPayload {
  query_text: string;
  keywords: string; // Keywords for search
  agent_id: string;
  conversation_id?: string;
  limit?: number;
}

export interface ReportFeedbackPayload {
  memory_block_id: string; // UUID
  feedback_type: 'positive' | 'negative' | 'neutral';
  comment?: string;
}

export interface GetAllMemoryBlocksResponse {
  items: MemoryBlock[];
  total_items: number;
  total_pages: number;
}

export class MemoryServiceClient {
  private client: AxiosInstance;

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Gets details for a specific memory block by its ID.
   * @param memoryBlockId The ID of the memory block to retrieve.
   * @returns The memory block details.
   */
  async getMemoryDetails(memoryBlockId: string): Promise<MemoryBlock> {
    const response = await this.client.get<any>(`/memory-blocks/${memoryBlockId}`);
    const raw = response.data || {};
    return {
      memory_id: raw.id ?? raw.memory_id,
      agent_id: raw.agent_id,
      conversation_id: raw.conversation_id,
      timestamp: raw.timestamp,
      content: raw.content,
      errors: raw.errors,
      lessons_learned: raw.lessons_learned,
      metadata: raw.metadata ?? raw.metadata_col ?? null,
      feedback_score: raw.feedback_score,
      created_at: raw.created_at,
      updated_at: raw.updated_at,
    };
  }

  /**
   * Creates a new memory block.
   * @param payload The data to create the memory block with.
   * @returns An object containing the created memory ID.
   */
  async createMemoryBlock(payload: CreateMemoryBlockPayload): Promise<{ memory_id: string }> {
    const response = await this.client.post<any>('/memory-blocks', payload);
    const raw = response.data || {};
    return { memory_id: raw.id ?? raw.memory_id };
  }

  /**
   * Creates a new agent.
   * @param payload The data to create the agent with (agent_name).
   * @returns The created agent object.
   */
  async createAgent(payload: CreateAgentPayload): Promise<Agent> {
    const response = await this.client.post<Agent>(
      '/agents/',
      payload
    );
    return response.data;
  }

  /**
   * Retrieves memory blocks associated with a specific conversation ID.
   * @param conversation_id UUID of the conversation to filter memories.
   * @param agent_id Optional UUID of the agent to further filter memories.
   * @param limit Optional maximum number of memories to retrieve.
   * @returns An array of memory blocks matching the criteria.
   */
  async getMemoryBlocksByConversationId(conversation_id: string, agent_id?: string, limit?: number): Promise<MemoryBlock[]> {
    const params: any = { conversation_id };
    if (agent_id) {
      params.agent_id = agent_id;
    }
    if (limit) {
      params.limit = limit;
    }
    const response = await this.client.get<any>('/memory-blocks', { params });
    const items = (response.data?.items ?? response.data ?? []) as any[];
    return items.map((raw: any) => ({
      memory_id: raw.id ?? raw.memory_id,
      agent_id: raw.agent_id,
      conversation_id: raw.conversation_id,
      timestamp: raw.timestamp,
      content: raw.content,
      errors: raw.errors,
      lessons_learned: raw.lessons_learned,
      metadata: raw.metadata ?? raw.metadata_col ?? null,
      feedback_score: raw.feedback_score,
      created_at: raw.created_at,
      updated_at: raw.updated_at,
    }));
  }

  /**
   * Retrieves all memory blocks, optionally filtered by agent_id.
   * @param agent_id Optional UUID of the agent to filter memories.
   * @param limit Optional maximum number of memories to retrieve.
   * @returns An object containing an array of memory blocks and pagination info.
   */
  async getAllMemoryBlocks(agent_id?: string, limit?: number): Promise<GetAllMemoryBlocksResponse> {
    const params: any = {};
    if (agent_id) {
      params.agent_id = agent_id;
    }
    if (limit) {
      params.limit = limit;
    }
    const response = await this.client.get<any>('/memory-blocks', { params });
    const items = (response.data?.items ?? []) as any[];
    const mapped = items.map((raw: any) => ({
      memory_id: raw.id ?? raw.memory_id,
      agent_id: raw.agent_id,
      conversation_id: raw.conversation_id,
      timestamp: raw.timestamp,
      content: raw.content,
      errors: raw.errors,
      lessons_learned: raw.lessons_learned,
      metadata: raw.metadata ?? raw.metadata_col ?? null,
      feedback_score: raw.feedback_score,
      created_at: raw.created_at,
      updated_at: raw.updated_at,
    }));
    return {
      items: mapped,
      total_items: response.data?.total_items ?? mapped.length,
      total_pages: response.data?.total_pages ?? 1,
    };
  }

  /**
   * Retrieves relevant memory blocks based on a query.
   * @param payload The query parameters for retrieving memories.
   * @returns An array of relevant memory blocks.
   */
  async retrieveRelevantMemories(payload: RetrieveMemoriesPayload): Promise<MemoryBlock[]> {
    const response = await this.client.get<any>('/memory-blocks/search', { params: payload });
    const items = response.data as any[];
    return (items ?? []).map((raw: any) => ({
      memory_id: raw.id ?? raw.memory_id,
      agent_id: raw.agent_id,
      conversation_id: raw.conversation_id,
      timestamp: raw.timestamp,
      content: raw.content,
      errors: raw.errors,
      lessons_learned: raw.lessons_learned,
      metadata: raw.metadata ?? raw.metadata_col ?? null,
      feedback_score: raw.feedback_score,
      created_at: raw.created_at,
      updated_at: raw.updated_at,
    }));
  }

  /**
   * Reports feedback for a specific memory block.
   * @param payload The feedback data.
   * @returns A success message.
   */
  async reportMemoryFeedback(payload: ReportFeedbackPayload): Promise<string> {
    // API expects memory_id and feedback_details; we send aliases it accepts
    const body = {
      memory_block_id: payload.memory_block_id,
      feedback_type: payload.feedback_type,
      comment: payload.comment,
    };
    const response = await this.client.post<string>(`/memory-blocks/${payload.memory_block_id}/feedback/`, body);
    return response.data as any;
  }
}
