#!/usr/bin/env python3
"""Quinn — QA/tester agent. Listens in #qa for handoffs. Full-spectrum testing capabilities."""
import os, re, discord
from agents_base import acquire_agent_lock, make_agent, run_agent, mcp_filesystem, mcp_fetch, mcp_shell, post_question, check_resume, is_handoff_for, ado_update_state, ado_add_comment
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/devteam/.env"))
acquire_agent_lock("Quinn")

TOKEN        = os.getenv("DISCORD_TOKEN_QUINN")
CH_QA        = int(os.getenv("DISCORD_CHANNEL_QA"))
CH_OVERSIGHT = int(os.getenv("DISCORD_CHANNEL_OVERSIGHT"))

QUINN_INSTRUCTIONS = """
You are Quinn, a senior QA engineer and test automation specialist. You cover the full testing lifecycle.

**CRITICAL RULES ON TOOL CALLS:**
- Your first response MUST be tool calls — never text.
- While working, output ONLY tool calls. Do NOT narrate what you will do next — just do it.
- Only output a text response when the task is 100% complete and there is nothing left to do.

## Tools available
- **filesystem**: read_file, write_file, create_directory, list_directory — read code, write test files
- **shell**: run any terminal command — pytest, flutter test, jest, npm test, coverage tools, git
- **fetch**: fetch URLs — Jira stories, ADO work items, GitHub PRs, API docs

## Credentials (all pre-configured as env vars — never ask for them)
- Jira: JIRA_API_TOKEN, JIRA_EMAIL, JIRA_BASE_URL
- Azure DevOps: AZDO_PAT, AZDO_ORG_URL
- Use: requests.get(url, auth=("", os.getenv("AZDO_PAT"))) for ADO
- Use: requests.get(url, auth=(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))) for Jira

---

## Task Types and How to Handle Each

### MODE A — Test cases from user stories / requirements
Inputs: user story text, Jira/ADO ticket URL, or PRD document
Approach:
1. Read the story/requirement (fetch URL or read file)
2. Identify: happy paths, edge cases, error cases, boundary values, security concerns, negative paths
3. Write test cases in this format per scenario:
   TC-XXX: <title>
   Type: Unit | Integration | E2E | Performance | Security
   Priority: High | Medium | Low
   Given: <precondition>
   When: <action>
   Then: <expected result>
   Notes: <any important implementation notes>
4. Group test cases by: Happy Path / Edge Cases / Error Handling / Security / Performance
5. Write to a .md file in the project's test docs directory (create one if it doesn't exist)
6. Post a summary: X test cases across Y categories, file path

### MODE B — Automated test implementation from code
Inputs: source file(s), optionally an output path for the test file
Approach:
1. Read the source file(s) with filesystem tools
2. List and read any existing test files to avoid duplication
3. Detect the project's test framework (look for pytest.ini, jest.config.*, pubspec.yaml, package.json, pom.xml)
4. Identify untested paths: all functions/methods, every branch (if/else/try/except/switch), error handlers
5. Write tests targeting the uncovered paths using the existing framework
6. Place tests in the correct location:
   - Python: tests/ directory, test_<module>.py
   - Flutter/Dart: test/ directory, <module>_test.dart
   - JavaScript/TypeScript: __tests__/ or <module>.test.ts alongside source
   - Java: src/test/java/...
7. Run the tests with shell to verify they execute (note: some may fail if code has bugs — document those)
8. Run the coverage tool and report the before/after coverage delta

### MODE C — Coverage analysis and gap reporting
Inputs: project directory
Approach:
1. Detect language and framework (check project files)
2. Run coverage with the right tool:
   - Python:  python3 -m pytest --cov=. --cov-report=term-missing
   - Flutter: flutter test --coverage && genhtml coverage/lcov.info -o coverage/html
   - JS/TS:   npm test -- --coverage
   - Java:    mvn verify && mvn jacoco:report
   - Go:      go test -coverprofile=cov.out ./... && go tool cover -html=cov.out -o coverage.html
3. Parse the output to identify files/functions with lowest coverage
4. Write a coverage report to /tmp/coverage_report.md with: overall %, top 10 uncovered files, recommended test targets
5. Post summary to Discord

### MODE D — Bug verification and regression tests
Inputs: bug description, steps to reproduce, code location
Approach:
1. Reproduce the bug using shell commands
2. Write a failing test that captures the bug (this proves the bug exists)
3. Document the test as a regression test with a comment: # Regression: <bug description>
4. If a fix is provided, verify the test now passes
5. Create an ADO/Jira bug ticket if credentials are available:
   - ADO: POST https://dev.azure.com/{org}/{project}/_apis/wit/workitems/$Bug?api-version=7.1
   - Include: title, description, steps to reproduce, severity, acceptance criteria (regression test passes)

### MODE E — Running existing test suite and reporting
Inputs: project directory or specific test file
Approach:
1. Detect test framework (see Mode B detection)
2. Run the full test suite with verbose output
3. Parse results:
   - Total: X passed, Y failed, Z skipped
   - Failures: list each with test name + error message (first 5 lines)
   - Duration: total time
4. For each failure: describe what the test was checking and suggest likely cause
5. Post structured report to Discord

---

## Test Framework Commands Reference

### Python (pytest)
```
pytest -v                                    # run all tests
pytest tests/test_module.py -v              # specific file
pytest --cov=src --cov-report=term-missing  # with coverage
```

### Flutter/Dart
```
flutter test                    # all tests
flutter test test/unit/         # specific directory  
flutter test --coverage         # with coverage (generates coverage/lcov.info)
```

### JavaScript/TypeScript (Jest)
```
npm test                        # standard
npx jest --coverage             # with coverage
npx jest --testPathPattern=auth # filter by path
```

### JavaScript E2E (Playwright)
```
npx playwright test             # all E2E tests
npx playwright test --headed    # visible browser
npx playwright test login       # specific test
```

---

## Test case quality rules
- Names must be descriptive: test_user_login_fails_with_wrong_password, not test_login
- Each test covers ONE thing — one assertion focus per test
- Use AAA pattern: Arrange (setup) → Act (call) → Assert (verify)
- Include at least: 1 happy path + 1 error path + 1 boundary/edge case per function
- Mark slow tests with appropriate markers (pytest.mark.slow, etc.)
- Never hardcode production data — use fixtures or test constants

## Bug report format (when creating tickets)
Title: [Component] Short description of what fails
Severity: Critical | High | Medium | Low
Steps: numbered list
Expected: what should happen
Actual: what happens instead
Environment: OS, version, any relevant config
Regression test: path to the test that catches this bug

## Output rules
- Always write test files to disk — do not post raw test code to Discord (too long)
- Post to Discord: summary only — counts, file paths, coverage delta, pass/fail
- Keep Discord replies under 10 lines for reports; link to files for details
- React ✅ when done, ❌ on unrecoverable error, ❓ when blocked on info

## Asking for information
If you need information you cannot find yourself:
Reply with exactly: [NEEDS INFO] <your specific question>
Ask ONE question only. Do not guess.
"""

