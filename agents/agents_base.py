import os, subprocess, shutil
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, ModelSettings
from agents.mcp import MCPServerStdio

load_dotenv(os.path.expanduser("~/devteam/.env"))
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"

LITELLM_URL   = os.getenv("LITELLM_BASE_URL", "http://localhost:4000/v1")
DEFAULT_MODEL = os.getenv("LITELLM_MODEL", "claude-sonnet-4-5")

JIRA_URL     = os.getenv("JIRA_BASE_URL", "")
JIRA_EMAIL   = os.getenv("JIRA_EMAIL", "")
JIRA_TOKEN   = os.getenv("JIRA_API_TOKEN", "")
AZDO_ORG     = os.getenv("AZDO_ORG_URL", "")
AZDO_PAT     = os.getenv("AZDO_PAT", "")

HOME = os.path.expanduser("~")

def acquire_agent_lock(agent_name: str):
    """Prevent multiple instances of the same agent. Exits if already running."""
    import fcntl, atexit
    lock_file = f"/tmp/devteam_{agent_name.lower()}.lock"
    fh = open(lock_file, "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(f"[LOCK] Another {agent_name} instance is already running. Exiting.", flush=True)
        sys.exit(1)
    fh.write(str(os.getpid()))
    fh.flush()
    atexit.register(lambda: (fcntl.flock(fh, fcntl.LOCK_UN), fh.close()))
    print(f"[LOCK] {agent_name} lock acquired (PID {os.getpid()})", flush=True)



# Build extended PATH that covers pyenv, devteam-env, npm-global
_EXTRA_PATHS = [
    f"{HOME}/.pyenv/shims",
    f"{HOME}/.pyenv/bin",
    f"{HOME}/devteam-env/bin",
    f"{HOME}/.npm-global/bin",
    f"{HOME}/.local/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
]
# Load .env so all credentials are available to shell subprocesses
from dotenv import dotenv_values
_DOTENV = dotenv_values(os.path.expanduser("~/devteam/.env"))
_ENV_WITH_PATH = {**os.environ, **_DOTENV, "PATH": ":".join(_EXTRA_PATHS + [os.environ.get("PATH", "")])}

def _find(cmd):
    """Find binary using extended PATH."""
    for p in _EXTRA_PATHS:
        full = os.path.join(p, cmd)
        if os.path.isfile(full) and os.access(full, os.X_OK):
            return full
    return shutil.which(cmd) or cmd

def _gh_token():
    try:
        return subprocess.check_output([_find("gh"), "auth", "token"], text=True, env=_ENV_WITH_PATH).strip()
    except Exception:
        return os.getenv("GITHUB_TOKEN", "")

def make_client():
    return AsyncOpenAI(base_url=LITELLM_URL, api_key="placeholder")

def make_agent(name, instructions, model=None, mcp_servers=None):
    client = make_client()
    return Agent(
        name=name,
        instructions=instructions,
        model=OpenAIChatCompletionsModel(model=model or DEFAULT_MODEL, openai_client=client),
        mcp_servers=mcp_servers or [],
        model_settings=ModelSettings(parallel_tool_calls=True),
    )

async def run_agent(agent, prompt, max_turns=30):
    result = await Runner.run(agent, prompt, max_turns=max_turns)
    return result.final_output

# --- MCP server factories ---

def mcp_filesystem(allowed_dirs=None):
    dirs = allowed_dirs or [HOME, "/tmp"]
    return MCPServerStdio(client_session_timeout_seconds=60, cache_tools_list=True, 
        name="filesystem",
        params={"command": _find("npx"), "args": ["-y", "@modelcontextprotocol/server-filesystem"] + dirs, "env": _ENV_WITH_PATH},
    )

def mcp_git(repo_path=None):
    return MCPServerStdio(client_session_timeout_seconds=60, cache_tools_list=True, 
        name="git",
        params={"command": _find("uvx"), "args": ["mcp-server-git", "--repository", repo_path or HOME], "env": _ENV_WITH_PATH},
    )

def mcp_github():
    return MCPServerStdio(client_session_timeout_seconds=60, cache_tools_list=True, 
        name="github",
        params={"command": _find("npx"), "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {**_ENV_WITH_PATH, "GITHUB_PERSONAL_ACCESS_TOKEN": _gh_token()}},
    )

def mcp_jira():
    return MCPServerStdio(client_session_timeout_seconds=60, cache_tools_list=True, 
        name="jira",
        params={"command": _find("mcp-atlassian"), "args": [],
                "env": {**_ENV_WITH_PATH, "JIRA_URL": JIRA_URL, "JIRA_USERNAME": JIRA_EMAIL, "JIRA_API_TOKEN": JIRA_TOKEN}},
    )

def mcp_azure_devops():
    org_name = AZDO_ORG.rstrip("/").split("/")[-1]
    return MCPServerStdio(client_session_timeout_seconds=60, cache_tools_list=True, 
        name="azure-devops",
        tool_filter=lambda ctx, tool: tool.name not in ("search_code",),
        params={"command": _find("npx"), "args": ["-y", "@azure-devops/mcp", org_name],
                "env": {**_ENV_WITH_PATH, "AZURE_DEVOPS_EXT_PAT": AZDO_PAT}},
    )


def mcp_shell(allowed_commands=None):
    """Shell execution MCP — lets agents write and run scripts."""
    env = {**_ENV_WITH_PATH}
    default_cmds = [
        "python3","python","bash","sh","git","curl","wget",
        "npm","node","npx","pip","pip3","uv","uvx",
        "ls","cat","echo","mkdir","cp","mv","rm","find","grep","sed","awk",
        "chmod","touch","head","tail","wc","sort","uniq","cut","tr","tee",
        "docker","az","gh","jq","zip","unzip","tar","env","which","pwd",
        "true","false","test","read","export"
    ]
    cmds = allowed_commands if allowed_commands else default_cmds
    env["ALLOW_COMMANDS"] = ",".join(cmds)
    return MCPServerStdio(client_session_timeout_seconds=120, cache_tools_list=True,
        name="shell",
        params={"command": _find("uvx"), "args": ["mcp-shell-server"], "env": env},
    )

def mcp_fetch():
    return MCPServerStdio(client_session_timeout_seconds=60, cache_tools_list=True, 
        name="fetch",
        params={"command": _find("uvx"), "args": ["mcp-server-fetch"], "env": _ENV_WITH_PATH},
    )



# ---------------------------------------------------------------------------
# Handoff helpers — standardised agent-to-agent task passing
# ---------------------------------------------------------------------------
# Standard sentinel format: [HANDOFF TO <AGENT>]
# Each agent listens for its own sentinel in its channel.
#
# Agent → Channel mapping (set in .env):
#   Oracle  → DISCORD_CHANNEL_TASKS
#   Dev     → DISCORD_CHANNEL_DEVELOPMENT (listens for [HANDOFF TO DEV])
#   Quinn   → DISCORD_CHANNEL_QA          (listens for [HANDOFF TO QUINN])
#   Arjun   → DISCORD_CHANNEL_ARCHITECTURE (listens for [HANDOFF TO ARJUN])
#   Priya   → DISCORD_CHANNEL_PRODUCT     (listens for [HANDOFF TO PRIYA])
#   Lex     → DISCORD_CHANNEL_DEVOPS      (listens for [HANDOFF TO LEX])
#   Dex     → DISCORD_CHANNEL_DATA        (listens for [HANDOFF TO DEX])

AGENT_CHANNELS = {
    "DEV":    "DISCORD_CHANNEL_DEVELOPMENT",
    "QUINN":  "DISCORD_CHANNEL_QA",
    "ARJUN":  "DISCORD_CHANNEL_ARCHITECTURE",
    "PRIYA":  "DISCORD_CHANNEL_PRODUCT",
    "LEX":    "DISCORD_CHANNEL_DEVOPS",
    "DEX":    "DISCORD_CHANNEL_DATA",
}

async def handoff(discord_client, to_agent: str, work_order: str, from_agent: str, thread_url: str = ""):
    """
    Hand off a task to another agent by posting to their channel.
    Standardised format so every agent knows exactly what to listen for.
    """
    to_agent = to_agent.upper()
    channel_env = AGENT_CHANNELS.get(to_agent)
    if not channel_env:
        raise ValueError(f"Unknown agent: {to_agent}. Valid agents: {list(AGENT_CHANNELS.keys())}")
    channel_id = int(os.getenv(channel_env, "0"))
    channel = discord_client.get_channel(channel_id)
    if not channel:
        raise ValueError(f"Channel not found for {to_agent} (env: {channel_env}={channel_id})")

    msg = (
        f"**[HANDOFF TO {to_agent}]**\n"
        f"From: {from_agent}\n"
        + (f"Thread: {thread_url}\n" if thread_url else "")
        + f"\n{work_order}"
    )
    # Chunk in case work order is long
    chunks = [msg[i:i+1900] for i in range(0, len(msg), 1900)]
    for chunk in chunks:
        await channel.send(chunk)
    print(f"[Handoff] {from_agent} → {to_agent}", flush=True)

def is_handoff_for(message_content: str, agent_name: str) -> bool:
    """Check if a Discord message is a handoff addressed to this agent."""
    return f"[HANDOFF TO {agent_name.upper()}]" in message_content

# ---------------------------------------------------------------------------
# Shared Q&A / clarification helpers — usable by any agent
# ---------------------------------------------------------------------------
# Each agent maintains its own _pending dict: thread_id -> context dict
# Context dict must have: "prompt", "original_message", plus any agent-specific keys

async def post_question(discord_client, original_message, question: str, context: dict, pending: dict):
    """
    Post a question from an agent, create a thread for the reply.
    Saves context in pending dict keyed by thread ID.
    Any agent or human can reply in that thread to resume.
    """
    try:
        q_reply = await original_message.reply(
            f"❓ **Question:**\n\n{question}\n\n"
            f"_Anyone — reply in this thread to continue._"
        )
        thread = await q_reply.create_thread(name=f"Q: {question[:60]}")
        pending[thread.id] = {**context, "original_message": original_message}
        await original_message.add_reaction("❓")
        oversight_id = int(os.getenv("DISCORD_CHANNEL_OVERSIGHT", "0"))
        oversight = discord_client.get_channel(oversight_id)
        if oversight:
            agent_name = context.get("agent_name", "Agent")
            await oversight.send(
                f"❓ **{agent_name} is waiting for information**\n"
                f"Question: {question}\n"
                f"_Reply in the thread to unblock._"
            )
        print(f"[Q&A] Question posted, waiting for reply in thread {thread.id}", flush=True)
    except Exception as e:
        # Fallback: no thread, key by channel
        print(f"[Q&A] Thread creation failed ({e}), falling back to channel", flush=True)
        await original_message.reply(
            f"❓ **Question:**\n\n{question}\n\n"
            f"_Reply in this channel to continue._"
        )
        pending[original_message.channel.id] = {**context, "original_message": original_message}
        await original_message.add_reaction("❓")

def check_resume(message, discord_client, pending: dict):
    """
    Call this at the top of on_message. Returns context dict if this message
    resumes a pending Q&A, None otherwise. Removes from pending dict on match.
    """
    if message.author == discord_client.user:
        return None
    if message.channel.id in pending:
        return pending.pop(message.channel.id)
    return None

async def notify_error(client, channel_id: int, agent_name: str, task: str, error: Exception):
    """Post error to #oversight with @here so human gets push-notified."""
    import traceback
    tb = traceback.format_exc()
    print(f"{agent_name} ERROR: {tb}", flush=True)
    oversight = client.get_channel(channel_id)
    if oversight:
        await oversight.send(
            f"@here \u26a0\ufe0f **{agent_name} agent failed**\n"
            f"**Task:** {str(task)[:200]}\n"
            f"**Error:** `{str(error)[:300]}`"
        )
