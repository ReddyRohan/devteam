<overview>
The user is building a multi-agent AI software development team using OpenAI Agents SDK + LiteLLM + Discord. Pi 5 runs management agents (Oracle, Priya, Lex) via Azure OpenAI GPT-4.1; laptop WSL2 runs compute agents (Arjun, Dev, Quinn, Dex) via GitHub Copilot Enterprise. Agents communicate through a Discord server, with human oversight via #oversight channel. The session progressed from PoC validation → Phase 1 agents working → MCP tool integration for real capabilities (file I/O, GitHub, Azure DevOps, Jira, web fetch).
</overview>

<history>
1. **PoC validation (prior session)**
   - Verified LiteLLM 1.63.0 + Copilot Enterprise works on laptop WSL2
   - Verified OpenAI Agents SDK works on both Pi (port 4000, Azure) and laptop (port 4000, Copilot)
   - Key fix: Pi LiteLLM is on port 4000 (not 3001), model alias `claude-sonnet-4-6` maps to Azure GPT-4.1

2. **Discord server setup**
   - User created server "Rohans.Dev.Server", invited 7 bots (Oracle, Priya, Arjun, Dev, Quinn, Dex, Lex)
   - Created 9 channels: tasks, general, architecture, development, qa, devops, data, product, oversight
   - Guild ID: `1485037469429792930`, all channel IDs stored in `.env`
   - Bots needed Message Content Intent enabled in developer portal

3. **Phase 1 agents — Oracle + Dev**
   - Built `oracle.py` (Pi): listens in #tasks, creates thread, generates work order, posts to #development
   - Built `dev.py` (laptop): listens in #development for `[TASK ASSIGNED TO DEV]`, responds with code
   - Bugs fixed: Dev ignored bot messages (Oracle is a bot) — changed filter to `message.author == client.user`; Oracle used `<@&everyone>` (invalid) — removed; Oracle reprocessed old messages on restart — added `_ready_time` check
   - Oracle deployed as systemd service (`devteam-oracle.service`) on Pi for persistence
   - Dev runs in foreground async PowerShell session (dev-agent9)
   - Fibonacci task confirmed working end-to-end ✅

4. **LiteLLM port unification**
   - Changed laptop LiteLLM from port 3002 to 4000 to match Pi — agents always use `localhost:4000`

5. **Windows Task Scheduler for laptop persistence**
   - Created `~/devteam/startup.sh` in WSL2: starts LiteLLM + Dev agent on login
   - Registered `DevTeam-WSL-Startup` task in Windows Task Scheduler (triggers at logon)
   - Could not enable systemd in WSL2 (sudo password required, blocked)

6. **Credentials setup**
   - Azure DevOps: `https://dev.azure.com/rohanreddy0892/`, PAT stored
   - Jira: `https://rohanreddy.atlassian.net/`, API token + email `rohan.reddyin@gmail.com` stored
   - Both APIs verified working: ADO projects `Test`, `flaskwebapp`; Jira logged in as Rohan R
   - All stored in `~/devteam/.env` on both laptop and Pi

7. **MCP tool integration**
   - Researched existing tool libraries — chose MCP (Model Context Protocol) as the approach
   - Installed on both machines:
     - `mcp-atlassian` (pip) — Jira + Confluence
     - `@azure-devops/mcp` (npm, Microsoft official) — Azure DevOps
     - `@modelcontextprotocol/server-github` (npm) — GitHub
     - `@modelcontextprotocol/server-filesystem` (npm) — file read/write
     - `mcp-server-git`, `mcp-server-fetch` (uvx/pip)
     - `uv`/`uvx` for running pip-based MCP servers
   - npm global prefix set to `~/.npm-global` (permissions fix)
   - Bugs fixed:
     - `MCPServerStdio` default timeout 5s → raised to 60s
     - Duplicate tool `search_code` across GitHub + ADO servers → filtered from ADO with `tool_filter`
     - MCP servers need `async with` context manager — fixed in `dev.py`
   - Dev agent now starts all 4 MCP servers per task (filesystem, github, azure-devops, fetch)
   - ADO MCP server confirmed connecting to `rohanreddy0892` org ✅

8. **Error notifications**
   - Added `@here` ping to `#oversight` on any agent error
   - Added `notify_error()` helper in `agents_base.py` for all future agents

9. **Azure DevOps summary task — in progress**
   - User asked Dev to create a summary of ADO projects and save to `C:\Rohan\Summary`
   - Created `C:\Rohan\Summary` directory, added `/mnt/c/Rohan` to filesystem MCP allowed dirs
   - Dev ran the task, MCP servers connected, but no file was created — Dev likely replied to Discord instead of writing to file
   - Task needs to be re-posted with explicit instruction to write to `/mnt/c/Rohan/Summary/devops-summary.md`