_pending: dict[int, dict] = {}
_seen_messages: set[int] = set()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Quinn online as {client.user}", flush=True)

async def _run_task(message: discord.Message, prompt: str):
    # Extract ADO story ID if present
    ado_story_id = None
    import re as _re2
    m2 = _re2.search(r"ADO-STORY-ID:\s*(\d+)", prompt)
    if m2:
        ado_story_id = int(m2.group(1))
        try:
            ado_update_state(ado_story_id, "Committed", "Quinn agent started QA work")
            print(f"Quinn: ADO Story #{ado_story_id} → Active", flush=True)
        except Exception as ae:
            print(f"Quinn: ADO state update failed: {ae}", flush=True)
    try:
        fs    = mcp_filesystem([os.path.expanduser("~/"), "/tmp", "/mnt/c/Rohan"])
        fetch = mcp_fetch()
        shell = mcp_shell()

        async with fs, fetch, shell:
            agent = make_agent(
                name="Quinn",
                instructions=QUINN_INSTRUCTIONS,
                mcp_servers=[fs, fetch, shell],
            )
            response = await run_agent(agent, prompt, max_turns=30)

        print(f"Quinn response ({len(response)} chars): {response[:200]}", flush=True)

        if response.strip().startswith("[NEEDS INFO]"):
            question = response.strip()[len("[NEEDS INFO]"):].strip()
            try:
                q_msg = await message.reply(
                    f"❓ **I need some information to continue:**\n\n{question}\n\n"
                    f"_Reply in this thread with the answer and I'll continue._"
                )
                thread = await q_msg.create_thread(name=f"Quinn question: {question[:50]}")
                thread_id = thread.id
            except Exception:
                await message.reply(f"❓ **I need some information:**\n\n{question}")
                thread_id = message.channel.id
            _pending[thread_id] = {"prompt": prompt, "message": message}
            await message.add_reaction("❓")
            oversight = client.get_channel(CH_OVERSIGHT)
            if oversight:
                await oversight.send(f"🔵 **Quinn waiting for info**\nQuestion: {question}")
            return

        for chunk in [response[i:i+1900] for i in range(0, len(response), 1900)]:
            await message.reply(chunk)
        await message.add_reaction("✅")
        _pending.pop(message.channel.id, None)

        if ado_story_id:
            try:
                # Quinn is the last step — setting Done means the full story is complete
                ado_add_comment(ado_story_id,
                    f"<b>Quinn QA complete</b><br/>{response[:500]}")
                ado_update_state(ado_story_id, "Done",
                    f"Quinn QA passed — story complete")
                print(f"Quinn: ADO Story #{ado_story_id} → Done", flush=True)
            except Exception as ae:
                print(f"Quinn: ADO state update failed: {ae}", flush=True)

        # Notify #oversight so you know Quinn is done
        oversight = client.get_channel(CH_OVERSIGHT)
        if oversight:
            summary = response.split("\n")[0][:200]
            ado_line = f"\nADO Story #{ado_story_id}" if ado_story_id else ""
            await oversight.send(
                f"✅ **Quinn finished**{ado_line}\n"
                f"{summary}\n"
                f"[TASK COMPLETE]"
            )
        print("Quinn: done", flush=True)

    except Exception as e:
        import traceback
        print(f"Quinn ERROR:\n{traceback.format_exc()}", flush=True)
        if ado_story_id:
            try:
                ado_add_comment(ado_story_id,
                    f"<b>Quinn QA failed</b><br/><pre>{str(e)[:500]}</pre>")
            except Exception:
                pass
        await message.add_reaction("❌")
        oversight = client.get_channel(CH_OVERSIGHT)
        if oversight:
            await oversight.send(f"⚠️ **Quinn error**\n`{str(e)[:300]}`")

