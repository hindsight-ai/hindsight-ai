#!/usr/bin/env node

import { randomUUID } from "crypto";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";
import axios, { AxiosError } from 'axios';
import { MemoryServiceClient, MemoryServiceClientConfig, CreateMemoryBlockPayload, RetrieveMemoriesPayload, ReportFeedbackPayload, MemoryBlock, Agent, CreateAgentPayload, AdvancedSearchPayload } from './client/MemoryServiceClient';

// --- Configuration ---
const normalizeUuid = (value: unknown): string | undefined => {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
};

const API_BASE_URL = process.env.HINDSIGHT_API_BASE_URL || 'https://api.hindsight-ai.com'; // Default to hosted API
const DEFAULT_AGENT_ID = normalizeUuid(process.env.DEFAULT_AGENT_ID);
const DEFAULT_CONVERSATION_ID = normalizeUuid(process.env.DEFAULT_CONVERSATION_ID);
const API_TOKEN = process.env.HINDSIGHT_API_TOKEN || process.env.HINDSIGHT_API_KEY;
const API_HEADER: 'Authorization' | 'X-API-Key' = process.env.HINDSIGHT_API_KEY ? 'X-API-Key' : 'Authorization';
const ACTIVE_SCOPE_ENV = process.env.HINDSIGHT_ACTIVE_SCOPE as ('personal' | 'organization' | 'public' | undefined);
const DEFAULT_ORGANIZATION_ID = process.env.HINDSIGHT_ORGANIZATION_ID;

if (!API_BASE_URL) {
  throw new Error('HINDSIGHT_API_BASE_URL environment variable is required');
}

// --- Type Guards ---
const isValidCreateMemoryBlockPayload = (payload: any): payload is CreateMemoryBlockPayload => {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    typeof payload.agent_id === 'string' &&
    typeof payload.conversation_id === 'string' &&
    typeof payload.content === 'string' &&
    (payload.lessons_learned === undefined || typeof payload.lessons_learned === 'string') &&
    (payload.errors === undefined || typeof payload.errors === 'string') &&
    (payload.metadata_col === undefined || typeof payload.metadata_col === 'object')
  );
};

const isValidRetrieveMemoriesPayload = (payload: any): payload is RetrieveMemoriesPayload => {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    typeof payload.keywords === 'string' &&
    payload.keywords.trim().length > 0 &&
    typeof payload.agent_id === 'string' &&
    (payload.conversation_id === undefined || typeof payload.conversation_id === 'string') &&
    (payload.limit === undefined || typeof payload.limit === 'number')
  );
};

const isValidReportFeedbackPayload = (payload: any): payload is ReportFeedbackPayload => {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    typeof payload.memory_id === 'string' &&
    ['positive', 'negative', 'neutral'].includes(payload.feedback_type) &&
    (payload.feedback_details === undefined || typeof payload.feedback_details === 'string')
  );
};

const isValidSearchAgentsPayload = (payload: any): payload is { query: string } => {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    typeof payload.query === 'string'
  );
};

const isValidAdvancedSearchPayload = (payload: any): payload is AdvancedSearchPayload => {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    typeof payload.search_query === 'string' &&
    (payload.search_type === undefined || ['basic', 'fulltext', 'semantic', 'hybrid'].includes(payload.search_type)) &&
    (payload.agent_id === undefined || typeof payload.agent_id === 'string') &&
    (payload.conversation_id === undefined || typeof payload.conversation_id === 'string') &&
    (payload.limit === undefined || typeof payload.limit === 'number') &&
    (payload.min_score === undefined || typeof payload.min_score === 'number') &&
    (payload.similarity_threshold === undefined || typeof payload.similarity_threshold === 'number') &&
    (payload.fulltext_weight === undefined || typeof payload.fulltext_weight === 'number') &&
    (payload.semantic_weight === undefined || typeof payload.semantic_weight === 'number') &&
    (payload.min_combined_score === undefined || typeof payload.min_combined_score === 'number') &&
    (payload.include_archived === undefined || typeof payload.include_archived === 'boolean')
  );
};

