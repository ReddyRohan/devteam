# devteam — Multi-Agent AI Software Development Team

An autonomous AI dev team built with [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) + [LiteLLM](https://github.com/BerriAI/litellm) + Discord.

## How it works

```
User posts task in #tasks channel on Discord
    → Oracle reads it, asks clarifying questions in a thread
    → Once clear, Oracle creates a work order and routes it to the right agent
    → e.g. [HANDOFF TO DEV] → Dev agent reads it, calls shell/filesystem/fetch tools
    → Dev completes the task and posts result back to Discord
```

## Agents

| Agent | Channel | Role |
|-------|---------|------|
| **Oracle** | #tasks | Orchestrator — clarifies tasks, creates work orders, routes to agents |
| **Dev** | #development | Senior developer — coding, APIs, scripts, ADO, git |
| **Quinn** | #qa | QA — testing, bug verification _(planned)_ |
| **Arjun** | #architecture | Architect — system design _(planned)_ |
| **Priya** | #product | Product — PRDs, user stories _(planned)_ |
| **Lex** | #devops | DevOps — CI/CD, Azure infra _(planned)_ |
| **Dex** | #data | Data — databases, pipelines _(planned)_ |

---

## Full Setup Guide

This guide is written for an LLM to follow step by step on a fresh Ubuntu/Debian machine (or WSL2 on Windows).

### Step 1 — Clone this repo

```bash
git clone https://github.com/ReddyRohan/devteam.git
cd devteam
```

### Step 2 — Install pyenv and Python 3.11.9

The system Python will not have the required packages. Use pyenv to install a dedicated Python.

```bash
# Install pyenv dependencies
sudo apt update && sudo apt install -y \
  build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
  libsqlite3-dev libncursesw5-dev xz-utils tk-dev libxml2-dev \
  libxmlsec1-dev libffi-dev liblzma-dev curl git

# Install pyenv
curl https://pyenv.run | bash

# Add pyenv to shell (bash)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# Install Python 3.11.9
pyenv install 3.11.9
pyenv global 3.11.9

# Verify
python3 --version   # should print Python 3.11.9
```

### Step 3 — Install Python packages

```bash
pip install \
  "openai-agents==0.12.5" \
  "discord.py==2.7.1" \
  "python-dotenv==1.1.1" \
  "openai==2.29.0" \
  requests
```

### Step 4 — Install Node.js and the filesystem MCP server

```bash
# Install Node.js (v18+)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install filesystem MCP server globally
npm install -g @modelcontextprotocol/server-filesystem

# Verify
npx @modelcontextprotocol/server-filesystem --help
```

### Step 5 — Install uv and the shell/fetch MCP servers

```bash
# Install uv (fast Python package runner)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc   # or restart terminal

# Pre-install MCP servers so they are cached (no network needed at runtime)
uvx mcp-server-fetch --help
uvx mcp-shell-server --help

# Verify
uvx mcp-shell-server --version   # should print version number
```

### Step 6 — Install LiteLLM

LiteLLM is the model proxy. All agents call `http://localhost:4000/v1` and LiteLLM routes to the real model.

```bash
pip install litellm

# Verify
litellm --version
```

### Step 7 — Configure LiteLLM

Create a LiteLLM config file at `~/litellm-config.yaml`. Example using GitHub Copilot Enterprise:

```yaml
model_list:
  - model_name: claude-sonnet-4-5
    litellm_params:
      model: openai/claude-sonnet-4.6
      api_base: https://api.enterprise.githubcopilot.com
      api_key: YOUR_GITHUB_COPILOT_TOKEN
      extra_headers:
        Copilot-Integration-Id: vscode-chat
        Editor-Version: vscode/1.85.0
```

To get the Copilot token:
```bash
gh auth login   # authenticate with GitHub CLI
gh auth token   # prints the token — use this as api_key above
```

Start LiteLLM:
```bash
litellm --config ~/litellm-config.yaml --port 4000 &

# Verify it's running
curl http://localhost:4000/health
# List available model names
curl http://localhost:4000/v1/models | python3 -m json.tool | grep '"id"'
```

The model name that appears in the `/v1/models` list is what goes in `LITELLM_MODEL` in `.env`.

### Step 8 — Set up Discord

You need one Discord bot per agent. Here is how to create them:

1. Go to https://discord.com/developers/applications
2. Click **New Application** → name it (e.g. "Oracle", "Dev")
3. Go to **Bot** → **Reset Token** → copy the token
4. Under **Privileged Gateway Intents** → enable **Message Content Intent**
5. Go to **OAuth2 → URL Generator** → select `bot` scope → select permissions: Read Messages, Send Messages, Add Reactions, Create Public Threads, Send Messages in Threads
6. Open the generated URL in a browser to invite the bot to your server
7. Repeat for each agent (Oracle, Dev — and Quinn/Arjun/Priya/Lex/Dex when you build them)

To get channel IDs:
1. In Discord: Settings → Advanced → enable **Developer Mode**
2. Right-click any channel → **Copy Channel ID**

Required channels: `#tasks`, `#development`, `#oversight`, `#general`, `#architecture`, `#qa`, `#devops`, `#data`, `#product`

To get your Guild (server) ID:
- Right-click your server name → **Copy Server ID**

### Step 9 — Configure `.env`

```bash
cp .env.template .env
```

Edit `.env` and fill in every value:

```bash
# Model proxy
LITELLM_BASE_URL=http://localhost:4000/v1
LITELLM_MODEL=claude-sonnet-4-5        # must match a model ID from /v1/models
LITELLM_API_KEY=placeholder            # not used but required by SDK

# Discord bots
DISCORD_TOKEN_ORACLE=<oracle bot token>
DISCORD_TOKEN_DEV=<dev bot token>
# Add others when you build more agents

# Discord server
DISCORD_GUILD_ID=<your server ID>
DISCORD_CHANNEL_TASKS=<#tasks channel ID>
DISCORD_CHANNEL_DEVELOPMENT=<#development channel ID>
DISCORD_CHANNEL_OVERSIGHT=<#oversight channel ID>
DISCORD_CHANNEL_GENERAL=<#general channel ID>
DISCORD_CHANNEL_ARCHITECTURE=<#architecture channel ID>
DISCORD_CHANNEL_QA=<#qa channel ID>
DISCORD_CHANNEL_DEVOPS=<#devops channel ID>
DISCORD_CHANNEL_DATA=<#data channel ID>
DISCORD_CHANNEL_PRODUCT=<#product channel ID>

# Azure DevOps (for Dev agent to create projects, push code)
AZDO_PAT=<personal access token from dev.azure.com>
AZDO_ORG_URL=https://dev.azure.com/<your-org>

# Jira (optional)
JIRA_BASE_URL=https://<your-org>.atlassian.net
JIRA_API_TOKEN=<api token from id.atlassian.com/manage-profile/security/api-tokens>
JIRA_EMAIL=<your jira login email>
```

**AZDO_PAT scopes needed:** Project and Team (Read, Write), Code (Read, Write), Work Items (Read, Write)

### Step 10 — Start the agents

```bash
cd ~/devteam/agents
source ../.env   # load env vars

# Start Oracle
python3 oracle.py &

# Start Dev
python3 dev.py &
```

Or use `startup.sh` which handles LiteLLM + both agents:

```bash
chmod +x startup.sh
./startup.sh
```

### Step 11 — Verify everything works

1. Check agent logs: `tail -f ~/devteam/logs/oracle.log` and `tail -f ~/devteam/logs/dev.log`
2. Both should print `Oracle online as Oracle#XXXX` and `Dev online as Dev#XXXX`
3. Post a message in your Discord `#tasks` channel: `Write hello world to /tmp/hello.py`
4. Oracle should react 👀, ask if it needs clarification, then post `[HANDOFF TO DEV]`
5. Dev should react ⚙️, write the file, and reply ✅

---

## Troubleshooting

See `DEPLOYMENT.md` for a full list of known gotchas. Quick reference:

| Symptom | Fix |
|---------|-----|
| `No commands are allowed` error in shell MCP | Already handled in `agents_base.py` — no action needed |
| Two instances of same agent running | `rm -f /tmp/devteam_*.lock` then restart |
| `ModuleNotFoundError: No module named discord` | Not using pyenv Python — run `which python3` and ensure it is the pyenv one |
| Oracle loses context between clarification rounds | Fixed — `check_resume()` runs before channel filter |
| Dev outputs planning text with no tool calls | Fixed — `CRITICAL RULES` in `DEV_INSTRUCTIONS` force tools-first behaviour |
| `Invalid model name` 400 error | `LITELLM_MODEL` in `.env` does not match — check `curl localhost:4000/v1/models` |
| Duplicate replies from agent | Lock file stale — `rm /tmp/devteam_dev.lock` |

---

## Repository structure

```
devteam/
├── agents/
│   ├── agents_base.py   # Shared: make_agent, MCP factories, Q&A helpers, handoffs, lock
│   ├── oracle.py        # Oracle orchestrator
│   └── dev.py           # Dev agent
├── .env.template        # Copy to .env and fill in secrets
├── .gitignore           # Ensures .env is never committed
├── startup.sh           # Start LiteLLM + all agents
├── README.md            # This file
└── DEPLOYMENT.md        # Deployment gotchas
```