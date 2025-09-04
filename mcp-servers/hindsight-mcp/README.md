# Hindsight MCP Server

TypeScript MCP server exposing Hindsight AI tools so agents can write and read memories, and report feedback.

## Try It Fast

1) Build
```bash
cd mcp-servers/hindsight-mcp
npm install
npm run build
```

2) Point your MCP client (e.g., Claude Desktop) to the built server:
```json
{
  "mcpServers": {
    "hindsight-mcp": {
      "command": "node",
      "args": ["/path/to/hindsight-ai/mcp-servers/hindsight-mcp/build/index.js"],
      "env": {
        "MEMORY_SERVICE_BASE_URL": "http://localhost:8000",
        "DEFAULT_AGENT_ID": "<your-agent-id>",
        "DEFAULT_CONVERSATION_ID": "00000000-0000-0000-0000-000000000001"
      },
      "transportType": "stdio"
    }
  }
}
```

3) Optional: run the MCP Inspector for local testing
```bash
npx @modelcontextprotocol/inspector --server "node build/index.js"
```

## Tools

- `create_memory_block` — content, lessons_learned, optional errors/metadata (agent/conversation default via env)
- `retrieve_relevant_memories` — basic keyword search with query + keywords
- `retrieve_all_memory_blocks` — list with optional agent filter
- `retrieve_memory_blocks_by_conversation_id` — scoped retrieval
- `report_memory_feedback` — positive/negative/neutral with optional comment
- `get_memory_details` — fetch content/errors/timestamp by ID

## Development

- `npm run build` — compile TypeScript
- `npm run dev` — watch mode with ts-node + nodemon

Handle errors gracefully: the server returns MCP‑formatted errors with HTTP status details from the API.
