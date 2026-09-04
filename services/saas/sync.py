import httpx
from typing import Optional, Dict, Any, List

from core.common.models import ScanResult, Diagnostic


def upload_scan_results(
    scan_result: ScanResult,
    repository_name: str,
    control_plane_url: str,
    api_token: str,
    organization_id: Optional[str] = None,
    commit_sha: str = "HEAD",
    branch: str = "main",
) -> Dict[str, Any]:
    """Transmits local scan metadata (diagnostics, summary statistics) to SaaS control plane.
    
    STRICT SECURITY GUARANTEE: Customer source code is NEVER uploaded. Only structured findings
    (file path, line number, rule id, severity, confidence, fingerprint) are transmitted.
    """
    findings_payload: List[Dict[str, Any]] = []
    for d in scan_result.diagnostics:
        line_num = 1
        if d.location:
            if hasattr(d.location, "start") and hasattr(d.location.start, "line"):
                line_num = d.location.start.line
            elif hasattr(d.location, "start_line"):
                line_num = d.location.start_line

        findings_payload.append({
            "rule_id": d.rule_id,
            "file_path": str(d.file_path),
            "line_number": line_num,
            "severity": str(d.severity),
            "confidence": str(d.confidence),
            "classification": d.classification.value if hasattr(d.classification, "value") else str(d.classification),
            "title": d.message,
            "description": getattr(d, "suggestion", "") or getattr(d, "remediation", ""),
            "fingerprint": getattr(d, "fingerprint", f"{d.rule_id}:{d.file_path}:{line_num}"),
        })

    payload = {
        "repository_name": repository_name,
        "commit_sha": commit_sha,
        "branch": branch,
        "scanned_files_count": scan_result.scanned_files_count,
        "duration_seconds": scan_result.duration_seconds,
        "policy_passed": scan_result.policy_passed,
        "findings": findings_payload,
    }

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    if organization_id:
        headers["X-Organization-ID"] = organization_id

    endpoint = f"{control_plane_url.rstrip('/')}/api/v1/scans"
    
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(endpoint, json=payload, headers=headers)
        resp.raise_for_request()
        return resp.json()
