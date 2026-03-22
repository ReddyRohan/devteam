<overview>
The user is building a multi-agent AI software development team using OpenAI Agents SDK + LiteLLM + Discord. Pi 5 runs management agents (Oracle) via Azure OpenAI GPT-4.1; laptop WSL2 runs compute agents (Dev, and future agents) via GitHub Copilot Enterprise. The session focused on: (1) fixing Dev agent to work reliably and like Copilot CLI, (2) moving Oracle from Pi to local for easier debugging, (3) implementing Oracle clarification loops + smart routing + standardised handoffs, and (4) planning task decomposition with ADO Boards integration.
</overview>

<history>
1. **Dev file write not working** — Dev kept saying "done" but never writing files
   - Root cause 1: `max_turns=10` default exhausted before write_file called → raised to 30
   - Root cause 2: Instructions didn't force script-first approach → added MANDATORY prompt prefix
   - Root cause 3: ADO MCP server causing 20+ sequential calls → removed it entirely
   - Dev now has: filesystem + shell + fetch MCP only (mirrors Copilot's tool set)

2. **Oracle moved from Pi to local WSL2**
   - Stopped + disabled `devteam-oracle.service` on Pi
   - Oracle now runs locally in WSL2 for easier debugging
   - `startup.sh` updated to start both Oracle + Dev on Windows logon

3. **Dev tool overhaul** — user asked "does Dev have tools a real dev would have?"
   - Removed GitHub MCP (shell covers git natively)
   - Removed ADO MCP (shell + REST API is more reliable)
   - Added `mcp-shell-server` (uvx) — lets Dev run python3, bash, git, docker, npm
   - Added web search via fetch to DuckDuckGo HTML (same as Copilot)
   - Enabled `parallel_tool_calls=True` in ModelSettings

4. **Full Dev instructions rewrite** — user asked "make Dev work like you"
   - Gap analysis: Dev was sequential, verbose, no planning phase, no verification, asked for credentials
   - New instructions: Explore→Plan→Execute→Verify→Report phases
   - Script-for-bulk rule: >3 fetches → write Python script, run once via shell
   - Parallel tool calls with concrete examples
   - Credential rules: use env vars (AZDO_PAT etc.), never ask for or create tokens
   - Concise output rules, progress updates for long tasks
   - Error recovery: 3 retries with different strategies

5. **Dev credential bug** — Dev created a new ADO PAT mid-task
   - Added hard rule: credentials are env vars, never create new tokens
   - Added `.env` vars to `_ENV_WITH_PATH` in agents_base so shell subprocesses inherit them

6. **Oracle credential bug** — Oracle work orders said "PAT must be provided by user"
   - Fixed Oracle instructions: "credentials are pre-configured as env vars, never mention as blocker"
   - Fixed Oracle message chunking (2000 char Discord limit was crashing Oracle)

7. **Conversational Q&A mechanism** — user: "agents should ask questions like you do"
   - Added `post_question()` and `check_resume()` shared helpers to `agents_base.py`
   - Dev: posts ❓ question, creates thread, saves `_pending` state, resumes when anyone replies
   - Oracle: clarification loop (up to 5 rounds) before creating work order
   - Any agent OR human can reply to resume — not just the original poster

8. **Oracle context loss bug** — Oracle was treating every reply as a new task
   - Root cause: `check_resume()` ran AFTER `CH_TASKS` channel filter, so thread replies (different channel ID) were dropped
   - Fix: moved `check_resume()` BEFORE channel filter in `on_message`
   - Extracted task processing into `_process_task()` helper

9. **Standardised handoffs** — user: "each agent should have a clear handoff"
   - Added `handoff()` and `is_handoff_for()` helpers to `agents_base.py`
   - Standard format: `[HANDOFF TO <AGENT>]`
   - Oracle now uses smart routing (LLM picks DEV/QUINN/ARJUN/PRIYA/LEX/DEX based on task type)
   - Dev updated to use `is_handoff_for(message.content, "DEV")`
   - AGENT_CHANNELS dict maps agent name → Discord channel env var

10. **Task decomposition planning** — user: "big tasks should be chunked into subtasks"
    - Planned: Oracle decomposes → shows breakdown → waits for ✅ → creates ADO Epic+Tasks → sequential handoffs
    - ADO "AgentTasks" project to be created
    - No approval timeout — wait indefinitely for critical task approval
    - Agent communication via task thread (not just own channel)
    - Plan written to plan.md, todos inserted into SQL

11. **Test run in progress** — user posted Test 1 "Write hello world to /tmp/hello.py"
    - Oracle picked it up: `[Handoff] Oracle → DEV` logged ✅
    - Dev-agent28 is processing it now
</history>

<work_done>
Files modified on WSL2 (`~/devteam/agents/`):

- `agents_base.py`:
  - `parallel_tool_calls=True` in `make_agent()`
  - `max_turns=30` default in `run_agent()`
  - Added `mcp_shell()` factory
  - Added `.env` vars loaded into `_ENV_WITH_PATH` so shell subprocesses inherit credentials
  - Added `post_question()` / `check_resume()` shared Q&A helpers
  - Added `handoff()` / `is_handoff_for()` shared handoff helpers with AGENT_CHANNELS dict

- `dev.py` (complete rewrite):
  - Tools: filesystem + fetch + shell only (no ADO MCP, no GitHub MCP)
  - Instructions: Explore→Plan→Execute→Verify→Report phases
  - `_pending` dict for Q&A state keyed by thread ID
  - `_run_task()` async helper separates task execution from Discord handling
  - `[NEEDS INFO]` detection → `post_question()` → saves state → resumes on reply
  - Uses `is_handoff_for(message.content, "DEV")` sentinel
  - Response logging: prints first 200 chars + length
  - max_turns=30, ✅/❌/⚙️ reactions

- `oracle.py`:
  - Moved from Pi, runs locally
  - `_pending` dict + `_process_task()` helper
  - Clarification loop: up to 5 rounds, READY/QUESTION format, waits for answer in thread
  - Smart routing: LLM picks agent (DEV/QUINN/etc.) based on task type
  - Uses `handoff()` instead of hardcoded channel send
  - Thread message chunking (2000 char limit fix)
  - `check_resume()` runs BEFORE CH_TASKS channel filter (context loss fix)
  - Credential rules in instructions

- `startup.sh`:
  - Starts both Oracle + Dev on WSL2 boot
  - Az CLI auth check removed (that's Lex's job)

Current state:
- [x] Oracle locally running (oracle-local11)
- [x] Dev locally running (dev-agent28)
- [x] Test 1 posted — Oracle handed off to Dev (`[Handoff] Oracle → DEV` logged)
- [ ] Test 1 not confirmed complete (Dev still running)
- [ ] Test 2 (ambiguous task clarification loop) not yet run
- [ ] Task decomposition + ADO integration not yet implemented
- [ ] Other 5 agents (Priya, Arjun, Quinn, Dex, Lex) not built
</work_done>

<technical_details>
**Architecture:**
- Pi LiteLLM: port 4000, `claude-sonnet-4-6` → Azure OpenAI GPT-4.1
- Laptop LiteLLM: port 4000, `claude-sonnet-4-5` → Copilot Enterprise claude-sonnet-4.6
- Oracle + Dev both run locally in WSL2 now (Pi Oracle disabled)
- Shell IDs: oracle-local11, dev-agent28

**MCP servers on Dev:**
- `filesystem` (npx `@modelcontextprotocol/server-filesystem`) — allowed: `~/`, `/tmp`, `/mnt/c/Rohan`
- `fetch` (uvx `mcp-server-fetch`) — web pages/docs/search
- `shell` (uvx `mcp-shell-server`) — any terminal command; inherits `.env` credentials

**Credentials in shell:**
- `.env` loaded via `dotenv_values()` and merged into `_ENV_WITH_PATH`
- Dev scripts use: `os.getenv("AZDO_PAT")` for ADO REST API with `requests.get(url, auth=("", PAT))`
- JIRA: `JIRA_API_TOKEN`, `JIRA_EMAIL`, `JIRA_BASE_URL`

**Handoff format:**
```
[HANDOFF TO DEV]
From: Oracle
Thread: <thread_url>

<work order text>
```
- `is_handoff_for(content, "DEV")` checks for `[HANDOFF TO DEV]` in message
- AGENT_CHANNELS maps: DEV→DISCORD_CHANNEL_DEVELOPMENT, QUINN→QA, ARJUN→ARCHITECTURE, PRIYA→PRODUCT, LEX→DEVOPS, DEX→DATA

**Q&A mechanism:**
- `post_question(client, message, question, context, _pending)` — posts ❓, creates thread, saves state
- `check_resume(message, client, pending)` — call before channel filter; returns context if thread reply matches
- Must be checked BEFORE channel ID filter — thread replies have different channel ID than main channel

**Key bugs fixed:**
- Oracle `check_resume` was after CH_TASKS filter → thread replies dropped → context lost
- Dev `max_turns=10` → exhausted before write_file → raised to 30
- Oracle messages >2000 chars crashed Discord send → now chunked
- Dev created new ADO PAT → added "never create credentials" rule
- Oracle said "PAT must be provided" → fixed instructions
- Duplicate `client.run(TOKEN)` in old dev.py → fixed

**Discord rate limiting:**
- 429 warnings seen regularly in Oracle logs (reactions hit rate limits)
- Not causing failures currently but worth monitoring

**File write approach:**
- When task has output path (`/mnt/c/...`), prompt prefixed with MANDATORY: write Python script to /tmp/gather_data.py, run it, write to path
- `extract_output_path()` regex: `/mnt/...`, `~/...`, `/tmp/...`

**Startup:**
- `startup.sh`: starts LiteLLM → waits for health → starts Oracle → starts Dev
- Windows Task Scheduler runs `startup.sh` at logon via WSL2
- Oracle and Dev run as `nohup` background processes (dies on WSL session end)
- `/tmp/run_oracle.sh` and `/tmp/run_dev.sh` — convenience scripts for manual restart

**ADO org:** `rohanreddy0892`, projects: `Test`, `flaskwebapp`

**Planned ADO project:** `AgentTasks` — to be created by Oracle for task tracking
</technical_details>

<important_files>
- `~/devteam/agents/agents_base.py`
  - Core module imported by all agents
  - Contains: `make_agent()` (parallel_tool_calls=True), `run_agent()` (max_turns=30), all 5 MCP factories, `post_question()`, `check_resume()`, `handoff()`, `is_handoff_for()`, `AGENT_CHANNELS` dict, `notify_error()`
  - Critical: `_ENV_WITH_PATH` now includes `.env` vars so shell MCP inherits credentials

- `~/devteam/agents/dev.py`
  - Dev agent — complete rewrite this session
  - Tools: filesystem + fetch + shell
  - `_pending` dict for Q&A, `_run_task()` helper, `[NEEDS INFO]` detection
  - Uses `is_handoff_for(message.content, "DEV")`
  - Shell IDs: currently dev-agent28

- `~/devteam/agents/oracle.py`
  - Oracle orchestrator — now runs locally
  - `_process_task()` helper, clarification loop (5 rounds), smart routing, `handoff()` call
  - `check_resume()` BEFORE channel filter (critical for context preservation)
  - Shell IDs: currently oracle-local11

- `~/devteam/.env`
  - All secrets: 7 Discord bot tokens, channel IDs, AZDO_PAT, JIRA_API_TOKEN, JIRA_EMAIL, JIRA_BASE_URL, LITELLM_BASE_URL, LITELLM_MODEL
  - Also on Pi at same path

- `~/devteam/startup.sh`
  - Auto-start on Windows logon via Task Scheduler
  - Starts LiteLLM (with gh token injection) + Oracle + Dev

- `C:\Users\rohan\.copilot\session-state\ae0b9b08-b91e-48ca-927c-f91cda05b514\plan.md`
  - Full architecture plan including task decomposition design, agent communication model, ADO integration decisions
</important_files>

<next_steps>
**Immediate — finish current test:**
1. Monitor dev-agent28 — check if Test 1 ("hello world to /tmp/hello.py") completes successfully and file is written
2. Check `/tmp/hello.py` exists in WSL2 after Dev reports done
3. Post Test 2 (ambiguous: "create a new project") — verify Oracle clarification loop works end-to-end

**After tests pass — implement task decomposition (in order):**
1. `oracle-decompose` — LLM prompt outputs JSON subtask list, Oracle posts breakdown, waits for ✅
2. `oracle-ado-epic` — Create "AgentTasks" ADO project + Epic + Tasks via REST API
3. `oracle-ado-update` — Update task status (To Do→Active→Done) throughout lifecycle
4. `oracle-sequential-chain` — Listen for `[TASK COMPLETE <ADO_ID>]`, chain next subtask
5. `oracle-approval-gate` — ✅ gate for critical tasks, no timeout
6. `agent-complete-signal` — Shared helper in agents_base, all agents post TASK COMPLETE
7. `agent-thread-listen` — Agents respond to @mentions in task threads
8. `agent-thread-post` — Agents post updates to task thread URL from handoff

**After task decomposition works:**
- Build remaining 5 agents: Priya, Arjun, Quinn, Dex, Lex
- Apply `AGENT_BASE_INSTRUCTIONS` pattern (shared operating principles)
- Transfer Oracle back to Pi once stable
- Test Task Scheduler startup on actual reboot
- Add personal GitHub account: `gh auth login` on laptop
</next_steps>