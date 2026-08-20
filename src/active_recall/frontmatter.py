"""Small dependency-free frontmatter reader/writer for generated records."""

from __future__ import annotations

import json
import re
from typing import Any


def _scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value in {"null", "~"}:
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.startswith("[") or value.startswith("{"):
        try:
            return json.loads(value.replace("'", '"'))
        except json.JSONDecodeError:
            return value
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Return ``(frontmatter, markdown_body)`` for a generated record."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("frontmatter starts with --- but has no closing delimiter")
    raw = text[4:end]
    body = text[end + len("\n---\n") :]
    result: dict[str, Any] = {}
    current_list: str | None = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list:
            result.setdefault(current_list, []).append(_scalar(line[4:]))
            continue
        if line.startswith("  ") and current_list:
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line!r}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            result[key] = []
            current_list = key
        else:
            result[key] = _scalar(value)
            current_list = None
    return result, body


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    value = str(value)
    if not value or any(ch in value for ch in ":#\n") or value.strip() != value:
        return json.dumps(value, ensure_ascii=False)
    return value


def render(metadata: dict[str, Any], body: str) -> str:
    """Render a stable, deliberately small YAML subset."""
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, list) and all(not isinstance(item, (dict, list)) for item in value):
            lines.append(f"{key}:")
            lines.extend(f"  - {_format_scalar(item)}" for item in value)
        else:
            lines.append(f"{key}: {_format_scalar(value)}")
    lines.extend(["---", ""])
    return "\n".join(lines) + body.lstrip("\n")
