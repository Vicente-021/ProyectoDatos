"""Normalización mínima y común para los mensajes de 20 Newsgroups."""

from __future__ import annotations

import re
import unicodedata


HEADER_FIELD_RE = re.compile(r"^([a-z][a-z0-9_-]*):\s*")
COMMON_HEADER_NAMES = {
    "from",
    "subject",
    "newsgroups",
    "message-id",
    "date",
    "path",
    "organization",
    "lines",
    "xref",
}
WORD_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)


def _looks_like_header_block(lines: list[str]) -> bool:
    """Heuristically recognize an initial email/news header block."""
    field_names = {
        match.group(1)
        for line in lines
        if (match := HEADER_FIELD_RE.match(line.strip())) is not None
    }
    return len(field_names) >= 2 or bool(field_names & COMMON_HEADER_NAMES)


def normalize_text(text: str) -> str:
    """Normalize Unicode/case, remove recognizable headers and signatures.

    Quoted text is intentionally retained. Punctuation is left until tokenization
    so this function's result remains inspectable and deterministic.
    """
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = text.split("\n")
    separator = next((i for i, line in enumerate(lines) if not line.strip()), None)
    if separator is not None and _looks_like_header_block(lines[:separator]):
        lines = lines[separator + 1 :]

    # The standard signature delimiter is a line containing only "--" (often
    # followed by a space). Remove it and everything after it.
    signature_start = next(
        (i for i, line in enumerate(lines) if line.strip() == "--"), None
    )
    if signature_start is not None:
        lines = lines[:signature_start]

    return " ".join(" ".join(lines).split())


def tokenize(text: str) -> list[str]:
    """Split normalized text into Unicode alphanumeric tokens.

    Underscores and punctuation delimit tokens. Numbers are retained; no
    stemming or stop-word removal is performed.
    """
    return WORD_RE.findall(text)


def preprocess_to_tokens(text: str) -> list[str]:
    """Apply the project normalization policy and tokenize one message."""
    return tokenize(normalize_text(text))
