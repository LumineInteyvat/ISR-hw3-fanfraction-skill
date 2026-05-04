from __future__ import annotations

from .schemas import Assertion, BranchRecommendation, CharacterDeviationConfig, Conflict


CATEGORIES = ["canon_safe", "fanon_consensus", "niche_but_coherent"]


def recommend_diverse_branches(assertions: list[Assertion], conflicts: list[Conflict], scenario: str, config: CharacterDeviationConfig) -> list[BranchRecommendation]:
    traces = [assertion.source_trace.to_dict() for assertion in assertions]
    credibility = _average_credibility(assertions, config)
    conflict_penalty = min(len(conflicts) * 0.1, 0.3)
    scenario_bonus = 0.1 if scenario in config.scenario_adapters else 0.0
    return [
        BranchRecommendation(
            category="canon_safe",
            title="保守贴近原著的表达分支",
            rationale="优先采用高可信来源和低 OOC 距离的断言。",
            score=round(min(1.0, credibility + scenario_bonus - conflict_penalty), 3),
            source_trace=traces,
        ),
        BranchRecommendation(
            category="fanon_consensus",
            title="粉丝共识表达分支",
            rationale="允许粉丝解释补足细节，但保留冲突警告。",
            score=round(min(1.0, credibility * 0.75 + 0.2 + scenario_bonus), 3),
            source_trace=traces,
        ),
        BranchRecommendation(
            category="niche_but_coherent",
            title="小众但自洽表达分支",
            rationale="选择证据较少但逻辑自洽、能适配当前场景的长尾解释。",
            score=round(min(1.0, 0.55 + scenario_bonus + _diversity_bonus(assertions)), 3),
            source_trace=traces,
        ),
    ]


def _average_credibility(assertions: list[Assertion], config: CharacterDeviationConfig) -> float:
    if not assertions:
        return 0.0
    values = []
    for assertion in assertions:
        channel = assertion.source_trace.source_channel
        values.append(float(config.source_channels.get(channel, {}).get("credibility", assertion.confidence)))
    return sum(values) / len(values)


def _diversity_bonus(assertions: list[Assertion]) -> float:
    channels = {assertion.source_trace.source_channel for assertion in assertions}
    return min(0.2, len(channels) * 0.05)
