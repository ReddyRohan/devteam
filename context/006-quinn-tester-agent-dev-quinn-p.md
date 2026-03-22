<overview>
The user is building a multi-agent AI software development team using OpenAI Agents SDK + LiteLLM + Discord. The team consists of Oracle (orchestrator), Dev (senior developer), and Quinn (QA/tester) agents running in WSL2 on a laptop. This session focused on: fixing multiple bugs discovered during live testing, deploying the agent code to GitHub for reproducibility, and building + testing the full Oracle→Dev→Quinn pipeline with automatic handoffs.
</overview>

<history>

1. **Session started mid-test** — Test 1 ("write hello world to /tmp/hello.p") had just completed
   - Dev wrote the file correctly (user confirmed they typed `.p` not `.py`)
   - Test 1 passed ✅

2. **Test 2 — ambiguous task clarification loop**
   - User posted ambiguous task to #tasks
   - Oracle clarified correctly, created work order, handed off to Dev ✅
   - Dev replied with planning text ("I'll tackle this systematically...") with NO tool calls
   - Multiple bugs discovered and fixed in sequence:

3. **Bug: Dev outputs planning text instead of calling tools**
   - Root cause: "Phase 2 — Plan: post a brief numbered plan first" in instructions encouraged narration
   - Fix: Removed plan-first instruction, added `CRITICAL: ALWAYS start your response by calling tools`
   - Added `_seen_messages` dedup set to prevent processing same Discord message twice

4. **Bug: Shell MCP blocking all commands**
   - Error: `ValueError: No commands are allowed. Please set ALLOW_COMMANDS environment variable`
   - Root cause: `mcp_shell()` in `agents_base.py` only set `ALLOWED_COMMANDS` when `allowed_commands` param passed; server checks `ALLOW_COMMANDS` (without D) and errors when empty
   - Fix: Added default `ALLOW_COMMANDS` list in `mcp_shell()` covering python3, bash, git, curl, npm, docker, az, gh, etc.

5. **Bug: Multiple agent instances processing same message**
   - Root cause: Each restart left old processes running; all instances picked up same Discord messages
   - Fix: Added `acquire_agent_lock(agent_name)` using `fcntl.flock` to `agents_base.py`; each agent calls it at startup; exits immediately if another instance holds the lock
   - Added to `dev.py`, `oracle.py`, `quinn.py`

6. **Bug: Dev `MANDATORY` prompt for simple tasks**
   - Root cause: All tasks triggered "write a gather_data.py script first" prompt regardless of complexity
   - Fix: Simplified to "For simple tasks: use write_file directly. For complex: use helper script"

7. **Bug: Duplicate `client.run(TOKEN)` in dev.py**
   - Fixed by removing the duplicate line

8. **ADO Flutter project task — real-world test**
   - User asked to upload C:\Rohan\FlutterApps\FlutterQuizApp to Azure DevOps
   - Oracle clarified, created work order, Dev created ADO project `FlutterQuizApp`, created repo `flutter-quiz`, added remote, pushed all 3 commits ✅
   - User initially thought files weren't there — they just needed to refresh; files confirmed present

9. **Save agent code to GitHub**
   - User wanted code on personal GitHub (ReddyRohan) for reproducibility
   - Enterprise `gh` account couldn't create personal repos — used personal PAT via REST API
   - Created repo `ReddyRohan/devteam` with `.gitignore` (protects `.env`), `README.md`, `DEPLOYMENT.md`, `.env.template`
   - Verified `.env` was NOT staged before committing ✅

10. **Expanded documentation for LLM-friendly setup**
    - User asked for instructions any LLM can follow to set up the environment
    - Rewrote README with: exact pyenv install commands, package versions, Node.js/npm setup, uv/uvx MCP server setup, LiteLLM config with GitHub Copilot example, Discord bot creation step-by-step, `.env` configuration with explanations, verification steps, troubleshooting table
    - Added `litellm-config.yaml` template with Copilot Enterprise, Azure OpenAI, and plain OpenAI options
    - Added detailed MCP server sections: npm global path fix, `ALLOW_COMMANDS` explained, fetch usage

11. **Deployment gotchas documented in plan.md**
    - 8 gotchas recorded: ALLOW_COMMANDS, lock files, pyenv python, check_resume order, task_thread on resume, no text before tools, old base.py, startup.sh duplicate line

12. **Built Quinn tester agent**
    - User wanted a tester that reads stories AND writes tests for code coverage
    - Explored comprehensive QA capabilities via sub-agent
    - Quinn has 5 modes: (A) test cases from stories, (B) automated tests from code, (C) coverage analysis, (D) bug verification + regression, (E) run existing suite and report
    - Supports pytest, flutter test, Jest, Playwright, Cypress, JUnit, Go test
    - Coverage tools: pytest-cov, lcov, istanbul, JaCoCo, go cover
    - Quinn added to startup.sh and GitHub

