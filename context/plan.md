# Multi-Agent AI Software Development Team — Plan

---

## Oracle Task Decomposition + ADO Integration

### Problem
Big tasks need to be broken into subtasks. Each subtask should be clear before being assigned. Tasks should run sequentially. Visibility should exist in Azure DevOps Boards so you can track progress like a real project.

### Proposed Architecture

```
User posts task in #tasks
        │
        ▼
Oracle: Decompose into subtasks
  - If task is atomic & clear → assign directly
  - If task is large → split into ordered subtasks (1, 2, 3...)
  - If any subtask is unclear → ask clarifying questions first
        │
        ▼
Oracle: Create ADO work items
  - One Epic per user request
  - One Task per subtask, linked to Epic
  - Tag with assigned agent (Dev, Quinn, Lex, etc.)
  - Status: "To Do" initially
        │
        ▼
Oracle: Hand off subtask 1 to appropriate agent
  - [HANDOFF TO DEV] with ADO task ID + work order
        │
        ▼
Agent completes subtask
  - Updates ADO task status to "Done"
  - Posts [TASK COMPLETE] + ADO task ID to #oversight
        │
        ▼
Oracle receives completion signal
  - For non-critical tasks → auto-proceeds to next subtask
  - For critical tasks (deploy, DB changes) → posts to #oversight for approval
  - If approved (✅ reaction) → hands off next subtask
        │
        ▼
All subtasks done → Oracle posts summary to original task thread
```

### Agent communication model

