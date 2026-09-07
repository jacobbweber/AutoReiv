"""
Transcript and Output Secret Scrubber [CARD-168].
"""

from typing import Any, Iterable, Optional, Set


class TranscriptScrubber:
    """
    Scrubs plaintext credential secrets from strings, dictionaries, and execution outputs.
    """

    MASK = "***MASKED***"

    def __init__(self, secrets: Optional[Iterable[str]] = None):
        self._secrets: Set[str] = set()
        if secrets:
            self.add_secrets(secrets)

    def add_secrets(self, secrets: Iterable[str]) -> None:
        for s in secrets:
            if s and isinstance(s, str) and len(s.strip()) >= 3:
                self._secrets.add(s.strip())

    def scrub(self, text: str) -> str:
        """
        Replace all known secrets in text with MASK.
        """
        if not text or not isinstance(text, str) or not self._secrets:
            return text

        scrubbed = text
        # Replace longer secrets first to avoid partial overlap issues
        sorted_secrets = sorted(self._secrets, key=len, reverse=True)
        for s in sorted_secrets:
            if s in scrubbed:
                scrubbed = scrubbed.replace(s, self.MASK)
        return scrubbed

    def scrub_object(self, obj: Any) -> Any:
        """
        Recursively scrub secrets from strings in dicts, lists, and primitives.
        """
        if isinstance(obj, str):
            return self.scrub(obj)
        elif isinstance(obj, dict):
            return {k: self.scrub_object(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.scrub_object(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self.scrub_object(item) for item in obj)
        return obj
