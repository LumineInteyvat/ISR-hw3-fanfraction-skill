from __future__ import annotations

import json
import os
import urllib.request
from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    @abstractmethod
    def complete_json(self, task: str, prompt: str, schema_hint: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class DeepSeekClient(LLMClient):
    def __init__(self, settings: dict[str, Any] | None = None, api_key: str | None = None, endpoint: str | None = None, model: str | None = None, temperature: float | None = None):
        settings = settings or {}
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.endpoint = endpoint or os.environ.get("DEEPSEEK_API_ENDPOINT") or settings.get("endpoint") or "https://api.deepseek.com/chat/completions"
        self.model = model or os.environ.get("DEEPSEEK_MODEL") or settings.get("model") or "deepseek-chat"
        self.temperature = float(temperature if temperature is not None else settings.get("temperature", 0.1))
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for DeepSeekClient")

    def complete_json(self, task: str, prompt: str, schema_hint: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": self.model,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"DeepSeek request failed for task {task}: {exc}") from exc
        content = payload["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"DeepSeek returned non-JSON content for task {task}") from exc


class OfflineLLMClient(LLMClient):
    def complete_json(self, task: str, prompt: str, schema_hint: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        if task == "assertion_extraction":
            claim = prompt.strip().splitlines()[-1].strip() or metadata.get("text", "")
            if "资料片段" in prompt:
                claim = metadata.get("text", claim)
            return {
                "client": "offline",
                "assertions": [
                    {
                        "assertion_type": _guess_assertion_type(claim),
                        "subject": metadata.get("character", "Example"),
                        "claim": claim,
                        "confidence": 0.75,
                        "source_id": metadata.get("source_id", "source-1"),
                        "source_type": metadata.get("source_type", "canon"),
                        "source_channel": metadata.get("source_channel", "canon"),
                        "quote": claim,
                        "version": metadata.get("version", "v1"),
                        "attributes": {"object": "Ally"} if "Ally" in claim else {},
                    }
                ],
            }
        if task == "conflict_detection":
            lower = prompt.lower()
            is_conflict = ("trust" in lower and "distrust" in lower) or ("相信" in lower and "不信" in lower)
            return {
                "client": "offline",
                "is_conflict": is_conflict,
                "conflict_type": "relationship_conflict" if is_conflict else "none",
                "severity": "high" if is_conflict else "low",
                "reasoning": "Relationship polarity differs across preserved source assertions." if is_conflict else "No deterministic conflict detected.",
            }
        return {"client": "offline"}


def _guess_assertion_type(claim: str) -> str:
    lower = claim.lower()
    if "trust" in lower or "distrust" in lower or "ally" in lower or "关系" in claim:
        return "relationship"
    if "promise" in lower or "承诺" in claim:
        return "personality_trait"
    return "personality_trait"
