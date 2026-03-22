# Deployment Gotchas

Things to check when setting up on a new machine (Pi, laptop, VM).

## 1. Python environment — use pyenv 3.11.9
System `python3` won't have the right packages. Use pyenv:
```bash
pyenv install 3.11.9
pyenv global 3.11.9
pip install openai-agents discord.py python-dotenv litellm requests
```

## 2. Shell MCP — `ALLOW_COMMANDS` must be set
`mcp-shell-server` blocks ALL commands if `ALLOW_COMMANDS` is not set. This is handled automatically in `agents_base.py` `mcp_shell()` which sets a default allow-list. No action needed unless you want to restrict commands.

## 3. Only one agent instance at a time
Each agent uses `acquire_agent_lock()` (fcntl lock file at `/tmp/devteam_<name>.lock`). If an agent crashed without releasing the lock:
```bash
rm -f /tmp/devteam_*.lock
```

## 4. Oracle `check_resume` must run before channel filter
Thread replies have a different channel ID than `#tasks`. `check_resume()` is called at the top of `on_message` before the channel guard — do not move it.

## 5. Oracle clarification — task thread is preserved across rounds
When resuming after a clarification question, `_process_task` receives the original `task_thread` so it continues posting there instead of creating a new thread. The `task_thread_id` is stored in the pending context dict.

## 6. Dev instructions — no text before first tool call
The model will narrate instead of acting if instructions allow it. The `CRITICAL RULES ON TOOL CALLS` block at the top of `DEV_INSTRUCTIONS` enforces tool-first behaviour.

## 7. Old `base.py` vs `agents_base.py`
`agents/base.py` is a legacy file with a hardcoded wrong model name. All agents import from `agents_base.py`. Delete `base.py` on new deployments to avoid confusion.

## 8. `startup.sh` — pyenv must be on PATH
`startup.sh` sets `PYENV_ROOT` and calls `pyenv init`. Make sure pyenv is installed at `~/.pyenv` before running it.

## 9. `.env` file location
All agents load `~/devteam/.env` via `load_dotenv`. Make sure this file exists and has all required vars filled in (see `.env.template`).

## 10. LiteLLM model names
LiteLLM model IDs must match exactly. Check `/v1/models` endpoint:
```bash
curl http://localhost:4000/v1/models | python3 -m json.tool | grep '"id"'
```
The `LITELLM_MODEL` env var in `.env` must match one of these IDs.