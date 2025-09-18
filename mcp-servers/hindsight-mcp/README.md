# Hindsight MCP Server

`hindsight-mcp` is a [Model Context Protocol](https://github.com/modelcontextprotocol) (MCP) server that exposes the Hindsight AI memory service to MCP-capable clients. It lets assistants create agents and memories, retrieve them with full-text/semantic search, and record feedback from downstream usage.

## Available Tools

| Tool | Description |
| --- | --- |
| `create_memory_block` | Create a new memory block. Requires `content`; `lessons_learned`, `errors`, and `metadata` (JSON) are optional. Agent/conversation IDs fall back to environment variables. |
| `create_agent` | Create a new agent. `agent_name` is required. Organization scope is inferred from environment variables. |
| `retrieve_relevant_memories` | Retrieve memories by supplying keywords (either a comma-separated string or an array of strings). Optional `limit`. |
| `retrieve_all_memory_blocks` | Page through memory blocks for the current agent. Optional `limit`. |
| `retrieve_memory_blocks_by_conversation_id` | Filter memories for a specific conversation. Optional `limit` and agent override. |
| `report_memory_feedback` | Record positive/negative/neutral feedback on a memory block. Optional `feedback_details` string. |
| `get_memory_details` | Return metadata and content for a single memory block by ID. |
| `search_agents` | Search agent names using a query string. |
| `advanced_search_memories` | Run full-text, semantic, or hybrid search with tuning parameters. |
| `whoami` | Return the authenticated user and memberships as seen by the Hindsight service. |

## Configuration

| Environment variable | Purpose |
| --- | --- |
| `MEMORY_SERVICE_BASE_URL` | Base URL for the Hindsight service (defaults to `http://localhost:8000`). |
| `HINDSIGHT_API_TOKEN` / `HINDSIGHT_API_KEY` | Personal access token. If `HINDSIGHT_API_KEY` is provided it is sent as `X-API-Key`; otherwise `Authorization: Bearer`. |
| `HINDSIGHT_ACTIVE_SCOPE` | Optional scope header (`personal`, `organization`, or `public`). When omitted the server infers the scope (organization if `HINDSIGHT_ORGANIZATION_ID` is set). |
| `HINDSIGHT_ORGANIZATION_ID` | UUID of the organization to operate within. Required when forcing organization scope. |
| `DEFAULT_AGENT_ID` | Default agent UUID used by tools when an argument is not supplied. |
| `DEFAULT_CONVERSATION_ID` | Default conversation UUID used by tools when an argument is not supplied. |

## Installation in Claude Desktop

```json
{
  "mcpServers": {
    "hindsight-mcp": {
      "command": "node",
      "args": ["/absolute/path/to/hindsight-ai/mcp-servers/hindsight-mcp/build/index.js"],
      "transportType": "stdio",
      "timeout": 60,
      "autoApprove": [
        "create_memory_block",
        "retrieve_relevant_memories",
        "retrieve_all_memory_blocks",
        "retrieve_memory_blocks_by_conversation_id",
        "report_memory_feedback",
        "get_memory_details"
      ],
      "env": {
        "MEMORY_SERVICE_BASE_URL": "http://localhost:8000",
        "DEFAULT_AGENT_ID": "00000000-0000-0000-0000-000000000000",
        "DEFAULT_CONVERSATION_ID": "00000000-0000-0000-0000-000000000000",
        "HINDSIGHT_API_TOKEN": "hs_pat_xxx",
        "HINDSIGHT_ORGANIZATION_ID": "00000000-0000-0000-0000-000000000000"
      }
    }
  }
}
```

## Development

```bash
npm install            # install dependencies
npm run build          # compile into ./build with declaration files
npm run watch          # incremental compilation during development
npm run clean          # remove the build directory
```

### Smoke Test Helpers

```bash
curl -sS "$MEMORY_SERVICE_BASE_URL/health"

curl -sS -H "Authorization: Bearer $HINDSIGHT_API_TOKEN" \
  "$MEMORY_SERVICE_BASE_URL/user-info" | jq .

curl -sS -H "Authorization: Bearer $HINDSIGHT_API_TOKEN" \
  "$MEMORY_SERVICE_BASE_URL/memory-blocks/?limit=1" | jq .
```

## Publishing

1. Create an `.npmrc` containing:
   ```ini
   //registry.npmjs.org/:_authToken=${NPM_TOKEN}
   ```
   Ensure `NPM_TOKEN` is set (already supported by this repository's `.env`).

2. Build the package:
   ```bash
   npm run clean && npm run build
   ```

3. Publish:
   ```bash
   npm publish --access public
   ```

### Optional alias (`hindsight-ai-mcp`)

To reserve the similar package name:
```bash
# create a temporary clone
cp -r . ../hindsight-ai-mcp-alias && cd ../hindsight-ai-mcp-alias
npm pkg set name="hindsight-ai-mcp" && npm pkg set version="0.1.0"
npm publish --access public
cd .. && rm -rf hindsight-ai-mcp-alias
```
Publish the alias immediately after the main package whenever a new version ships.

## Authentication & Scope Notes

- PATs with an embedded `organization_id` automatically restrict scope server-side.
- Setting `HINDSIGHT_ACTIVE_SCOPE=organization` without `HINDSIGHT_ORGANIZATION_ID` triggers a warning and falls back to personal scope.
- Write tools (`create_memory_block`, `create_agent`, `report_memory_feedback`) require tokens with `write` scope. Read tools work with `read` scope.

## License

This package is released under the [Unlicense](LICENSE), matching the main Hindsight repository.
