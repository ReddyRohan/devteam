#!/usr/bin/env python3
"""Oracle — orchestrator agent. Listens in #tasks, clarifies, creates work orders."""
import asyncio, os, discord, datetime
from agents_base import acquire_agent_lock, make_agent, run_agent, post_question, check_resume, handoff, ado_create_epic, ado_create_story, ado_update_state
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/devteam/.env"))
acquire_agent_lock("Oracle")

TOKEN        = os.getenv("DISCORD_TOKEN_ORACLE")
GUILD_ID     = int(os.getenv("DISCORD_GUILD_ID"))
CH_TASKS     = int(os.getenv("DISCORD_CHANNEL_TASKS"))
CH_OVERSIGHT = int(os.getenv("DISCORD_CHANNEL_OVERSIGHT"))

ORACLE_INSTRUCTIONS = """
You are Oracle, the calm and precise orchestrator of an AI software development team.
Your job is to receive task requests and create clear, actionable work orders for the Dev agent.

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
- ALL credentials (Azure DevOps PAT, GitHub token, Jira token) are PRE-CONFIGURED as environment variables. NEVER mention authentication as a blocker or requirement in work orders.
- Dev has shell access and can call any REST API using Python requests or curl. Credentials are available as env vars (AZDO_PAT, JIRA_API_TOKEN, etc.).
- In Technical Notes: describe API endpoints and data shapes only. NEVER say "PAT must be provided", "authentication required", or mention any specific auth mechanism.
- Keep work orders concise and actionable. Focus on WHAT to do and WHAT the output should be.
"""

agent = make_agent("Oracle", ORACLE_INSTRUCTIONS)
_pending: dict = {}
_ready_time = None

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    global _ready_time
    _ready_time = datetime.datetime.now(datetime.timezone.utc)
    print(f"Oracle online as {client.user} (ready at {_ready_time})", flush=True)

@client.event
async def on_message(message: discord.Message):
    # Ignore own messages; allow other bots (agents hand off to each other)
    if message.author == client.user:
        return

    # Check resume FIRST — thread replies have different channel IDs than #tasks
    ctx = check_resume(message, client, _pending)
    if ctx:
        print(f"Oracle: resuming clarification round: {message.content[:60]}", flush=True)
        await message.add_reaction("⚙️")
        enriched = ctx["original_content"] + "\nAdditional info provided: " + message.content
        original_message = ctx["original_message"]
        # Recover the existing task thread so we keep posting there
        task_thread_id = ctx.get("task_thread_id")
        task_thread = client.get_channel(task_thread_id) if task_thread_id else None
        await _process_task(original_message, enriched, task_thread=task_thread)
        return

    if message.channel.id != CH_TASKS:
        return
    if _ready_time and message.created_at < _ready_time:
        return

    await _process_task(message, message.content)

