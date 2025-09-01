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
  memory_id: string; // UUID - Changed from 'id' to 'memory_id'
  agent_id: string; // UUID
  conversation_id: string; // UUID
  timestamp: string; // TIMESTAMP
  content: string;
  errors: string | null;
  lessons_learned: string;
  metadata: Record<string, any> | null;
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
      '/memory-blocks',
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
  async getMemoryBlocksByConversationId(conversation_id: string, agent_id?: string, limit?: number): Promise<MemoryBlock[]> {
    const params: any = { conversation_id };
    if (agent_id) {
      params.agent_id = agent_id;
    }
    if (limit) {
      params.limit = limit;
    }
    const response = await this.client.get<MemoryBlock[]>('/memory-blocks', { params });
    return response.data;
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
    const response = await this.client.get<GetAllMemoryBlocksResponse>('/memory-blocks', { params });
    return response.data;
  }

  /**
   * Retrieves relevant memory blocks based on a query.
   * @param payload The query parameters for retrieving memories.
   * @returns An array of relevant memory blocks.
   */
  async retrieveRelevantMemories(payload: RetrieveMemoriesPayload): Promise<MemoryBlock[]> {
    const response = await this.client.get<MemoryBlock[]>('/memory-blocks/search', { params: payload });
    return response.data;
  }

  /**
   * Performs advanced search on memory blocks with support for multiple search types.
   * @param payload The advanced search parameters.
   * @returns An object containing search results and pagination info.
   */
  async advancedSearch(payload: AdvancedSearchPayload): Promise<GetAllMemoryBlocksResponse> {
    const params: any = {
      search_query: payload.search_query,
      search_type: payload.search_type || 'basic',
    };
    
    // Add optional parameters only if they're provided
    if (payload.agent_id) params.agent_id = payload.agent_id;
    if (payload.conversation_id) params.conversation_id = payload.conversation_id;
    if (payload.limit) params.limit = payload.limit;
    if (payload.min_score !== undefined) params.min_score = payload.min_score;
    if (payload.similarity_threshold !== undefined) params.similarity_threshold = payload.similarity_threshold;
    if (payload.fulltext_weight !== undefined) params.fulltext_weight = payload.fulltext_weight;
    if (payload.semantic_weight !== undefined) params.semantic_weight = payload.semantic_weight;
    if (payload.min_combined_score !== undefined) params.min_combined_score = payload.min_combined_score;
    if (payload.include_archived !== undefined) params.include_archived = payload.include_archived;
    
    const response = await this.client.get<GetAllMemoryBlocksResponse>('/memory-blocks/', { params });
    return response.data;
  }

  /**
   * Reports feedback for a specific memory block.
   * @param payload The feedback data.
   * @returns A success message.
   */
  async reportMemoryFeedback(payload: ReportFeedbackPayload): Promise<string> {
    const response = await this.client.post<string>(`/memory-blocks/${payload.memory_block_id}/feedback`, payload);
    return response.data;
  }
}
