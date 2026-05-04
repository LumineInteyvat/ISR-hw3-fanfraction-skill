from __future__ import annotations

from .schemas import Assertion, ClaimGraph, GraphEdge, GraphNode


EDGE_TYPES = {"supports", "contradicts", "supplements", "derives_from", "scenario_adapts"}


def build_claim_graph(assertions: list[Assertion]) -> ClaimGraph:
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    for assertion in assertions:
        source_id = f"source:{assertion.source_trace.source_id}"
        assertion_id = f"assertion:{assertion.assertion_id}"
        character_id = f"character:{assertion.subject}"
        type_node_id = _type_node(assertion)
        nodes[source_id] = GraphNode(source_id, "Source", assertion.source_trace.to_dict())
        nodes[assertion_id] = GraphNode(assertion_id, "Assertion", assertion.to_dict())
        nodes[character_id] = GraphNode(character_id, "Character", {"name": assertion.subject})
        nodes[type_node_id] = GraphNode(type_node_id, _node_type_for(assertion.assertion_type), {"claim": assertion.claim})
        edges.append(GraphEdge(source_id, assertion_id, "derives_from"))
        edges.append(GraphEdge(assertion_id, character_id, "supports"))
        edges.append(GraphEdge(assertion_id, type_node_id, "supplements"))
    _add_pairwise_edges(assertions, edges)
    return ClaimGraph(nodes=list(nodes.values()), edges=edges, assertions=list(assertions))


def _type_node(assertion: Assertion) -> str:
    suffix = assertion.attributes.get("object") or assertion.claim
    if assertion.assertion_type == "relationship":
        return f"relationship:{assertion.subject}:{suffix}"
    if assertion.assertion_type == "event_memory":
        return f"event:{suffix}"
    return f"trait:{assertion.subject}:{suffix}"


def _node_type_for(assertion_type: str) -> str:
    if assertion_type == "relationship":
        return "Relationship"
    if assertion_type == "event_memory":
        return "Event"
    return "Trait"


def _add_pairwise_edges(assertions: list[Assertion], edges: list[GraphEdge]) -> None:
    for left_index, left in enumerate(assertions):
        for right in assertions[left_index + 1 :]:
            if left.subject != right.subject:
                continue
            if _polarity_conflicts(left.claim, right.claim):
                edges.append(GraphEdge(f"assertion:{left.assertion_id}", f"assertion:{right.assertion_id}", "contradicts"))
            elif left.assertion_type == right.assertion_type:
                edges.append(GraphEdge(f"assertion:{left.assertion_id}", f"assertion:{right.assertion_id}", "supplements"))


def _polarity_conflicts(left: str, right: str) -> bool:
    left_lower = left.lower()
    right_lower = right.lower()
    return ("trust" in left_lower and "distrust" in right_lower) or ("distrust" in left_lower and "trust" in right_lower) or ("相信" in left and "不信" in right) or ("不信" in left and "相信" in right)
