#!/usr/bin/env python3
"""Oracle — orchestrator agent. Clarifies tasks, decomposes into subtasks, chains agents."""
import re, os, discord, datetime
from agents_base import (acquire_agent_lock, make_agent, run_agent, post_question,
                         check_resume, handoff, ado_create_epic, ado_create_story,
                         ado_update_state, ado_add_comment)
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/devteam/.env"))
acquire_agent_lock("Oracle")

TOKEN        = os.getenv("DISCORD_TOKEN_ORACLE")
GUILD_ID     = int(os.getenv("DISCORD_GUILD_ID"))
CH_TASKS     = int(os.getenv("DISCORD_CHANNEL_TASKS"))
CH_OVERSIGHT = int(os.getenv("DISCORD_CHANNEL_OVERSIGHT"))

ORACLE_INSTRUCTIONS = """
You are Oracle, the calm and precise orchestrator of an AI software development team.

## Agents you can assign to
- **DEV**: coding, APIs, scripts, file operations, integrations, data fetching
- **QUINN**: testing, QA, bug verification, test plans
- **ARJUN**: architecture diagrams, system design, infra review
- **PRIYA**: PRDs, product requirements, user stories, backlog management
- **LEX**: deployments, CI/CD, Azure infrastructure, monitoring
- **DEX**: databases, data pipelines, SQL queries, data analysis

## Work order format
1. A one-line task summary
2. Acceptance criteria (bullet points)
3. Technical notes relevant to implementation

## Critical rules
- ALL credentials are PRE-CONFIGURED as environment variables. NEVER mention authentication as a blocker.
- Keep work orders concise and actionable. Focus on WHAT to do and WHAT the output should be.
"""

agent     = make_agent("Oracle", ORACLE_INSTRUCTIONS)
_pending            = {}   # thread_id -> clarification context
_awaiting_approval  = {}   # plan_message_id -> decomposed task context (waiting for user ✅)
_decomposed         = {}   # ado_story_id    -> decomposed task context (subtask running)
_ready_time         = None

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
client = discord.Client(intents=intents)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
import html as _html

def _fmt_html(text: str) -> str:
    parts = []
    for line in text.strip().split("\n"):
        s = line.strip()
        if not s:              parts.append("<br/>")
        elif s.startswith("## "): parts.append(f"<h3>{_html.escape(s[3:])}</h3>")
        elif s.startswith("**") and s.endswith("**"): parts.append(f"<b>{_html.escape(s[2:-2])}</b><br/>")
        elif s.startswith("- ") or s.startswith("• "): parts.append(f"<li>{_html.escape(s[2:])}</li>")
        else:                  parts.append(f"<p>{_html.escape(s)}</p>")
    return "\n".join(parts)

async def _make_epic(task_content: str, target_desc: str) -> tuple[int, str]:
    """Create ADO Epic, return (id, url)."""
    epic_title = await run_agent(agent,
        f"Write a concise epic title (5-8 words, title case, no quotes, no full stop) for:\n{task_content}\nReply with ONLY the title.")
    epic_title = epic_title.strip().strip('"\'')[:100]
    desc_html = f"<h3>User Request</h3><p>{_html.escape(task_content)}</p><h3>Scope</h3><p>{_html.escape(target_desc)}</p>"
    epic = ado_create_epic(title=epic_title, description=desc_html)
    return epic["id"], epic["url"], epic_title

