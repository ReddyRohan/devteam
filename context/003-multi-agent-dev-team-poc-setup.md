<overview>
The user has a Raspberry Pi 5 (8GB) running Pi-hole, Unbound, Tailscale, and NanoClaw (AI chatbot framework). The session focused on two parallel tracks: (1) improving the existing Chotu AI assistant personality and WhatsApp/Discord bot configuration, and (2) planning and beginning to build a multi-agent AI software development team. The approach settled on OpenAI Agents SDK + LiteLLM as the stack, with Pi running management agents (Azure OpenAI) and laptop running compute-heavy agents (GitHub Copilot Enterprise), both sharing a Discord server for communication and human oversight.
</overview>

<history>
1. **WhatsApp group "Chotu test" registration**
   - Found group JID `120363405584741948@g.us` in messages.db
   - Registered with `--no-trigger-required` flag, copied Chotu personality CLAUDE.md
   - Restarted NanoClaw

2. **Chotu personality updates (multiple iterations)**
   - Made replies shorter (1–3 sentences max)
   - Changed language from heavy Hinglish to mostly English with light Tamil sprinkles
   - Dropped chai wala persona entirely — replaced with Tamilian who lived in Mumbai
   - Final personality: English-first, occasional Tamil (*da*, *machan*, *aiyo*), minimal Hindi (*arre*, *yaar*)

3. **Trigger-only mode for Chotu test group**
   - Changed `requires_trigger=1` via SQLite on `120363405584741948@g.us`
   - Now only responds when `@Chotu` is typed

4. **Docker image rebuilt with Python/Azure/diagram packages**
   - Added to NanoClaw Dockerfile: `python3`, `python3-pip`, `graphviz`, `default-jre-headless`, Azure CLI
   - Added npm global: `@mermaid-js/mermaid-cli`
   - Added ~50 Python packages: `python-docx`, `openpyxl`, `pandas`, `numpy`, all `azure-*` packages, `azure-monitor-query`, `azure-monitor-ingestion`, `msrest`, `msrestazure`, `matplotlib`, `seaborn`, `plotly`, `kaleido`, `graphviz`, `diagrams`, `cairosvg`, `reportlab`, `plantuml-markdown`
   - Build succeeded, NanoClaw restarted

5. **Multi-agent dev team planning**
   - User requested plan for AI dev team with agents for full software lifecycle
   - Ran two background research agents: multi-agent system design + Pi capacity assessment
   - Pi assessment: ✅ GO with NVMe SSD (hard requirement), persistent containers, memory limits, active cooling
   - Research: recommended MetaGPT-style event-driven pub/sub, LangGraph/CrewAI patterns, 7 agents for Pi constraints
   - Created comprehensive `plan.md` in session state folder

6. **Pi vs Laptop agent split decision**
   - Pi (always-on): Oracle, Priya, Lex → Azure OpenAI
   - Laptop (WSL2, when on): Arjun, Dev, Quinn, Dex → GitHub Copilot Enterprise
   - Fallback: each side runs all 7 if the other is offline
   - Decided: NanoClaw stays only on Pi (orchestrates all containers), laptop only runs LiteLLM proxy
   - Then revised: laptop needs NanoClaw too so agents work when Pi is off

7. **Framework selection: CrewAI → OpenAI Agents SDK**
   - Initially chose CrewAI (installed on Pi venv + laptop)
   - User questioned whether Copilot SDK would be better
   - Settled on OpenAI Agents SDK — simpler, LiteLLM handles all multi-LLM switching
   - User confirmed wants ability to switch: Claude Sonnet/Opus, GPT models, Gemini
   - CrewAI cleanup noted for end of session

8. **GitHub Copilot Enterprise PoC**
   - WSL2 Ubuntu 20.04: installed Node 22, Python 3.11 (via pyenv), LiteLLM 1.63.0, GitHub CLI
   - Authenticated with work account (`rohan-reddy_rmgh`) via `gh auth login` + `gh auth refresh --scopes copilot`
   - Key finding: Enterprise endpoint is `https://api.enterprise.githubcopilot.com` (not standard)
   - Key finding: LiteLLM 1.82.5 broken (Responses API default) — must use **LiteLLM 1.63.0**
   - Available models: `claude-sonnet-4.6`, `claude-opus-4.6`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.3-codex`
   - Working config: `openai/claude-sonnet-4.6` with `api_base: https://api.enterprise.githubcopilot.com`
   - Direct API test ✅, LiteLLM proxy test ✅, response: `"PoC successful"`

