#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

CURRENT = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT))

from character_deviation.config_loader import load_character_deviation_config
from character_deviation.llm_client import DeepSeekClient, OfflineLLMClient
from character_deviation.pipeline import run_pipeline
from character_deviation.schemas import SourceDocument


def default_config_dir() -> Path:
    return CURRENT.parent / "config" / "character_deviation"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze character canon deviation and generate a temporary character card.")
    parser.add_argument("--profile", help="Optional story profile path for metadata compatibility.")
    parser.add_argument("--config-dir", default=str(default_config_dir()), help="Character deviation config directory.")
    parser.add_argument("--input", action="append", default=[], help="Input JSON or JSONL source/evidence file. Can be repeated.")
    parser.add_argument("--source-text", help="Direct source text for standalone analysis.")
    parser.add_argument("--source-json", help="Direct source JSON object or array.")
    parser.add_argument("--source-channel", default="canon", help="Source channel for direct source text.")
    parser.add_argument("--source-type", default="canon", help="Source type for direct source text.")
    parser.add_argument("--character", required=True, help="Target character name.")
    parser.add_argument("--scenario", default="canon_default", help="Scenario adapter key.")
    parser.add_argument("--output", help="Path to write JSON output. Defaults to stdout.")
    parser.add_argument("--offline", action="store_true", help="Use deterministic offline client instead of DeepSeek.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_character_deviation_config(Path(args.config_dir))
    sources = collect_sources(args)
    if not sources:
        raise SystemExit("No input source provided. Use --input, --source-text, or --source-json.")
    client = OfflineLLMClient() if args.offline else DeepSeekClient(settings=config.llm)
    result = run_pipeline(sources, args.character, args.scenario, config, client)
    result["metadata"] = {
        "llm_provider": "offline" if args.offline else os.environ.get("FICTION_ASSISTANT_LLM_PROVIDER", "deepseek"),
        "profile": args.profile,
        "scenario": args.scenario,
        "character": args.character,
    }
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


def collect_sources(args: argparse.Namespace) -> list[SourceDocument]:
    sources: list[SourceDocument] = []
    for input_path in args.input:
        sources.extend(_sources_from_file(Path(input_path)))
    if args.source_text:
        sources.append(
            SourceDocument(
                source_id="direct-text-1",
                source_type=args.source_type,
                source_channel=args.source_channel,
                text=args.source_text,
                version="v1",
                metadata={"input_mode": "source_text"},
            )
        )
    if args.source_json:
        payload = json.loads(args.source_json)
        rows = payload if isinstance(payload, list) else [payload]
        for index, row in enumerate(rows, start=1):
            sources.append(_source_from_mapping(row, f"direct-json-{index}"))
    return sources


def _sources_from_file(path: Path) -> list[SourceDocument]:
    text = path.read_text(encoding="utf-8")
    rows: list[Any]
    if path.suffix == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        payload = json.loads(text)
        rows = payload if isinstance(payload, list) else payload.get("sources") or payload.get("evidence_chunks") or [payload]
    return [_source_from_mapping(row, f"{path.stem}-{index}") for index, row in enumerate(rows, start=1)]


def _source_from_mapping(row: dict[str, Any], fallback_id: str) -> SourceDocument:
    source_id = str(row.get("source_id") or row.get("id") or fallback_id)
    source_type = str(row.get("source_type") or row.get("type") or "unknown")
    source_channel = str(row.get("source_channel") or row.get("channel") or source_type)
    text = str(row.get("text") or row.get("content") or row.get("chunk_text") or row.get("quote") or "")
    return SourceDocument(
        source_id=source_id,
        source_type=source_type,
        source_channel=source_channel,
        text=text,
        version=str(row.get("version") or "v1"),
        metadata={key: value for key, value in row.items() if key not in {"text", "content", "chunk_text", "quote"}},
    )


if __name__ == "__main__":
    raise SystemExit(main())
