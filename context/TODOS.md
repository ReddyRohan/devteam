# Task Backlog — Multi-Agent Dev Team

Last updated: 2026-03-22

## ✅ Done

| ID | Title |
|----|-------|
| agent-tools | Add tools to all agents |
| dev-az-login-check | Dev: Az CLI login verification |
| dev-concise-comms | Dev: Concise Discord communication |
| dev-error-recovery | Dev: Intelligent error recovery |
| dev-explore-first | Dev: Explore before acting |
| dev-instructions-rewrite | Dev: Full instructions rewrite |
| dev-parallel-instruct | Dev: Reinforce parallel tool calls |
| dev-script-for-bulk | Dev: Script for bulk operations |
| dev-structured-output | Dev: Structured Discord output |
| dev-task-decompose | Dev: Task decomposition |
| dev-verify-always | Dev: Verify every output |
| persist-agents | Make agents persistent (systemd/WSL auto-start) |

## 🔲 Pending

### Track A — Oracle: Task Decomposition + ADO
| ID | Title | Description |
|----|-------|-------------|
| oracle-decompose | Oracle: decompose tasks into ordered subtasks | After decomposing subtasks, Oracle posts the full plan to the task thread with numbered list + agent assignment. Posts "React ✅ to start". Waits for ✅ before creating ADO items or handing off. |
| oracle-ado-epic | Oracle: create ADO Epic + Tasks | Create ADO project "AgentTasks" via REST API. One Epic per user request + one Task per subtask linked to Epic, tagged with agent name. Use AZDO_PAT. |
| oracle-approval-gate | Oracle: approval gate for critical tasks | For requires_approval=true tasks, post to #oversight with ✅/❌. NO timeout — wait indefinitely. |
| oracle-sequential-chain | Oracle: sequential subtask chaining | Hand off subtask 1. Listen for [TASK COMPLETE <ADO_ID>] in #oversight. Hand off next. Repeat until all done. Post summary to original thread. |
| oracle-ado-update | Oracle: update ADO task status throughout lifecycle | To Do → Active on handoff. Active → Done on completion. Comment with agent output summary. |
| oracle-thread-monitor | Oracle: monitor task thread for TASK COMPLETE signals | Oracle listens in task threads for [TASK COMPLETE <ADO_ID>]. On receipt, chains to next subtask or closes Epic. |

### Track B — Agent Communication
| ID | Title | Description |
|----|-------|-------------|
| agent-complete-signal | All agents: post TASK COMPLETE signal | Every agent posts [TASK COMPLETE <ADO_ID>] to #oversight when done + updates ADO task to Done. Shared helper in agents_base.py. |
| agent-thread-post | All agents: post updates to task thread | Agents receive thread_url in handoff. They post progress/questions/completion to that thread. |
| agent-thread-listen | All agents: listen for @mentions in task threads | Each agent listens not just to its own channel but also to any thread where it is @mentioned. |

### Track C — More Agents
| ID | Title | Description |
|----|-------|-------------|
| more-agents | Build remaining agents | Build Priya (PM), Arjun (Architect), Lex (DevOps), Dex (Data). Deploy Pi agents to Pi, laptop agents to laptop. Quinn is done ✅. |
| agent-standards | Apply Dev operating principles to all agents | Extract core operating principles into AGENT_BASE_INSTRUCTIONS in agents_base.py. Each agent adds only role-specific behaviour. |

### Track D — Cleanup
| ID | Title |
|----|-------|
| cleanup-crewai | Clean up old CrewAI remnants from Pi and laptop WSL2 |
