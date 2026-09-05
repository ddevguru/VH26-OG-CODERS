# 🛡️ LeakGuard for Visual Studio Code

<p align="center">
  <b>Deterministic AST Static Resource Lifetime Analyzer & CodeRabbit-Style AI Code Security Engine for Python</b>
</p>

---

## 📌 Overview

**LeakGuard VS Code Extension** brings enterprise-grade, offline **static resource leak detection** directly into your editor as you type. 

Never leave unclosed database connections, sockets, files, subprocesses, thread locks, or HTTP sessions. LeakGuard statically parses your Python code using Abstract Syntax Trees (AST) without ever executing customer source files, ensuring **0% false-positive AI hallucinations** on leak detection!

---

## 🌟 Key Features

- 🔴 **Live Error Underlines**: Red squiggly error underlines appear instantly on unclosed resource handles upon saving your `.py` file.
- 💡 **1-Click Lightbulb Quick Fixes**: Click the VS Code lightbulb (`Ctrl+.`) on any leak diagnostic to generate an AI patch verified inside an isolated AST sandbox.
- 🎙️ **Voice Audio Alerts**: System Voice Audio announcements alert you instantly if a leak is introduced (`Ctrl+Alt+L`).
- ⚡ **What-If Exception Simulator**: Simulate stack unwinding and exception paths (`leakguard.whatIf`) to verify cleanup safety.
- 📊 **Commercial Web Dashboard Link**: 1-Click launcher to open your LeakGuard PR Security Portal (`http://localhost:3000`).
- 🛡️ **Footer Status Bar**: Real-time indicator in your VS Code status bar displaying `🟢 LeakGuard: Safe` vs `🔴 LeakGuard: 2 Leaks`.

---

## ⌨️ Keyboard Shortcuts

| Command | Windows / Linux | macOS | Description |
| :--- | :--- | :--- | :--- |
| `LeakGuard: Scan Active File` | `Ctrl + Alt + L` | `Cmd + Alt + L` | Runs immediate static lifetime scan on active Python file. |
| `LeakGuard: Generate Verified Fix` | `Ctrl + Alt + F` | `Cmd + Alt + F` | Generates AI patch and applies verified code fix. |
| `Quick Fix Lightbulb` | `Ctrl + .` | `Cmd + .` | Opens lightbulb menu to apply AST-verified fix. |

---

## ⚙️ Extension Settings

Configure settings in VS Code Preferences (`Ctrl+,` -> search **LeakGuard**):

| Setting | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `leakguard.enableAutoScan` | `boolean` | `true` | Automatically scan Python files on save. |
| `leakguard.voiceAlerts` | `boolean` | `true` | Enable system voice audio alerts on leak detection. |
| `leakguard.serverUrl` | `string` | `http://localhost:8000` | LeakGuard SaaS Control Plane API URL. |
| `leakguard.dashboardUrl` | `string` | `http://localhost:3000` | LeakGuard Commercial Web Dashboard URL. |
| `leakguard.failOn` | `enum` | `error` | Severity threshold (`error`, `warning`, `info`, `none`). |

---

## 🚀 Requirements

- **Python 3.10+** installed on system path.
- **LeakGuard CLI**: `pip install -e .` (or `pip install leakguard`).

---

## 📄 License

Released under the **MIT License**.
Copyright © 2026 LeakGuard Team.
