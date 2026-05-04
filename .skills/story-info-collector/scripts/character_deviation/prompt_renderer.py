from __future__ import annotations

import json
import re
from typing import Any

from .schemas import CharacterDeviationConfig


class PromptRenderer:
    def __init__(self, config: CharacterDeviationConfig):
        self.config = config

    def render(self, stage: str, variables: dict[str, Any]) -> str:
        if stage not in self.config.prompts:
            raise KeyError(f"Unknown prompt stage: {stage}")
        merged = {
            "assertion_types": self.config.assertion_types,
            "conflict_types": self.config.conflict_types,
            "scenario_adapters": self.config.scenario_adapters,
            **variables,
        }
        template = self.config.prompts[stage]
        return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", lambda match: self._format(merged.get(match.group(1), "")), template)

    def _format(self, value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        return str(value)
