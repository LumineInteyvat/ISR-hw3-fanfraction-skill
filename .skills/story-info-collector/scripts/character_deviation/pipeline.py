from __future__ import annotations

from itertools import combinations
from typing import Any

from .graph_store import build_claim_graph
from .llm_client import LLMClient
from .prompt_renderer import PromptRenderer
from .reranker import recommend_diverse_branches
from .schemas import (
    Assertion,
    BranchRecommendation,
    CharacterCard,
    CharacterDeviationConfig,
    Conflict,
    DeviationReport,
    GraphEdge,
    ScenarioConditioning,
    SourceDocument,
    SourceTrace,
)


def extract_assertions(sources: list[SourceDocument], character: str, scenario: str, config: CharacterDeviationConfig, llm: LLMClient) -> list[Assertion]:
    renderer = PromptRenderer(config)
    assertions: list[Assertion] = []
    for source in sources:
        prompt = renderer.render(
            "assertion_extraction",
            {
                "character": character,
                "scenario": scenario,
                "source_snippets": [source.text],
            },
        )
        result = llm.complete_json(
            "assertion_extraction",
            prompt,
            {"assertion_types": config.assertion_types},
            {
                "source_id": source.source_id,
                "source_type": source.source_type,
                "source_channel": source.source_channel,
                "version": source.version,
                "character": character,
                "text": source.text,
            },
        )
        for index, raw in enumerate(result.get("assertions", []), start=1):
            assertions.append(_assertion_from_raw(raw, f"{source.source_id}:{index}", character, source))
    return assertions


def detect_conflicts(assertions: list[Assertion], llm: LLMClient, config: CharacterDeviationConfig, character: str = "", scenario: str = "") -> DeviationReport:
    renderer = PromptRenderer(config)
    conflicts: list[Conflict] = []
    for left, right in combinations(assertions, 2):
        if left.subject != right.subject:
            continue
        if left.assertion_type != right.assertion_type and not _compatible_conflict_types(left.assertion_type, right.assertion_type, config):
            continue
        prompt = renderer.render(
            "conflict_detection",
            {
                "character": character or left.subject,
                "scenario": scenario,
                "assertion_a": left.to_dict(),
                "assertion_b": right.to_dict(),
            },
        )
        result = llm.complete_json("conflict_detection", prompt, {"conflict_types": config.conflict_types}, {})
        if result.get("is_conflict"):
            conflicts.append(
                Conflict(
                    assertion_ids=[left.assertion_id, right.assertion_id],
                    conflict_type=result.get("conflict_type", _default_conflict_type(left.assertion_type)),
                    severity=result.get("severity", "medium"),
                    reasoning=result.get("reasoning", "Conflicting assertions were detected."),
                    source_trace=[left.source_trace.to_dict(), right.source_trace.to_dict()],
                )
            )
    return DeviationReport(conflicts=conflicts, summary=f"Detected {len(conflicts)} conflict(s).")


def apply_scenario(assertions: list[Assertion], scenario: str, config: CharacterDeviationConfig) -> ScenarioConditioning:
    adapter = config.scenario_adapters.get(scenario) or config.scenario_adapters.get("canon_default", {})
    core_invariants = [_claim_invariant(assertion.claim) for assertion in assertions if assertion.assertion_type in {"personality_trait", "value", "relationship"}]
    if not core_invariants:
        core_invariants = [_claim_invariant(assertion.claim) for assertion in assertions]
    scenario_edges = [GraphEdge(f"assertion:{assertion.assertion_id}", f"scenario:{scenario}", "scenario_adapts", dict(adapter)) for assertion in assertions]
    return ScenarioConditioning(scenario=scenario, core_invariants=core_invariants, adjustments=dict(adapter), scenario_edges=scenario_edges)


def recommend_branches(assertions: list[Assertion], conflicts: list[Conflict], scenario: str, config: CharacterDeviationConfig) -> list[BranchRecommendation]:
    return recommend_diverse_branches(assertions, conflicts, scenario, config)


