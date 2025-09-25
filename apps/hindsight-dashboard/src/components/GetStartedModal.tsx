import React, { useEffect, useMemo, useState } from 'react';
import Portal from './Portal';

interface GetStartedModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type ClientStatus = 'ready' | 'comingSoon';

interface Snippet {
  id: string;
  label: string;
  content: string;
  language?: string;
}

interface ClientConfigureData {
  summary?: string;
  steps?: Array<React.ReactNode>;
  snippets?: Snippet[];
  comingSoonMessage?: string;
}

interface ClientWorkflowData {
  groupId?: string;
  summary?: Array<React.ReactNode>;
  snippets?: Snippet[];
  comingSoonMessage?: string;
  note?: string;
}

interface ClientInfo {
  id: string;
  name: string;
  description: string;
  status: ClientStatus;
  configure?: ClientConfigureData;
  workflow?: ClientWorkflowData;
}

interface WorkflowEntry {
  clientId: string;
  label?: string;
  detail: string;
}

interface WorkflowGroup {
  id: string;
  name: string;
  description: string;
  entries: WorkflowEntry[];
}

const codexConfigSnippet = `[mcp_servers.hindsight-mcp]
command = "hindsight-mcp"
env = { "HINDSIGHT_API_TOKEN" = "<yourtoken>", "DEFAULT_AGENT_ID" = "<youragentid>", "DEFAULT_CONVERSATION_ID" = "f47ac10b-58cc-4372-a567-0123456789ab" }`;

const workflowExample = `# Workflow Guidance

## Before You Start
- Retrieve all memories via the hindsight MCP interface.

## Continuous Learning
After meaningful progress or surprises, self-reflect and capture a "lesson learned" via the hindsight MCP interface. These memories keep parity work efficient and prevent repeating mistakes.`;

const geminiConfigSnippet = `{
  "mcpServers": {
    "hindsight-mcp": {
      "command": "hindsight-mcp",
      "env": {
        "HINDSIGHT_API_TOKEN": "<yourtoken>",
        "DEFAULT_AGENT_ID": "<youragentid>",
        "DEFAULT_CONVERSATION_ID": "f47ac10b-58cc-4372-a567-0123456789ab"
      }
    }
  }
}`;

const claudeConfigSnippet = `claude mcp add-json hindsight-mcp '{
  "type": "stdio",
  "command": "hindsight-mcp",
  "env": {
    "HINDSIGHT_API_TOKEN": "<yourtoken>",
    "DEFAULT_AGENT_ID": "<youragentid>",
    "DEFAULT_CONVERSATION_ID": "f47ac10b-58cc-4372-a567-0123456789ab"
  }
}'`;

const clineConfigSnippet = `{
  "mcpServers": {
    "hindsight-mcp": {
      "command": "hindsight-mcp",
      "env": {
        "HINDSIGHT_API_TOKEN": "<yourtoken>",
        "DEFAULT_AGENT_ID": "<youragentid>",
        "DEFAULT_CONVERSATION_ID": "f47ac10b-58cc-4372-a567-0123456789ab"
      },
      "disabled": false
    }
  }
}`;

const roocodeConfigSnippet = `{
  "servers": [
    {
      "name": "hindsight-mcp",
      "transport": "stdio",
      "command": "hindsight-mcp",
      "env": {
        "HINDSIGHT_API_TOKEN": "<yourtoken>",
        "DEFAULT_AGENT_ID": "<youragentid>",
        "DEFAULT_CONVERSATION_ID": "f47ac10b-58cc-4372-a567-0123456789ab"
      }
    }
  ]
}`;

const copilotConfigSnippet = `{
  "servers": {
    "hindsight-mcp": {
      "type": "stdio",
      "command": "hindsight-mcp",
      "env": {
        "HINDSIGHT_API_TOKEN": "<yourtoken>",
        "DEFAULT_AGENT_ID": "<youragentid>",
        "DEFAULT_CONVERSATION_ID": "f47ac10b-58cc-4372-a567-0123456789ab"
      }
    }
  }
}`;