13. **Dev→Quinn automatic handoff**
    - User asked Dev to automatically hand off to Quinn after completing any task
    - Added: extract file names from Dev's response, send `[HANDOFF TO QUINN]` with original task, Dev summary, files changed, instructions to test
    - Bug found: `dict.fromkeys(files_mentioned)[:10]` throws `TypeError: unhashable type: 'slice'` — fixed to `list(dict.fromkeys(files_mentioned))[:10]`

14. **Bug: Quinn ignoring Dev's handoffs (all bots blocked)**
    - Root cause: Quinn had `if message.author.bot: return` which blocked Dev's messages (Dev is a bot)
    - Oracle had the same issue
    - Fix: Changed to `if message.author == client.user: return` in quinn.py and oracle.py
    - Dev was already correct (had been updated earlier)
    - Note: Dev was already receiving Oracle's handoffs — this was because dev.py was already using `client.user` check

15. **End-to-end test: Oracle→Dev→Quinn pipeline**
    - Task: "Write a Python function that calculates compound interest and save it to /tmp/compound_interest.py"
    - Oracle → Dev ✅ (file written)
    - Dev → Quinn ✅ (`[Handoff] Dev → QUINN (auto)` in logs)
    - Quinn → wrote `/tmp/test_compound_interest.py` with 30 tests ✅
    - Tests manually verified: **30/30 passed** ✅
    - Quinn's test suite covered: happy paths, boundary values, edge cases, error/negative paths, regression tests

</history>

<work_done>

**Files modified in `~/devteam/agents/`:**

- `agents_base.py`:
  - Added `acquire_agent_lock(agent_name)` — fcntl-based singleton lock
  - Fixed `mcp_shell()` — now sets default `ALLOW_COMMANDS` list (python3, bash, git, curl, npm, docker, az, gh, etc.)
  - Oracle + Dev `on_message` bots filter changed from `author.bot` to `author == client.user`

- `dev.py`:
  - Instructions: Removed "Phase 2 — Plan first", added `CRITICAL RULES ON TOOL CALLS` (tools-first, no mid-task text)
  - Prompt: strips `[HANDOFF TO DEV]` header before passing to model
  - Prompt: added `first_action` that forces credential check as first tool call
  - Added `_seen_messages` dedup set
  - Fixed duplicate `client.run(TOKEN)`
  - Added auto Quinn handoff after task completion
  - Fixed `dict.fromkeys()[:10]` TypeError → `list(dict.fromkeys())[:10]`
  - `if message.author == client.user` (was already correct)

- `oracle.py`:
  - Fixed `if message.author == client.user` (was `author.bot`)
  - `check_resume()` runs BEFORE channel filter
  - Passes `task_thread` on clarification resume (no new thread per round)
  - Stores `task_thread_id` in pending context

- `quinn.py` (new file):
  - Full QA agent with 5 task modes
  - Uses `if message.author == client.user` (not `author.bot`)
  - Tools: filesystem, shell, fetch
  - `acquire_agent_lock("Quinn")`

- `startup.sh`: Added Quinn startup line

**Files in GitHub (`ReddyRohan/devteam`):**
- `README.md` — comprehensive LLM-friendly setup guide
- `DEPLOYMENT.md` — 10 deployment gotchas
- `.env.template` — all env var names with comments
- `litellm-config.yaml` — template with 3 provider options
- `agents/agents_base.py`, `agents/dev.py`, `agents/oracle.py`, `agents/quinn.py`
- `startup.sh`, `.gitignore`

**Currently running (WSL2):**
- Oracle (PID ~37673) — oracle.log
- Dev (PID 39895) — dev.log
- Quinn (PID 36651) — quinn.log
- LiteLLM on port 4000

**What works:**
- ✅ Oracle clarification loop (preserves thread across rounds)
- ✅ Oracle → Dev handoff
- ✅ Dev → Quinn automatic handoff
- ✅ Quinn writes comprehensive tests and runs them
- ✅ Lock prevents multiple instances
- ✅ Shell MCP executes commands

**Known issues / cosmetic:**
- Dev posts intermediate text replies ("I'll explore...") between tool calls — only final summary should post
- Multiple Oracle handoffs sometimes sent (race condition in dedup when restarting)

</work_done>

<technical_details>

**Architecture:**
- Laptop LiteLLM: port 4000, `claude-sonnet-4-5` → Copilot Enterprise `claude-sonnet-4.6`
- All agents use `~/.pyenv/versions/3.11.9/bin/python3` — system python3 lacks packages
- `.env` at `~/devteam/.env` loaded by all agents via `load_dotenv`

**MCP servers:**
- `filesystem`: `npx -y @modelcontextprotocol/server-filesystem` — needs npm global path `~/.npm-global/bin`
- `shell`: `uvx mcp-shell-server` — requires `ALLOW_COMMANDS` env var (not `ALLOWED_COMMANDS`) — `agents_base.py` sets default list
- `fetch`: `uvx mcp-server-fetch` — no config needed

