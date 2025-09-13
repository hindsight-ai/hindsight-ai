# Hindsight MCP Server

MCP server for interacting with the Hindsight AI Agent Memory Service.

This is a TypeScript-based MCP server that provides tools for managing memory blocks, retrieving relevant memories, and reporting feedback.

## Features

### Tools

- `create_memory_block`: To record new learnings, observed errors, and relevant context after an interaction or task completion.
  - Required parameters: `content` (TEXT), `lessons_learned` (TEXT).
  - Optional parameters: `errors` (TEXT, if applicable), `metadata` (JSON, for additional contextual info).
  - Note: `agent_id` and `conversation_id` are automatically filled by environment variables.
- `retrieve_relevant_memories`: To fetch memory blocks that are highly relevant to the agent's current task, query, or conversation.
  - Required parameters: `query_text` (TEXT), `keywords` (ARRAY of TEXT).
  - Optional parameters: `limit` (INT).
  - Note: `agent_id` and `conversation_id` are automatically filled by environment variables.
- `retrieve_all_memory_blocks`: To retrieve all memory blocks, filtered by agent_id.
  - Required parameters: `agent_id` (UUID).
  - Optional parameters: `limit` (INT).
  - Note: `agent_id` is automatically filled by the `DEFAULT_AGENT_ID` environment variable if not provided in arguments. If neither is provided, an error will be thrown.
- `retrieve_memory_blocks_by_conversation_id`: To retrieve memory blocks associated with a specific conversation.
  - Required parameters: `conversation_id` (UUID).
  - Optional parameters: `limit` (INT).
  - Note: `agent_id` can be automatically filled by environment variables if not present.
- `report_memory_feedback`: To provide explicit feedback on the utility or correctness of a previously retrieved `memory_block`.
  - Required parameters: `memory_block_id` (UUID), `feedback_type` (enum: 'positive', 'negative', 'neutral').
  - Optional parameters: `comment` (TEXT).
- `get_memory_details`: To retrieve the full content and metadata of a specific `memory_block` by its ID.
  - Required parameters: `memory_block_id` (UUID).

## Development

Install dependencies:
```bash
npm install
```

Build the server:
```bash
npm run build
```

For development with auto-rebuild:
```bash
npm run watch
```

## Installation

To use with Claude Desktop, add the following server configuration to your `claude_desktop_config.json` file.

On MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "hindsight-mcp": {
      "autoApprove": [
        "create_memory_block",
        "retrieve_relevant_memories",
        "report_memory_feedback",
        "get_memory_details",
        "retrieve_all_memory_blocks",
        "retrieve_memory_blocks_by_conversation_id"
      ],
      "disabled": false,
      "timeout": 60,
      "command": "node",
      "args": [
        "/path/to/hindsight-ai/mcp-servers/hindsight-mcp/build/index.js"
      ],
      "env": {
        "MEMORY_SERVICE_BASE_URL": "http://localhost:8000",
        "DEFAULT_AGENT_ID": "7a229550-d8ad-4726-a529-6380949e878c",
        "DEFAULT_CONVERSATION_ID": "f47ac10b-58cc-4372-a567-0123456789ab",
        "HINDSIGHT_API_TOKEN": "hs_pat_xxx", // or use HINDSIGHT_API_KEY for X-API-Key header
        "HINDSIGHT_ORGANIZATION_ID": "00000000-0000-0000-0000-000000000000" // optional: force org scope for creates/reads
      },
      "transportType": "stdio"
    }
  }
}
```

### Debugging

Since MCP servers communicate over stdio, debugging can be challenging. We recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector), which is available as a package script:

```bash
npm run inspector
```

The Inspector will provide a URL to access debugging tools in your browser.

### Smoke Test (curl)

Verify your token and org setup quickly:

```bash
# Health
curl -sS $MEMORY_SERVICE_BASE_URL/health

# Who am I (works with PAT)
curl -sS -H "Authorization: Bearer $HINDSIGHT_API_TOKEN" \
  $MEMORY_SERVICE_BASE_URL/user-info | jq .

# List memory blocks (narrow to org if PAT is org-restricted)
curl -sS -H "Authorization: Bearer $HINDSIGHT_API_TOKEN" \
  "$MEMORY_SERVICE_BASE_URL/memory-blocks/?limit=1" | jq .
```

## Authentication & Scoping

- Provide one of:
  - `HINDSIGHT_API_TOKEN`: will be sent as `Authorization: Bearer <token>`
  - `HINDSIGHT_API_KEY`: will be sent as `X-API-Key: <token>`

- Scopes required by tools:
  - Read tools (`retrieve_*`, `search_*`, `get_memory_details`): token with `read` (or `write`) scope
  - Write tools (`create_memory_block`, `create_agent`, `report_memory_feedback`): token with `write` scope

- Organization scoping:
  - If you want the MCP to always operate within a specific organization, set `HINDSIGHT_ORGANIZATION_ID`.
    - Creates will use `visibility_scope=organization` and this `organization_id` by default.
    - List tools will include `scope=organization` and the same `organization_id`.
  - Stronger enforcement: issue a PAT restricted to that `organization_id` in the backend. The MCP works with either approach, but PAT org restriction is authoritative.

If neither `HINDSIGHT_ORGANIZATION_ID` nor an org-restricted PAT is provided, creation defaults to personal scope, and reads filter by the authenticated user’s memberships.