</history>

<work_done>
Files on laptop WSL2 (`~/devteam/`):
- `agents/agents_base.py` — base module: make_client, make_agent, run_agent, all MCP factory functions (mcp_filesystem, mcp_git, mcp_github, mcp_jira, mcp_azure_devops, mcp_fetch), notify_error helper. Extended PATH for finding binaries.
- `agents/oracle.py` — Oracle agent: listens #tasks, creates thread, generates work order, posts to #development and #oversight. Has `_ready_time` guard against old messages.
- `agents/dev.py` — Dev agent: listens #development, uses 4 MCP servers (filesystem ~/+/tmp+/mnt/c/Rohan, github, azure-devops, fetch), posts errors to #oversight with @here
- `agents/agents_base.py` — also deployed to Pi at same path
- `.env` — all tokens, channel IDs, Azure DevOps + Jira credentials
- `startup.sh` — starts LiteLLM + Dev on WSL2 boot
- `~/nanoclaw-laptop/litellm/config.yaml` — LiteLLM config for Copilot Enterprise (port 4000)
- `~/nanoclaw-laptop/litellm/start.sh` — injects `gh auth token` and starts LiteLLM

Files on Pi (`~/devteam/`):
- `agents/agents_base.py` — same base module deployed
- `agents/oracle.py` — Oracle deployed here, runs as systemd service
- `.env` — same credentials
- `/etc/systemd/system/devteam-oracle.service` — systemd service for Oracle (auto-restart, survives reboot)