**Critical gotchas:**
- `mcp-shell-server` checks `ALLOW_COMMANDS` (without D); if empty → blocks ALL commands with no clear error
- `message.author.bot` blocks ALL bots including other agents → must use `message.author == client.user`
- Thread replies have different `channel.id` than the original channel → `check_resume()` must run BEFORE channel filter
- `dict.fromkeys(x)` returns a dict, not list → can't slice directly, need `list()` wrapper
- LiteLLM version must be `1.63.x` — newer versions break with OpenAI Agents SDK Responses API
- `acquire_agent_lock` uses `/tmp/devteam_<name>.lock` — must `rm -f /tmp/devteam_*.lock` after crash before restart
- Model narrates instead of calling tools if instructions allow planning text — must have explicit "call tools first" rule
- Bot handoff messages: Dev sends `**[HANDOFF TO QUINN]**` (bold markdown) — `is_handoff_for()` checks for `[HANDOFF TO QUINN]` which IS a substring match ✅

**Personal GitHub PAT:** `<REDACTED_GITHUB_PAT>` (used for `ReddyRohan/devteam` repo push, do NOT commit)

**AGENT_CHANNELS mapping:**
- DEV → `DISCORD_CHANNEL_DEVELOPMENT`
- QUINN → `DISCORD_CHANNEL_QA`
- ARJUN → `DISCORD_CHANNEL_ARCHITECTURE`
- PRIYA → `DISCORD_CHANNEL_PRODUCT`
- LEX → `DISCORD_CHANNEL_DEVOPS`
- DEX → `DISCORD_CHANNEL_DATA`

**Handoff format:** `**[HANDOFF TO AGENT]**\nFrom: X\nThread: url\n\n<work order>`

**Quinn test results:** 30/30 passed for compound_interest.py — happy paths, boundary, edge cases, error handling, regression

</technical_details>

<important_files>

- `~/devteam/agents/agents_base.py`
  - Core shared module imported by all agents
  - Contains: `make_agent`, `run_agent` (max_turns=30), all MCP factories, `post_question`, `check_resume`, `handoff`, `is_handoff_for`, `AGENT_CHANNELS`, `acquire_agent_lock`, `notify_error`
  - Critical: `mcp_shell()` now sets `ALLOW_COMMANDS` default; `_ENV_WITH_PATH` includes `.env` vars for shell subprocess credential inheritance

- `~/devteam/agents/dev.py`
  - Dev agent — senior developer
  - Tools: filesystem + fetch + shell
  - Key: `_seen_messages` dedup, `_pending` for Q&A, auto Quinn handoff after completion, `first_action` forces credential check as first tool call, strips `[HANDOFF TO DEV]` header from prompt
  - `if message.author == client.user` (accepts handoffs from other bots)

- `~/devteam/agents/oracle.py`
  - Oracle orchestrator — clarification loop, smart routing, task threads
  - Key: `check_resume()` BEFORE channel filter, `task_thread_id` stored in pending context for multi-round clarification
  - `if message.author == client.user`

- `~/devteam/agents/quinn.py`
  - New QA agent — 5 task modes
  - `if message.author == client.user` — accepts Dev's handoffs
  - Supports pytest, flutter test, Jest, Playwright, coverage tools

- `~/devteam/.env`
  - All secrets: Discord tokens, channel IDs, AZDO_PAT, JIRA credentials, LiteLLM config
  - Never committed — protected by `.gitignore`

- `~/devteam/startup.sh`
  - Starts LiteLLM (with gh token injection) + Oracle + Dev + Quinn
  - Uses pyenv path setup

- `C:\Users\rohan\.copilot\session-state\ae0b9b08-b91e-48ca-927c-f91cda05b514\plan.md`
  - Full architecture plan + deployment gotchas section (8 items) appended this session

</important_files>

<next_steps>

**Pending todos (from SQL):**
- `oracle-decompose` — Oracle LLM prompt: decompose into ordered subtasks, show breakdown, wait for ✅
- `oracle-ado-epic` — Create ADO Epic + Tasks via REST API
- `oracle-approval-gate` — ✅ gate for critical tasks, no timeout
- `oracle-sequential-chain` — chain subtask 1→2→3 on TASK COMPLETE signal
- `oracle-ado-update` — update ADO task status throughout lifecycle
- `oracle-thread-monitor` — monitor task thread for TASK COMPLETE signals
- `agent-complete-signal` — all agents post `[TASK COMPLETE]` when done
- `agent-thread-post` — agents post updates to task thread
- `agent-thread-listen` — agents respond to @mentions in task threads
- `more-agents` — Priya, Arjun, Lex, Dex
- `agent-standards` — apply Dev operating principles to all agents
- `cleanup-crewai` — clean up old CrewAI remnants

**Immediate cosmetic fix to consider:**
- Dev posts intermediate text replies between tool calls — only final `✅ Work Order Complete` should go to Discord. Fix: buffer responses and only post the last one, or detect incomplete responses

**Deployment note to add to DEPLOYMENT.md:**
- `message.author.bot` blocks agent-to-agent handoffs — must use `message.author == client.user`

**Next planned work per user direction:**
- User was working through Track C (more agents) — Quinn done, Priya is next candidate
- Or switch to Track A (task decomposition) which unlocks multi-step project execution

</next_steps>