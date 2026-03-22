# devteam — Multi-Agent AI Software Development Team

An autonomous AI dev team built with [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) + [LiteLLM](https://github.com/BerriAI/litellm) + Discord.

## Agents

| Agent | Role | Model |
|-------|------|-------|
| **Oracle** | Orchestrator — clarifies tasks, creates work orders, routes to agents | GPT-4.1 (Azure) or Claude Sonnet (Copilot) |
| **Dev** | Senior developer — coding, APIs, scripts, file ops, ADO | Claude Sonnet (Copilot Enterprise) |
| **Quinn** | QA — testing, bug verification, test plans | _(planned)_ |
| **Arjun** | Architect — system design, infra review | _(planned)_ |
| **Priya** | Product — PRDs, user stories, backlog | _(planned)_ |
| **Lex** | DevOps — CI/CD, Azure infra, monitoring | _(planned)_ |
| **Dex** | Data — databases, pipelines, SQL | _(planned)_ |

## Architecture

```
User posts task in #tasks
    → Oracle clarifies (Q&A loop), creates work order
    → Oracle routes to right agent via [HANDOFF TO AGENT]
    → Agent executes with MCP tools (filesystem, shell, fetch)
    → Agent posts result back to Discord
```

## Setup

### Prerequisites
- Python 3.11 (via pyenv recommended)
- Node.js (for filesystem MCP server)
- `uv` / `uvx` (for fetch + shell MCP servers)
- Discord bot tokens (one per agent)
- LiteLLM proxy pointing to your model provider

### Installation

```bash
git clone https://github.com/ReddyRohan/devteam.git
cd devteam

# Install Python deps
pip install openai-agents discord.py python-dotenv litellm

# Install MCP servers
npm install -g @modelcontextprotocol/server-filesystem
uvx mcp-server-fetch --help   # auto-installs
uvx mcp-shell-server --help   # auto-installs

# Copy and fill in your secrets
cp .env.template .env
# Edit .env with your Discord tokens, channel IDs, model config
```

### Running

```bash
# Start LiteLLM proxy first (see litellm config in your setup)
litellm --config litellm-config.yaml --port 4000

# Start agents
cd agents
python3 oracle.py &
python3 dev.py &
```

Or use `startup.sh` for automated startup (configure for your init system).

## MCP Tools (Dev agent)

| Tool | Server | Purpose |
|------|--------|---------|
| `filesystem` | `@modelcontextprotocol/server-filesystem` | Read/write files |
| `shell` | `mcp-shell-server` | Run terminal commands (python3, bash, git, curl, etc.) |
| `fetch` | `mcp-server-fetch` | Fetch URLs, docs, search |

## Key Files

- `agents/agents_base.py` — Shared helpers: `make_agent`, `run_agent`, MCP factories, Q&A helpers, handoff helpers
- `agents/oracle.py` — Oracle orchestrator
- `agents/dev.py` — Dev agent
- `startup.sh` — Start all agents + LiteLLM
- `.env.template` — Copy to `.env` and fill in secrets

## Environment Variables

See `.env.template` for the full list. Key vars:
- `LITELLM_BASE_URL` + `LITELLM_MODEL` — model proxy config
- `DISCORD_TOKEN_*` — one token per agent bot
- `DISCORD_CHANNEL_*` — channel IDs for each agent
- `AZDO_PAT` — Azure DevOps PAT for Dev agent
- `JIRA_API_TOKEN` / `JIRA_EMAIL` / `JIRA_BASE_URL` — Jira integration

## Known Deployment Notes

See `DEPLOYMENT.md` for gotchas when setting up on a new machine.