// --- MCP Server Setup ---
const server = new Server(
  {
    name: "hindsight-mcp",
    version: "0.1.0",
    description: "MCP server for interacting with the AI agent memory service (create, retrieve, report feedback, get details)"
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// --- MemoryServiceClient Instance ---
const resolvedScope: 'personal' | 'organization' | 'public' | undefined = ACTIVE_SCOPE_ENV || (DEFAULT_ORGANIZATION_ID ? 'organization' : undefined);
if (resolvedScope === 'organization' && !DEFAULT_ORGANIZATION_ID) {
  console.warn('[hindsight-mcp] HINDSIGHT_ACTIVE_SCOPE resolved to organization but no HINDSIGHT_ORGANIZATION_ID provided. Falling back to personal scope.');
}

const clientConfig: MemoryServiceClientConfig = {
  baseUrl: API_BASE_URL,
  apiToken: API_TOKEN,
  headerName: API_HEADER,
};
if (resolvedScope && (resolvedScope !== 'organization' || DEFAULT_ORGANIZATION_ID)) {
  clientConfig.scope = resolvedScope;
}
if (resolvedScope === 'organization' && DEFAULT_ORGANIZATION_ID) {
  clientConfig.organizationId = DEFAULT_ORGANIZATION_ID;
}

const memoryServiceClient = new MemoryServiceClient(clientConfig);

// --- Tool Handlers ---

/**
 * Handler that lists available tools.
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "create_memory_block",
        description: "Create a new memory block in the AI agent memory service. conversation_id is optional; one is generated when omitted.",
        inputSchema: {
          type: "object",
          properties: {
            agent_id: {
              type: "string",
              description: "UUID of the agent (this value should not be provided, it will be filled automatically by env variables).",
            },
            conversation_id: {
              type: "string",
              description: "Optional UUID of the conversation. If omitted, a new conversation_id is generated and returned in the response.",
            },
            content: {
              type: "string",
              description: "The main content of the memory block (required).",
            },
            lessons_learned: {
              type: "string",
              description: "Lessons learned from the conversation (required, often duplicates content).",
            },
            errors: {
              type: "string",
              description: "Optional string detailing errors encountered.",
            },
            metadata: {
              type: "object",
              description: "Optional JSON object for additional metadata.",
              additionalProperties: true,
            },
          },
          required: ["content", "lessons_learned"],
        },
      },
      {
        name: "create_agent",
        description: "Create a new agent in the AI agent memory service. Requires an agent_name.",
        inputSchema: {
          type: "object",
          properties: {
            agent_name: {
              type: "string",
              description: "The name of the agent to create (required).",
            },
          },
          required: ["agent_name"],
        },
      },
      {
        name: "retrieve_relevant_memories",
        description: "Retrieve relevant memory blocks from the AI agent memory service based on a query.",
        inputSchema: {
          type: "object",
          properties: {
            keywords: {
              description: "Keywords to search for relevant memories. Accepts a comma-separated string or an array of keyword strings.",
              oneOf: [
                { type: "string" },
                { type: "array", items: { type: "string" } }
              ],
            },
            agent_id: {
              type: "string",
              description: "UUID of the agent (this value should not be provided, it will be filled automatically by env variables).",
            },
            conversation_id: {
              type: "string",
              description: "Optional conversation UUID to narrow context when desired.",
            },
            limit: {
              type: "number",
              description: "Optional maximum number of memories to retrieve (default: 10).",
            },
          },
          required: ["keywords"],
        },
      },
      {
        name: "retrieve_all_memory_blocks",
        description: "Retrieve all memory blocks, optionally filtered by agent_id and limit.",
        inputSchema: {
          type: "object",
          properties: {
            agent_id: {
              "type": "string",
              "description": "Optional UUID of the agent to filter memories (this value should not be provided, it will be filled automatically by env variables if not present).",
            },
            limit: {
              "type": "number",
              "description": "Optional maximum number of memories to retrieve (default: 50).",
            },
          },
          required: []
        },
      },
      {
        name: "retrieve_memory_blocks_by_conversation_id",
        description: "Retrieve memory blocks associated with a specific conversation_id, optionally filtered by agent_id and limit.",
        inputSchema: {
          type: "object",
          properties: {
            conversation_id: {
              "type": "string",
              "description": "UUID of the conversation to retrieve memories for (provide the value returned from create_memory_block or a configured default).",
            },
            agent_id: {
              "type": "string",
              "description": "Optional UUID of the agent to filter memories (this value should not be provided, it will be filled automatically by env variables if not present).",
            },
            limit: {
              "type": "number",
              "description": "Optional maximum number of memories to retrieve (default: 10).",
            },
          },
          required: []
        },
      },
      {
        name: "report_memory_feedback",
        description: "Report feedback (positive, negative, neutral) for a specific memory block.",
        inputSchema: {
          type: "object",
          properties: {
            memory_block_id: {
              type: "string",
              description: "UUID of the memory block to report feedback for (required).",
            },
            feedback_type: {
              type: "string",
              enum: ["positive", "negative", "neutral"],
              description: "Type of feedback (positive, negative, or neutral) (required).",
            },
            feedback_details: {
              type: "string",
              description: "Optional comment or context regarding the feedback.",
            },
            comment: {
              type: "string",
              description: "Deprecated alias for feedback_details (will be removed in a future release).",
            },
          },
          required: ["memory_block_id", "feedback_type"],
        },
      },
      {
        name: "get_memory_details",
        description: "Get details for a specific memory block by its ID.",
        inputSchema: {
          type: "object",
          properties: {
            memory_block_id: {
              type: "string",
              description: "UUID of the memory block to retrieve details for (required).",
            },
          },
          required: ["memory_block_id"],
        },
      },
      {
        name: "search_agents",
        description: "Search for agents by name using a query string.",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "The search query for the agent name (required).",
            },
          },
          required: ["query"],
        },
      },
      {
        name: "advanced_search_memories",
        description: "Perform intelligent search on memories using full-text, semantic, or hybrid search. Use 'fulltext' for keyword-based search, 'semantic' for meaning-based search, or 'hybrid' for best of both.",
        inputSchema: {
          type: "object",
          properties: {
            search_query: {
              type: "string",
              description: "The search query string (required).",
            },
            search_type: {
              type: "string",
              description: "Search method: 'fulltext' for keyword search, 'semantic' for meaning-based search, 'hybrid' for combined approach (optional, defaults to 'fulltext').",
              enum: ["fulltext", "semantic", "hybrid"],
            },
            agent_id: {
              type: "string",
              description: "Optional agent UUID. Falls back to DEFAULT_AGENT_ID when omitted.",
            },
            conversation_id: {
              type: "string",
              description: "Optional conversation UUID filter.",
            },
            limit: {
              type: "number",
              description: "Maximum number of memories to retrieve (optional, default: 10).",
            },
            min_score: {
              type: "number",
              description: "Minimum relevance score (0.0-1.0). Higher values return more relevant results (optional, default: 0.1).",
            },
            similarity_threshold: {
              type: "number",
              description: "Similarity threshold for semantic search (0.0-1.0).",
            },
            fulltext_weight: {
              type: "number",
              description: "Weighting applied to full-text results in hybrid mode (0.0-1.0).",
            },
            semantic_weight: {
              type: "number",
              description: "Weighting applied to semantic results in hybrid mode (0.0-1.0).",
            },
            min_combined_score: {
              type: "number",
              description: "Minimum combined score for hybrid search (0.0-1.0).",
            },
            include_archived: {
              type: "boolean",
              description: "Whether to include archived memories in the search (default: false).",
            },
          },
          required: ["search_query"],
        },
      },
      {
        name: "whoami",
        description: "Return the authenticated user and memberships as seen by the backend (works with PAT or OAuth)",
        inputSchema: { type: "object", properties: {}, required: [] },
      },
    ],
  };
});

/**
 * Handler for calling tools.
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const toolName = request.params.name;
  const typedArgs: Record<string, any> = request.params.arguments || {};

  try {
    // --- create_memory_block ---
    if (toolName === "create_memory_block") {
      const agent_id = normalizeUuid(typedArgs?.agent_id) || DEFAULT_AGENT_ID;
      const providedConversationId = normalizeUuid(typedArgs?.conversation_id);
      const fallbackConversationId = DEFAULT_CONVERSATION_ID;
      const conversation_id = providedConversationId || fallbackConversationId || randomUUID();
      const generatedConversationId = !providedConversationId && !fallbackConversationId;

      if (!agent_id) {
        throw new McpError(ErrorCode.InvalidParams, "Agent ID is required for create_memory_block and not provided via arguments or DEFAULT_AGENT_ID environment variable.");
      }

      const payload: CreateMemoryBlockPayload = {
        agent_id: agent_id,
        conversation_id: conversation_id,
        content: typedArgs.content,
        lessons_learned: typedArgs.lessons_learned,
        errors: typedArgs.errors,
        metadata_col: typedArgs.metadata,
      };
      if (DEFAULT_ORGANIZATION_ID) {
        payload.visibility_scope = 'organization';
        payload.organization_id = DEFAULT_ORGANIZATION_ID;
      }

      if (!isValidCreateMemoryBlockPayload(payload)) {
        throw new McpError(
          ErrorCode.InvalidParams,
          "Invalid arguments for create_memory_block. Requires 'content' (string) and 'lessons_learned' (string)."
        );
      }
      const result = await memoryServiceClient.createMemoryBlock(payload);
      let responseText = `Successfully created memory block with ID: ${result.id}. Conversation ID: ${conversation_id}.`;
      if (generatedConversationId) {
        responseText += ' Use this conversation_id for future MCP tool calls to continue the discussion context.';
      }
      return {
        content: [{ type: "text", text: responseText }]
      };
    }

    // --- create_agent ---
    else if (toolName === "create_agent") {
      const payload: CreateAgentPayload = {
        agent_name: typedArgs.agent_name,
      };
      if (DEFAULT_ORGANIZATION_ID) {
        payload.visibility_scope = 'organization';
        payload.organization_id = DEFAULT_ORGANIZATION_ID;
      }

      if (typeof payload.agent_name !== 'string' || payload.agent_name.trim() === '') {
        throw new McpError(
          ErrorCode.InvalidParams,
          "Invalid arguments for create_agent. 'agent_name' (string) is required."
        );
      }
      const result = await memoryServiceClient.createAgent(payload);
      return {
        content: [{ type: "text", text: `Successfully created agent with ID: ${result.agent_id} and name: ${result.agent_name}` }]
      };
    }

    // --- retrieve_all_memory_blocks ---
    else if (toolName === "retrieve_all_memory_blocks") {
      const agent_id = normalizeUuid(typedArgs?.agent_id) || DEFAULT_AGENT_ID;
      const limit = typedArgs?.limit as number | undefined;

      if (!agent_id) {
        throw new McpError(ErrorCode.InvalidParams, "Agent ID is required for retrieve_all_memory_blocks and not provided via arguments or DEFAULT_AGENT_ID environment variable.");
      }

      const response = await memoryServiceClient.getAllMemoryBlocks(
        agent_id,
        limit,
        DEFAULT_ORGANIZATION_ID ? { scope: 'organization', organization_id: DEFAULT_ORGANIZATION_ID } : undefined
      );
      // The API returns an object with an 'items' array
      const memories = Array.isArray(response.items) ? response.items : [];
      const filteredResult = memories.map(block => ({
        content: block.content,
        errors: block.errors,
        timestamp: block.timestamp
      }));
      return {
        content: [{ type: "text", text: JSON.stringify(filteredResult, null, 2) }]
      };
    }

    // --- retrieve_memory_blocks_by_conversation_id ---
    else if (toolName === "retrieve_memory_blocks_by_conversation_id") {
      const conversation_id = normalizeUuid(typedArgs?.conversation_id) || DEFAULT_CONVERSATION_ID;
      const agent_id = normalizeUuid(typedArgs?.agent_id) || DEFAULT_AGENT_ID;
      const limit = typedArgs?.limit as number | undefined;

      if (!conversation_id) {
        throw new McpError(
          ErrorCode.InvalidParams,
          "Conversation ID is required for retrieve_memory_blocks_by_conversation_id. Use the conversation_id returned from create_memory_block or configure DEFAULT_CONVERSATION_ID."
        );
      }

      const result = await memoryServiceClient.getMemoryBlocksByConversationId(
        conversation_id,
        agent_id,
        limit,
        DEFAULT_ORGANIZATION_ID ? { scope: 'organization', organization_id: DEFAULT_ORGANIZATION_ID } : undefined
      );
      const filteredResult = result.map(block => ({
        content: block.content,
        errors: block.errors,
        timestamp: block.timestamp
      }));
      return {
        content: [{ type: "text", text: JSON.stringify(filteredResult, null, 2) }]
      };
    }

    // --- retrieve_relevant_memories ---
    else if (toolName === "retrieve_relevant_memories") {
      const agent_id = normalizeUuid(typedArgs?.agent_id) || DEFAULT_AGENT_ID;
      const conversation_id = normalizeUuid(typedArgs?.conversation_id);

      if (!typedArgs.keywords) {
        throw new McpError(ErrorCode.InvalidParams, "Invalid arguments for retrieve_relevant_memories. 'keywords' is required as a comma-separated string or array of strings.");
      }
      if (!agent_id) {
        throw new McpError(ErrorCode.InvalidParams, "Agent ID is required for retrieve_relevant_memories and not provided via arguments or DEFAULT_AGENT_ID environment variable.");
      }

      let keywordCsv: string | undefined;
      if (Array.isArray(typedArgs.keywords)) {
        const processed = typedArgs.keywords
          .map((keyword: any) => typeof keyword === 'string' ? keyword.trim() : '')
          .filter((keyword: string) => keyword.length > 0);
        keywordCsv = processed.join(',');
      } else if (typeof typedArgs.keywords === 'string') {
        keywordCsv = typedArgs.keywords
          .split(',')
          .map((keyword: string) => keyword.trim())
          .filter((keyword: string) => keyword.length > 0)
          .join(',');
      }

      if (!keywordCsv) {
        throw new McpError(ErrorCode.InvalidParams, "Invalid arguments for retrieve_relevant_memories. Provide at least one keyword.");
      }

      const payload: RetrieveMemoriesPayload = {
        keywords: keywordCsv,
        agent_id: agent_id,
        limit: typedArgs.limit,
      };
      if (conversation_id) {
        payload.conversation_id = conversation_id;
      }

      if (!isValidRetrieveMemoriesPayload(payload)) {
        throw new McpError(ErrorCode.InvalidParams, "Invalid arguments for retrieve_relevant_memories. Keywords must resolve to a non-empty string.");
      }

      const result = await memoryServiceClient.retrieveRelevantMemories(payload);
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }]
      };
    }

    // --- report_memory_feedback ---
    else if (toolName === "report_memory_feedback") {
      if (!typedArgs || typeof typedArgs.memory_block_id !== 'string' || !['positive', 'negative', 'neutral'].includes(typedArgs.feedback_type)) {
        throw new McpError(
          ErrorCode.InvalidParams,
          "Invalid arguments for report_memory_feedback. Requires 'memory_block_id' (string) and 'feedback_type' ('positive', 'negative', or 'neutral')."
        );
      }
      const payload: ReportFeedbackPayload = {
        memory_id: typedArgs.memory_block_id,
        feedback_type: typedArgs.feedback_type,
        feedback_details: typeof typedArgs.feedback_details === 'string'
          ? typedArgs.feedback_details
          : (typeof typedArgs.comment === 'string' ? typedArgs.comment : undefined),
      };

      if (!isValidReportFeedbackPayload(payload)) {
        throw new McpError(ErrorCode.InvalidParams, "Invalid arguments for report_memory_feedback. Optional comment must be a string if provided.");
      }

      const result = await memoryServiceClient.reportMemoryFeedback(payload);
      const summary = {
        id: result.id,
        content: result.content,
        errors: result.errors,
        feedback_score: result.feedback_score,
      };
      return {
        content: [{ type: "text", text: `Feedback recorded. Updated memory: ${JSON.stringify(summary, null, 2)}` }]
      };
    }

      // --- get_memory_details ---
      else if (toolName === "get_memory_details") {
        if (!typedArgs || typeof typedArgs.memory_block_id !== 'string') {
          throw new McpError(ErrorCode.InvalidParams, "Invalid arguments for get_memory_details. Requires 'memory_block_id' (string).");
        }
        const memoryBlockId: string = typedArgs.memory_block_id as string;
        const result = await memoryServiceClient.getMemoryDetails(memoryBlockId);
        const filteredResult = {
          content: result.content,
          errors: result.errors,
          timestamp: result.timestamp
        };
        return {
          content: [{ type: "text", text: JSON.stringify(filteredResult, null, 2) }]
        };
      }

      // --- search_agents ---
      else if (toolName === "search_agents") {
        if (!isValidSearchAgentsPayload(typedArgs)) {
          throw new McpError(ErrorCode.InvalidParams, "Invalid arguments for search_agents. Requires 'query' (string).");
        }
        const query: string = typedArgs.query;
        const agents = await memoryServiceClient.searchAgents(query);
        return {
          content: [{ type: "text", text: JSON.stringify(agents, null, 2) }]
        };
      }

      // --- advanced_search_memories ---
    else if (toolName === "advanced_search_memories") {
      if (!typedArgs?.search_query || typeof typedArgs.search_query !== 'string') {
        throw new McpError(ErrorCode.InvalidParams, "Invalid arguments for advanced_search_memories. Requires 'search_query' (string).");
      }

      const agent_id: string | undefined = normalizeUuid(typedArgs?.agent_id) || DEFAULT_AGENT_ID;
      const conversation_id: string | undefined = normalizeUuid(typedArgs?.conversation_id);

      const st: string = typedArgs.search_type || 'fulltext';
      const q: string = typedArgs.search_query;
      const limit: number = typeof typedArgs.limit === 'number' ? typedArgs.limit : 10;
      const min_score: number = typeof typedArgs.min_score === 'number' ? typedArgs.min_score : 0.1;
      const similarity_threshold: number = typeof typedArgs.similarity_threshold === 'number' ? typedArgs.similarity_threshold : 0.7;
      const fulltext_weight: number = typeof typedArgs.fulltext_weight === 'number' ? typedArgs.fulltext_weight : 0.7;
      const semantic_weight: number = typeof typedArgs.semantic_weight === 'number' ? typedArgs.semantic_weight : 0.3;
      const min_combined_score: number = typeof typedArgs.min_combined_score === 'number' ? typedArgs.min_combined_score : 0.1;
      const include_archived: boolean = typeof typedArgs.include_archived === 'boolean' ? typedArgs.include_archived : false;

      let results: any[] = [];
      if (st === 'fulltext') {
        const params = {
          query: q,
          ...(agent_id ? { agent_id } : {}),
          ...(conversation_id ? { conversation_id } : {}),
          limit,
          include_archived,
          min_score,
        };
        results = await memoryServiceClient.searchFulltext(params);
      } else if (st === 'semantic') {
        const params = {
          query: q,
          ...(agent_id ? { agent_id } : {}),
          ...(conversation_id ? { conversation_id } : {}),
          limit,
          include_archived,
          similarity_threshold,
        };
        results = await memoryServiceClient.searchSemantic(params);
      } else {
        const params = {
          query: q,
          ...(agent_id ? { agent_id } : {}),
          ...(conversation_id ? { conversation_id } : {}),
          limit,
          include_archived,
          fulltext_weight,
          semantic_weight,
          min_combined_score,
        };
        results = await memoryServiceClient.searchHybrid(params);
      }

      const formattedResults = results.map((block: any) => ({
        content: block.content,
        lessons_learned: block.lessons_learned,
        timestamp: block.timestamp,
        feedback_score: block.feedback_score,
      }));

      return {
        content: [
          { type: 'text', text: JSON.stringify({ results: formattedResults, search_type: st, query: q }, null, 2) },
        ],
      };
    }

      // --- whoami ---
      else if (toolName === "whoami") {
        const info = await memoryServiceClient.whoAmI();
        return {
          content: [{ type: 'text', text: JSON.stringify(info, null, 2) }]
        };
      }

    // --- Unknown tool ---
    else {
      throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${toolName}`);
    }

  } catch (error) {
    let errorMessage = `Failed to execute tool '${toolName}'.`;
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<any>;
      console.error(`Memory Service API Error (${toolName}):`, axiosError.response?.status, axiosError.response?.data);
      errorMessage += ` Status: ${axiosError.response?.status}. Message: ${JSON.stringify(axiosError.response?.data?.detail || axiosError.response?.data?.message || axiosError.message)}`;
    } else if (error instanceof McpError) {
        console.error(`MCP Error (${toolName}):`, error.code, error.message);
        errorMessage = error.message; // Use the specific MCP error message
    } else if (error instanceof Error) {
      console.error(`Error (${toolName}):`, error);
      errorMessage += ` Error: ${error.message}`;
    } else {
      console.error(`Unknown error (${toolName}):`, error);
    }

    return {
      content: [{ type: "text", text: errorMessage }],
      isError: true
    };
  }
});

// --- Server Start ---

/**
 * Start the server using stdio transport.
 */
async function main() {
  const transport = new StdioServerTransport();
  // Log errors to stderr
  server.onerror = (error) => console.error("[MCP Error]", error);
  process.on('SIGINT', async () => {
      await server.close();
      process.exit(0);
  });

  await server.connect(transport);
  console.error(`Memory MCP server running. Waiting for requests...`); // Log to stderr
}

main().catch((error) => {
  console.error("Server failed to start:", error); // Log to stderr
  process.exit(1);
});