const forgecodeConfigSnippet = `{
  "mcpServers": {
    "hindsight-mcp": {
      "command": "hindsight-mcp",
      "env": {
        "HINDSIGHT_API_TOKEN": "<yourtoken>",
        "DEFAULT_AGENT_ID": "<youragentid>",
        "DEFAULT_CONVERSATION_ID": "f47ac10b-58cc-4372-a567-0123456789ab"
      }
    }
  }
}`;

const openhandsConfigSnippet = `[mcp]
stdio_servers = [
  {name = "hindsight-mcp", command = "hindsight-mcp", env = { HINDSIGHT_API_TOKEN = "<yourtoken>", DEFAULT_AGENT_ID = "<youragentid>", DEFAULT_CONVERSATION_ID = "f47ac10b-58cc-4372-a567-0123456789ab" }}
]`;

const sharedMarkdownDetail = 'Document retrieval-first and reflection-last workflow rules using the template below so teammates stay in parity.';

const workflowGroups: WorkflowGroup[] = [
  {
    id: 'markdown',
    name: 'Markdown File for Instructions',
    description: 'Edit the listed Markdown file and reuse the template below to enforce start/end workflow rules.',
    entries: [
      {
        clientId: 'codex-cli',
        label: 'AGENTS.md',
        detail: sharedMarkdownDetail,
      },
      {
        clientId: 'gemini-cli',
        label: 'GEMINI.md',
        detail: sharedMarkdownDetail,
      },
      {
        clientId: 'claude-code',
        label: 'CLAUDE.md',
        detail: 'Document retrieval-first and reflection-last workflow rules using the template below; add optional .claude/commands/*.md files for command-specific prompts.',
      },
      {
        clientId: 'github-copilot-cli',
        label: '.github/copilot-instructions.md',
        detail: 'Document retrieval-first and reflection-last workflow rules using the template below; add path-specific prompts in .github/instructions/*.instructions.md (frontmatter required).',
      },
    ],
  },
  {
    id: 'rules',
    name: 'Rules File',
    description: 'Tweak a specialised rules file to steer AI behaviour.',
    entries: [
      {
        clientId: 'cline',
        label: '.clinerules',
        detail: 'Add retrieval-first and reflection-last instructions; reuse the workflow template below for consistency.',
      },
    ],
  },
  {
    id: 'yaml',
    name: 'YAML Config File',
    description: 'Set custom rules by editing a YAML configuration.',
    entries: [
      {
        clientId: 'forgecode',
        label: 'forge.yaml',
        detail: 'Use the custom_rules section in forge.yaml to require memory retrieval at the start and a reflection step at the end.',
      },
    ],
  },
  {
    id: 'toml',
    name: 'TOML Config File',
    description: 'Configure behaviour via a TOML config file.',
    entries: [
      {
        clientId: 'openhands-cli',
        label: 'config.toml',
        detail: 'Set [agent] instructions in config.toml to enforce retrieval-first and reflection-last behaviour; override with AGENT_* environment variables when needed.',
      },
    ],
  },
];

