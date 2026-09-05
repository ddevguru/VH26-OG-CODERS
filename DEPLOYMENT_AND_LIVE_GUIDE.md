# 🚀 LeakGuard Complete Production Deployment & Live Distribution Guide

---

## 📌 Executive Summary

This guide details how to **deploy LeakGuard to production** and **publish its extensions & packages** live for public users across 4 key distribution channels:

1. 🌐 **Live SaaS Web Platform & API**: FastAPI Control Plane + Next.js Web Dashboard (Docker / Vercel / Render).
2. 📦 **PyPI Public Package (`pip install leakguard`)**: Python Package Index distribution.
3. 🔌 **VS Code Extension Marketplace (`extensions/vscode/`)**: Official VS Code Linter extension.
4. 🤖 **GitHub Action Marketplace (`integrations/github_action/`)**: CI/CD security scan workflow action.

---

## 🌐 1. Live SaaS Cloud Deployment (FastAPI + Next.js)

### A. 1-Command Production Launch via Docker Compose
To run the full commercial production stack locally or on a cloud VPS (AWS EC2, DigitalOcean, Hetzner):

```bash
# Set your environment secrets
export GITHUB_WEBHOOK_SECRET="your_secure_webhook_secret"
export GITHUB_TOKEN="ghp_your_github_token"
export OPENAI_API_KEY="sk-your_openai_api_key"

# Build and start all production services in background
docker-compose -f docker-compose.prod.yml up --build -d
```
- **Backend API**: `http://localhost:8000`
- **Web Dashboard**: `http://localhost:3000`

---

### B. Deploying Backend to Render / Railway / AWS

1. Push your repository to GitHub.
2. Go to [Render](https://render.com) or [Railway](https://railway.app).
3. Create a **New Web Service** pointing to `VH26-OG-CODERS`.
4. Set Build Command: `pip install -e .`
5. Set Start Command: `python -m leakguard server --host 0.0.0.0 --port 8000`
6. Add Environment Variables:
   - `LEAKGUARD_ENV` = `production`
   - `GITHUB_WEBHOOK_SECRET` = `<your_secret>`
   - `GITHUB_TOKEN` = `<your_github_pat>`
   - `OPENAI_API_KEY` = `<your_openai_key>`

---

### C. Deploying Next.js Web Dashboard to Vercel

1. Go to [Vercel](https://vercel.com) and click **Add New Project**.
2. Select repository `ddevguru/VH26-OG-CODERS`.
3. Set **Root Directory**: `presentation/dashboard`
4. Set Environment Variable:
   - `NEXT_PUBLIC_API_URL` = `https://<your-render-api-url>.onrender.com`
5. Click **Deploy**!

---

## 📦 2. Publishing PyPI Package (`pip install leakguard`)

To make LeakGuard installable by Python developers worldwide:

```bash
# 1. Install build tool & twine
pip install build twine

# 2. Build Python wheel and source distribution
python -m build

# 3. Upload to PyPI (requires PyPI account & token)
twine upload dist/*
```

Once uploaded, anyone can install LeakGuard in 1 command:
```bash
pip install leakguard
```

---

## 🔌 3. Publishing VS Code Extension (`extensions/vscode/`)

The VS Code Extension allows developers to see live squiggly underlines and hear voice alerts directly inside VS Code:

```bash
# 1. Navigate to extension directory
cd extensions/vscode

# 2. Install VS Code Extension packaging tool
npm install -g @vscode/vsce

# 3. Create .vsix package
vsce package
```
This creates `leakguard-vscode-1.0.0.vsix`.

### To publish live on VS Code Marketplace:
1. Create a publisher account at [VS Code Marketplace Management](https://marketplace.visualstudio.com/manage).
2. Run:
   ```bash
   vsce publish
   ```
3. Now all VS Code users can search **"LeakGuard"** in VS Code Extensions and click Install!

---

## 🤖 4. Publishing GitHub Action Marketplace (`integrations/github_action/`)

To publish LeakGuard as a reusable GitHub Action:

```bash
# 1. Tag release version
git tag -a v1.0.0 -m "LeakGuard GitHub Action v1 Release"
git push origin v1.0.0
```

2. Go to your GitHub repository -> **Releases -> Draft a new release**.
3. Check the box **"Publish this Action to the GitHub Marketplace"**.
4. Now any GitHub repository can include LeakGuard in their workflow:

```yaml
- uses: ddevguru/VH26-OG-CODERS@v1.0.0
  with:
    fail_on: error
```

---

## ✅ Deployment Checklist

| Target | Channel | Command / Link | Status |
| :--- | :--- | :--- | :--- |
| **Backend API** | Render / Railway / Docker | `docker-compose -f docker-compose.prod.yml up` | 🟢 Ready |
| **Web Dashboard** | Vercel / Netlify | `presentation/dashboard` | 🟢 Ready |
| **PyPI Package** | PyPI | `pip install leakguard` | 🟢 Build Ready (`python -m build`) |
| **VS Code Extension** | VS Code Marketplace | `extensions/vscode/` (`vsce package`) | 🟢 Build Ready |
| **GitHub Action** | GitHub Marketplace | `integrations/github_action/action.yml` | 🟢 Release Ready |