9. **OpenAI Agents SDK smoke test**
   - Installed `openai-agents-0.12.5` + `discord.py` on Pi (venv `~/devteam-env`) and laptop
   - Laptop test ✅: `Agent response: OpenAI Agents SDK working on laptop via Copilot`
   - Fix required: must use `OpenAIChatCompletionsModel` + `set_default_openai_client()` pattern
   - Must set `OPENAI_AGENTS_DISABLE_TRACING=1` to suppress 401 noise from OpenAI tracing endpoint
   - Pi test ❌: connection refused — LiteLLM not running at test time (not a real failure)
   - Laptop LiteLLM test also failed (LiteLLM wasn't started before test due to PowerShell escaping issue)
</history>

<work_done>
Files modified on Pi (`rohan@192.168.1.50`):
- `/home/rohan/nanoclaw/container/Dockerfile` — added Python 3, pip, graphviz, JRE, Azure CLI, mermaid-cli, ~50 Python packages
- `/home/rohan/nanoclaw/groups/global/CLAUDE.md` — Chotu personality (Tamilian in Mumbai, English-first)
- `/home/rohan/nanoclaw/groups/*/CLAUDE.md` — all group folders synced with same personality
- `/home/rohan/nanoclaw/store/messages.db` — `requires_trigger=1` for `120363405584741948@g.us`

Files on laptop WSL2 (`~/`):
- `~/nanoclaw-laptop/litellm/config.yaml` — working LiteLLM config for Copilot Enterprise
- `~/nanoclaw-laptop/litellm/start.sh` — startup script that auto-injects `gh auth token`
- `~/devteam/` — scaffolded project structure (agents/, tools/, flows/, config/, logs/, .env)

Session state files:
- `C:\Users\rohan\.copilot\session-state\ae0b9b08-b91e-48ca-927c-f91cda05b514\plan.md` — full multi-agent plan

Environment state:
- Pi: Docker image rebuilt with all packages ✅, NanoClaw running ✅
- Pi: `~/devteam-env` venv with `openai-agents-0.12.5`, `discord.py`, `python-dotenv`
- Pi: `~/crewai-env` venv with CrewAI (to be deleted)
- Laptop WSL2: Python 3.11 (pyenv), Node 22, LiteLLM 1.63.0, openai-agents-0.12.5, discord.py, gh CLI authenticated

Work completed:
- [x] Chotu personality finalised (Tamilian/Mumbai/English-first)
- [x] WhatsApp "Chotu test" group registered and trigger-only
- [x] NanoClaw Docker image rebuilt with Python/Azure/diagram packages
- [x] Multi-agent plan created and saved
- [x] Pi capacity assessment completed
- [x] GitHub Copilot Enterprise PoC passed
- [x] OpenAI Agents SDK installed on Pi + laptop
- [x] Laptop SDK smoke test passed (agent → LiteLLM → Copilot)
- [ ] Pi agent smoke test (LiteLLM wasn't running — needs retry)
- [ ] Discord server setup (7 bots, channels)
- [ ] Build Phase 1 agents (Oracle + Dev)
- [ ] Clean up CrewAI venvs
- [ ] Add personal GitHub account to laptop `gh`
</work_done>

<technical_details>
**LiteLLM version critical:** Must use 1.63.0. Version 1.82.5 defaults to OpenAI Responses API which GitHub Copilot Enterprise doesn't support for Claude models. Error: `"model claude-sonnet-4.6 does not support Responses API"`.

**Copilot Enterprise endpoint:** `https://api.enterprise.githubcopilot.com` (NOT `api.githubcopilot.com`). Standard endpoint returns 404. Enterprise subscription confirmed: Royal Mail org, `copilot_enterprise_seat_multi_quota`.

**Copilot auth flow:** Use `gh auth token` to get OAuth token. Requires `gh auth refresh --scopes copilot` first. Token used directly as Bearer. No need for `copilot_internal/v2/token` endpoint exchange — LiteLLM 1.63.0 handles it natively with `openai/` prefix + custom `api_base`.

**LiteLLM config pattern for Copilot Enterprise:**
```yaml
model_list:
  - model_name: claude-sonnet-4-5
    litellm_params:
      model: openai/claude-sonnet-4.6
      api_base: https://api.enterprise.githubcopilot.com
      api_key: <gh_auth_token>
      extra_headers:
        Copilot-Integration-Id: vscode-chat
        Editor-Version: vscode/1.85.0
litellm_settings:
  drop_params: true
```

**OpenAI Agents SDK usage pattern:**
```python
import os
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
from openai import AsyncOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_default_openai_client

client = AsyncOpenAI(base_url="http://localhost:3002/v1", api_key="placeholder")
set_default_openai_client(client)

agent = Agent(
    name="Dev",
    instructions="...",
    model=OpenAIChatCompletionsModel(model="claude-sonnet-4-5", openai_client=client),
)
result = await Runner.run(agent, "task")
```

**Token injection:** LiteLLM config stores `GITHUB_WORK_TOKEN_PLACEHOLDER`, `start.sh` uses `sed` to inject live `gh auth token` into `/tmp/litellm-active.yaml` at startup. Tokens not stored in files permanently.

**NanoClaw SQLite access:** Must use `sudo pihole-FTL sqlite3 /home/rohan/nanoclaw/store/messages.db` (sqlite3 not installed on Pi).

**NanoClaw register syntax:** `--no-trigger-required` flag (not `--requires-trigger false`), `--trigger` is required argument even if not used.

**WSL2 distro name:** `Ubuntu-20.04` (not `Ubuntu`). Always use `wsl -d Ubuntu-20.04`.

**PowerShell heredoc issue:** Cannot use bash heredocs reliably from PowerShell. Always write scripts to `\\wsl$\Ubuntu-20.04\tmp\script.sh` then run with `wsl -d Ubuntu-20.04 -- bash /tmp/script.sh`.

**Pi Python:** System Python 3.13, no pip (PEP 668 externally managed). Use venvs: `python3 -m venv ~/devteam-env && ~/devteam-env/bin/pip install ...`

**Laptop pyenv activation:** Always source pyenv in scripts: `export PYENV_ROOT="$HOME/.pyenv" && export PATH="$PYENV_ROOT/bin:$PATH" && eval "$(pyenv init -)"`. Cannot be done inline from PowerShell.

**Available Copilot models (Enterprise):** `claude-opus-4.6`, `claude-sonnet-4.6`, `gpt-5.3-codex`, `gpt-5.4-mini`, `gpt-5.4` (as of March 2026).

**Architecture decision:** Pi NanoClaw (Chotu bots) is kept separate from the dev team agents. Dev team uses OpenAI Agents SDK + discord.py. When Pi is off, laptop NanoClaw handles Chotu bots too. When laptop is off, Pi dev agents use Azure.

**Pi LiteLLM port:** 3001 (existing, Azure OpenAI). Laptop LiteLLM port: 3002 (Copilot Enterprise). Both expose Anthropic-compatible `/v1/messages` endpoint for NanoClaw, and OpenAI-compatible `/v1/chat/completions` for dev team agents.
</technical_details>

<important_files>
- `/home/rohan/nanoclaw/container/Dockerfile`
  - NanoClaw agent Docker image definition
  - Added Python 3, pip, graphviz, JRE, Azure CLI, mermaid-cli, ~50 Python packages
  - Image rebuilt and deployed

- `/home/rohan/nanoclaw/groups/global/CLAUDE.md`
  - Chotu's personality definition (source of truth, copied to all group folders)
  - Current: Tamilian in Mumbai, English-first, light Tamil sprinkles, short punchy replies

- `/home/rohan/nanoclaw/store/messages.db`
  - SQLite DB with registered_groups table
  - `120363405584741948@g.us` (Chotu test) has `requires_trigger=1`
  - Access: `sudo pihole-FTL sqlite3 /home/rohan/nanoclaw/store/messages.db`

- `~/nanoclaw-laptop/litellm/config.yaml` (WSL2)
  - Working LiteLLM config for GitHub Copilot Enterprise
  - Uses `GITHUB_WORK_TOKEN_PLACEHOLDER` — replaced at runtime by `start.sh`
  - Must use LiteLLM 1.63.0 exactly

- `~/nanoclaw-laptop/litellm/start.sh` (WSL2)
  - Startup script: calls `gh auth token`, injects into config, starts LiteLLM on port 3002
  - Must be run before any laptop agents

- `C:\Users\rohan\.copilot\session-state\ae0b9b08-b91e-48ca-927c-f91cda05b514\plan.md`
  - Full multi-agent dev team plan
  - Contains: agent roster, personalities, Discord structure, skills matrix, Pi capacity assessment, PoC results, phased implementation

- `/home/rohan/nanoclaw/.env` (Pi)
  - ASSISTANT_NAME=Chotu, all bot tokens (Telegram, Discord, WhatsApp)
  - Must always be synced to `data/env/env`

- `/opt/litellm/config.yaml` (Pi)
  - Routes to Azure OpenAI GPT-4.1, `drop_params: true`
  - Port 3001
</important_files>

<next_steps>
Immediate next steps:

1. **Verify Pi agent smoke test** — LiteLLM was running when test failed (connection issue was timing). Run:
```bash
cd ~/devteam-env && bin/python3 /tmp/agents_test.py  # with OPENAI_AGENTS_DISABLE_TRACING=1
```

2. **Set up Discord server** for dev team agents:
   - Create Discord server with channel structure from plan.md
   - Create 7 Discord bots (one per agent: Oracle, Priya, Arjun, Dev, Quinn, Dex, Lex)
   - Each bot needs its own token stored in `~/devteam/.env`

3. **Build Phase 1 agents** (MVP):
   - Oracle (orchestrator) on Pi — Azure OpenAI
   - Dev (senior developer) on Pi (fallback) + laptop (primary) — Copilot
   - Simple task handoff: Oracle receives request → routes to Dev → Dev responds in Discord thread

4. **Add personal GitHub account** to `gh` on laptop:
```bash
gh auth login --hostname github.com --git-protocol https --web
# log in with personal account
```

5. **Clean up CrewAI** from Pi and laptop:
```bash
# Pi
rm -rf ~/crewai-env
# Laptop WSL2
pip3 uninstall crewai crewai-tools -y
```

6. **Add Copilot models to Pi's LiteLLM** (for fallback when laptop is off):
   - Need GitHub classic PAT with `copilot` scope stored on Pi
   - Add `claude-sonnet-4.6` models pointing to Enterprise endpoint

Blockers:
- Discord server + bot tokens needed before agents can be built
- Pi LiteLLM smoke test not yet confirmed (timing issue, likely works)
</next_steps>