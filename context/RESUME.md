# How to Resume This Session With a New Copilot Login

This folder contains the full context of the multi-agent dev team project built in GitHub Copilot CLI.
If you start a new session (new login, new machine), paste this file into your first message to the AI.

---

## What We Built

A multi-agent AI software development team running on:
- **Laptop (WSL2 Ubuntu-20.04):** LiteLLM proxy → GitHub Copilot Enterprise → Claude Sonnet 4.6
- **Discord bots:** Oracle (orchestrator), Dev (senior developer), Quinn (QA/tester)
- **Code repo:** https://github.com/ReddyRohan/devteam

## Working Directory

All agent code lives at: `~/devteam/` (WSL2 path: `/home/rohanreddy/devteam/`)

Key files:
- `agents/agents_base.py` — shared utilities (MCP servers, lock, handoff helpers)
- `agents/oracle.py` — orchestrator bot
- `agents/dev.py` — developer bot
- `agents/quinn.py` — QA/tester bot
- `startup.sh` — starts LiteLLM + all agents
- `.env` — secrets (NOT in git, see `.env.template`)

## Current Status (as of 2026-03-22)

✅ **Working end-to-end:**
- Oracle clarification loop → Dev → Quinn pipeline
- Dev auto-hands off to Quinn after every task
- Quinn runs tests and posts [TASK COMPLETE] to #oversight
- Dev also posts [TASK COMPLETE] to #oversight

🔲 **Next up (see TODOS.md):**
- Oracle task decomposition + ADO integration (Track A)
- More agents: Priya, Arjun, Lex, Dex (Track C)

## How to Start Agents

```bash
cd ~/devteam
bash startup.sh
```

Or individually:
```bash
rm -f /tmp/devteam_*.lock
~/.pyenv/versions/3.11.9/bin/python3 agents/oracle.py >> oracle.log 2>&1 &
~/.pyenv/versions/3.11.9/bin/python3 agents/dev.py   >> dev.log   2>&1 &
~/.pyenv/versions/3.11.9/bin/python3 agents/quinn.py >> quinn.log 2>&1 &
```

Check logs: `tail -f ~/devteam/dev.log`

## Key Technical Decisions

| Decision | Why |
|----------|-----|
| `message.author == client.user` (not `.bot`) | `.bot` blocks agent-to-agent messages |
| `ALLOW_COMMANDS` env var (not `ALLOWED_COMMANDS`) | mcp-shell-server checks for this exact name |
| `check_resume()` runs BEFORE channel filter | Thread replies have different channel.id |
| `list(dict.fromkeys(x))[:10]` not `dict.fromkeys(x)[:10]` | dict can't be sliced |
| LiteLLM `1.63.x` pinned | newer versions break OpenAI Agents SDK Responses API |
| `rm -f /tmp/devteam_*.lock` before restart | stale locks from crashed processes block startup |
| No text before first tool call in agent instructions | model narrates instead of acting otherwise |

## Files in This Folder

| File | Contents |
|------|----------|
| `plan.md` | Full architecture plan + deployment gotchas |
| `TODOS.md` | All tasks — done and pending |
| `001-*.md` through `006-*.md` | Session checkpoint summaries (full history) |
| `CLAUDE.md` | Original project notes |
| `customizations.md` | Agent personality / behaviour customizations |
| `index.md` | Checkpoint index |

## To Resume in a New Copilot Session

1. Open GitHub Copilot CLI in this directory (`C:\Rohan\RaspberryPi`)
2. Say: _"Read devteam-context/RESUME.md and devteam-context/plan.md — I want to continue building the multi-agent dev team"_
3. The AI will read those files and have full context of where we left off

---

*This folder is intentionally committed to the devteam GitHub repo so it survives any machine/login change.*