The task thread (created by Oracle in #tasks) is the **single source of truth** for a task:
- Oracle creates the thread, all subtask updates happen there
- Agents post progress, questions, and results in the thread
- Any agent can @mention another agent in the thread to ask a question or hand off
- Oracle monitors the thread for completion signals

```
#tasks thread (owned by Oracle for this task)
  │
  ├── Oracle: "Breaking into 3 subtasks..."
  ├── Oracle: "Subtask 1 assigned to Dev [ADO#123]"
  ├── Dev: "📋 Plan: 1. Clone repo 2. Implement 3. Test"
  ├── Dev: "❓ @Quinn — can you confirm the test spec for this endpoint?"
  ├── Quinn: "Yes, test for 200 + 400 responses"
  ├── Dev: "✅ Done. Code at PR#45. [TASK COMPLETE ADO#123]"
  ├── Oracle: "✅ Subtask 1 done. Starting Subtask 2 → Quinn"
  ├── Quinn: "Running tests..."
  ├── Quinn: "❌ 2 tests failing. @Dev — line 42 throws null ref"
  ├── Dev: "Fixed in PR#46"
  ├── Quinn: "✅ All tests pass. [TASK COMPLETE ADO#124]"
  └── Oracle: "✅ All subtasks complete. Summary: ..."
```

**Agent-to-agent rules:**
- Agents listen to their own channel for new handoffs (`[HANDOFF TO X]`)
- Agents also listen to ANY thread they're mentioned in (`@Dev`, `@Quinn`)
- Questions go in the task thread, not a new thread
- Completion signal `[TASK COMPLETE <ADO_ID>]` goes to #oversight AND the task thread


- Epic = your original request  
- Tasks = each subtask, with agent assignment, status, and comments
- Full audit trail of who did what and when
- Boards view shows real-time progress

### Approval mechanism
Oracle marks a subtask as "needs approval" by:
- Posting to #oversight with ✅/❌ reaction buttons
- Waiting for your ✅ reaction before proceeding
- Auto-timeout: if no response in X minutes, ping again

### Decisions
- **ADO project**: Create new project "AgentTasks" — all agent-created tickets go here
- **Subtask approval**: Always show breakdown to user and wait for ✅ before starting (can remove later)
- **Critical task approval**: No timeout — Oracle waits indefinitely until you react ✅ or ❌
- **Sequential execution**: One subtask at a time, next only starts after previous completes + approval

### Updated Oracle flow
```
User posts task
  → Oracle gathers all info (clarification loop)
  → Oracle decomposes into ordered subtasks
  → Oracle posts subtask plan to thread: "Here are the subtasks, react ✅ to start"
  → User reacts ✅
  → Oracle creates ADO Epic + Tasks in "AgentTasks" project
  → Oracle hands off Subtask 1 to agent
  → Agent works, posts in thread, completes
  → Agent posts [TASK COMPLETE ADO#X] to thread + #oversight
  → For critical tasks: Oracle posts "Subtask 2 ready — react ✅ to proceed"
  → For non-critical tasks: Oracle auto-proceeds
  → All done → Oracle posts summary, closes Epic
```



1. **`oracle-decompose`** — Oracle LLM prompt: given a task, output a JSON list of ordered subtasks with `{title, agent, description, requires_approval: bool}`
2. **`oracle-ado-epic`** — Oracle creates ADO Epic + Tasks via REST API on task receipt
3. **`oracle-sequential-chain`** — Oracle hands off subtask 1, then listens for `[TASK COMPLETE <ADO_ID>]`, then hands off subtask 2, etc.
4. **`oracle-approval-gate`** — For `requires_approval: true` tasks, Oracle posts to #oversight and waits for ✅ reaction before proceeding
5. **`agent-complete-signal`** — All agents post `[TASK COMPLETE <ADO_ID>]` to #oversight when done + update ADO task status
6. **`oracle-ado-update`** — Oracle updates ADO task status throughout lifecycle (To Do → Active → Done)

### Open questions
- ADO project to create tasks in: likely a dedicated "AgentTasks" project, or reuse existing?
- Approval timeout: how long before Oracle re-pings? (suggest 30 min)
- Should subtask breakdown be shown to you before execution starts, or just proceed?

---

## Dev Agent: Make Dev Work Like Copilot

### Problem
Dev (the LLM agent) and GitHub Copilot CLI use the same underlying model but operate very differently. Copilot is efficient, parallel, surgical, and self-sufficient. Dev is sequential, verbose, and fragile. This plan closes that gap.

### Root Cause Analysis

| Dimension | Copilot CLI | Dev (current) |
|-----------|-------------|---------------|
| **Tool calls** | Parallel — multiple tools in one turn | Sequential — one tool per turn (now fixed with `parallel_tool_calls=True` but model needs prompting) |
| **Bulk data** | Writes a script, runs once | Makes 15+ sequential MCP calls → hits max_turns |
| **Before acting** | Explores/reads first, then plans, then acts | Jumps straight to tool calls |
| **On failure** | Reads error carefully, tries different approach | Reports error or repeats same call |
| **Output** | Concise summary — what changed, where, why | Dumps raw data into Discord |
| **Verification** | Checks result after every action | Assumes it worked |
| **Task decomposition** | Reports intent, breaks into steps | No planning step |
| **Self-sufficiency** | Never asks for things it can find | Asked for credentials (fixed), verbose clarification requests |
| **Communication** | Progress update for long tasks, brief final reply | Single long reply at end |
| **Error recovery** | Up to 3 retries with different strategies | Fails and reports, or retries same way |

### Implementation Plan (priority order)

1. **`dev-instructions-rewrite`** — Full rewrite of `DEV_INSTRUCTIONS` from scratch using Copilot's operating principles. Consolidate all ad-hoc patches into one clean, structured instruction block.

2. **`dev-explore-first`** — Add Phase 1 (Explore) to task approach: read relevant files/context before making changes.

3. **`dev-script-for-bulk`** — Hard rule: >3 sequential data fetches = write a Python script and run it in one shell call.

4. **`dev-parallel-instruct`** — Concrete parallel examples in instructions (already enabled in ModelSettings).

5. **`dev-task-decompose`** — Post a brief numbered plan to Discord before executing long tasks.

6. **`dev-verify-always`** — Verify every output: read_file after write, check exit codes, confirm git pushes.

7. **`dev-error-recovery`** — Structured retry: read error → identify cause → try different approach (not same call).

8. **`dev-concise-comms`** — Output rules: progress updates for long tasks, concise final summary, never dump raw data.

9. **`dev-structured-output`** — Use checkboxes/bullets for multi-step progress reporting.

10. **`dev-az-login-check`** — Verify az CLI auth at startup so Dev never fails mid-task.

---

> Synthesised from: MetaGPT (arXiv:2308.00352), Anthropic "Building Effective Agents", AutoGen, CrewAI, LangGraph, SWE-bench research + Pi 5 capacity assessment.

---

## Problem Statement

Build a self-organising team of AI agents that can receive product requirements (features, epics, user stories) and autonomously work through the full software lifecycle — design → develop → test → deploy — with code stored in GitHub/Azure DevOps, communication over Discord, and a human able to monitor and intervene at any point.

---

## Proposed Approach

**Agent framework:** OpenAI Agents SDK (`openai-agents` Python package) — simple, clean, built-in handoffs and tool use. Runs identically on Pi and laptop.

**LLM abstraction:** LiteLLM on both machines — handles all model switching (Azure, Copilot Claude/GPT, Gemini) with a single config change. Agent code never changes when switching models.

**NanoClaw:** Kept as-is for Chotu (personal assistant — WhatsApp, Telegram, Discord chatbot). Completely separate from dev team agents.

**LLM routing:**
- Pi agents → Pi LiteLLM (port 4000) → Azure OpenAI GPT-4.1 (default), switchable
- Laptop agents → Laptop LiteLLM (port 3002) → GitHub Copilot Enterprise (claude-sonnet-4.6 default), switchable to GPT-5.4, Claude Opus, Gemini
- Fallback: if Pi off → laptop runs all agents via Copilot. If laptop off → Pi runs all via Azure.

**Communication:** Discord — threaded (one thread per task), discord.py bots, emoji reactions for HITL approvals.

**Cleanup pending:** Remove CrewAI venv from Pi (`~/crewai-env`) and laptop at end of session.

---

## Agent Roster (Pi-optimised: 7 core agents)

Research recommends 10–12 agents; we consolidate to 7 to fit Pi 5 8GB constraints (Pi assessment: safe limit = 8–10 concurrent containers at 450 MB each).

| # | Agent | Personality | Always-On? | Context |
|---|---|---|---|---|
| 1 | **Orchestrator** | Calm, methodical, never codes — delegates everything, thinks in workflows | ✅ Yes | 128K |
| 2 | **Product Manager** | Business-focused, user-advocate, asks "why not how", challenges vague requirements | ✅ Yes | 64K |
| 3 | **Solutions Architect** | Pragmatic engineer-turned-designer, obsessed with simplicity, draws diagrams | 🟡 Warm | 64K |
| 4 | **Senior Developer** | Staff-level, writes clean testable code, pushes back on bad designs, self-reflects | 🟡 Warm (1 pre-warmed) | 128K |
| 5 | **QA Engineer** | Sceptical, systematic, tries to break things, never trusts code until tests pass | ⚡ On-demand | 64K |
| 6 | **DevOps Engineer** | Infrastructure-first, "if it's not automated it's a future incident", speaks in YAML | ⚡ On-demand | 32K |
| 7 | **Tech Lead / Code Reviewer** | Merged role: reviews PRs, gates deployments, mentors, owns architectural integrity | ✅ Yes | 64K |

> **Deferred to Phase 2:** Security Reviewer, Technical Writer, Junior Developer sub-agents. These add value but aren't critical for MVP.

---

## Agent Personalities

### 1. Orchestrator — "Oracle"
> Cool-headed. Speaks in bullet points and task IDs. Never emotional. "TASK-042 assigned to @dev-senior. ETA: 2h. Blocking: none."

### 2. Product Manager — "Priya"
> Sharp, business-savvy. Will ask uncomfortable questions. Refuses to proceed on vague requirements. "Before I write this PRD — who is the primary user and what's their pain point?"

### 3. Solutions Architect — "Arjun"
> Calm, big-picture thinker. Loves a good diagram. Pragmatic — "the simplest thing that could possibly work" before adding complexity. Will quote CAP theorem unprompted.

### 4. Senior Developer — "Dev"
> Experienced, direct, slightly sarcastic about bad code. Writes tests before implementation. Self-critiques every output. "This works but it smells — let me refactor before I push."

### 5. QA Engineer — "Quinn"
> Methodical, relentless edge-case finder. Writes test cases like a checklist. Never celebrates until CI is green. "It passed happy path. What about empty input? What about 10k concurrent users?"

### 6. DevOps Engineer — "Dex"
> YAML-brained, automation-obsessed. Considers anything done manually twice to be a bug. Will add a pipeline for everything. "Why are you clicking? That's a job for a workflow."

### 7. Tech Lead / Code Reviewer — "Lex"
> Experienced generalist. Balances pragmatism with quality. Reviews with specific, actionable comments. Guards architectural consistency across PRs.

---

## Discord Server Structure

```
📁 MANAGEMENT
  #requests           ← User submits features, epics, user stories here
  #orchestrator-log   ← Oracle posts task decompositions and routing decisions
  #project-status     ← Daily sprint summaries
  #human-review       ← HITL gate: agents await approval here (✅/❌ reactions)
  #prod-approvals     ← Production deployment approvals only

📁 DEVELOPMENT
  #prd-review         ← Priya posts PRDs; human approves before Arjun proceeds
  #architecture       ← Arjun posts system designs + diagrams
  #code-reviews       ← Lex posts PR reviews
  #qa-reports         ← Quinn posts test results and bug reports

📁 OPERATIONS
  #deployments        ← Dex posts deployment statuses
  #monitoring         ← Azure Monitor alerts land here

📁 AGENT-INTERNAL (hidden from humans or read-only)
  #task-queue         ← Structured JSON task assignments between agents
  #blockers           ← Agents escalate here after 3 failed retries
  #agent-bus          ← Internal pub/sub event stream

📁 LEARNING
  #retrospectives     ← Post-sprint summaries
  #knowledge-base     ← Agents post discovered patterns, anti-patterns, lessons
  #prompt-updates     ← Log of all system prompt changes with rationale
```

**Threading rule:** Every task gets its own Discord thread under the relevant channel. Thread name = `[TASK-ID] Brief description`. All conversation about that task lives in the thread.

---

## Communication Pattern

**Pattern: Event-Driven Pub/Sub (MetaGPT blackboard)**

All inter-agent messages use structured JSON:

```json
{
  "schema_version": "1.0",
  "message_id": "uuid",
  "correlation_id": "EPIC-001",
  "from_agent": "product_manager",
  "to_channel": "architecture",
  "message_type": "HANDOFF",
  "priority": "NORMAL",
  "task_id": "TASK-003",
  "subject": "PRD v1.0 approved — ready for architecture",
  "artifacts": [{ "type": "document", "url": "github.com/.../prd_v1.md" }],
  "requires_human_approval": false,
  "next_expected_actor": "architect"
}
```

**NanoClaw internal bus** handles agent-to-agent routing directly (sub-millisecond). Discord is used for **human visibility + HITL**, not as the primary message transport.

---

## HITL Gates (Human-in-the-Loop)

| Gate | Trigger | Human Action |
|---|---|---|
| G1: PRD Approval | Priya posts PRD | ✅ react to approve, ❌ to reject with comment |
| G2: Architecture Approval | Arjun posts design | Review + react |
| G3: Pre-Production Deploy | Dex ready to push to prod | `/approve deploy TASK-ID` |
| G4: Ambiguity | Any agent in #blockers after 3 retries | Provide clarification in thread |
| G5: Critical Bug | QA finds P0 bug | Human triages severity |

---

## Skills / Tools Per Agent

> **Common to all agents:** `web_search(query)`, `run_python(code)`, `run_command(cmd)` with full stdout/stderr capture for debugging.

### All Agents (baseline)
- Discord send/receive (via NanoClaw channel)
- File read/write in `/workspace/group/`
- Memory read/write (conversations/ folder)
- Web search (via agent-browser or requests)

### Orchestrator (Oracle)
- Azure DevOps API — create/update epics, features, work items
- GitHub API — create issues, milestones
- **Jira API** — create_issue, update_issue, search_issues, assign_issue, transition_status
- Task graph builder (JSON DAG output)
- Status dashboard writer → #project-status
- Agent registry query (what's running, what's queued)

### Product Manager (Priya)
- Web search (competitive analysis, market research)
- Azure DevOps API — create epics and user stories
- **Azure DevOps Boards** — create/update/move work items, manage sprints, query boards
- GitHub API — create issues, milestones
- Structured document output (PRD template)
- HITL trigger (post to #human-review, await reaction)
- Requirements version control (commit PRD to GitHub)

### Solutions Architect (Arjun)
- Mermaid CLI (`mmdc`) — generate architecture diagrams → PNG
- PlantUML — sequence/component diagrams
- File I/O — read/write files, list_directory, scaffold structure
- Git — create repo, push skeleton, create branches
- Azure DevOps — create ADRs as wiki pages
- **az infra read** — `az resource list`, `az group list`, `az network`, `az webapp show`, `az containerapp show`
- **az monitor read** — `az monitor metrics list`, `az monitor activity-log`, Application Insights queries (read-only, for diagram generation)
- Codebase search (grep, AST)

### Senior Developer (Dev)
- File I/O — read_file, write_file, list_directory
- run_command (python/node/bash/pip/npm) with stderr capture
- Git — clone, branch, commit, push, create PR
- **GitHub PR API** — create/read/merge PRs
- **Azure Repos** — clone, push, create PR (`az devops repos`)
- Linter/formatter (ruff, eslint, prettier)
- az deploy — `az webapp deploy`, `az containerapp update`, `az functionapp deploy`, `az acr build`
- **Debug runner** — run code, capture full traceback, suggest fix, retry loop (max 3)
- Self-reflection loop (generate → test → critique → revise, max 3 iterations)

### QA Engineer (Quinn)
- read_file, write_file (test files)
- run_command (pytest, jest, coverage, lint) with full output capture
- Git diff reader (read PR diffs)
- **GitHub** — create_issue (bugs with repro steps), add PR review comments
- **Azure Repos** — read PRs, add review comments
- **Jira** — create_bug, link_to_story, update_status
- **az monitor** — Application Insights queries, Log Analytics workspace queries

### DevOps Engineer (Dex)
- Azure CLI (full access)
- Azure DevOps Pipelines API
- GitHub Actions API
- Docker build and push
- Terraform / Bicep execution
- Azure Key Vault (secrets management)
- Azure Monitor API
- Git (merge to main, tag releases)
- Python azure-mgmt-* packages

### Tech Lead / Code Reviewer (Lex) — DevOps
- run_command (docker build/push, kubectl, helm, terraform, bicep)
- az infra — `az acr`, `az aks`, `az containerapp`, `az webapp`, `az functionapp`
- **az monitor** — activity-log, diagnostic-settings, alert list, `az webapp log tail`, log analytics (error detection)
- GitHub Actions — trigger `workflow_dispatch`, read run status
- read_file, write_file (IaC: Dockerfiles, bicep, terraform, GitHub Actions YAML)
- Git — read configs, tag releases

---

## Context Window Management

**Problem:** Long epics accumulate 100K+ tokens. Exceeds even 128K context and causes cost explosion.

**Strategy: 3-tier memory**

```
TIER 1 — Working Memory (In-context, ~16K tokens)
  Current task brief + last 10 messages + active code section

TIER 2 — Session Memory (Retrieved on demand)
  This sprint's decisions, completed tasks, key findings
  Storage: /workspace/group/conversations/
  Access: Summarised retrieval (2K token summaries)

TIER 3 — Project Knowledge Base (RAG)
  Full codebase, all PRDs, ADRs, test results
  Storage: Vector DB (pgvector or Chroma on Pi NVMe)
  Access: Semantic search, 300-token chunks, hybrid BM25+vector
```

**Summarisation trigger:** Every 40 turns, agent summarises its conversation history into a structured 2K-token summary and stores it. Full history archived to SQLite, working context reset.

**Per-agent context budgets:**
| Agent | Max Context | Notes |
|---|---|---|
| Orchestrator | 128K | Full project state + task graph |
| PM | 64K | Full PRD + requirements |
| Architect | 64K | PRD in + design out |
| Senior Dev | 128K | Code context is large |
| QA | 64K | PRD criteria + code + test results |
| DevOps | 32K | Pipeline config + state |
| Tech Lead | 64K | PR diff + codebase context |

---

## Feedback Loops & Learning

### 1. Per-task: Reflexion Loop (Intra-agent)
Every agent runs: Generate → Test/Validate → Critique → Revise — up to 3 iterations before escalating to #blockers.

### 2. Cross-agent: Knowledge Propagation
When QA or Reviewer finds a recurring pattern, they post to #knowledge-base with schema:
```json
{
  "type": "lesson|pattern|anti-pattern",
  "title": "Always validate nullable fields at service boundary",
  "content": "...",
  "created_by": "qa_engineer",
  "tags": ["validation", "null-safety"],
  "applicable_to": ["developer_senior"]
}
```
Agents retrieve relevant entries at task start via RAG.

### 3. Post-sprint: Retrospective + Prompt Updates
- After each sprint, Oracle aggregates error counts, retry rates, human interventions
- Posts retrospective to #retrospectives
- **Human reviews and approves** proposed system prompt improvements
- Changes committed to GitHub (versioned agent configs)
- Logged to #prompt-updates with rationale

> ⚠️ **Agents NEVER update their own system prompts autonomously.** Always human-supervised.

---

## Software Lifecycle Flow

```
User posts in #requests
         ↓
[Oracle] decomposes → routes to Priya
         ↓
[Priya] creates PRD → posts to #prd-review
         ↓
[HUMAN] reviews + approves PRD ✅
         ↓
[Arjun] creates system design + diagrams → posts to #architecture
         ↓
[HUMAN] reviews architecture ✅ (optional but recommended)
         ↓
[Oracle] creates task breakdown → assigns to Dev via #task-queue threads
         ↓
[Dev] implements → self-tests → pushes PR → notifies #code-reviews
         ↓ (parallel)
[Lex] reviews PR → comments → Dev fixes
[Quinn] writes + runs tests → reports to #qa-reports
         ↓
[Lex] approves PR → merge to main
         ↓
[Dex] runs CI/CD → deploys to staging → posts to #deployments
         ↓
[HUMAN] approves production deployment ✅
         ↓
[Dex] deploys to production
         ↓
[Dev/Lex] updates docs + ADRs → #knowledge-base
         ↓
Post-sprint retrospective → Oracle → #retrospectives
```

---

## Pi 5 Capacity Assessment — Summary

**Verdict: ✅ GO — with 4 hard requirements**

### Hard Requirements (Blockers)
1. **NVMe SSD** — microSD cannot handle the IOPS (needs 5,000+ IOPS; microSD provides 80–120). The system WILL fail on microSD. Recommended: WD Green SN350 500GB or Kingston NV3 (~£15–25 via Pi 5 M.2 HAT+).
2. **Persistent agent containers** — current spawn/kill model must be replaced with always-on registry.
3. **Docker memory limits** — every container must have `--memory=600m` to prevent one agent OOM'ing the Pi.
4. **Active CPU cooling** — Pi 5 will throttle to 1 GHz without it under sustained multi-agent load.

### Resource Budget
| Component | RAM |
|---|---|
| OS + Pi-hole + Unbound + Tailscale | ~435 MB |
| NanoClaw host + SQLite | ~350 MB |
| Docker daemon | ~90 MB |
| **7 agent containers (7 × 450 MB)** | ~3,150 MB |
| **3 existing bots (Telegram/Discord/WhatsApp)** | ~1,100 MB |
| Safety buffer | ~512 MB |
| **TOTAL** | **~5,637 MB of 8,192 MB** ✅ |

### Container Scheduling Rules
```
maxConcurrentContainers: 10         # Hard ceiling
maxConcurrentCodeExecution: 2       # CPU-bound tasks only
containerMemoryLimit: 600m          # Docker --memory flag
containerCpuLimit: 0.8 cores        # Per agent
agentHeapMax: 400m                  # NODE_OPTIONS=--max-old-space-size=400
contextSummariseAt: 40 turns        # Prevent unbounded heap growth
```

### Required Pi Optimisations
```bash
# 4 GB swap on NVMe (not microSD!)
echo "CONF_SWAPSIZE=4096" >> /etc/dphys-swapfile

# Kernel tuning
vm.swappiness=10
vm.overcommit_memory=1

# CPU performance mode
echo performance > /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Docker daemon.json
{ "storage-driver": "overlay2", "log-opts": { "max-size": "10m", "max-file": "3" } }
```

---

## PoC Results (Completed ✅)

| Check | Result |
|---|---|
| GitHub Copilot Enterprise subscription | ✅ Confirmed — Royal Mail org, `copilot_enterprise_seat_multi_quota` |
| Enterprise API endpoint | ✅ `https://api.enterprise.githubcopilot.com` |
| Available models | ✅ `claude-sonnet-4.6`, `claude-opus-4.6`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.3-codex` |
| Direct API call | ✅ `PoC successful` response confirmed |
| LiteLLM proxy → Copilot | ✅ Working with **LiteLLM 1.63.0** |
| OpenAI Agents SDK — Laptop | ✅ `OpenAI Agents SDK working on laptop via Copilot` |
| OpenAI Agents SDK — Pi | ✅ `OpenAI Agents SDK working on Pi via Azure` (port 4000, model `claude-sonnet-4-6`) |
| Anthropic `/v1/messages` format | ✅ LiteLLM translates correctly; NanoClaw-compatible |
| Node.js 22 in WSL2 | ✅ Installed |
| Python 3.11 via pyenv | ✅ Installed |
| GitHub CLI (`gh`) auth | ✅ Authenticated as `rohan-reddy_rmgh` (work account) |

**Critical finding:** LiteLLM 1.82.5 broken — defaults to OpenAI Responses API which Copilot doesn't support for Claude models. **Must use LiteLLM 1.63.0**.

**Working config saved at:** `~/nanoclaw-laptop/litellm/config.yaml`  
**Start script:** `~/nanoclaw-laptop/litellm/start.sh` (auto-injects fresh `gh auth token` on every start)

---

## Phased Implementation

### Phase 1 — MVP (Foundation)
**Agents:** Oracle + Priya + Dev + Quinn + Discord integration  
**Goal:** Handle simple feature requests end-to-end with human supervision  
**Deliverables:**
- [ ] NanoClaw: persistent agent registry (keep containers alive between messages)
- [ ] NanoClaw: agent state serialisation to SQLite (survives restarts)
- [ ] Discord server set up with channel structure above
- [ ] Oracle agent + CLAUDE.md + tools: Azure DevOps, task graph
- [ ] Priya agent + CLAUDE.md + tools: web search, PRD template, HITL trigger
- [ ] Dev agent + CLAUDE.md + tools: code exec, git, linter, test runner
- [ ] Quinn agent + CLAUDE.md + tools: test runner, coverage, bug reporter
- [ ] HITL gate: emoji reaction approval on #human-review
- [ ] NVMe SSD installed (blocker)

### Phase 2 — Full Lifecycle
**Add:** Arjun + Dex + Lex + RAG memory + GitHub/ADO full integration  
**Goal:** Structured design → code → review → deploy pipeline  
**Deliverables:**
- [ ] Arjun agent + Mermaid/PlantUML diagram generation
- [ ] Lex agent + PR review tools + SAST scanning
- [ ] Dex agent + Azure CLI + Pipelines + Key Vault
- [ ] pgvector knowledge base on NVMe
- [ ] Context summarisation (40-turn trigger)
- [ ] Full GitHub/ADO work item automation

### Phase 3 — Learning & Self-Improvement
**Add:** Retrospective loop, knowledge base RAG, prompt versioning  
**Goal:** Agents improve from experience  
**Deliverables:**
- [ ] Post-sprint retrospective automation
- [ ] Knowledge base RAG (agents retrieve lessons at task start)
- [ ] Versioned agent configs in GitHub
- [ ] Human-supervised prompt update workflow
- [ ] Metrics dashboard (error rates, retry counts, task durations)

### Phase 4 — Security + Scale
**Add:** Security Reviewer, Technical Writer, sub-agent spawning  
**Goal:** Production-grade with security scanning and documentation  
**Deliverables:**
- [ ] Security agent with Semgrep, Trivy, gitleaks
- [ ] TechWriter agent for auto-docs
- [ ] Junior Dev sub-agent spawning (PM can spawn 1–2 for parallel tasks)
- [ ] LangSmith or equivalent observability

---

## Key Anti-Patterns to Avoid

1. ❌ Free-form chat between agents — always structured JSON
2. ❌ Agents updating own system prompts — always human-supervised
3. ❌ More than 8 tools per agent — degrades performance
4. ❌ No max retries — always escalate after 3 failures
5. ❌ Running on microSD — NVMe is non-negotiable
6. ❌ No HITL on irreversible actions (deployments, DB migrations)
7. ❌ Dumping entire codebase into context — use RAG

---

## Notes & Decisions

- **LLM routing:**
  - **Pi agents** (Oracle, Priya, Lex): Azure OpenAI GPT-4.1 via existing LiteLLM proxy on Pi (`http://localhost:3001`)
  - **Laptop agents** (Arjun, Dev, Quinn, Dex): GitHub Copilot Enterprise via a separate LiteLLM instance on laptop (WSL2, `http://localhost:3002`). Uses work GitHub PAT for Copilot session tokens.
  - Each NanoClaw instance sets `ANTHROPIC_BASE_URL` to its local LiteLLM — no cross-host LLM calls.

- **Dual GitHub accounts:**
  - `GITHUB_WORK_TOKEN` — work GitHub PAT. Used for: (1) Copilot Enterprise LLM calls, (2) pushing to work org repos
  - `GITHUB_PERSONAL_TOKEN` — personal GitHub PAT. Used for: pushing to personal repos only
  - Agents select the correct token based on repo owner/org at task time: `git -c include.path=~/.gitconfig_work clone ...` vs `~/.gitconfig_personal`
  - Both tokens stored in NanoClaw `.env` on laptop; never sent to Pi or Azure
- **Code execution:** Runs inside the NanoClaw Docker container (already sandboxed). No separate E2B/Modal needed.
- **Agent identity on Discord:** Each agent is a separate Discord bot (separate bot token). They each have their own avatar and colour.
- **Chromium policy:** Never keep Chromium resident in an agent container. Load on demand, kill after use.
- **LATS (tree search):** Defer to Phase 4. Expensive; only valuable for irreversible architecture decisions.


---

## Deployment Gotchas (apply when deploying to Pi or new machine)

These bugs were found during local testing. Must be fixed before deploying any agent to Pi.

### 1. `mcp-shell-server` — `ALLOW_COMMANDS` must be set
- **Bug**: Shell MCP blocks ALL commands if `ALLOW_COMMANDS` env var is not set. Agent silently fails on any shell call.
- **Fix**: `agents_base.py` `mcp_shell()` now sets a default `ALLOW_COMMANDS` list covering python3, bash, git, curl, npm, docker, az, gh, etc.
- **Note**: The env var is `ALLOW_COMMANDS` (not `ALLOWED_COMMANDS`) — server checks both but only errors on the former.

### 2. Multiple agent instances — lock file required
- **Bug**: Re-running startup.sh or manual restarts leave old processes running. All instances pick up the same Discord messages, causing duplicate replies and race conditions.
- **Fix**: `agents_base.py` `acquire_agent_lock(agent_name)` uses `fcntl.flock` to ensure only one instance runs. Add `acquire_agent_lock("Dev")` / `acquire_agent_lock("Oracle")` at startup.
- **Deployment**: Run `rm -f /tmp/devteam_*.lock` before starting agents on a new machine or after a crash.

### 3. Python environment — must use pyenv 3.11.9
- **Bug**: System python3 (`/usr/bin/python3`) does not have `discord`, `openai`, `agents` etc. installed.
- **Fix**: Use `~/.pyenv/versions/3.11.9/bin/python3` explicitly, or ensure pyenv is on PATH before running agents.
- **Pi**: Verify `pyenv` is installed and the correct version is active before deploying.

### 4. Oracle `check_resume` — must run BEFORE channel filter
- **Bug**: Thread replies have a different channel ID than `#tasks`. If channel filter runs first, thread replies are dropped and Oracle loses context between clarification rounds.
- **Fix**: `check_resume()` is called at the top of `on_message`, before the `CH_TASKS` channel guard.

### 5. Oracle clarification — pass `task_thread` on resume
- **Bug**: On resume after clarification, `_process_task` was called with the reply message, causing it to create a new thread each round (losing prior context).
- **Fix**: Context dict stores `task_thread_id`; on resume, the existing thread is recovered via `client.get_channel(task_thread_id)` and passed to `_process_task`.

### 6. Dev instructions — no planning text before tools
- **Bug**: Dev outputs planning text ("I'll tackle this systematically...") as its first response with no tool calls. The SDK treats this as the final output and exits.
- **Fix**: Added `CRITICAL: ALWAYS start your response by calling tools. NEVER output planning text before using tools.` to top of `DEV_INSTRUCTIONS`. Removed "Phase 2 — Plan: post a brief numbered plan first" from instructions.

### 7. Old `base.py` vs `agents_base.py`
- **Bug**: Old `~/devteam/agents/base.py` exists with hardcoded `model="claude-sonnet-4-6"` (wrong model). Any process accidentally using it will get a 400 error from LiteLLM.
- **Fix**: All agents import from `agents_base.py`. Consider deleting `base.py` to avoid confusion.

### 8. `startup.sh` — duplicate log line and missing newline
- **Bug**: `startup.sh` has a duplicated `echo` line at the end (two identical `Dev started` log lines). Minor but worth cleaning.
- **Note**: `startup.sh` also has no newline at end of file — harmless but messy.

