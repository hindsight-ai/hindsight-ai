#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";
import axios, { AxiosError } from 'axios';
import { MemoryServiceClient, CreateMemoryBlockPayload, RetrieveMemoriesPayload, ReportFeedbackPayload, MemoryBlock, Agent, CreateAgentPayload, AdvancedSearchPayload } from './client/MemoryServiceClient';

// --- Configuration ---
const MEMORY_SERVICE_BASE_URL = process.env.MEMORY_SERVICE_BASE_URL || 'http://localhost:8000'; // Default to localhost:8000
const DEFAULT_AGENT_ID = process.env.DEFAULT_AGENT_ID;
const DEFAULT_CONVERSATION_ID = process.env.DEFAULT_CONVERSATION_ID;

if (!MEMORY_SERVICE_BASE_URL) {
  throw new Error('MEMORY_SERVICE_BASE_URL environment variable is required');
}

// --- Type Guards ---
const isValidCreateMemoryBlockPayload = (payload: any): payload is CreateMemoryBlockPayload => {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    typeof payload.agent_id === 'string' && // Added agent_id check
    typeof payload.conversation_id === 'string' &&
    typeof payload.lessons_learned === 'string' &&
    (payload.errors === undefined || typeof payload.errors === 'string') &&
    (payload.metadata === undefined || typeof payload.metadata === 'object')
  );
};

const isValidRetrieveMemoryBlocksByConversationIdPayload = (payload: any): payload is { conversation_id: string; agent_id?: string; limit?: number } => {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    (payload.conversation_id === undefined || typeof payload.conversation_id === 'string') && // Made optional
    (payload.agent_id === undefined || typeof payload.agent_id === 'string') &&
    (payload.limit === undefined || typeof payload.limit === 'number')
  );
};

const isValidRetrieveMemoriesPayload = (payload: any): payload is RetrieveMemoriesPayload => {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    typeof payload.query_text === 'string' &&
    Array.isArray(payload.keywords) && // Changed to check for array
    payload.keywords.every((item: any) => typeof item === 'string') && // Ensure all items are strings
    (payload.agent_id === undefined || typeof payload.agent_id === 'string') && // Made optional
    (payload.conversation_id === undefined || typeof payload.conversation_id === 'string') &&
    (payload.limit === undefined || typeof payload.limit === 'number')
  );
};

const isValidRetrieveAllMemoryBlocksPayload = (payload: any): payload is { agent_id?: string; limit?: number } => {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    (payload.agent_id === undefined || typeof payload.agent_id === 'string') &&
    (payload.limit === undefined || typeof payload.limit === 'number')
  );
};

