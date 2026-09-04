# LeakGuard: End-to-End System Architecture, Flow & Implementation Blueprint

---

## 1. Executive Summary & System Mission

**LeakGuard** is an enterprise-grade static analysis engine designed to detect unclosed Python resource handles (file streams, database connections, sockets, HTTP client sessions, subprocesses, and locks) across complex control flow paths. 

The system operates across a **unified 4-layer ecosystem**:
1. **AST Static Analysis Engine**: Evaluates Python Abstract Syntax Trees (AST) and constructs Control Flow Graphs (CFG) to track resource acquisition vs. release across all execution branches.
2. **Git Pre-Push Automation**: A one-time setup (`leakguard init`) that installs `.git/hooks/pre-push` to automatically run local scans on `git push`, log reports to `.leakguard/reports/`, and block pushes containing unhandled leaks.
3. **VS Code Live Extension**: Provides real-time squiggly line diagnostics, hover tooltips, and status bar updates (`LeakGuard: Clean` / `LeakGuard: X Leaks`) upon document save (`onDidSaveTextDocument`).
4. **SaaS Control Plane & Admin Portal**: Powered by a **PostgreSQL** database backend, FastAPI REST API, **Google OAuth 2.0 / JWT Authentication**, and a Next.js 14 Web Dashboard featuring an **Admin Panel** for organization-wide visibility.

---

## 2. Complete End-to-End System Flow

```
[ Developer Code ] ──> [ VS Code Extension Live Scan ] ──> Inline Diagnostics & Quick Fixes
       │
       ├──> [ Git Push ] ──> [ Git Pre-Push Hook ] ──> Generates .leakguard/reports/
       │                                         ──> Blocks Push if Definite Leaks Exist
       │
       └──> [ CLI Sync / Ingest ] ──> [ FastAPI SaaS Server ] ──> [ PostgreSQL Database ]
                                                                       │
                                                                       ▼
                                                          [ Next.js Admin Dashboard ]
```

### Step 1: AST Analysis & Control Flow Graph (CFG)
- **Acquisition Tracking**: When `open()`, `sqlite3.connect()`, `socket.socket()`, or `create_engine()` is called, LeakGuard assigns a unique `ResourceSymbol` tracking line number, variable alias, and acquisition method.
- **CFG Execution Path Evaluation**: Evaluates return statements, exception branches (`try/except/finally`), and early returns.
- **Classification**:
  - `DEFINITE_LEAK`: Resource acquired but never closed along the normal execution path.
  - `POTENTIAL_LEAK`: Resource closed on some branches but left open on others, or bypassable by an unhandled exception without a `finally` block or `with` context manager.
  - `CLEAN`: Resource enclosed in a `with` context manager or explicitly closed on all exit paths.

### Step 2: Codebase Initialization & Pre-Push Hook (`leakguard init`)
- Running `leakguard init .` performs a **one-time setup**:
  - Creates `.leakguard.yml` project configuration.
  - Creates `.leakguard/reports/` for storing scan logs.
  - Adds `.leakguard/reports/` to `.gitignore`.
  - Installs `.git/hooks/pre-push` shell script.
- On `git push`, the hook automatically runs `python -m leakguard scan . --format json --out .leakguard/reports/latest_scan.json`. If leaks violate threshold (`--fail-on error`), `git push` exits with code 1 and aborts the push.

### Step 3: VS Code Extension Live Diagnostics
- Extension registers `onDidSaveTextDocument` and `onDidChangeActiveTextEditor`.
- Invokes `python -m leakguard scan <file> --format json --quiet`.
- Populates VS Code `DiagnosticCollection` with red/yellow squiggly underlines.
- Updates VS Code Status Bar with `$(shield) LeakGuard: Clean` or `$(warning) LeakGuard: X Leaks`.

### Step 4: SaaS Backend, PostgreSQL & Google OAuth
- **Database**: PostgreSQL engine configured via SQLAlchemy (`DATABASE_URL="postgresql://postgres:postgres@localhost:5432/leakguard_db"`).
- **Authentication**: Supports standard email/password JWT login (`/auth/login`) and **Google OAuth 2.0** (`/auth/google`).
- **Admin Control Plane**: `/admin/stats`, `/admin/users`, `/admin/scans` return system-wide tenant statistics, registered user accounts, and scan audit logs.

---

## 3. Architecture & Topology Diagrams

### 3.1 System Component Topology Diagram

```mermaid
flowchart TD
    subgraph Developer Workspace
        A[Python Source Code] --> B[LeakGuard AST Scanner]
        B --> C[VS Code Extension]
        B --> D[Git Pre-Push Hook]
        D --> E[.leakguard/reports/latest_scan.json]
    end

    subgraph SaaS Control Plane Backend
        B -->|Auto Sync / CLI Upload| F[FastAPI REST API Server]
        F --> G[JWT & Google OAuth Router]
        F --> H[Admin & Stats Router]
        F --> I[Scans & Findings Ingester]
        I --> J[(PostgreSQL Database)]
        G --> J
        H --> J
    end

    subgraph Web Portal & Admin Dashboard
        K[Next.js 14 Frontend] -->|Auth Token| F
        K --> L[Login / Register Page]
        K --> M[Google OAuth Button]
        K --> N[Global Admin Panel]
        K --> O[Organization Overview]
    end
```