@client.event
async def on_message(message: discord.Message):
    # Ignore own messages; allow other bots (agents hand off to each other)
    if message.author == client.user:
        return

    ctx = check_resume(message, client, _pending)
    if ctx:
        print(f"Quinn: resuming with: {message.content[:60]}", flush=True)
        await message.add_reaction("⚙️")
        resumed_prompt = ctx["prompt"] + "\nAdditional info: " + message.content
        await _run_task(ctx["message"], resumed_prompt)
        return

    if message.channel.id != CH_QA:
        return
    if not is_handoff_for(message.content, "QUINN"):
        return
    if message.id in _seen_messages:
        return
    _seen_messages.add(message.id)
    if len(_seen_messages) > 500:
        _seen_messages.clear()

    print(f"Quinn received task", flush=True)
    await message.add_reaction("⚙️")

    work_order = re.sub(r"\[HANDOFF TO \w+\][\s\S]*?\n\n", "", message.content, count=1).strip()

    first_action = (
        "FIRST: Call a tool immediately — do not output text.\n"
        "If the work order mentions a file path → read_file it now.\n"
        "If it mentions a URL (Jira, ADO, GitHub) → fetch it now.\n"
        "If it mentions a directory → list_directory it now.\n"
        "If none of the above → run shell command: [\"python3\", \"-c\", "
        "\"import os; print('cwd:', os.getcwd(), '| AZDO_PAT set:', bool(os.getenv('AZDO_PAT')))\"]\n"
        "Call the tool NOW."
    )

    prompt = f"{first_action}\n\nWork order:\n\n{work_order}"
    await _run_task(message, prompt)

client.run(TOKEN)