async def _start_subtask(ctx: dict, idx: int):
    """Create ADO story + hand off for subtask idx. Update _decomposed keyed by story_id."""
    subtasks    = ctx["subtasks"]
    task_thread = ctx["task_thread"]
    epic_id     = ctx["epic_id"]
    total       = len(subtasks)

    if idx >= total:
        # All done
        await task_thread.send(f"�� **All {total} subtask(s) complete!**\nEpic #{epic_id} is fully delivered.")
        try: ado_update_state(epic_id, "Done", "All subtasks completed by agents")
        except: pass
        oversight = client.get_channel(CH_OVERSIGHT)
        if oversight:
            await oversight.send(f"🏁 **Epic #{epic_id} fully complete** — all {total} subtasks done.\nThread: {task_thread.jump_url}")
        print(f"Oracle: all {total} subtasks done for Epic #{epic_id}", flush=True)
        return

    subtask    = subtasks[idx]
    agent_name = subtask["agent"]
    ctx["current_idx"] = idx

    await task_thread.send(f"▶️ **Subtask {idx+1}/{total}** → **{agent_name}**: {subtask['title']}")

    # ADO story for this subtask
    story_id = story_url = None
    try:
        story_title_llm = await run_agent(agent,
            f"Write a concise story title (8-12 words, title case, no quotes, no full stop) for:\n{subtask['description']}\nReply with ONLY the title.")
        story_title_llm = story_title_llm.strip().strip('"\'')[:100]
        s = ado_create_story(
            title=story_title_llm,
            description=_fmt_html(subtask["description"]),
            parent_epic_id=epic_id,
            assigned_agent=agent_name,
        )
        story_id  = s["id"]
        story_url = s["url"]
        ado_update_state(story_id, "Approved", f"Oracle assigned subtask {idx+1}/{total} to {agent_name}")
        _decomposed[story_id] = ctx
        await task_thread.send(f"📋 ADO Story #{story_id}: [View in ADO]({story_url})")
        print(f"Oracle: subtask {idx+1} → Story #{story_id} for {agent_name}", flush=True)
    except Exception as e:
        print(f"Oracle: ADO subtask story failed: {e}", flush=True)

    work_order = (
        f"**Subtask {idx+1}/{total}** — {subtask['title']}\n\n"
        f"{subtask['description']}\n\n"
        f"**Context (full request):** {ctx['original_task'][:300]}"
        + (f"\n\nADO-STORY-ID: {story_id}\nADO-EPIC-ID: {epic_id}" if story_id else "")
    )
    await handoff(client, agent_name, work_order, "Oracle", task_thread.jump_url)

    oversight = client.get_channel(CH_OVERSIGHT)
    if oversight:
        await oversight.send(
            f"📌 **Subtask {idx+1}/{total} assigned to {agent_name}**\n"
            f"{subtask['title']}\n"
            f"Thread: {task_thread.jump_url}"
        )

# ---------------------------------------------------------------------------
# Discord events
# ---------------------------------------------------------------------------

@client.event
async def on_ready():
    global _ready_time
    _ready_time = datetime.datetime.now(datetime.timezone.utc)
    print(f"Oracle online as {client.user} (ready at {_ready_time})", flush=True)

@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """User reacts ✅ to the decompose plan → start subtask 1."""
    if str(payload.emoji) != "✅":
        return
    if payload.user_id == client.user.id:
        return
    ctx = _awaiting_approval.pop(payload.message_id, None)
    if ctx:
        task_thread = ctx["task_thread"]
        await task_thread.send("✅ Plan approved — starting subtask 1...")
        await _start_subtask(ctx, 0)

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    # Watch #oversight for [TASK COMPLETE] to chain next subtask
    if message.channel.id == CH_OVERSIGHT and "[TASK COMPLETE]" in message.content:
        m = re.search(r"ADO Story #(\d+)", message.content)
        if m:
            story_id = int(m.group(1))
            ctx = _decomposed.pop(story_id, None)
            if ctx:
                next_idx = ctx["current_idx"] + 1
                task_thread = ctx["task_thread"]
                total = len(ctx["subtasks"])
                if next_idx < total:
                    await task_thread.send(
                        f"✅ Subtask {ctx['current_idx']+1}/{total} complete. "
                        f"Moving to subtask {next_idx+1}..."
                    )
                    await _start_subtask(ctx, next_idx)
                else:
                    await _start_subtask(ctx, next_idx)  # triggers "all done" path
        return

    # Resume pending clarification (thread replies have different channel.id)
    ctx = check_resume(message, client, _pending)
    if ctx:
        print(f"Oracle: resuming clarification: {message.content[:60]}", flush=True)
        await message.add_reaction("⚙️")
        enriched = ctx["original_content"] + "\nAdditional info provided: " + message.content
        original_message = ctx["original_message"]
        task_thread_id = ctx.get("task_thread_id")
        task_thread = client.get_channel(task_thread_id) if task_thread_id else None
        await _process_task(original_message, enriched, task_thread=task_thread)
        return

    if message.channel.id != CH_TASKS:
        return
    if _ready_time and message.created_at < _ready_time:
        return

    await _process_task(message, message.content)