async def _process_task(message: discord.Message, task_content: str, task_thread=None):
    try:
        # Only create thread + initial reactions for brand-new tasks
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

        # Clarification loop — keep asking until ALL questions are answered
        await task_thread.send("🔍 Checking requirements...")
        for attempt in range(5):
            clarification_check = await run_agent(
                agent,
                f"""You are gathering requirements before assigning a task to a developer.

Current task (may include answers to previous questions):
{task_content}

Do you have ALL the information needed to write a complete, unambiguous work order?
Think carefully — check for: target environment, project/repo names, specific requirements, output format, constraints.

Reply with ONLY one of:
- READY: <one sentence confirming you have everything needed>
- QUESTION: <the single most important missing piece of information>

Be thorough. Do not assign until you are 100% clear."""
            )

            if clarification_check.strip().upper().startswith("READY"):
                await task_thread.send("✅ Requirements clear. Creating work order...")
                break
            elif clarification_check.strip().upper().startswith("QUESTION:"):
                question = clarification_check.strip()[len("QUESTION:"):].strip()
                await post_question(client, message, question,
                    {"agent_name": "Oracle", "original_content": task_content,
                     "task_thread_id": task_thread.id},
                    _pending)
                await task_thread.send(f"❓ **Waiting for answer before proceeding.**")
                print(f"Oracle: round {attempt+1} — asked: {question[:80]}", flush=True)
                return  # resumes via check_resume when anyone replies
            else:
                break  # unexpected format, proceed

        work_order = await run_agent(
            agent,
            f"Create a work order for this task: {task_content}"
        )

        for chunk in [work_order[i:i+1900] for i in range(0, len(work_order), 1900)]:
            await task_thread.send(("**Work Order:**\n" if chunk == work_order[:1900] else "") + chunk)

        routing = await run_agent(
            agent,
            f"""Based on this work order, which agent should handle it?

Work order: {work_order}

Agents: DEV (coding/scripts/APIs), QUINN (testing/QA), ARJUN (architecture),
PRIYA (product/PRDs), LEX (devops/CI/CD), DEX (databases/data)

Reply with ONLY the agent name (e.g. DEV). Pick the single best fit."""
        )
        target_agent = routing.strip().upper().split()[0]
        if target_agent not in ("DEV","QUINN","ARJUN","PRIYA","LEX","DEX"):
            target_agent = "DEV"

        # Generate meaningful ADO names using the LLM
        epic_title = await run_agent(
            agent,
            f"""Write a concise epic title (5-8 words, title case, no quotes, no full stop) that captures the goal of this request:

{task_content}

Reply with ONLY the title."""
        )
        epic_title = epic_title.strip().strip('"').strip("'")[:100]

        story_title = await run_agent(
            agent,
            f"""Write a concise user story title (8-12 words, title case, no quotes, no full stop) for this work order.
Focus on WHAT will be delivered, not who does it:

{work_order[:600]}

Reply with ONLY the title."""
        )
        story_title = story_title.strip().strip('"').strip("'")[:100]

        # Format description as HTML for ADO
        import html as _html
        def _fmt_work_order_html(wo: str) -> str:
            lines = wo.strip().split("\n")
            html_parts = []
            for line in lines:
                s = line.strip()
                if not s:
                    html_parts.append("<br/>")
                elif s.startswith("## "):
                    html_parts.append(f"<h3>{_html.escape(s[3:])}</h3>")
                elif s.startswith("**") and s.endswith("**"):
                    html_parts.append(f"<b>{_html.escape(s[2:-2])}</b><br/>")
                elif s.startswith("- ") or s.startswith("• "):
                    html_parts.append(f"<li>{_html.escape(s[2:])}</li>")
                else:
                    html_parts.append(f"<p>{_html.escape(s)}</p>")
            return "\n".join(html_parts)

        epic_desc_html = (
            f"<h3>User Request</h3><p>{_html.escape(task_content)}</p>"
            f"<h3>Assigned To</h3><p>{target_agent}</p>"
        )
        story_desc_html = _fmt_work_order_html(work_order)

        # Create ADO Epic + User Story
        ado_epic_id = None
        ado_story_id = None
        ado_story_url = None
        try:
            epic = ado_create_epic(title=epic_title, description=epic_desc_html)
            ado_epic_id = epic["id"]
            story = ado_create_story(
                title=story_title,
                description=story_desc_html,
                parent_epic_id=ado_epic_id,
                assigned_agent=target_agent
            )
            ado_story_id = story["id"]
            ado_story_url = story["url"]
            await task_thread.send(
                f"📋 **ADO work items created:**\n"
                f"• Epic #{ado_epic_id}: **{epic_title}**\n"
                f"• Story #{ado_story_id} → {target_agent}: [View in ADO]({ado_story_url})"
            )
            print(f"Oracle: ADO Epic #{ado_epic_id} '{epic_title}', Story #{ado_story_id}", flush=True)
        except Exception as ado_err:
            print(f"Oracle: ADO creation failed (non-fatal): {ado_err}", flush=True)
            await task_thread.send(f"⚠️ ADO creation failed: {ado_err}")

        # Include ADO IDs in the handoff so agents can update state
        ado_suffix = ""
        if ado_story_id:
            ado_suffix = f"\n\nADO-STORY-ID: {ado_story_id}\nADO-EPIC-ID: {ado_epic_id}"
        await handoff(client, target_agent, work_order + ado_suffix, "Oracle", task_thread.jump_url)

        oversight = client.get_channel(CH_OVERSIGHT)
        if oversight:
            await oversight.send(
                f"📌 **New task assigned to {target_agent}**\n"
                f"Requested by: {message.author.mention}\n"
                f"Task: {task_content[:200]}\n"
                f"Thread: {task_thread.jump_url}"
            )

        await task_thread.send(f"✅ Assigned to {target_agent} — awaiting response.")
        print(f"Oracle: assigned to {target_agent}", flush=True)

    except Exception as e:
        import traceback
        print(f"Oracle ERROR: {traceback.format_exc()}", flush=True)

client.run(TOKEN)