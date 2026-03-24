#!/usr/bin/env python3
"""Dev — senior developer agent. Runs on laptop. Listens in #development."""
import os, re, discord
from agents_base import acquire_agent_lock, make_agent, run_agent, mcp_filesystem, mcp_fetch, mcp_shell, post_question, check_resume, is_handoff_for, handoff, ado_update_state, ado_add_comment
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/devteam/.env"))
acquire_agent_lock("Dev")

TOKEN        = os.getenv("DISCORD_TOKEN_DEV")
CH_DEV       = int(os.getenv("DISCORD_CHANNEL_DEVELOPMENT"))
CH_OVERSIGHT = int(os.getenv("DISCORD_CHANNEL_OVERSIGHT"))

DEV_INSTRUCTIONS = """
You are Dev, a pragmatic senior software developer. You receive work orders and deliver clean, verified solutions.

**CRITICAL RULES ON TOOL CALLS:**
- Your first response MUST be tool calls — never text.
- While a task is in progress, output ONLY tool calls. Do NOT output text mid-task saying what you will do next — just do it.
- Only output a text response when the task is 100% complete and there is nothing left to do.
- If you have 5 more steps to do, make tool calls for all 5. Do not narrate between them.

**CRITICAL: ANALYSIS IS NOT COMPLETION:**
- If the work order asks you to CREATE, MODIFY, UPDATE, ADD, or IMPLEMENT something — you MUST write the code using write_file or a shell command.
- A response that only DESCRIBES or ANALYZES what should be done is INCOMPLETE.
- Do not finish your task until you can confirm with read_file or shell output that the change exists on disk.
- Your final text reply MUST list: files changed, what was changed, and confirmation (e.g. test output or read_file result).

## Tools available
- **filesystem**: read_file, write_file, create_directory, list_directory
- **shell**: run ANY terminal command — python3, bash, git, docker, npm, pip, curl
- **fetch**: fetch any URL (docs, search results, APIs)

## Credentials (available as env vars in shell)
- Azure DevOps: AZDO_PAT, use `requests.get(url, auth=("", os.getenv("AZDO_PAT")))`
- Jira: JIRA_API_TOKEN, JIRA_EMAIL, JIRA_BASE_URL
- Never ask for credentials — they are pre-configured.

## Asking for information
If you need information you cannot find yourself, ask ONE specific question:
Reply with exactly: [NEEDS INFO] <your specific question>
Do not guess. Do not assume. Ask if genuinely blocked.

## How to approach every task

### Phase 1 — Explore first
Read relevant files, check what exists before changing anything.

### Phase 2 — Execute
**Parallel**: call independent tools simultaneously — never sequentially if they don't depend on each other.
**Script for bulk work**: if task needs >3 data fetches, write a Python script to /tmp/ and run it once via shell. Never make 10+ sequential tool calls to gather data.
**File output**: when task specifies a file path, use write_file. Verify with read_file after.

### Phase 4 — Verify
After every action: check exit codes, read_file after write, confirm results.

### Phase 5 — Report
Concise reply: what was done, files changed, any follow-ups. Never dump raw data into Discord.

## Error handling
On error: read carefully, try a different approach, retry up to 3 times with different strategies.

## Hard rules
- Allowed filesystem paths: /home/rohanreddy, /tmp, /mnt/c/Rohan (= C:\\Rohan on Windows)
- Web search: fetch "https://html.duckduckgo.com/html/?q=query" → extract URLs → fetch the best one
"""

def extract_output_path(text: str) -> str | None:
    match = re.search(r'(/mnt/[^\s,\n]+\.\w+|~/[^\s,\n]+\.\w+|/tmp/[^\s,\n]+\.\w+)', text)
    return match.group(1) if match else None

# Stores pending tasks awaiting user clarification: channel_id -> {prompt, output_path}
_pending: dict[int, dict] = {}
_seen_messages: set[int] = set()  # dedup Discord messages

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Dev online as {client.user}", flush=True)