### 3.2 Git Pre-Push Guardrail Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Developer
    participant Git as Git Client
    participant Hook as pre-push Hook
    participant Scanner as LeakGuard AST Scanner
    participant Report as .leakguard/reports/
    participant Backend as SaaS Control Plane

    Developer->>Git: git push origin main
    Git->>Hook: Trigger .git/hooks/pre-push
    Hook->>Scanner: python -m leakguard scan . --format json
    Scanner->>Report: Write latest_scan.json & scan_timestamp.log
    alt Definite Leaks Detected
        Scanner-->>Hook: Exit Code 1 (Policy Violation)
        Hook-->>Git: Abort Push (Exit 1)
        Git-->>Developer: [X] Push Blocked: Resource Leaks Found
    else Zero Leaks
        Scanner->>Backend: Auto-sync findings (if credentials present)
        Scanner-->>Hook: Exit Code 0 (Passed)
        Hook-->>Git: Proceed Push (Exit 0)
        Git-->>Developer: [OK] Push Successful!
    end
```

### 3.3 Database ERD Schema (PostgreSQL Model)

```mermaid
erDiagram
    users ||--o{ user_org_roles : belongs_to
    organizations ||--o{ user_org_roles : contains
    organizations ||--o{ repositories : owns
    organizations ||--o{ scans : executes
    repositories ||--o{ scans : target
    scans ||--o{ findings : produces
    organizations ||--o{ audit_events : logs

    users {
        string id PK
        string email UK
        string hashed_password
        string full_name
        boolean is_active
        datetime created_at
    }

    organizations {
        string id PK
        string name
        string slug UK
        datetime created_at
    }

    user_org_roles {
        string id PK
        string user_id FK
        string org_id FK
        string role
    }

    repositories {
        string id PK
        string org_id FK
        string name
        string default_branch
    }

    scans {
        string id PK
        string org_id FK
        string repo_id FK
        string commit_sha
        string branch
        int total_findings
        boolean policy_passed
    }

    findings {
        string id PK
        string scan_id FK
        string rule_id
        string file_path
        int line_number
        string severity
        string classification
        string status
    }
```

---

## 4. AI Prompt Engineering & Construction Guide

Below are the exact master prompts used to construct each subsystem of LeakGuard.

### 4.1 Prompt 1: AST Analysis Engine
```text
Build a Python AST static analysis engine that parses Python source code, constructs a Control Flow Graph (CFG), and tracks resource handle acquisitions (open, socket.socket, sqlite3.connect, create_engine, Popen). Analyze all execution exit branches to classify findings into DEFINITE_LEAK, POTENTIAL_LEAK, or CLEAN based on context manager ('with') usage or explicit release calls.
```

### 4.2 Prompt 2: Pre-Push Git Automation (`leakguard init`)
```text
Create a 'leakguard init' CLI command that sets up codebase configuration (.leakguard.yml), creates a local report directory (.leakguard/reports/), updates .gitignore, and installs a executable .git/hooks/pre-push script. The hook must run static scans on 'git push', save JSON/log reports locally, and block push (exit 1) if definite resource leaks are detected.
```

### 4.3 Prompt 3: VS Code Extension Live Diagnostics
```text
Create a VS Code extension in TypeScript that registers document save handlers (onDidSaveTextDocument) for Python files. Execute the Python scanner via CLI, parse JSON diagnostics, set VS Code DiagnosticCollection squiggly lines on resource leak locations, and update a Status Bar item with 'LeakGuard: Clean' or 'LeakGuard: X Leaks'.
```

### 4.4 Prompt 4: SaaS FastAPI Backend with PostgreSQL & Google OAuth
```text
Build a multi-tenant FastAPI SaaS Control Plane backed by a PostgreSQL database using SQLAlchemy models. Implement JWT authentication, Google OAuth 2.0 endpoint (/api/v1/auth/google), auto-seeding default admin account (admin@leakguard.io / Admin123!), and an Admin Control Plane router (/api/v1/admin/stats, /users, /scans) returning system-wide analytics.
```

### 4.5 Prompt 5: Next.js 14 Admin Dashboard & Portal
```text
Build a modern Next.js 14 dark-mode Web Dashboard with glassmorphism design. Implement /login with Google Sign-In and Email form, /register with Google Sign-Up, and an /admin page featuring system metric cards (Total Users, Orgs, Scans, Leaks), registered users data table, and system-wide scan logs.
```

---

## 5. Full Technology Stack & Dependencies

### Core & Static Analysis Engine
- **Language**: Python 3.12+
- **Parser**: Standard Library `ast`, `dis`
- **CLI Framework**: Typer, Rich (Terminal formatting & Progress bars)
- **Export Formats**: SARIF 2.1.0, JSON, Text

### Pre-Push & Git Integration
- **Git Hooks**: Shell script (`.git/hooks/pre-push`, `.git/hooks/pre-commit`)
- **Config**: PyYAML (`.leakguard.yml`)

### VS Code Extension
- **Language**: TypeScript 5.5
- **API**: VS Code Extension API `^1.80.0`
- **Packaging**: `@vscode/vsce`

### SaaS Control Plane Backend
- **Framework**: FastAPI 0.111+
- **Database**: PostgreSQL 15+ / SQLAlchemy ORM 2.0+
- **Driver**: `psycopg2-binary`
- **Auth**: Passlib (Bcrypt), PyJWT, Google OAuth 2.0
- **Validation**: Pydantic v2

### Web Dashboard & Admin Portal
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS, Glassmorphism CSS utilities
- **Icons**: Lucide React
- **HTTP Client**: Native Fetch API (`ApiClient` wrapper with localStorage token state)
