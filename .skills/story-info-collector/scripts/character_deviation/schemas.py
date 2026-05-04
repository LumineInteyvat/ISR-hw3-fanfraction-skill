from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CharacterDeviationConfig:
    assertion_types: dict[str, Any]
    source_channels: dict[str, Any]
    conflict_types: dict[str, Any]
    severity_rules: dict[str, Any]
    scenario_adapters: dict[str, Any]
    output_formats: dict[str, Any]
    llm: dict[str, Any]
    prompts: dict[str, str]


@dataclass
class SourceDocument:
    source_id: str
    source_type: str
    source_channel: str
    text: str
    version: str = "v1"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "source_channel": self.source_channel,
            "text": self.text,
            "version": self.version,
            "metadata": self.metadata,
        }


@dataclass
class SourceTrace:
    source_id: str
    source_type: str
    source_channel: str
    quote: str
    version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "source_channel": self.source_channel,
            "quote": self.quote,
            "version": self.version,
        }


@dataclass
class Assertion:
    assertion_id: str
    subject: str
    assertion_type: str
    claim: str
    confidence: float
    source_trace: SourceTrace
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assertion_id": self.assertion_id,
            "subject": self.subject,
            "assertion_type": self.assertion_type,
            "claim": self.claim,
            "confidence": self.confidence,
            "source_trace": self.source_trace.to_dict(),
            "attributes": self.attributes,
        }


@dataclass
class GraphNode:
    node_id: str
    node_type: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"node_id": self.node_id, "node_type": self.node_type, "payload": self.payload}


@dataclass
class GraphEdge:
    source: str
    target: str
    edge_type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "target": self.target, "edge_type": self.edge_type, "payload": self.payload}


@dataclass
class ClaimGraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    assertions: list[Assertion]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "assertions": [assertion.to_dict() for assertion in self.assertions],
        }


@dataclass
class Conflict:
    assertion_ids: list[str]
    conflict_type: str
    severity: str
    reasoning: str
    source_trace: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "assertion_ids": self.assertion_ids,
            "conflict_type": self.conflict_type,
            "severity": self.severity,
            "reasoning": self.reasoning,
            "source_trace": self.source_trace,
        }


@dataclass
class DeviationReport:
    conflicts: list[Conflict]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {"conflicts": [conflict.to_dict() for conflict in self.conflicts], "summary": self.summary}


@dataclass
class ScenarioConditioning:
    scenario: str
    core_invariants: list[str]
    adjustments: dict[str, Any]
    scenario_edges: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "core_invariants": self.core_invariants,
            "adjustments": self.adjustments,
            "scenario_edges": [edge.to_dict() for edge in self.scenario_edges],
        }


@dataclass
class BranchRecommendation:
    category: str
    title: str
    rationale: str
    score: float
    source_trace: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "title": self.title,
            "rationale": self.rationale,
            "score": self.score,
            "source_trace": self.source_trace,
        }


@dataclass
class CharacterCard:
    character: str
    scenario: str
    core_invariants: list[str]
    adjustable_variables: dict[str, Any]
    forbidden_zones: list[str]
    conflict_warnings: list[str]
    recommended_expression: list[str]
    source_trace: list[dict[str, Any]]
    character_card_v2: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "character": self.character,
            "scenario": self.scenario,
            "core_invariants": self.core_invariants,
            "adjustable_variables": self.adjustable_variables,
            "forbidden_zones": self.forbidden_zones,
            "conflict_warnings": self.conflict_warnings,
            "recommended_expression": self.recommended_expression,
            "source_trace": self.source_trace,
            "character_card_v2": self.character_card_v2,
        }
