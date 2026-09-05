import re
from pathlib import Path

PATTERNS = {
    "AWS Access Key": r"\bAKIA[0-9A-Z]{16}\b",
    "GitHub Token": r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b",
    "Google API Key": r"\bAIza[0-9A-Za-z\-_]{35}\b",
    "JWT Token": r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
    "Password": r"(?i)\b(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]+['\"]",
    "API Key": r"(?i)\b(api[_-]?key)\s*[:=]\s*['\"][^'\"]+['\"]",
    "Secret Key": r"(?i)\b(secret[_-]?key)\s*[:=]\s*['\"][^'\"]+['\"]",
    "Bearer Token": r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}",
}


def scan_file(file_path):
    findings = []

    try:
        content = Path(file_path).read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return findings

    for line_number, line in enumerate(content.splitlines(), start=1):

        for secret_type, pattern in PATTERNS.items():

            matches = re.finditer(pattern, line)

            for match in matches:
                findings.append({
                    "file": str(file_path),
                    "line": line_number,
                    "type": secret_type,
                    "match": mask_secret(match.group())
                })

    return findings


def mask_secret(secret):
    if len(secret) <= 8:
        return "*" * len(secret)

    return secret[:4] + "*" * (len(secret) - 8) + secret[-4:]


def scan_project(project_path):
    project_path = Path(project_path)

    results = []

    ignored_dirs = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".idea",
        ".vscode"
    }

    for file_path in project_path.rglob("*"):

        if not file_path.is_file():
            continue

        if any(part in ignored_dirs for part in file_path.parts):
            continue

        findings = scan_file(file_path)
        results.extend(findings)

    return results


if __name__ == "__main__":

    project = "."

    results = scan_project(project)

    print("\n========== LEAKGUARD SCAN ==========\n")

    if not results:
        print("✅ No potential secrets found.")
    else:

        print(f"⚠️ Found {len(results)} potential leaks:\n")

        for finding in results:
            print(
                f"[HIGH] "
                f"{finding['type']} | "
                f"{finding['file']}:{finding['line']} | "
                f"{finding['match']}"
            )