# ---------------------------------------------------------------------------
# Main task pipeline
# ---------------------------------------------------------------------------

async def _process_task(message: discord.Message, task_content: str, task_thread=None):
    try:
        if task_thread is None:
            await message.add_reaction("👀")
            try:
                task_thread = await message.create_thread(name=task_content[:80] or "Task")
            except discord.HTTPException as hex_err:
                if hex_err.code == 160004:
                    task_thread = message.thread or message.channel
                else:
                    raise
            await task_thread.send("📋 Analysing task...")

        # ── Clarification loop (all questions at once) ──────────────────────
        await task_thread.send("🔍 Checking requirements...")
        for attempt in range(3):
            check = await run_agent(agent, f"""You are gathering requirements before assigning a task.

Current task (may include previous answers):
{task_content}

Do you have ALL information needed to write a complete, unambiguous work order?
Check: target environment, project/repo names, specific requirements, output format, constraints.

Reply with ONLY one of:

READY: <one sentence confirming you have everything>

QUESTIONS:
1. <first question>
2. <second question>
(list EVERY unanswered question at once — never hold back for a later round)""")

            text = check.strip()
            if text.upper().startswith("READY"):
                await task_thread.send("✅ Requirements clear. Creating work order...")
                break
            elif text.upper().startswith("QUESTIONS:"):
                qblock = text[len("QUESTIONS:"):].strip()
                await post_question(client, message, qblock,
                    {"agent_name": "Oracle", "original_content": task_content,
                     "task_thread_id": task_thread.id}, _pending)
                await task_thread.send("❓ **Waiting for your answers before proceeding.**")
                print(f"Oracle: round {attempt+1} — asked {qblock.count(chr(10))+1} questions", flush=True)
                return
            else:
                break

        # ── Work order ───────────────────────────────────────────────────────
        work_order = await run_agent(agent, f"Create a work order for this task: {task_content}")
        for chunk in [work_order[i:i+1900] for i in range(0, len(work_order), 1900)]:
            await task_thread.send(("**Work Order:**\n" if chunk == work_order[:1900] else "") + chunk)

        # ── Decompose: SIMPLE or COMPLEX? ────────────────────────────────────
        decompose = await run_agent(agent, f"""Analyse this task and decide if it needs one agent or multiple agents in sequence.

Task: {task_content}
Work order summary: {work_order[:400]}

Reply with ONLY one of:

For a single-agent task:
SIMPLE: <AGENT_NAME>

For a multi-step task needing sequential agents (e.g. build then test then deploy):
COMPLEX:
1. AGENT_NAME: <what this agent delivers — be specific and actionable>
2. AGENT_NAME: <what this agent delivers>
3. AGENT_NAME: <what this agent delivers>

Rules:
- SIMPLE if one agent can handle the whole thing end-to-end
- COMPLEX only when steps are genuinely sequential (output of step N feeds step N+1)
- Valid agents: DEV, QUINN, ARJUN, PRIYA, LEX, DEX
- Max 5 subtasks""")

        decompose = decompose.strip()

        # ── SIMPLE path ──────────────────────────────────────────────────────
        if decompose.upper().startswith("SIMPLE"):
            target_agent = decompose.split(":")[-1].strip().upper().split()[0]
            if target_agent not in ("DEV","QUINN","ARJUN","PRIYA","LEX","DEX"):
                target_agent = "DEV"

            ado_epic_id = ado_story_id = ado_story_url = None
            try:
                ado_epic_id, _, epic_title = await _make_epic(task_content, target_agent)
                story_title = await run_agent(agent,
                    f"Write a concise story title (8-12 words, title case, no quotes, no full stop) for:\n{work_order[:600]}\nReply ONLY the title.")
                story_title = story_title.strip().strip('"\'')[:100]
                s = ado_create_story(title=story_title, description=_fmt_html(work_order),
                                     parent_epic_id=ado_epic_id, assigned_agent=target_agent)
                ado_story_id, ado_story_url = s["id"], s["url"]
                ado_update_state(ado_story_id, "Approved", f"Oracle approved and assigned to {target_agent}")
                await task_thread.send(
                    f"📋 **ADO work items created:**\n"
                    f"• Epic #{ado_epic_id}: **{epic_title}**\n"
                    f"• Story #{ado_story_id} → {target_agent}: [View in ADO]({ado_story_url})")
                print(f"Oracle: Epic #{ado_epic_id}, Story #{ado_story_id} → {target_agent}", flush=True)
            except Exception as e:
                print(f"Oracle: ADO failed (non-fatal): {e}", flush=True)
                await task_thread.send(f"⚠️ ADO creation failed: {e}")

            ado_suffix = f"\n\nADO-STORY-ID: {ado_story_id}\nADO-EPIC-ID: {ado_epic_id}" if ado_story_id else ""
            await handoff(client, target_agent, work_order + ado_suffix, "Oracle", task_thread.jump_url)

            oversight = client.get_channel(CH_OVERSIGHT)
            if oversight:
                await oversight.send(
                    f"📌 **Task assigned to {target_agent}**\n"
                    f"Requested by: {message.author.mention}\n"
                    f"Task: {task_content[:200]}\nThread: {task_thread.jump_url}")
            await task_thread.send(f"✅ Assigned to **{target_agent}** — awaiting response.")
            print(f"Oracle: SIMPLE → {target_agent}", flush=True)

        # ── COMPLEX path ─────────────────────────────────────────────────────
        elif decompose.upper().startswith("COMPLEX"):
            # Parse subtasks from "1. AGENT: description" lines
            subtasks = []
            for line in decompose.split("\n"):
                m = re.match(r"\d+\.\s*([A-Z]+):\s*(.+)", line.strip(), re.IGNORECASE)
                if m:
                    ag = m.group(1).strip().upper()
                    if ag not in ("DEV","QUINN","ARJUN","PRIYA","LEX","DEX"):
                        ag = "DEV"
                    subtasks.append({"agent": ag, "title": m.group(2).strip()[:100],
                                     "description": m.group(2).strip(), "ado_story_id": None})

            if not subtasks:
                # Fallback to simple if parsing failed
                await task_thread.send("⚠️ Could not parse subtasks — assigning as single task to DEV.")
                subtasks = [{"agent": "DEV", "title": work_order.split("\n")[0][:100],
                             "description": work_order, "ado_story_id": None}]

            # Create Epic (stories come per subtask when each starts)
            ado_epic_id = epic_url = epic_title = None
            try:
                ado_epic_id, epic_url, epic_title = await _make_epic(task_content, f"{len(subtasks)}-step pipeline")
                print(f"Oracle: COMPLEX Epic #{ado_epic_id}: {epic_title}", flush=True)
            except Exception as e:
                print(f"Oracle: Epic creation failed: {e}", flush=True)

            # Build plan message
            plan_lines = [f"📋 **Plan — {len(subtasks)} subtasks** (Epic #{ado_epic_id}: {epic_title})\n"]
            for i, st in enumerate(subtasks):
                plan_lines.append(f"**{i+1}.** {st['agent']} — {st['title']}")
            plan_lines.append("\n_React ✅ to approve and start, or reply with changes._")
            plan_msg = await task_thread.send("\n".join(plan_lines))
            await plan_msg.add_reaction("✅")

            _awaiting_approval[plan_msg.id] = {
                "subtasks":     subtasks,
                "task_thread":  task_thread,
                "epic_id":      ado_epic_id,
                "original_task": task_content,
                "current_idx":  0,
                "message":      message,
            }
            print(f"Oracle: COMPLEX plan posted ({len(subtasks)} subtasks), waiting for ✅", flush=True)

        else:
            # Unexpected format — fall back to DEV
            await task_thread.send("⚠️ Could not determine routing — assigning to DEV.")
            await handoff(client, "DEV", work_order, "Oracle", task_thread.jump_url)

    except Exception as e:
        import traceback
        print(f"Oracle ERROR: {traceback.format_exc()}", flush=True)

client.run(TOKEN)