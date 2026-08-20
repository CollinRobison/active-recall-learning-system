"""Model-provider boundaries for source-grounded tutoring."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import urllib.request
from dataclasses import dataclass
from typing import Any, Sequence, Protocol


class ModelProvider(Protocol):
    name: str

    def complete(self, *, system: str, user: str) -> dict[str, Any]:
        ...


def _decode_json(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("model response was not a JSON object") from exc
    if not isinstance(payload, dict):
        raise ValueError("model response must be a JSON object")
    return payload


@dataclass
class CommandModelProvider:
    """Invoke a local model/harness adapter through a JSON stdin/stdout contract."""

    command: Sequence[str]
    timeout: int = 180
    name: str = "command"

    @classmethod
    def from_string(cls, command: str, timeout: int = 180) -> "CommandModelProvider":
        return cls(shlex.split(command), timeout)

    def complete(self, *, system: str, user: str) -> dict[str, Any]:
        if not self.command:
            raise ValueError("model command is empty")
        request = {"system": system, "user": user, "response_format": "json"}
        result = subprocess.run(
            list(self.command),
            input=json.dumps(request),
            text=True,
            capture_output=True,
            timeout=self.timeout,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(f"model command failed with exit code {result.returncode}")
        return _decode_json(result.stdout)


@dataclass
class OpenAICompatibleProvider:
    """Opt-in OpenAI-compatible chat endpoint; key is read only from the environment."""

    endpoint: str
    model: str
    api_key_env: str = "ACTIVE_RECALL_MODEL_API_KEY"
    timeout: int = 180
    name: str = "openai-compatible"

    def complete(self, *, system: str, user: str) -> dict[str, Any]:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"model API key is not set in {self.api_key_env}")
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("OpenAI-compatible response has no assistant content") from exc
        return _decode_json(content)
