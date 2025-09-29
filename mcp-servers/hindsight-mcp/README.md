# Hindsight MCP Server

`hindsight-mcp` is the official Model Context Protocol (MCP) server for the Hindsight AI Memory Service. By wiring it into an MCP-capable client, you enable AI assistants to read and write persistent memories, search conversation history, create agents, and close the loop with feedback—without leaving the tools you already use.

## Overview

The `hindsight-mcp` server bridges any MCP-compatible AI client with the Hindsight AI Memory Service. Once connected, assistants can securely operate on personal or organization-wide memories, making interactions more contextual, personalized, and auditable. This guide covers installation, configuration, and integration tips for the most common MCP clients.

### What is the Model Context Protocol (MCP)?

The [Model Context Protocol](https://modelcontextprotocol.io/) is an open standard that defines how AI models talk to external tools, APIs, and data sources. Instead of maintaining bespoke integrations for each client/tool pair, MCP provides a shared contract. Any MCP-compliant client (IDE extension, desktop app, CLI, chatbot, etc.) can invoke any MCP-compliant server—like `hindsight-mcp`—with zero custom glue code. The result is an interoperable ecosystem where you can swap clients or servers at will.

### Core Capabilities

- **Memory retrieval:** Use read-scoped tokens to pull relevant memories, run semantic/full-text search, and inspect metadata.
- **Memory creation & updates:** With write scope, assistants can log new memory blocks, create new agents, or update existing context.
- **Agent & feedback management:** Search for agents, inspect identities, and report feedback on memory accuracy to continuously improve outcomes.

## Prerequisites & Installation

### System requirements

- Node.js ≥ 18 (LTS recommended)
- npm (ships with Node.js)
- [`jq`](https://stedolan.github.io/jq/) – optional, used in the smoke-test helpers

### Global installation

Most workflows install the server globally so the `hindsight-mcp` command is on `PATH`:

```bash
npm install -g hindsight-mcp
```

#### Verify the executable

Confirm the binary is discoverable:

```bash
which hindsight-mcp
```

If the command is not found, ensure your shell `PATH` includes the global npm bin directory (e.g., `$HOME/.npm-global/bin` on macOS/Linux, `%AppData%\npm` on Windows). Update your shell profile (`.zshrc`, `.bash_profile`, etc.) if necessary, then restart your terminal or client.

For local development you can instead install from a checkout:

```bash
npm install -g /absolute/path/to/hindsight-ai/mcp-servers/hindsight-mcp
# or
cd /absolute/path/to/hindsight-ai/mcp-servers/hindsight-mcp
npm install && npm run build && npm link
```

Verify the binary resolves on your `PATH` and report its version:

```bash
hindsight-mcp --version
```

## Available Tools

| Tool | Description |
| --- | --- |
| `create_memory_block` | Create a new memory block. Requires `content` **and** `lessons_learned`. `agent_id` must reference an existing agent¹. `conversation_id` is optional; when omitted the server auto-generates one and returns it for reuse. Optional: `errors`, `metadata` (JSON). |
| `create_agent` | Create a new agent. `agent_name` is required. Scope is derived from `HINDSIGHT_ORGANIZATION_ID` when set, otherwise from the token's embedded organization³. |
| `retrieve_relevant_memories` | Retrieve memories for keywords (comma-separated string or array). Optional `limit`. Uses the resolved agent context and errors if the agent is unknown¹. |
| `retrieve_all_memory_blocks` | Page through memory blocks for the current agent. Optional `limit`. Requires a valid agent context¹. |
| `retrieve_memory_blocks_by_conversation_id` | Filter memories for a specific conversation. Optional `limit` and agent override. Requires a valid agent context¹. |
| `report_memory_feedback` | Record positive/negative/neutral feedback on a memory block. Optional `feedback_details`. |
| `get_memory_details` | Return metadata and content for one memory block by ID. |
| `search_agents` | Search agent names via a query string. |
| `advanced_search_memories` | Run full-text, semantic, or hybrid search. Accepts optional `agent_id` (falls back to env) and optional `conversation_id` filters. Requires a valid agent context¹. Tuning knobs: `limit`, `min_score`, `similarity_threshold`, `fulltext_weight`, `semantic_weight`, `min_combined_score`, `include_archived`. |
| `whoami` | Return the authenticated user and memberships as seen by the Hindsight service. |

> **Usage notes:** ¹ Agent IDs must exist; the service returns an error if the resolved agent is unknown. ² If no `conversation_id` is supplied when creating a memory, the server generates one and returns it (any UUID is accepted when you provide one explicitly). ³ If `HINDSIGHT_ORGANIZATION_ID` is set it overrides the token's organization scope; a mismatch between the env override and the token causes an error. We recommend issuing organization-scoped tokens and leaving the override unset to avoid configuration drift.

## Core Configuration: Environment & Authentication

Configuration is driven entirely through environment variables so secrets never live in config files. Provide them via your client’s MCP settings, shell profile, or secret store.

### Minimal configuration (hosted service)

| Variable | Description | Example |
| --- | --- | --- |
| `HINDSIGHT_API_TOKEN` | Personal Access Token (PAT) for the hosted Hindsight service. | `hs_pat_xxxxxxxxxxxx` |

### Optional overrides and helpers

| Variable | Purpose |
| --- | --- |
| `HINDSIGHT_API_BASE_URL` | Base URL override. Defaults to `https://api.hindsight-ai.com`; set this only for self-hosted or local deployments. |
| `DEFAULT_AGENT_ID` | Fallback agent UUID when a tool omits `agent_id`. Must reference an existing agent. |
| `DEFAULT_CONVERSATION_ID` | Optional fallback conversation UUID when you want every request to reuse a fixed conversation. When omitted, the server auto-generates one during `create_memory_block` and returns it for future calls. |
| `HINDSIGHT_ACTIVE_SCOPE` | Override scope header (`personal`, `organization`, `public`). Defaults based on token/org inference. |
| `HINDSIGHT_ORGANIZATION_ID` | Organization override. Takes precedence over the token scope—set sparingly and ensure it matches the token’s organization. |

> **Important:** The server does not automatically discover agent IDs. Supply them via arguments or environment; otherwise the request fails with `InvalidParams`. When a `conversation_id` is missing during `create_memory_block`, a new UUID is generated and returned in the response so downstream calls can reuse it.

### Authentication, scope & security

- Tokens control capabilities. Read scope covers retrieval/search; write scope is required for `create_memory_block`, `create_agent`, and `report_memory_feedback`.
- Generate PATs in the Hindsight AI dashboard under **API Settings**. Organization-scoped tokens embed their organization by default.
- Prefer issuing organization-scoped tokens and omit `HINDSIGHT_ORGANIZATION_ID` unless you explicitly need to override it; the override takes precedence and mismatches with the token cause errors.
- Treat your token like a password. Prefer environment variable interpolation (`${env:HINDSIGHT_API_TOKEN}`) or secure input prompts when supported by the client. Never commit tokens to configuration files.

## Client Setup Guide

Different MCP clients use different configuration mechanisms (JSON/TOML/YAML files, GUIs, secret stores). Use the quick-reference summary generated below, then expand the relevant section for detailed steps. Update the content via `npm run generate:docs` whenever `docs/client-config.json` changes.

<!-- GENERATED:CLIENT_SETUP -->

<details>
<summary>Configuration summary (selected clients)</summary>

| Client | Configuration method | Format | Default location |
| --- | --- | --- | --- |
| Claude Desktop | Config file | JSON | macOS: ~/Library/Application Support/Claude/claude_desktop_config.json<br>Windows: %APPDATA%\Claude\claude_desktop_config.json |
| Claude Code | VS Code settings | JSON | User/Workspace settings.json |
| Cline | Command Palette / config file | JSON | Workspace .cline/config.json |
| Codex CLI | Config file | TOML | ~/.codex/config.toml |
| Cursor | Config file / UI | JSON | ~/.cursor/mcp.json or .cursor/mcp.json |
| Continue | Config file | YAML | .continue/mcpServers/*.yaml |
| LibreChat | Config file | YAML | librechat.yaml |
| VS Code GitHub Copilot | MCP configuration | JSON | .vscode/mcp.json (workspace) or user-level equivalent |

</details>

### Claude Desktop

<details>
<summary>Show instructions</summary>

1. Open **Settings → Model Context Protocol → Open Configuration File**.
2. Extend the `mcpServers` object with the entry below, replacing placeholder values with your actual token and UUIDs.
3. Fully quit and relaunch Claude Desktop (or toggle MCP off/on) so it reloads the configuration.

```json
{
  "mcpServers": {
    "hindsight-mcp": {
      "command": "hindsight-mcp",
      "transportType": "stdio",
      "timeout": 60,
      "env": {
        "DEFAULT_AGENT_ID": "00000000-0000-0000-0000-000000000000",
        "HINDSIGHT_API_TOKEN": "hs_pat_xxx"
      }
    }
  }
}
```

- The hosted API is used by default—set `HINDSIGHT_API_BASE_URL` only for self-hosted deployments.
</details>

### Cline (VS Code)

<details>
<summary>Show instructions</summary>

Install the [Cline extension](https://github.com/cline/cline) and make sure the `hindsight-mcp` binary is available on your `PATH`.

1. Run **Cline: Manage MCP Servers → Add Server** from the Command Palette.
2. Set **Name** to `hindsight-mcp`, **Command** to `hindsight-mcp`, and leave **Args** empty (`[]`).
3. Add the environment variables you need (token plus optional defaults) as shown below.
4. Save the entry (written to `.cline/config.json`) and run **Cline: Reload MCP Servers**.

```json
{
  "DEFAULT_AGENT_ID": "00000000-0000-0000-0000-000000000000",
  "HINDSIGHT_API_TOKEN": "hs_pat_xxx"
}
```

- You can edit `.cline/config.json` directly later if you prefer working in JSON.
- Add `HINDSIGHT_API_BASE_URL` only when pointing at a self-hosted or local deployment.
</details>

### Claude Code (VS Code)

<details>
<summary>Show instructions</summary>

1. Ensure `hindsight-mcp` is installed globally or reachable via `npx`.
2. Open VS Code **Settings (JSON)** and add/extend the `claudeCode.mcpServers` array as shown below.
3. Reload the Claude Code view (or restart VS Code) to pick up the change.

```json
"claudeCode.mcpServers": [
  {
    "name": "hindsight-mcp",
    "command": "hindsight-mcp",
    "transport": "stdio",
    "env": {
      "DEFAULT_AGENT_ID": "00000000-0000-0000-0000-000000000000",
      "HINDSIGHT_API_TOKEN": "hs_pat_xxx"
    }
  }
]
```
</details>

### Codex CLI

<details>
<summary>Show instructions</summary>

1. Install the [Codex CLI](https://github.com/OpenAI/codex-cli) if you have not already.
2. Install or link `hindsight-mcp` so the binary is on `PATH` (see the installation section above).
3. Add the TOML block below to the `mcp_servers` table in `~/.codex/config.toml`.
4. Restart any active Codex sessions and verify with `codex mcp --list` or the MCP Inspector.

```toml
[mcp_servers.hindsight-mcp]
command = "hindsight-mcp"
args = []
env = {
  DEFAULT_AGENT_ID = "00000000-0000-0000-0000-000000000000",
  HINDSIGHT_API_TOKEN = "hs_pat_your_token_here"
}
```

- Prefer `command = "node"` plus an absolute path or `command = "npx"` when you do not want a global install.
- Omit `HINDSIGHT_API_BASE_URL` unless you need to target a non-hosted endpoint.
</details>

### Cursor

<details>
<summary>Show instructions</summary>

Cursor supports environment interpolation, so keep secrets out of the JSON by referencing `${env:VAR}` placeholders.

1. Create or open `~/.cursor/mcp.json` for global settings or `.cursor/mcp.json` for the current project.
2. Add the server definition shown below. Ensure `HINDSIGHT_API_TOKEN` is exported in your shell before launching Cursor.
3. Reload Cursor (Command Palette → `Cursor: Reload Window`) to apply the configuration.

```json
{
  "mcpServers": {
    "hindsight-mcp": {
      "command": "hindsight-mcp",
      "transportType": "stdio",
      "env": {
        "HINDSIGHT_API_TOKEN": "${env:HINDSIGHT_API_TOKEN}"
      }
    }
  }
}
```

- If the token is missing, Cursor prompts you to enter it securely the next time it launches.
- Set `HINDSIGHT_API_BASE_URL` in the `env` block only when you need to override the hosted API.
</details>

### Continue (VS Code / JetBrains)

<details>
<summary>Show instructions</summary>

1. Create the directory `.continue/mcpServers/` in the root of your workspace if it does not already exist.
2. Add a new file `hindsight.yaml` with the contents below (environment variables are resolved via `${{ env.VAR }}` syntax).
3. Reload Continue (Command Palette → `Continue: Reload`) so the new server is registered.

```yaml
name: Hindsight Memory
mcpServers:
  - name: hindsight-mcp
    command: hindsight-mcp
    env:
      HINDSIGHT_API_TOKEN: ${{ env.HINDSIGHT_API_TOKEN }}
```

- Add `HINDSIGHT_API_BASE_URL` if you are connecting to a self-hosted instance.
</details>

### LibreChat

<details>
<summary>Show instructions</summary>

1. Open `librechat.yaml` in your LibreChat deployment.
2. Add (or extend) the `mcpServers` section with the block below. LibreChat reads environment variables from the host system or a `.env` file.
3. Restart LibreChat so it loads the revised configuration.

```yaml
mcpServers:
  hindsight-mcp:
    command: hindsight-mcp
    env:
      HINDSIGHT_API_TOKEN: "${HINDSIGHT_API_TOKEN}"
    # chatMenu: false  # Optional: limit to agents only
```

- Include `HINDSIGHT_API_BASE_URL` in the env map only when using a custom deployment.
</details>

### VS Code GitHub Copilot (MCP)

<details>
<summary>Show instructions</summary>

The Copilot MCP integration supports secure inputs. Use the configuration below to store your token via the built-in secret manager.

1. Open the Command Palette and run **MCP: Open Workspace Folder Configuration** (or the user-level equivalent).
2. Paste the JSON below into `.vscode/mcp.json`.
3. When prompted, supply your Hindsight API token—VS Code stores it in the system keychain.

```json
{
  "servers": {
    "hindsight-mcp": {
      "command": "hindsight-mcp",
      "env": {
        "HINDSIGHT_API_TOKEN": "${user.input.hindsightApiToken}"
      }
    }
  },
  "inputs": {
    "hindsightApiToken": {
      "type": "command",
      "command": "mcp.selectSecret",
      "description": "Hindsight API token"
    }
  }
}
```

- Add `HINDSIGHT_API_BASE_URL` to the `env` block only for self-hosted environments.
</details>

### Other client categories

- **Code-based / SDK clients** (askit-mcp, Dolphin-MCP, MCP CLI, etc.): spawn `hindsight-mcp` from your runtime and pass environment variables programmatically.
- **UI-first desktop apps** (Cherry Studio, Windsurf, DeepChat, Tome, etc.): add a stdio server in the app's MCP or Tools preferences with the same command and env values.
- **Remote or web clients** (Runbear, Superinterface, WhatsMCP, etc.): most expect HTTP-based MCP servers. Use an MCP proxy to expose the local stdio process over HTTPS if required.

<!-- END GENERATED:CLIENT_SETUP -->

## Verification & Troubleshooting

### Smoke tests

Export `HINDSIGHT_API_BASE_URL` and `HINDSIGHT_API_TOKEN` in your shell, then run:

```bash
curl -sS "$HINDSIGHT_API_BASE_URL/health"

curl -sS -H "Authorization: Bearer $HINDSIGHT_API_TOKEN" \
  "$HINDSIGHT_API_BASE_URL/user-info" | jq .

curl -sS -H "Authorization: Bearer $HINDSIGHT_API_TOKEN" \
  "$HINDSIGHT_API_BASE_URL/memory-blocks/?limit=1" | jq .
```

### Common issues

- **`command not found: hindsight-mcp`** – The binary is not on `PATH`. Reinstall globally or add the npm global bin directory to `PATH`.
- **401 / 403 errors** – The token is missing, expired, or lacks required scope. Generate a new PAT and re-run the smoke tests.
- **Client fails to load the server** – Check the MCP configuration file for syntax errors. Many clients cache configs; restart the app/editor after changes.
- **Need logs?** –
  - Claude Desktop: Settings → Developer → select `hindsight-mcp` → **Open Logs Folder**.
  - Cursor: Output panel → “MCP Logs”.
  - VS Code: Output panel → “MCP” / “GitHub Copilot Chat”.
  - Cline: Command Palette → `Cline: Show Logs`.

## Development & Contribution

1. Clone and install dependencies:
   ```bash
   git clone <repo-url>
   cd hindsight-ai/mcp-servers/hindsight-mcp
   npm install
   ```
2. Useful scripts:
   ```bash
   npm run build   # compile TypeScript into ./build
   npm run watch   # incremental compilation during development
   npm run clean   # remove ./build
   ```

> Tip: Keep `.env` or shell exports handy for `HINDSIGHT_API_BASE_URL` and tokens when running integration tests locally.

## Publishing

1. Create `.npmrc` with your token:
   ```ini
   //registry.npmjs.org/:_authToken=${NPM_TOKEN}
   ```
2. Build from a clean slate:
   ```bash
   npm run clean && npm run build
   ```
3. Publish:
   ```bash
   npm publish --access public
   ```

### Maintaining the alias package (`hindsight-ai-mcp`)

To reserve the hyphenated package name, publish it immediately after the main release:

```bash
cp -r . ../hindsight-ai-mcp-alias && cd ../hindsight-ai-mcp-alias
npm pkg set name="hindsight-ai-mcp"
npm pkg set version="0.1.0"  # update as needed
npm publish --access public
cd .. && rm -rf hindsight-ai-mcp-alias
```

## License

Released under the [Unlicense](LICENSE), matching the main Hindsight repository.
