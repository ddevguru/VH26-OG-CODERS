import re
from typing import Tuple


class SecretRedactor:
    """Sanitizes source code snippets and prompts to strip API keys, secrets, tokens,
    and passwords before sending context to LLM providers.
    """

    PATTERNS = [
        # API Keys & Tokens
        (r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{16,})['\"]?", r"\1 = '[REDACTED_API_KEY]'"),
        # OpenAI / Anthropic / GitHub / AWS Tokens
        (r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_OPENAI_KEY]"),
        (r"ghp_[a-zA-Z0-9]{36}", "[REDACTED_GITHUB_TOKEN]"),
        (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
        (r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?([a-zA-Z0-9/+=]{30,})['\"]?", "aws_secret_access_key = '[REDACTED_AWS_SECRET]'"),
        # Database Connection Strings
        (r"(mongodb(?:\+srv)?|postgres(?:ql)?|mysql|redis)://([^:]+):([^@]+)@", r"\1://\2:[REDACTED_PASSWORD]@"),
        # Generic Password Assignments
        (r"(?i)(password|passwd|pwd|db_pass)\s*[:=]\s*['\"]?([^'\"]{4,})['\"]?", r"\1 = '[REDACTED_PASSWORD]'"),
        # Private Keys
        (r"-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----[\s\S]+?-----END \1 KEY-----", "[REDACTED_PRIVATE_KEY]"),
    ]

    @classmethod
    def redact(cls, text: str) -> Tuple[str, int]:
        """Redacts sensitive strings from the input text. Returns (sanitized_text, redaction_count)."""
        if not text:
            return "", 0

        sanitized = text
        redactions = 0
        for pattern, repl in cls.PATTERNS:
            matches = len(re.findall(pattern, sanitized))
            if matches > 0:
                redactions += matches
                sanitized = re.sub(pattern, repl, sanitized)

        return sanitized, redactions
