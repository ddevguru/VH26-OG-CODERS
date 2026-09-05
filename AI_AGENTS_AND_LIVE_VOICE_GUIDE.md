# LeakGuard AI Multi-Agent, Live Radar & Voice System Guide

Welcome to the **LeakGuard AI Multi-Agent, Live Radar & Voice System Guide**. This document explains how AI, real-time live telemetry, voice audio alerts, and automated remediation work in LeakGuard.

---

## 1. 🧠 Core Principle: Deterministic AST Engine is Sole Source of Truth

> [!IMPORTANT]
> **Deterministic Guarantee**: AI is **NEVER** allowed to decide whether a resource leak exists. LeakGuard's deterministic Python standard library `ast` and Control Flow Graph (CFG) intra-procedural path analyzer hold **100% authority** over resource leak detection.

### Why this matters:
- **Zero Customer Code Execution**: LeakGuard statically parses AST and dataflow graphs without running target Python source files.
- **No Hallucinated Leaks**: AI does not guess leak rules or generate fake security findings.
- **Isolated 9-Step Verification**: When AI generates a candidate fix patch, the patch is applied in an isolated temporary workspace and **re-analyzed by the deterministic LeakGuard engine**. Only patches that clear the leak with 0 new findings receive the `VERIFIED_FIX` status.

---

## 2. ⚡ Live Developer Experience & Live Radar (`leakguard watch .`)

When developers edit code, LeakGuard monitors file saves in real-time:

```bash
leakguard watch .
```

### Key Features:
- **Debounced Keystroke Protection**: Coalesces rapid saves (default `300ms`) to avoid unnecessary CPU usage.
- **Incomplete Syntax Tolerance**: Gracefully skips partial syntax while typing without crashing.
- **Live Lifecycle Radar**: Renders active open resources, function scope lifetimes, and status shifts (`POTENTIAL` → `DEFINITE` → `SAFE`).
- **Web Dashboard Sync**: Live scan results stream to `http://localhost:3000`.

---

## 3. 🔊 Voice Audio Alerts (Pre-Push Hooks, CLI & Web)

LeakGuard includes a **System Voice Audio Engine** for instant spoken alerts.

### 1. Git Pre-Push Hook & CLI Spoken Alerts
When pushing code or running scans with `--voice`:
```bash
leakguard scan . --voice
leakguard speak "LeakGuard pre-push check passed!"
```
- **If Leaks Detected**: Spoken alert: *"Attention! LeakGuard detected unclosed resource leaks. Git push aborted!"*
- **If Zero Leaks**: Spoken alert: *"LeakGuard static check passed! Zero resource leaks detected."*

### 2. Web Dashboard Voice Agent
- Located in the global Web Dashboard UI header (`presentation/dashboard/src/components/VoiceAgent.tsx`).
- Uses browser native **Web Speech API** (`window.speechSynthesis`).
- Provides a 🔊 **Voice Alerts Active** / 🔇 **Voice Muted** toggle and speaks findings out loud when inspecting issues or running AI agents.

---

## 4. 🤖 The 10 Specialized AI Agents & Web Hub (`/agents`)

LeakGuard features **10 specialized AI agents** operating in a coordinated swarm:

| Agent Name | Key | Role & Capabilities |
| :--- | :--- | :--- |
| **Resource Hunter Agent** | `hunter` | AST variable tracking & lifetime boundary checking |
| **Code Reviewer Agent** | `reviewer` | Senior static security review with architectural advice |
| **Root Cause Agent** | `root_cause` | CFG exception branch unwinding & missing cleanup tracing |
| **Security Impact Agent** | `security` | Resource exhaustion scoring (FD leaks, socket starvation) |
| **Fix Generator Agent** | `fix_generator` | Strategy-pattern patch synthesis (`with`, `try-finally`) |
| **Regression Prevention Agent** | `regression` | Behavioral preservation check & side-effect prevention |
| **Verification Sandbox Agent** | `verification` | 9-step AST sandbox validation & deterministic re-analysis |
| **PR Summary Agent** | `pr_agent` | Pull Request diff security summaries & delta reporting |
| **Documentation Agent** | `documentation` | Markdown remediation guidelines & best-practice patterns |
| **Policy Enforcement Agent** | `policy` | Firewall rule checking (`block`, `warn`, `allow`) |

### How to Access & Run Agents:

#### A. Web Dashboard Hub (`/agents`)
Visit `http://localhost:3000/agents` in your web browser. Click **Run Agent** on any agent card to launch live execution.

#### B. CLI AI Commands
```bash
leakguard review . --mode detailed               # Run multi-agent review
leakguard explain --finding LEAK_001             # Run Hunter, Root Cause & Security agents
leakguard fix --file app.py --finding LEAK_001   # Run Fix Generator strategy engine
leakguard verify --patch candidate.patch        # Run Verification Sandbox agent
```

#### C. Control Plane REST API
```bash
# Catalog endpoint
GET /api/v1/ai/agents

# Run individual agent
POST /api/v1/ai/agents/hunter/run
{
  "file_path": "database.py",
  "source_code": "conn = connect()",
  "line_number": 5
}
```
