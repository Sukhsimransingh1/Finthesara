from __future__ import annotations

import re
import unicodedata


class TextCleaner:
    """Normalize extracted document text without changing its meaning."""

    _MULTIPLE_SPACES = re.compile(r"[ \t]+")
    _MULTIPLE_NEWLINES = re.compile(r"\n{3,}")

    def clean(self, text: str) -> str:
        """Clean extracted text while preserving meaningful content."""
        if not text:
            return ""

        # Normalize Unicode representation.
        cleaned = unicodedata.normalize("NFKC", text)

        # Normalize line endings.
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        # Remove trailing whitespace from each line.
        cleaned = "\n".join(
            line.rstrip()
            for line in cleaned.split("\n")
        )

        # Collapse spaces/tabs inside lines.
        cleaned = self._MULTIPLE_SPACES.sub(
            " ",
            cleaned,
        )

        # Collapse excessive blank lines.
        cleaned = self._MULTIPLE_NEWLINES.sub(
            "\n\n",
            cleaned,
        )

        return cleaned.strip()