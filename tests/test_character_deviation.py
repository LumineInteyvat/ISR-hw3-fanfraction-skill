import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".skills" / "story-info-collector" / "scripts"
CONFIG_DIR = ROOT / ".skills" / "story-info-collector" / "config" / "character_deviation"
sys.path.insert(0, str(SCRIPTS))

from character_deviation import pipeline
from character_deviation.config_loader import load_character_deviation_config
from character_deviation.graph_store import build_claim_graph
from character_deviation.llm_client import OfflineLLMClient
from character_deviation.prompt_renderer import PromptRenderer
from character_deviation.schemas import Assertion, SourceTrace

def make_assertion(assertion_id, source_id, claim, assertion_type="relationship"):
    return Assertion(
        assertion_id=assertion_id,
        subject="Example",
        assertion_type=assertion_type,
        claim=claim,
        confidence=0.8,
        source_trace=SourceTrace(
            source_id=source_id,
            source_type="canon",
            source_channel="canon",
            quote=claim,
            version="v1",
        ),
        attributes={"object": "Ally"},
    )


def test_default_config_loads_required_assertion_and_conflict_types():
    config = load_character_deviation_config(CONFIG_DIR)
    assert "personality_trait" in config.assertion_types
    assert "relationship_conflict" in config.conflict_types
    assert "modern_au" in config.scenario_adapters


def test_prompt_renderer_injects_context_without_hardcoded_prompt_logic():
    config = load_character_deviation_config(CONFIG_DIR)
    prompt = PromptRenderer(config).render(
        "assertion_extraction",
        {
            "character": "Example",
            "scenario": "modern_au",
            "source_snippets": ["Example keeps promises."],
        },
    )
    assert "Example" in prompt
    assert "modern_au" in prompt
    assert "Example keeps promises." in prompt


def test_offline_llm_extracts_structured_assertions_with_source_trace():
    client = OfflineLLMClient()
    result = client.complete_json("assertion_extraction", "Example trusts Ally.", {}, {"source_id": "s1"})
    assert result["assertions"][0]["source_id"] == "s1"
    assert result["assertions"][0]["claim"] == "Example trusts Ally."


def test_multiple_sources_are_not_merged_in_claim_graph():
    assertions = [
        make_assertion("a1", "s1", "Example trusts Ally"),
        make_assertion("a2", "s2", "Example distrusts Ally"),
    ]
    graph = build_claim_graph(assertions)
    assert len(graph.assertions) == 2
    assert {a.source_trace.source_id for a in graph.assertions} == {"s1", "s2"}


def test_relationship_conflict_is_detected_for_same_character_pair():
    assertions = [
        make_assertion("a1", "s1", "Example trusts Ally", assertion_type="relationship"),
        make_assertion("a2", "s2", "Example distrusts Ally", assertion_type="relationship"),
    ]
    report = pipeline.detect_conflicts(assertions, OfflineLLMClient(), load_character_deviation_config(CONFIG_DIR))
    assert report.conflicts[0].conflict_type == "relationship_conflict"


def test_au_scenario_adjusts_variables_without_changing_core_invariants():
    config = load_character_deviation_config(CONFIG_DIR)
    conditioning = pipeline.apply_scenario(
        [make_assertion("a1", "s1", "Example keeps promises", assertion_type="personality_trait")],
        "modern_au",
        config,
    )
    assert "keeps promises" in conditioning.core_invariants[0]
    assert conditioning.adjustments["world_constraints"] != "canon_default"


def test_three_branch_recommendation_includes_niche_coherent_branch():
    config = load_character_deviation_config(CONFIG_DIR)
    recommendations = pipeline.recommend_branches(
        [make_assertion("a1", "s1", "Example trusts Ally")],
        [],
        "modern_au",
        config,
    )
    assert {r.category for r in recommendations} == {"canon_safe", "fanon_consensus", "niche_but_coherent"}


def test_character_card_contains_source_trace():
    config = load_character_deviation_config(CONFIG_DIR)
    card = pipeline.generate_character_card(
        [make_assertion("a1", "s1", "Example trusts Ally")],
        [],
        [],
        "modern_au",
        config,
    )
    assert card.source_trace[0]["source_id"] == "s1"


def test_cli_offline_source_text_outputs_character_card_json(tmp_path):
    output = tmp_path / "card.json"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "analyze_character_deviation.py"),
            "--source-text",
            "Example trusts Ally.",
            "--source-channel",
            "canon",
            "--character",
            "Example",
            "--scenario",
            "modern_au",
            "--offline",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
    )
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "character_card" in data
    assert data["character_card"]["source_trace"]