def generate_character_card(
    assertions: list[Assertion],
    conflicts: list[Conflict],
    recommendations: list[BranchRecommendation],
    scenario: str,
    config: CharacterDeviationConfig,
    character: str | None = None,
) -> CharacterCard:
    conditioning = apply_scenario(assertions, scenario, config)
    selected_character = character or (assertions[0].subject if assertions else "Unknown")
    conflict_warnings = [conflict.reasoning for conflict in conflicts]
    forbidden_zones = [f"避免无解释地改写核心断言：{invariant}" for invariant in conditioning.core_invariants]
    recommended_expression = [recommendation.rationale for recommendation in recommendations] or ["保持核心人格不变，只在场景变量内调整表达。"]
    source_trace = _unique_traces([assertion.source_trace.to_dict() for assertion in assertions])
    return CharacterCard(
        character=selected_character,
        scenario=scenario,
        core_invariants=conditioning.core_invariants,
        adjustable_variables=conditioning.adjustments,
        forbidden_zones=forbidden_zones,
        conflict_warnings=conflict_warnings,
        recommended_expression=recommended_expression,
        source_trace=source_trace,
        character_card_v2={"reserved": True},
    )


def run_pipeline(sources: list[SourceDocument], character: str, scenario: str, config: CharacterDeviationConfig, llm: LLMClient) -> dict[str, Any]:
    assertions = extract_assertions(sources, character, scenario, config, llm)
    graph = build_claim_graph(assertions)
    report = detect_conflicts(assertions, llm, config, character=character, scenario=scenario)
    conditioning = apply_scenario(assertions, scenario, config)
    recommendations = recommend_branches(assertions, report.conflicts, scenario, config)
    card = generate_character_card(assertions, report.conflicts, recommendations, scenario, config, character=character)
    return {
        "assertions": [assertion.to_dict() for assertion in assertions],
        "claim_graph": graph.to_dict(),
        "deviation_report": report.to_dict(),
        "scenario_conditioning": conditioning.to_dict(),
        "recommendations": [recommendation.to_dict() for recommendation in recommendations],
        "character_card": card.to_dict(),
    }


def _assertion_from_raw(raw: dict[str, Any], fallback_id: str, character: str, source: SourceDocument) -> Assertion:
    return Assertion(
        assertion_id=str(raw.get("assertion_id") or fallback_id),
        subject=str(raw.get("subject") or character),
        assertion_type=str(raw.get("assertion_type") or "personality_trait"),
        claim=str(raw.get("claim") or source.text),
        confidence=float(raw.get("confidence", 0.7)),
        source_trace=SourceTrace(
            source_id=str(raw.get("source_id") or source.source_id),
            source_type=str(raw.get("source_type") or source.source_type),
            source_channel=str(raw.get("source_channel") or source.source_channel),
            quote=str(raw.get("quote") or raw.get("claim") or source.text),
            version=str(raw.get("version") or source.version),
        ),
        attributes=dict(raw.get("attributes") or {}),
    )


def _compatible_conflict_types(left_type: str, right_type: str, config: CharacterDeviationConfig) -> bool:
    for conflict in config.conflict_types.values():
        types = set(conflict.get("assertion_types", []))
        if left_type in types and right_type in types:
            return True
    return False


def _default_conflict_type(assertion_type: str) -> str:
    if assertion_type == "relationship":
        return "relationship_conflict"
    if assertion_type == "event_memory":
        return "timeline_conflict"
    if assertion_type in {"world_rule", "scene_constraint"}:
        return "worldview_conflict"
    return "personality_conflict"


def _claim_invariant(claim: str) -> str:
    return claim.strip().rstrip(".")


def _unique_traces(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    unique = []
    for trace in traces:
        key = (trace.get("source_id"), trace.get("quote"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(trace)
    return unique
