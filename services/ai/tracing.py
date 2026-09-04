import os
import time
import uuid
import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from services.ai.models import AgentActivityLog, AgentStatus


class LangFuseTracer:
    """LangFuse Tracer for Multi-Tenant & Per-User Agent Tracking.
    
    Records agent activity, execution duration, model metadata, and trace events
    scoped to specific org_id and user_id.
    """

    def __init__(self, trace_id: Optional[str] = None, user_id: Optional[str] = None, org_id: Optional[str] = None) -> None:
        self.trace_id = trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        self.user_id = user_id or "user_default"
        self.org_id = org_id or "org_default"
        self.secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        self.public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        self.host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        self.logs: List[AgentActivityLog] = []

    def start_trace(self, name: str = "LeakGuard AI Review") -> str:
        """Initializes a new LangFuse trace session."""
        self.trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        return self.trace_id

    def log_agent_step(
        self,
        agent_name: str,
        status: AgentStatus,
        duration_ms: float,
        details: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentActivityLog:
        """Logs an agent step tied to the current trace, user_id, and org_id."""
        entry = AgentActivityLog(
            timestamp=datetime.datetime.now().strftime("%H:%M:%S"),
            agent_name=agent_name,
            status=status,
            duration_ms=round(duration_ms, 2),
            user_id=self.user_id,
            org_id=self.org_id,
            trace_id=self.trace_id,
            details=details,
        )
        self.logs.append(entry)
        
        # If LangFuse SDK keys are present, attempt optional async dispatch
        if self.secret_key and self.public_key:
            self._dispatch_to_langfuse(entry, metadata)

        return entry

    def _dispatch_to_langfuse(self, entry: AgentActivityLog, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Dispatches telemetry data to LangFuse API if configured."""
        try:
            import httpx
            url = f"{self.host.rstrip('/')}/api/public/ingestion"
            payload = {
                "batch": [
                    {
                        "id": f"event_{uuid.uuid4().hex[:10]}",
                        "type": "event-create",
                        "body": {
                            "traceId": entry.trace_id,
                            "name": entry.agent_name,
                            "startTime": entry.timestamp,
                            "metadata": {
                                "user_id": entry.user_id,
                                "org_id": entry.org_id,
                                "duration_ms": entry.duration_ms,
                                "status": entry.status.value,
                                "details": entry.details,
                                **(metadata or {}),
                            },
                        },
                    }
                ]
            }
            # Non-blocking best-effort HTTP post
            headers = {"Authorization": f"Basic {self.public_key}:{self.secret_key}"}
            with httpx.Client(timeout=2.0) as client:
                client.post(url, json=payload, headers=headers)
        except Exception:
            pass  # Fail gracefully, tracer never disrupts analysis workflow