Windows:
- `C:\Rohan\Summary\` — created, empty (intended target for Dev file output)
- Windows Task Scheduler task `DevTeam-WSL-Startup` — runs startup.sh at logon

Work completed:
- [x] Pi + laptop smoke tests passing
- [x] Discord server + 7 bots + 9 channels set up
- [x] Oracle (Pi) working as systemd service
- [x] Dev (laptop) working with MCP tools
- [x] End-to-end flow: #tasks → Oracle → #development → Dev ✅ (fibonacci task)
- [x] Azure DevOps + Jira APIs verified
- [x] MCP servers installed on both machines
- [x] Error notifications to #oversight with @here
- [ ] Dev file write task not completing (ADO summary to C:\Rohan\Summary)
- [ ] Remaining 5 agents (Priya, Arjun, Quinn, Dex, Lex) not built yet
- [ ] CrewAI cleanup pending
- [ ] Personal GitHub account not added
</work_done>

<technical_details>
**Architecture:**
- Pi LiteLLM: port 4000, model alias `claude-sonnet-4-6` → Azure OpenAI GPT-4.1
- Laptop LiteLLM: port 4000, model alias `claude-sonnet-4-5` → Copilot Enterprise claude-sonnet-4.6
- Both use `LITELLM_MODEL` env var to select correct alias per machine
- `OPENAI_AGENTS_DISABLE_TRACING=1` required to suppress 401 noise

**MCP servers:**
- Must be used as `async with server:` context managers — the SDK does NOT auto-connect them
- Default `client_session_timeout_seconds=5` too short for npx — use 60s
- `cache_tools_list=True` set on all servers for performance
- ADO MCP server exposes `search_code` which conflicts with GitHub's — filtered with `tool_filter=lambda ctx, tool: tool.name not in ("search_code",)`
- npm global: `~/.npm-global` prefix (permissions fix), binaries at `~/.npm-global/bin/`
- `_find()` function in agents_base searches extended PATH to locate binaries reliably
- WSL2 Windows path: `C:\Rohan\Summary` → `/mnt/c/Rohan/Summary`

**Discord:**
- Guild ID: `1485037469429792930`
- `message_content` privileged intent must be enabled in developer portal for each bot
- Oracle filters: `message.author.bot`, `channel.id != CH_TASKS`, `message.created_at < _ready_time`
- Dev filters: `message.author == client.user` (not all bots), `[TASK ASSIGNED TO DEV]` sentinel
- Bots show as "offline" in Discord member list until first message event — normal behaviour

**Persistence:**
- Oracle: systemd service on Pi (`devteam-oracle.service`), auto-restart, enabled at boot
- Dev: runs in foreground PowerShell async session (dev-agent9); Windows Task Scheduler starts it at logon via `startup.sh`
- WSL2 background processes (`nohup ... &`) get killed on SSH disconnect — must use systemd or foreground sessions

**Pi LiteLLM quirk:**
- Port 4000, not 3001 as previously assumed
- Three model aliases all map to same `azure/gpt-41` deployment: `claude-3-5-sonnet-20241022`, `claude-sonnet-4-6`, `claude-3-7-sonnet-20250219`

**ADO MCP tools available:** core_list_projects, wit_create_work_item, wit_update_work_item, repo_create_pull_request, repo_list_repos_by_project, pipelines_run_pipeline, search_workitem, wiki_*, testplan_*, advsec_* — comprehensive coverage

**Unresolved:**
- Dev sometimes responds to Discord without using the filesystem write tool — need to make instructions more explicit or verify tool usage
- WSL2 systemd not enabled (requires sudo) — relying on Task Scheduler instead
- Personal GitHub account not yet added to `gh` on laptop
</technical_details>

<important_files>
- `~/devteam/agents/agents_base.py` (WSL2 + Pi)
  - Core module imported by all agents
  - Defines: LiteLLM client, make_agent, run_agent, all 6 MCP server factories, notify_error helper, extended PATH for binary discovery
  - Critical: `_find()` for binary paths, `client_session_timeout_seconds=60`, `tool_filter` on ADO server

- `~/devteam/agents/dev.py` (WSL2)
  - Dev agent — currently only fully-tooled agent
  - Uses: filesystem (`~/`, `/tmp`, `/mnt/c/Rohan`), github, azure-devops, fetch MCP servers
  - Error handler posts to `CH_OVERSIGHT` with `@here`
  - Running as shellId `dev-agent9`

- `~/devteam/agents/oracle.py` (Pi)
  - Oracle agent — orchestrator
  - Systemd service: `devteam-oracle.service`
  - Posts work orders to #development with `[TASK ASSIGNED TO DEV]` sentinel
  - Posts task notifications to #oversight

- `~/devteam/.env` (WSL2 + Pi)
  - All secrets: Discord tokens (7 bots), channel IDs, AZDO_PAT, JIRA_API_TOKEN, JIRA_EMAIL, LITELLM_BASE_URL, LITELLM_MODEL
  - Pi version has `LITELLM_MODEL=claude-sonnet-4-6`; laptop has `LITELLM_MODEL=claude-sonnet-4-5`

- `~/nanoclaw-laptop/litellm/config.yaml` (WSL2)
  - LiteLLM proxy config — model aliases for Copilot Enterprise
  - Uses `GITHUB_WORK_TOKEN_PLACEHOLDER` replaced at runtime by `start.sh`
  - Must use LiteLLM 1.63.0 exactly (1.82.5 breaks with Responses API)

- `~/devteam/startup.sh` (WSL2)
  - Auto-start script for LiteLLM + Dev agent on Windows logon
  - Registered in Windows Task Scheduler as `DevTeam-WSL-Startup`

- `/etc/systemd/system/devteam-oracle.service` (Pi)
  - Systemd unit for Oracle — survives reboots, auto-restarts on failure
  - Depends on `litellm.service`
</important_files>

<next_steps>
Immediate — fix Dev file write issue:
- Re-post task to #tasks with explicit path: *"List all Azure DevOps projects with their repos, work items and pipelines. Write a markdown summary to the file /mnt/c/Rohan/Summary/devops-summary.md using the filesystem write tool."*
- If Dev still doesn't write, add explicit instruction in `DEV_INSTRUCTIONS` to always use filesystem tool for file tasks

Remaining todos (from SQL):
1. **`agent-tools`** (in_progress) — wire tools into Oracle, Priya, Lex (on Pi) and Arjun, Quinn, Dex (on laptop). Each gets role-specific MCP servers per the tool matrix in plan.md.
2. **`more-agents`** (pending) — build Priya, Arjun, Quinn, Dex, Lex with personalities + tools. Pi agents: Priya (ADO Boards, GitHub, Jira, write PRDs), Lex (docker/kubectl, az deploy, az monitor). Laptop agents: Arjun (filesystem, az infra read, mermaid), Quinn (run tests, az monitor, Jira bugs), Dex (SQL tools, az data).
3. **`persist-agents`** (in_progress) — Dev persistence via Task Scheduler done; need to verify it works on reboot; add LiteLLM health check to startup.sh.
4. **`cleanup-crewai`** (pending) — `rm -rf ~/crewai-env` on Pi; `pip uninstall crewai` on laptop WSL2.

Also pending:
- Add personal GitHub account: `gh auth login --hostname github.com` on laptop
- Update Oracle's `mcp_servers` to include Jira + ADO MCP servers
- Test Task Scheduler startup on actual reboot
</next_steps>