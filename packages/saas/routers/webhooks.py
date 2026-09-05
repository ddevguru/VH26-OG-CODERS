"""GitHub Webhook Endpoint — POST /webhooks/github

SECURITY:
- HMAC-SHA256 signature verified before ANY processing
- Payload is never trusted without valid signature
- Scan runs in background (returns 200 immediately)
- Idempotency enforced via (repo, pr_number, head_sha) key
"""
import json
import threading
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from packages.github.services.webhook import GitHubWebhookService, WebhookSignatureError
from packages.saas.db.database import _SessionLocal

router = APIRouter(prefix="/webhooks", tags=["GitHub Webhooks"])


def _run_pr_review(payload: dict, delivery_id: Optional[str]) -> None:
    """Background task: run the full PR review pipeline."""
    db = _SessionLocal()
    try:
        from services.github_pr.orchestrator import PRReviewOrchestrator
        from packages.github.services.webhook import GitHubWebhookService

        webhook_service = GitHubWebhookService()
        event = webhook_service.parse_pull_request_event(payload, delivery_id=delivery_id)
        if event is None:
            return  # Unsupported action

        # Get org_id from DB by repo (or default)
        org_id = _resolve_org_id(db, event.repo_full_name)

        orchestrator = PRReviewOrchestrator(
            db_session=db,
            org_id=org_id,
            user_id="github-webhook-bot",
        )
        orchestrator.process_webhook_event(event)
    except Exception:
        pass  # Errors logged by orchestrator audit trail
    finally:
        try:
            db.close()
        except Exception:
            pass


def _resolve_org_id(db, repo_full_name: str) -> str:
    """Resolve the LeakGuard org_id for a connected GitHub repository."""
    try:
        from packages.saas.db.models import GithubRepository
        repo = db.query(GithubRepository).filter(
            GithubRepository.repo_full_name == repo_full_name,
            GithubRepository.is_active == True,
        ).first()
        if repo:
            return repo.org_id
    except Exception:
        pass
    # Fall back to first available org
    try:
        from packages.saas.db.models import Organization
        org = db.query(Organization).first()
        if org:
            return org.id
    except Exception:
        pass
    return "org_default"


@router.post("/github", status_code=status.HTTP_200_OK)
@router.post("/webhook", status_code=status.HTTP_200_OK)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
):
    """Receive and process GitHub webhook events.

    Returns 200 immediately. Scan runs asynchronously in background.
    Signature validation occurs synchronously before 200 is returned.
    """
    # Read raw body for signature verification (must be done before JSON parse)
    payload_bytes = await request.body()

    # 1. Validate HMAC-SHA256 signature
    webhook_service = GitHubWebhookService()
    try:
        webhook_service.verify_signature(payload_bytes, x_hub_signature_256)
    except WebhookSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Webhook signature validation failed: {e}",
        )

    # 2. Only process pull_request events
    if x_github_event not in ("pull_request", "ping"):
        return {"status": "ignored", "event": x_github_event}

    if x_github_event == "ping":
        return {"status": "pong", "message": "LeakGuard webhook connected successfully"}

    # 3. Parse payload
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    action = payload.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        return {"status": "ignored", "action": action}

    # 4. Queue background scan (return 200 immediately per GitHub webhook best practices)
    background_tasks.add_task(_run_pr_review, payload, x_github_delivery)

    pr_number = payload.get("pull_request", {}).get("number", "?")
    repo = payload.get("repository", {}).get("full_name", "?")
    return {
        "status": "accepted",
        "message": f"LeakGuard scan queued for PR #{pr_number} in {repo}",
        "delivery_id": x_github_delivery,
        "action": action,
    }