const isValidReportFeedbackPayload = (payload: any): payload is ReportFeedbackPayload => {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    typeof payload.memory_block_id === 'string' &&
    ['positive', 'negative', 'neutral'].includes(payload.feedback_type) &&
    (payload.comment === undefined || typeof payload.comment === 'string')
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
const memoryServiceClient = new MemoryServiceClient(MEMORY_SERVICE_BASE_URL);

// --- Tool Handlers ---

/**
 * Handler that lists available tools.
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "create_memory_block",
        description: "Create a new memory block in the AI agent memory service. Requires agent_id, a valid UUID for conversation_id, and content/lessons_learned.",
        inputSchema: {
          type: "object",
          properties: {
            agent_id: {
              type: "string",
              description: "UUID of the agent (this value should not be provided, it will be filled automatically by env variables).",
            },
            conversation_id: {
              type: "string",
              description: "UUID of the conversation (this value should not be provided, it will be filled automatically by env variables).",
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
            query_text: {
              type: "string",
              description: "The query text to find relevant memories (required, often duplicates keywords).",
            },
            keywords: {
              type: "array",
              items: {
                type: "string"
              },
              description: "Keywords to search for relevant memories (required, often duplicates query_text).",
            },
            agent_id: {
              type: "string",
              description: "UUID of the agent (this value should not be provided, it will be filled automatically by env variables).",
            },
            conversation_id: {
              type: "string",
              description: "UUID of the conversation (this value should not be provided, it will be filled automatically by env variables).",
            },
            limit: {
              type: "number",
              description: "Optional maximum number of memories to retrieve (default: 10).",
            },
          },
          required: ["query_text", "keywords"],
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
          required: ["agent_id"]
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
              "description": "UUID of the conversation to retrieve memories for (this value should not be provided, it will be filled automatically by env variables).",
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
            comment: {
              type: "string",
              description: "Optional comment regarding the feedback.",
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
            limit: {
              type: "number",
              description: "Maximum number of memories to retrieve (optional, default: 10).",
            },
            min_score: {
              type: "number",
              description: "Minimum relevance score (0.0-1.0). Higher values return more relevant results (optional, default: 0.1).",
            },
          },
          required: ["search_query"],
        },
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
      const agent_id = (typedArgs?.agent_id as string | undefined) || DEFAULT_AGENT_ID;
      const conversation_id = (typedArgs?.conversation_id as string | undefined) || DEFAULT_CONVERSATION_ID;

      if (!agent_id) {
        throw new McpError(ErrorCode.InvalidParams, "Agent ID is required for create_memory_block and not provided via arguments or DEFAULT_AGENT_ID environment variable.");
      }
      if (!conversation_id) {
        throw new McpError(ErrorCode.InvalidParams, "Conversation ID is required for create_memory_block and not provided via arguments or DEFAULT_CONVERSATION_ID environment variable.");
      }

      const payload: CreateMemoryBlockPayload = {
        agent_id: agent_id,
        conversation_id: conversation_id,
        content: typedArgs.content,
        lessons_learned: typedArgs.lessons_learned,
        errors: typedArgs.errors,
        metadata: typedArgs.metadata,
      };

      if (!isValidCreateMemoryBlockPayload(payload)) {
        throw new McpError(
          ErrorCode.InvalidParams,
          "Invalid arguments for create_memory_block. Requires 'content' (string) and 'lessons_learned' (string)."
        );
      }
      const result = await memoryServiceClient.createMemoryBlock(payload);
      return {
        content: [{ type: "text", text: `Successfully created memory block with ID: ${result.id}` }]
      };
    }

    // --- create_agent ---
    else if (toolName === "create_agent") {
      const payload: CreateAgentPayload = {
        agent_name: typedArgs.agent_name,
      };

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
      const agent_id = (typedArgs?.agent_id as string | undefined) || DEFAULT_AGENT_ID;
      const limit = typedArgs?.limit as number | undefined;

      if (!agent_id) {
        throw new McpError(ErrorCode.InvalidParams, "Agent ID is required for retrieve_all_memory_blocks and not provided via arguments or DEFAULT_AGENT_ID environment variable.");
      }

      const response = await memoryServiceClient.getAllMemoryBlocks(agent_id, limit);
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
      const conversation_id = (typedArgs?.conversation_id as string | undefined) || DEFAULT_CONVERSATION_ID;
      const agent_id = (typedArgs?.agent_id as string | undefined) || DEFAULT_AGENT_ID;
      const limit = typedArgs?.limit as number | undefined;

      if (!conversation_id) {
        throw new McpError(ErrorCode.InvalidParams, "Conversation ID is required for retrieve_memory_blocks_by_conversation_id and not provided via arguments or DEFAULT_CONVERSATION_ID environment variable.");
      }

      const result = await memoryServiceClient.getMemoryBlocksByConversationId(conversation_id, agent_id, limit);
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
      const agent_id = (typedArgs?.agent_id as string | undefined) || DEFAULT_AGENT_ID;
      const conversation_id = (typedArgs?.conversation_id as string | undefined) || DEFAULT_CONVERSATION_ID;

      if (!typedArgs.query_text || typeof typedArgs.query_text !== 'string') {
        throw new McpError(ErrorCode.InvalidParams, "Invalid arguments for retrieve_relevant_memories. 'query_text' (string) is required.");
      }
      if (!Array.isArray(typedArgs.keywords) || !typedArgs.keywords.every((item: any) => typeof item === 'string')) {
        throw new McpError(ErrorCode.InvalidParams, "Invalid arguments for retrieve_relevant_memories. 'keywords' (array of strings) is required.");
      }
      if (!agent_id) {
        throw new McpError(ErrorCode.InvalidParams, "Agent ID is required for retrieve_relevant_memories and not provided via arguments or DEFAULT_AGENT_ID environment variable.");
      }

      const processedKeywords = typedArgs.keywords
        .map((keyword: string) => keyword.trim()) // Trim whitespace from each keyword
        .filter((keyword: string) => keyword.length > 0); // Filter out empty strings

      const payload: RetrieveMemoriesPayload = {
        query_text: typedArgs.query_text,
        keywords: processedKeywords.join(','), // Join processed keywords into a comma-separated string
        agent_id: agent_id,
        conversation_id: conversation_id,
        limit: typedArgs.limit,
      };

      const result = await memoryServiceClient.retrieveRelevantMemories(payload);
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }]
      };
    }

    // --- report_memory_feedback ---
    else if (toolName === "report_memory_feedback") {
      if (!isValidReportFeedbackPayload(typedArgs)) {
        throw new McpError(
          ErrorCode.InvalidParams,
          "Invalid arguments for report_memory_feedback. Requires 'memory_block_id' (string) and 'feedback_type' ('positive', 'negative', or 'neutral')."
        );
      }
      const payload: ReportFeedbackPayload = typedArgs;
      const result = await memoryServiceClient.reportMemoryFeedback(payload);
      return {
        content: [{ type: "text", text: `Successfully reported feedback for memory block ${payload.memory_block_id}: ${result}` }]
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
        const response = await axios.get(`${MEMORY_SERVICE_BASE_URL}/agents/search/?query=${encodeURIComponent(query)}`);
        return {
          content: [{ type: "text", text: JSON.stringify(response.data, null, 2) }]
        };
      }

      // --- advanced_search_memories ---
      else if (toolName === "advanced_search_memories") {
        if (!typedArgs?.search_query || typeof typedArgs.search_query !== 'string') {
          throw new McpError(ErrorCode.InvalidParams, "Invalid arguments for advanced_search_memories. Requires 'search_query' (string).");
        }
        
        // Fill in required IDs from environment
        const agent_id = DEFAULT_AGENT_ID;
        const conversation_id = DEFAULT_CONVERSATION_ID;
        
        if (!agent_id) {
          throw new McpError(ErrorCode.InvalidParams, "Agent ID is required for advanced_search_memories and not provided via DEFAULT_AGENT_ID environment variable.");
        }
        
        const payload: AdvancedSearchPayload = {
          search_query: typedArgs.search_query,
          search_type: typedArgs.search_type || 'fulltext',  // Default to fulltext for more predictable results
          agent_id: agent_id,
          conversation_id: conversation_id,
          limit: typedArgs.limit || 10,
          min_score: typedArgs.min_score || 0.1,
          // Set sensible defaults for other parameters
          similarity_threshold: 0.7,
          fulltext_weight: 0.7,
          semantic_weight: 0.3,
          min_combined_score: 0.1,
          include_archived: false
        };
        
        const response = await memoryServiceClient.advancedSearch(payload);
        
        // Format response for the AI - show only the most relevant fields
        const formattedResults = response.items.map(block => ({
          content: block.content,
          lessons_learned: block.lessons_learned,
          timestamp: block.timestamp,
          feedback_score: block.feedback_score
        }));
        
        return {
          content: [{ 
            type: "text", 
            text: JSON.stringify({
              results: formattedResults,
              total_found: response.total_items,
              search_type: payload.search_type,
              query: payload.search_query
            }, null, 2) 
          }]
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
