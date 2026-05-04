from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schemas import CharacterDeviationConfig


CONFIG_FILES = {
    "assertion_types": "assertion_types.yaml",
    "source_channels": "source_channels.yaml",
    "conflict_types": "conflict_types.yaml",
    "scenario_adapters": "scenario_adapters.yaml",
    "output_formats": "output_formats.yaml",
}

PROMPT_STAGES = [
    "assertion_extraction",
    "conflict_detection",
    "scenario_conditioning",
    "branch_recommendation",
    "character_card_generation",
]


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_character_deviation_config(config_dir: Path | str) -> CharacterDeviationConfig:
    base = Path(config_dir)
    assertion_doc = _read_yaml(base / CONFIG_FILES["assertion_types"])
    source_doc = _read_yaml(base / CONFIG_FILES["source_channels"])
    conflict_doc = _read_yaml(base / CONFIG_FILES["conflict_types"])
    scenario_doc = _read_yaml(base / CONFIG_FILES["scenario_adapters"])
    output_doc = _read_yaml(base / CONFIG_FILES["output_formats"])
    prompts = {}
    for stage in PROMPT_STAGES:
        prompts[stage] = (base / "prompts" / f"{stage}.md").read_text(encoding="utf-8")
    return CharacterDeviationConfig(
        assertion_types=assertion_doc.get("assertion_types", {}),
        source_channels=source_doc.get("source_channels", {}),
        conflict_types=conflict_doc.get("conflict_types", {}),
        severity_rules=conflict_doc.get("severity_rules", {}),
        scenario_adapters=scenario_doc.get("scenario_adapters", {}),
        output_formats=output_doc.get("output_formats", {}),
        llm=output_doc.get("llm", {}),
        prompts=prompts,
    )
