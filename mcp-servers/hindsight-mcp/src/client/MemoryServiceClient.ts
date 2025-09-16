import axios, { AxiosInstance } from 'axios';

// Define interfaces for the data models based on architecture_memoire_agent_en.md
export interface CreateMemoryBlockPayload {
  agent_id: string; // UUID
  conversation_id: string; // UUID
  content: string; // Main content of the memory block
  errors?: string;
  lessons_learned?: string;
  metadata_col?: Record<string, any>;
  visibility_scope?: 'personal' | 'organization' | 'public';
  organization_id?: string;
}

export interface MemoryBlock {
  // Note: backend returns `id` (UUID). Keep other fields that tools actually use.
  id?: string;
  agent_id: string; // UUID
  conversation_id: string; // UUID
  timestamp: string; // TIMESTAMP
  content: string;
  errors: string | null;
  lessons_learned?: string | null;
  metadata_col?: Record<string, any> | null;
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
  visibility_scope?: 'personal' | 'organization' | 'public';
  organization_id?: string;
}

export interface RetrieveMemoriesPayload {
  keywords: string; // CSV keywords for search
  agent_id: string;
  conversation_id?: string;
  limit?: number;
}

export interface ReportFeedbackPayload {
  memory_id: string; // UUID
  feedback_type: 'positive' | 'negative' | 'neutral';
  feedback_details?: string;
}

export interface AdvancedSearchPayload {
  search_query: string;
  search_type?: 'basic' | 'fulltext' | 'semantic' | 'hybrid';
  agent_id?: string;
  conversation_id?: string;
  limit?: number;
  min_score?: number;
  similarity_threshold?: number;
  fulltext_weight?: number;
  semantic_weight?: number;
  min_combined_score?: number;
  include_archived?: boolean;
}

export interface GetAllMemoryBlocksResponse {
  items: MemoryBlock[];
  total_items: number;
  total_pages: number;
}

export interface MemoryServiceClientConfig {
  baseUrl: string;
  apiToken?: string;
  headerName?: 'Authorization' | 'X-API-Key';
  scope?: 'personal' | 'organization' | 'public';
  organizationId?: string;
}

export class MemoryServiceClient {
  private client: AxiosInstance;

  constructor(config: MemoryServiceClientConfig) {
    const {
      baseUrl,
      apiToken,
      headerName = 'Authorization',
      scope,
      organizationId,
    } = config;

    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (apiToken) {
      if (headerName === 'Authorization') {
        headers['Authorization'] = `Bearer ${apiToken}`;
      } else {
        headers['X-API-Key'] = apiToken;
      }
    }
    if (scope) {
      headers['X-Active-Scope'] = scope;
    }
    if (organizationId) {
      headers['X-Organization-Id'] = organizationId;
    }

    this.client = axios.create({ baseURL: baseUrl, headers });
  }

  async whoAmI(): Promise<any> {
    const response = await this.client.get('/user-info');
    return response.data;
  }

  /**
   * Gets details for a specific memory block by its ID.
   * @param memoryBlockId The ID of the memory block to retrieve.
   * @returns The memory block details.
   */
  async getMemoryDetails(memoryBlockId: string): Promise<MemoryBlock> {
    const response = await this.client.get<MemoryBlock>(`/memory-blocks/${memoryBlockId}`);
    return response.data;
  }

  /**
   * Creates a new memory block.
   * @param payload The data to create the memory block with.
   * @returns An object containing the created memory ID.
   */
  async createMemoryBlock(payload: CreateMemoryBlockPayload): Promise<{ id: string }> {
    const response = await this.client.post<{ id: string }>(
      '/memory-blocks/',
      payload
    );
    return response.data;
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
  async getMemoryBlocksByConversationId(conversation_id: string, agent_id?: string, limit?: number, opts?: { scope?: string; organization_id?: string }): Promise<MemoryBlock[]> {
    const params: any = { conversation_id };
    if (agent_id) {
      params.agent_id = agent_id;
    }
    if (limit) {
      params.limit = limit;
    }
    if (opts?.scope) params.scope = opts.scope;
    if (opts?.organization_id) params.organization_id = opts.organization_id;
    const response = await this.client.get<GetAllMemoryBlocksResponse>('/memory-blocks/', { params });
    return response.data.items || [];
  }

  /**
   * Retrieves all memory blocks, optionally filtered by agent_id.
   * @param agent_id Optional UUID of the agent to filter memories.
   * @param limit Optional maximum number of memories to retrieve.
   * @returns An object containing an array of memory blocks and pagination info.
   */
  async getAllMemoryBlocks(agent_id?: string, limit?: number, opts?: { scope?: string; organization_id?: string }): Promise<GetAllMemoryBlocksResponse> {
    const params: any = {};
    if (agent_id) {
      params.agent_id = agent_id;
    }
    if (limit) {
      params.limit = limit;
    }
    if (opts?.scope) params.scope = opts.scope;
    if (opts?.organization_id) params.organization_id = opts.organization_id;
    const response = await this.client.get<GetAllMemoryBlocksResponse>('/memory-blocks/', { params });
    return response.data;
  }

  /**
   * Retrieves relevant memory blocks based on a query.
   * @param payload The query parameters for retrieving memories.
   * @returns An array of relevant memory blocks.
   */
  async retrieveRelevantMemories(payload: RetrieveMemoriesPayload): Promise<MemoryBlock[]> {
    const response = await this.client.get<MemoryBlock[]>('/memory-blocks/search/', { params: payload });
    return response.data;
  }

  // Search endpoints returning scored memory blocks
  async searchFulltext(params: { query: string; agent_id?: string; conversation_id?: string; limit?: number; min_score?: number; include_archived?: boolean; }): Promise<MemoryBlock[]> {
    const response = await this.client.get<MemoryBlock[]>('/memory-blocks/search/fulltext', { params });
    return response.data;
  }

  async searchSemantic(params: { query: string; agent_id?: string; conversation_id?: string; limit?: number; similarity_threshold?: number; include_archived?: boolean; }): Promise<MemoryBlock[]> {
    const response = await this.client.get<MemoryBlock[]>('/memory-blocks/search/semantic', { params });
    return response.data;
  }

  async searchHybrid(params: { query: string; agent_id?: string; conversation_id?: string; limit?: number; fulltext_weight?: number; semantic_weight?: number; min_combined_score?: number; include_archived?: boolean; }): Promise<MemoryBlock[]> {
    const response = await this.client.get<MemoryBlock[]>('/memory-blocks/search/hybrid', { params });
    return response.data;
  }

  async searchAgents(query: string): Promise<Agent[]> {
    const response = await this.client.get<Agent[]>(`/agents/search/`, { params: { query } });
    return response.data;
  }

  /**
   * Reports feedback for a specific memory block.
   * @param payload The feedback data.
   * @returns A success message.
   */
  async reportMemoryFeedback(payload: ReportFeedbackPayload): Promise<MemoryBlock> {
    const response = await this.client.post<MemoryBlock>(`/memory-blocks/${payload.memory_id}/feedback/`, payload);
    return response.data;
  }
}