const GetStartedModal: React.FC<GetStartedModalProps> = ({ isOpen, onClose }) => {
  const clientOptions = useMemo((): ClientInfo[] => {
    const clients: ClientInfo[] = [
      {
        id: 'codex-cli',
        name: 'Codex CLI',
        description: 'OpenAI’s reference MCP CLI harness',
        status: 'ready',
        configure: {
          steps: [
            <>
              Update <code className="bg-gray-100 px-1 py-0.5 rounded">~/.config/codex.toml</code> with the agent ID and token you saved above (see snippet).
            </>,
            <>
              Restart <code className="bg-gray-100 px-1 py-0.5 rounded">codex-cli</code> and run <code className="bg-gray-100 px-1 py-0.5 rounded">/mcp</code>; the <strong>Hindsight MCP</strong> should appear in the list.
            </>,
          ],
          snippets: [
            { id: 'codex-config', label: '~/.config/codex.toml', language: 'toml', content: codexConfigSnippet },
          ],
        },
        workflow: {
          groupId: 'markdown',
          summary: [
            <>
              Document retrieval-first and reflection-last workflow rules in <code className="bg-gray-100 px-1 py-0.5 rounded">AGENTS.md</code> using the shared template below.
            </>,
          ],
          snippets: [
            { id: 'codex-workflow', label: 'AGENTS.md template', language: 'markdown', content: workflowExample },
          ],
        },
      },
      {
        id: 'gemini-cli',
        name: 'Gemini CLI',
        description: 'Google’s experimental MCP CLI',
        status: 'ready',
        configure: {
          summary: 'Gemini CLI stores MCP configuration in `.gemini/settings.json`. Add the Hindsight server under `mcpServers` and restart the CLI.',
          steps: [
            'Upgrade Gemini CLI (`npm upgrade -g @google/gemini-cli`).',
            'Open or create `.gemini/settings.json` inside your project.',
            'Add the `mcpServers` entry shown below and save.',
            'Launch Gemini CLI and run `/mcp` to verify the server is registered.',
          ],
          snippets: [
            { id: 'gemini-config', label: '.gemini/settings.json', language: 'json', content: geminiConfigSnippet },
          ],
        },
        workflow: {
          groupId: 'markdown',
          summary: [
            <>
              Document retrieval-first and reflection-last workflow rules in <code className="bg-gray-100 px-1 py-0.5 rounded">GEMINI.md</code> using the shared template below.
            </>,
            'Add optional slash commands via environment variables or command folders to automate reminders if needed.',
          ],
          snippets: [
            { id: 'gemini-workflow', label: 'GEMINI.md template', language: 'markdown', content: workflowExample },
          ],
        },
      },
      {
        id: 'claude-code',
        name: 'Claude Code',
        description: 'Anthropic’s VS Code extension',
        status: 'ready',
        configure: {
          summary: 'Use the `claude mcp` CLI to register the Hindsight server; a `.mcp.json` file is generated for project sharing.',
          steps: [
            'Install or upgrade Claude Code (`npm install -g @anthropic-ai/claude-code`).',
            'Run the command below to add the stdio MCP server with required environment variables.',
            'Confirm with `claude mcp list` or `/mcp` inside the Claude chat.',
          ],
          snippets: [
            { id: 'claude-config', label: 'claude mcp add-json command', language: 'bash', content: claudeConfigSnippet },
          ],
        },
        workflow: {
          groupId: 'markdown',
          summary: [
            <>
              Document retrieval-first and reflection-last workflow rules in <code className="bg-gray-100 px-1 py-0.5 rounded">CLAUDE.md</code> using the shared template below, then add <code className="bg-gray-100 px-1 py-0.5 rounded">.claude/commands/*.md</code> files for command-specific prompts if needed.
            </>,
          ],
          snippets: [
            { id: 'claude-workflow', label: 'CLAUDE.md template', language: 'markdown', content: workflowExample },
          ],
        },
      },
      {
        id: 'cline',
        name: 'Cline',
        description: 'VS Code MCP assistant',
        status: 'ready',
        configure: {
          summary: 'Cline stores MCP servers in `cline_mcp_settings.json`. Add the Hindsight entry under `mcpServers`.',
          steps: [
            'In VS Code, open the Cline MCP panel and choose Configure MCP Servers (or edit the JSON directly).',
            'Paste the configuration below into `cline_mcp_settings.json`.',
            'Ensure the server is enabled and reload if prompted.',
          ],
          snippets: [
            { id: 'cline-config', label: 'cline_mcp_settings.json', language: 'json', content: clineConfigSnippet },
          ],
        },
        workflow: {
          groupId: 'rules',
          summary: [
            <>
              Document retrieval-first and reflection-last workflow rules in <code className="bg-gray-100 px-1 py-0.5 rounded">.clinerules</code> using the shared template below so Cline enforces the sequence.
            </>,
          ],
          snippets: [
            { id: 'cline-workflow', label: '.clinerules template', language: 'markdown', content: workflowExample },
          ],
        },
      },
      {
        id: 'roocode',
        name: 'Roo Code',
        description: 'JetBrains-compatible MCP assistant',
        status: 'ready',
        configure: {
          summary: 'Roo Code reuses `cline_mcp_settings.json`. Add the server under the `servers` array.',
          steps: [
            'Open Roo Code › MCP panel and select Edit MCP Settings.',
            'Insert the JSON snippet below inside `servers` and save.',
            'Reload Roo Code or toggle the server to apply changes.',
          ],
          snippets: [
            { id: 'roocode-config', label: 'cline_mcp_settings.json (Roo Code)', language: 'json', content: roocodeConfigSnippet },
          ],
        },
        workflow: {
          comingSoonMessage: 'Workflow adjustment guidance for Roo Code is coming soon. Apply the shared template until dedicated docs are available.',
        },
      },
      {
        id: 'github-copilot-cli',
        name: 'GitHub Copilot CLI',
        description: 'MCP-enabled Copilot workflows',
        status: 'ready',
        configure: {
          summary: 'Copilot CLI stores MCP servers in `.vscode/mcp.json` (or global mcp.json). Add the server under `servers`.',
          steps: [
            'Open VS Code Command Palette › “MCP: Add Server” or edit `.vscode/mcp.json` manually.',
            'Paste the JSON snippet below and save.',
            'Run “MCP: Show Installed Servers” to confirm Hindsight is available.',
          ],
          snippets: [
            { id: 'copilot-config', label: '.vscode/mcp.json', language: 'json', content: copilotConfigSnippet },
          ],
        },
        workflow: {
          groupId: 'markdown',
          summary: [
            <>
              Document retrieval-first and reflection-last workflow rules in <code className="bg-gray-100 px-1 py-0.5 rounded">.github/copilot-instructions.md</code> using the shared template below.
            </>,
            'For path-specific prompts, add .github/instructions/*.instructions.md (with frontmatter). Copilot also reads AGENTS.md/CLAUDE.md/GEMINI.md if present.',
          ],
          snippets: [
            { id: 'copilot-workflow', label: '.github/copilot-instructions.md template', language: 'markdown', content: workflowExample },
          ],
        },
      },
      {
        id: 'forgecode',
        name: 'ForgeCode',
        description: 'ForgeCode workflow assistant',
        status: 'ready',
        configure: {
          summary: 'ForgeCode reads MCP servers from `.mcp.json` or via the `forge mcp add` CLI. Add the JSON snippet under `mcpServers`.',
          steps: [
            'Create `.mcp.json` in the project root if it does not exist.',
            'Insert the configuration below and save.',
            'Run `forge mcp list` to verify the server is registered.',
          ],
          snippets: [
            { id: 'forge-config', label: '.mcp.json', language: 'json', content: forgecodeConfigSnippet },
          ],
        },
        workflow: {
          groupId: 'yaml',
          summary: ['Add custom_rules in forge.yaml to require memory retrieval at the start and reflection at the end for each task.'],
        },
      },
      {
        id: 'openhands-cli',
        name: 'OpenHands CLI',
        description: 'OpenHands MCP-enabled CLI',
        status: 'ready',
        configure: {
          summary: 'OpenHands CLI uses `config.toml` to declare MCP servers. Add the Hindsight entry under `[mcp].stdio_servers`.',
          steps: [
            'Open `config.toml` (create it if needed).',
            'Add the snippet below under the `[mcp]` section.',
            'Start OpenHands and run `/mcp` to ensure the server is active.',
          ],
          snippets: [
            { id: 'openhands-config', label: 'config.toml', language: 'toml', content: openhandsConfigSnippet },
          ],
        },
        workflow: {
          groupId: 'toml',
          summary: [
            <>
              Configure <code className="bg-gray-100 px-1 py-0.5 rounded">[agent]</code> sections in <code className="bg-gray-100 px-1 py-0.5 rounded">config.toml</code> so sessions start with retrieval and end with reflection; use <code className="bg-gray-100 px-1 py-0.5 rounded">AGENT_*</code> environment variables for overrides.
            </>,
          ],
        },
      },
    ];

    return clients.sort((a, b) => a.name.localeCompare(b.name));
  }, []);

  const [selectedClientId, setSelectedClientId] = useState<string>('codex-cli');

  useEffect(() => {
    if (isOpen) {
      setSelectedClientId('codex-cli');
    }
  }, [isOpen]);

  const workflowLookup = useMemo(() => {
    const map = new Map<string, { group: WorkflowGroup; entry: WorkflowEntry }>();
    workflowGroups.forEach(group => {
      group.entries.forEach(entry => {
        map.set(entry.clientId, { group, entry });
      });
    });
    return map;
  }, []);

  if (!isOpen) {
    return null;
  }

  const selectedClient = clientOptions.find(client => client.id === selectedClientId) ?? clientOptions[0];
  const workflowReference = workflowLookup.get(selectedClient.id);

  const copyToClipboard = (text: string) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      void navigator.clipboard.writeText(text).catch(() => {});
    }
  };

  const handleBackdropClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  const renderSnippet = (snippet: Snippet) => (
    <div key={snippet.id} className="relative mt-4">
      <button
        type="button"
        className="absolute right-3 top-3 inline-flex items-center justify-center rounded-md border border-slate-600/60 bg-slate-800/60 px-2 py-1 text-[11px] font-medium text-slate-100 hover:bg-slate-700"
        onClick={() => copyToClipboard(snippet.content)}
        aria-label={`Copy ${snippet.label}`}
      >
        <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M9 9V3h12v12h-6" />
          <path d="M9 3H3v18h12v-6" />
        </svg>
      </button>
      <pre className="rounded-lg bg-slate-900 text-slate-100 text-xs sm:text-sm p-4 pr-12 overflow-x-auto whitespace-pre">
        <code>{snippet.content}</code>
      </pre>
    </div>
  );

  const renderClientSetup = () => {
    if (!selectedClient.configure) {
      return null;
    }

    if (selectedClient.status !== 'ready') {
      return (
        <section>
          <h3 className="text-lg font-semibold text-gray-900">Configure {selectedClient.name}</h3>
          <div className="mt-4 rounded-xl border border-dashed border-indigo-200 bg-indigo-50/60 p-4 text-sm text-indigo-900">
            {selectedClient.configure.comingSoonMessage || 'Setup guidance is coming soon. Follow the common preparation steps above while we publish the client-specific snippet.'}
          </div>
        </section>
      );
    }

    return (
      <section>
        <h3 className="text-lg font-semibold text-gray-900">Configure {selectedClient.name}</h3>
        {selectedClient.configure.summary && (
          <p className="mt-3 text-sm text-gray-600 leading-relaxed">{selectedClient.configure.summary}</p>
        )}
        {selectedClient.configure.steps && selectedClient.configure.steps.length > 0 && (
          <ol className="mt-4 space-y-3 list-decimal list-inside text-sm text-gray-700">
            {selectedClient.configure.steps.map((step, idx) => (
              <li key={idx} className="leading-relaxed">
                {step}
              </li>
            ))}
          </ol>
        )}
        {selectedClient.configure.snippets?.map(renderSnippet)}
      </section>
    );
  };

  const renderWorkflowSection = () => {
    if (!selectedClient.workflow) {
      return null;
    }

    const workflowSummary = selectedClient.workflow.summary ?? [];

    return (
      <section>
        <h3 className="text-lg font-semibold text-gray-900">Adjust your workflow</h3>
        {workflowReference && (
          <div className="mt-4 rounded-xl border border-gray-200 bg-white/80 p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-indigo-600">{workflowReference.group.name}</p>
                <p className="mt-1 text-sm text-gray-600">{workflowReference.group.description}</p>
              </div>
              {workflowReference.entry.label && (
                <span className="inline-flex items-center rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                  {workflowReference.entry.label}
                </span>
              )}
            </div>
            <p className="mt-3 text-sm text-gray-700 leading-relaxed">{workflowReference.entry.detail}</p>
          </div>
        )}
        {workflowSummary.length > 0 && (
          <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-gray-700">
            {workflowSummary.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        )}
        {selectedClient.workflow.snippets?.map(renderSnippet)}
        {!workflowReference && workflowSummary.length === 0 && selectedClient.workflow.comingSoonMessage && (
          <div className="mt-4 rounded-xl border border-dashed border-indigo-200 bg-indigo-50/60 p-4 text-sm text-indigo-900">
            {selectedClient.workflow.comingSoonMessage}
          </div>
        )}
      </section>
    );
  };

  return (
    <Portal>
      <div className="fixed inset-0 z-50 flex items-center justify-center px-4" onClick={handleBackdropClick}>
        <div className="absolute inset-0 bg-gray-900/70" />
        <div className="relative w-full max-w-4xl bg-white rounded-2xl shadow-2xl overflow-hidden">
          <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-indigo-500/10 to-blue-500/10">
            <div>
              <h2 className="text-2xl font-semibold text-gray-900">Get Started with Hindsight AI</h2>
              <p className="mt-1 text-sm text-gray-600">Follow these steps to bring the application online for the first time.</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 transition"
              aria-label="Close get started guide"
            >
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M6 18L18 6" />
              </svg>
            </button>
          </header>

          <div className="px-6 py-6 space-y-8 overflow-y-auto max-h-[80vh]">
            <section>
              <h3 className="text-lg font-semibold text-gray-900">Prepare your Hindsight workspace</h3>
              <ol className="mt-4 space-y-4 text-sm text-gray-700 list-decimal list-inside">
                <li className="leading-relaxed">
                  Go to <strong>Agents → Create Agent</strong>, create your first agent, and capture its <code className="bg-gray-100 px-1 py-0.5 rounded">Agent ID</code>. Keep it somewhere safe—you’ll drop it into your MCP client settings next.
                </li>
                <li className="leading-relaxed">
                  Open the account menu (top-right avatar) and choose <strong>API Tokens</strong>. Click <em>Create Token</em>, name it (e.g. “CLI Access”), and leave the organization blank unless you need to confine the token to a single org.
                  <div className="mt-2 text-xs text-gray-600">
                    • Enable the <code className="bg-gray-100 px-1 py-0.5 rounded">read</code> scope so clients can fetch memories and metadata.<br />
                    • Enable the <code className="bg-gray-100 px-1 py-0.5 rounded">write</code> scope if you plan to push lessons learned or add memories.<br />
                    • Copy the one-time secret immediately—Hindsight won’t show it again after you close the banner.
                  </div>
                </li>
              </ol>
            </section>

            <section>
              <h3 className="text-lg font-semibold text-gray-900">Select your MCP client</h3>
              <p className="mt-2 text-sm text-gray-600">Pick the interface you use; we’ll tailor the setup and workflow adjustments below.</p>
              <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
                {clientOptions.map(client => {
                  const isActive = client.id === selectedClient.id;
                  return (
                    <button
                      key={client.id}
                      type="button"
                      onClick={() => setSelectedClientId(client.id)}
                      className={`group relative flex h-12 items-center justify-center rounded-xl border px-4 text-sm font-semibold shadow-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 ${isActive ? 'border-indigo-500 bg-indigo-50 text-indigo-700' : 'border-gray-200 bg-white text-gray-700 hover:border-indigo-300 hover:bg-indigo-50/60'}`}
                      aria-pressed={isActive}
                      title={client.description}
                    >
                      {client.status === 'comingSoon' && (
                        <span className="absolute right-3 top-2 inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-medium text-indigo-700">Soon</span>
                      )}
                      <span>{client.name}</span>
                    </button>
                  );
                })}
              </div>
            </section>

            {renderClientSetup()}
            {renderWorkflowSection()}
          </div>

          <footer className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 px-6 py-4 bg-gray-50 border-t border-gray-200">
            <p className="text-xs text-gray-500">Need a hand? Visit the Support page anytime or reach out to the platform team.</p>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={onClose}
                className="inline-flex items-center justify-center rounded-full border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 transition"
              >
                Got it
              </button>
            </div>
          </footer>
        </div>
      </div>
    </Portal>
  );
};

export default GetStartedModal;