async def _run_task(message: discord.Message, prompt: str, output_path: str | None):
    """Run a task and handle [NEEDS INFO] by saving state and asking the user."""
    # Extract ADO story ID if present (added by Oracle in handoff)
    ado_story_id = None
    import re as _re
    m = _re.search(r"ADO-STORY-ID:\s*(\d+)", prompt)
    if m:
        ado_story_id = int(m.group(1))
        try:
            ado_update_state(ado_story_id, "Committed", "Dev agent started work")
            print(f"Dev: ADO Story #{ado_story_id} → Active", flush=True)
        except Exception as ae:
            print(f"Dev: ADO state update failed: {ae}", flush=True)
    try:
        fs    = mcp_filesystem([os.path.expanduser("~/"), "/tmp", "/mnt/c/Rohan"])
        fetch = mcp_fetch()
        shell = mcp_shell()

        async with fs, fetch, shell:
            agent = make_agent(
                name="Dev",
                instructions=DEV_INSTRUCTIONS,
                mcp_servers=[fs, fetch, shell],
            )
            response = await run_agent(agent, prompt, max_turns=30)

        print(f"Dev response ({len(response)} chars): {response[:200]}", flush=True)

        if response.strip().startswith("[NEEDS INFO]"):
            question = response.strip()[len("[NEEDS INFO]"):].strip()
            # Create a thread so the reply stays organised
            try:
                q_msg = await message.reply(f"❓ **I need some information to continue:**\n\n{question}\n\n_Reply in this thread with the answer and I\'ll continue._")
                thread = await q_msg.create_thread(name=f"Dev question: {question[:50]}")
                thread_id = thread.id
            except Exception:
                # Fallback: use channel if thread creation fails
                await message.reply(f"❓ **I need some information to continue:**\n\n{question}\n\n_Reply in #development with the answer and I\'ll continue._")
                thread_id = message.channel.id
            _pending[thread_id] = {"prompt": prompt, "output_path": output_path, "message": message}
            await message.add_reaction("❓")
            oversight = client.get_channel(CH_OVERSIGHT)
            if oversight:
                await oversight.send(f"🔵 **Dev waiting for user input**\nQuestion: {question}")
            print("Dev: waiting for user info", flush=True)
            return

        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        for chunk in chunks:
            await message.reply(chunk)
        await message.add_reaction("✅")
        _pending.pop(message.channel.id, None)
        print(f"Dev: done", flush=True)
        if ado_story_id:
            try:
                # Don't set Done yet — Quinn will do that after QA passes
                ado_add_comment(ado_story_id,
                    f"<b>Dev work complete — awaiting QA</b><br/>{response[:500]}")
                print(f"Dev: ADO Story #{ado_story_id} — comment added (awaiting Quinn)", flush=True)
            except Exception as ae:
                print(f"Dev: ADO comment failed: {ae}", flush=True)

        # Auto-handoff to Quinn for testing
        # Extract file paths from response so Quinn knows what to test
        files_mentioned = re.findall(r'[\w./\-]+\.(?:py|dart|ts|js|java|go|cs|rb|swift)', response)
        files_str = "\n".join(f"- {f}" for f in list(dict.fromkeys(files_mentioned))[:10]) if files_mentioned else "- (see Dev summary above)"
        ado_tag = f"\nADO-STORY-ID: {ado_story_id}" if ado_story_id else ""
        quinn_work_order = (
            f"Dev just completed this task and needs test coverage.\n\n"
            f"**Original task:**\n{message.content[:500]}\n\n"
            f"**Dev summary:**\n{response[:600]}\n\n"
            f"**Files to test:**\n{files_str}\n\n"
            f"Please:\n"
            f"1. Read the files Dev created/modified\n"
            f"2. Check for existing tests\n"
            f"3. Write or update automated tests to cover the new code\n"
            f"4. Run the tests and report pass/fail + coverage delta"
            f"{ado_tag}"
        )
        try:
            await handoff(client, "QUINN", quinn_work_order, "Dev")
            print("[Handoff] Dev → QUINN (auto)", flush=True)
        except Exception as he:
            print(f"Dev: Quinn handoff failed: {he}", flush=True)

        # Notify #oversight so you know Dev is done
        oversight = client.get_channel(CH_OVERSIGHT)
        if oversight:
            summary = response.split("\n")[0][:200]
            ado_line = f"\nADO Story #{ado_story_id}" if ado_story_id else ""
            await oversight.send(
                f"✅ **Dev finished**{ado_line}\n"
                f"{summary}\n"
                f"[TASK COMPLETE]"
            )

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"Dev ERROR:\n{tb}", flush=True)
        if ado_story_id:
            try:
                ado_add_comment(ado_story_id,
                    f"<b>Dev failed</b><br/><pre>{str(e)[:500]}</pre>")
            except Exception:
                pass
        await message.add_reaction("❌")
        await message.reply(f"❌ **Dev failed:** `{str(e)[:300]}`")
        oversight = client.get_channel(CH_OVERSIGHT)
        if oversight:
            await oversight.send(f"@here ⚠️ **Dev failed**\n**Error:** `{str(e)[:300]}`")
            for chunk in [tb[i:i+1900] for i in range(0, len(tb), 1900)]:
                await oversight.send(f"```\n{chunk}\n```")

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    # --- Resume if someone replies to a pending question thread ---
    ctx = check_resume(message, client, _pending)
    if ctx:
        print(f"Dev: resuming task with new info", flush=True)
        await message.add_reaction("⚙️")
        resumed_prompt = f"{ctx['prompt']}\n\nAdditional information: {message.content}"
        await _run_task(ctx["original_message"], resumed_prompt, ctx.get("output_path"))
        return

    # --- New task assignment (only in #development main channel) ---
    if message.channel.id != CH_DEV:
        return
    if not is_handoff_for(message.content, "DEV"):
        return

    if message.id in _seen_messages:
        return
    _seen_messages.add(message.id)
    # Trim set to avoid unbounded growth
    if len(_seen_messages) > 500:
        _seen_messages.clear()

    print(f"Dev received task", flush=True)
    await message.add_reaction("⚙️")

    output_path = extract_output_path(message.content)
    question_instructions = (
        "If you need information you cannot find yourself, reply with exactly: "
        "[NEEDS INFO] <your specific question>. Ask ONE question only."
    )

    # Strip handoff header — pass just the work order body to the model
    work_order = re.sub(r"\[HANDOFF TO \w+\][\s\S]*?\n\n", "", message.content, count=1).strip()

    # Concrete first-action forces the model to call a tool immediately
    first_action = (
        "FIRST: Run this shell command NOW before anything else:\n"
        "  command: [\"python3\", \"-c\", \"import os; print({k: bool(v) for k,v in {'AZDO_PAT':os.getenv('AZDO_PAT'),'GH_TOKEN':os.getenv('GH_TOKEN')}.items()})\"]\n"
        "  directory: \"/tmp\"\n"
        "This confirms credentials and unblocks your work. Call the tool — do not output text."
    )

    if output_path:
        prompt = (
            f"OUTPUT FILE: {output_path}\n"
            f"When done, use write_file to save your result there, then verify with read_file.\n"
            f"{question_instructions}\n\n"
            f"{first_action}\n\n"
            f"Work order:\n\n{work_order}"
        )
    else:
        prompt = (
            f"{question_instructions}\n\n"
            f"{first_action}\n\n"
            f"Work order:\n\n{work_order}"
        )

    await _run_task(message, prompt, output_path)

client.run(TOKEN)