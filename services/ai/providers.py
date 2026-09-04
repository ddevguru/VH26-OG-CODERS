import os
import json
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import httpx

from services.ai.redactor import SecretRedactor


class LLMProvider(ABC):
    """Abstract base class for LLM providers (Ollama, OpenAI, Mock)."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0) -> str:
        """Generates a text completion given a prompt."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class OllamaProvider(LLMProvider):
    """Provider for local Ollama instances (e.g. llama3, qwen2.5-coder, mistral)."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 3.0,
    ) -> None:
        self.endpoint = (endpoint or os.getenv("LEAKGUARD_OLLAMA_ENDPOINT", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("LEAKGUARD_OLLAMA_MODEL", "qwen2.5-coder:7b")
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return f"Ollama ({self.model})"

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0) -> str:
        sanitized_prompt, _ = SecretRedactor.redact(prompt)
        url = f"{self.endpoint}/api/generate"
        payload = {
            "model": self.model,
            "prompt": sanitized_prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            sanitized_sys, _ = SecretRedactor.redact(system_prompt)
            payload["system"] = sanitized_sys

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("response", "").strip()
                else:
                    return f"[Ollama HTTP {resp.status_code}] Local Ollama endpoint unavailable."
        except Exception:
            return "[Ollama Offline] Local Ollama service is not running. Set LEAKGUARD_LLM_API_KEY for OpenAI or start Ollama."


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI-compatible API endpoints."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.getenv("LEAKGUARD_LLM_API_KEY", "")
        self.endpoint = endpoint or os.getenv("LEAKGUARD_LLM_ENDPOINT", "https://api.openai.com/v1/chat/completions")
        self.model = model or os.getenv("LEAKGUARD_LLM_MODEL", "gpt-4o")
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return f"OpenAI ({self.model})"

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0) -> str:
        if not self.api_key:
            return "[OpenAI Provider Error: LEAKGUARD_LLM_API_KEY is not configured]"

        sanitized_prompt, _ = SecretRedactor.redact(prompt)
        messages = []
        if system_prompt:
            sanitized_sys, _ = SecretRedactor.redact(system_prompt)
            messages.append({"role": "system", "content": sanitized_sys})
        messages.append({"role": "user", "content": sanitized_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.endpoint, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"]
                    return text.strip()
                else:
                    return f"[OpenAI API Error: HTTP {resp.status_code}] {resp.text}"
        except Exception as e:
            return f"[OpenAI Connection Error: {str(e)}]"


class MockLLMProvider(LLMProvider):
    """Mock LLM Provider for 100% deterministic offline unit testing."""

    def __init__(self, name: str = "MockLLM") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0) -> str:
        # Inspect prompt to return realistic mock responses for agents
        if "FIX_GENERATOR" in prompt or "Fix the unclosed resource" in prompt:
            # Extract code block if present
            if "with " in prompt or "try:" in prompt:
                return "```python\n# Fixed code\nwith open('file.txt') as f:\n    data = f.read()\n```"
            return "```python\nconn = sqlite3.connect(DB)\ntry:\n    res = fetch()\n    return res\nfinally:\n    conn.close()\n```"
        elif "BAD_PATCH_GEN" in prompt:
            return "```python\nif False:\n    conn.close()\n```"
        elif "ROOT_CAUSE" in prompt:
            return "The resource is acquired without try/finally or a context manager, leaving it owned when control exits."
        elif "SECURITY_IMPACT" in prompt:
            return "Unclosed connection may contribute to database connection-pool exhaustion and service degradation."
        elif "CODE_REVIEW" in prompt:
            return "RESOURCE SAFETY REVIEW\n\n- DEFINITE_LEAK detected on unclosed handle.\n- Recommended remediation: Wrap in try/finally or context manager."

        return "Mock LLM Response: Static resource review completed successfully."


def get_llm_provider(
    provider_name: str = "auto",
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMProvider:
    """Factory method to get configured LLM provider."""
    provider_type = (provider_name or os.getenv("LEAKGUARD_AI_PROVIDER", "auto")).lower()

    if provider_type == "mock":
        return MockLLMProvider()
    elif provider_type == "ollama":
        return OllamaProvider(endpoint=endpoint, model=model)
    elif provider_type == "openai":
        return OpenAIProvider(api_key=api_key, endpoint=endpoint, model=model)

    # Auto mode: if API key exists -> OpenAI, else Ollama, else Mock fallback
    if api_key or os.getenv("LEAKGUARD_LLM_API_KEY"):
        return OpenAIProvider(api_key=api_key, endpoint=endpoint, model=model)
    
    # Default to Ollama provider
    return OllamaProvider(endpoint=endpoint, model=model)
