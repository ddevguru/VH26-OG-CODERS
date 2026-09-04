import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple

from services.ai.models import AgentResult, AgentStatus
from services.ai.providers import LLMProvider, get_llm_provider
from services.ai.redactor import SecretRedactor
from services.ai.tracing import LangFuseTracer


class BaseAgent(ABC):
    """Base class for specialized LeakGuard AI Agents."""

    def __init__(self, agent_name: str, provider: Optional[LLMProvider] = None, tracer: Optional[LangFuseTracer] = None) -> None:
        self.agent_name = agent_name
        self.provider = provider or get_llm_provider()
        self.tracer = tracer or LangFuseTracer()

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> AgentResult:
        """Executes the agent's core task using context parameters."""
        pass

    def _execute_prompt(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0) -> Tuple[str, float]:
        start = time.perf_counter()
        sanitized_prompt, _ = SecretRedactor.redact(prompt)
        response = self.provider.generate(prompt=sanitized_prompt, system_prompt=system_prompt, temperature=temperature)
        duration_ms = (time.perf_counter() - start) * 1000.0
        return response, duration_ms
