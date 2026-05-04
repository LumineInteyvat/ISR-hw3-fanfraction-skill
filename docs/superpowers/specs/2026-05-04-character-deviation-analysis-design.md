# Character Deviation Analysis Design

## Goal

Add a reusable, configurable fiction-writing assistant capability to the existing Python `story-info-collector` skill. The new subsystem detects character-canon deviations, preserves source-aware evidence, adapts analysis to writing scenarios, recommends coherent interpretation branches, and generates temporary character cards for the current story context.

The design prioritizes extensibility. Core pipeline code must not hardcode user prompts, fandoms, characters, scenario types, assertion types, conflict types, or output formats. Works, roles, scenarios, and prompt behavior are injected through config, source metadata, and prompt templates.

## Chosen Approach

Extend the existing Python skill in `.skills/story-info-collector` instead of migrating to TypeScript or creating a separate package. This reuses the current profile-driven collector, evidence/source data model, skill entrypoint, and pytest setup while adding a separate `character_deviation` subsystem with clear boundaries.

## Architecture

The subsystem will be organized in four layers under the existing skill:

- `config/character_deviation/`: assertion types, source channels, conflict types, scenario adapters, output formats, and centralized prompt templates.
- `schemas/character_deviation/`: explicit schema objects for assertions, sources, claim graph, deviation reports, scenario conditioning, recommendations, and character cards.
- `scripts/character_deviation/`: pipeline stages for extraction, graph building, conflict detection, scenario conditioning, branch recommendation, and card generation.
- `scripts/character_deviation/services/`: config loading, prompt rendering, LLM clients, reranking, and graph storage helpers.

Suggested Python mapping:

```text
.skills/story-info-collector/
  config/character_deviation/
    assertion_types.yaml
    source_channels.yaml
    conflict_types.yaml
    scenario_adapters.yaml
    output_formats.yaml
    prompts/
      assertion_extraction.md
      conflict_detection.md
      scenario_conditioning.md
      branch_recommendation.md
      character_card_generation.md
  scripts/
    analyze_character_deviation.py
    character_deviation/
      schemas/
      pipeline/
      services/
```

## Data Flow

1. **Input normalization**
   - CLI accepts existing story-info-collector outputs such as source manifests, extracted documents, or evidence chunk JSON/JSONL.
   - CLI also accepts direct text or JSON source input for small standalone analyses.
   - All inputs normalize into source-aware documents containing `source_id`, `source_type` or source channel, version, original snippets, and metadata.

2. **Assertion extraction**
   - `assertion_types.yaml` defines assertion schema metadata and type vocabulary.
   - `prompts/assertion_extraction.md` defines extraction behavior.
   - The pipeline calls `LLMClient` and validates returned JSON into a uniform `Assertion` schema.
   - Core code depends only on `Assertion`, not on concrete prompt text or fandom-specific labels.

3. **Source-aware claim graph**
   - Graph nodes include Character, Trait, Relationship, Event, Source, and Assertion.
   - Edge types include supports, contradicts, supplements, derives_from, and scenario_adapts.
   - Each assertion retains `source_id`, `source_type`, source channel, quote, confidence, and version.
   - Multiple sources are not merged into a single conclusion early; conflicting and supplemental claims remain visible for audit.

4. **Conflict detection**
   - Relevant assertion pairs are evaluated by LLM or offline deterministic logic.
   - Conflict types and severity rules come from config.
   - Output is a structured `DeviationReport` that lists evidence and reasoning without averaging contradictory evidence into one answer.

5. **Scenario conditioning**
   - Scenario adapters support cases such as modern AU, postwar, if-line, darkening, and romance line through config.
   - Scenario conditioning preserves core invariants and adjusts only `behavior_weight`, `world_constraints`, `relationship_pressure`, and `acceptable_ooc_threshold`.
   - Scenario adaptation is represented in schema and graph edges rather than rewriting the character globally.

6. **Branch recommendation**
   - Reranking returns exactly three categories: `canon_safe`, `fanon_consensus`, and `niche_but_coherent`.
   - Ranking considers source credibility, logical coherence, scenario compatibility, evidence diversity, and distance from core personality.
   - Diversity-aware reranking prevents high-frequency fan consensus from suppressing coherent long-tail branches.

7. **Temporary character card generation**
   - Character cards default to JSON output.
   - Required fields include `core_invariants`, `adjustable_variables`, `forbidden_zones`, `conflict_warnings`, `recommended_expression`, and `source_trace`.
   - The schema reserves Character Card V2 extension fields without binding the pipeline to one fixed output shape.

## DeepSeek LLM Integration

DeepSeek is the default real LLM provider for assertion extraction and analysis. The project local settings provide:

- `DEEPSEEK_API_KEY`
- `FICTION_ASSISTANT_LLM_PROVIDER=deepseek`

`DeepSeekClient` implements a provider-neutral `LLMClient` interface, for example:

```python
complete_json(task: str, prompt: str, schema_hint: dict, metadata: dict) -> dict
```

Endpoint, model, and temperature are config-driven. Pipeline stages receive an `LLMClient` instance and do not import DeepSeek-specific code directly.

Default CLI behavior uses the real configured provider. If the provider call fails, the command fails with a clear error. The CLI supports `--offline`, which uses deterministic fallback behavior for tests, demos, and no-network development. Offline output must be labeled by client metadata and should not masquerade as real LLM analysis.

## Prompt Customization Layer

All LLM prompts live under `config/character_deviation/prompts/`. Business logic does not contain long prompt strings.

`PromptRenderer` selects and renders templates by:

- task stage,
- character,
- fandom or world,
- scenario,
- output format,
- profile or adapter overrides.

User prompt content is passed as template variables and source context, not read globally or embedded in core logic. Future customization for a new fandom or character should usually require config/profile/template changes, not pipeline changes.

## CLI and Skill Entry

Add a minimum CLI entrypoint under the existing skill, for example:

```bash
python3 .skills/story-info-collector/scripts/analyze_character_deviation.py \
  --profile .skills/story-info-collector/profiles/genshin.story-profile.yaml \
  --input docs/story-info/genshin/evidence_chunks.jsonl \
  --character "Example Character" \
  --scenario "modern_au" \
  --output /tmp/character_card.json
```

Standalone text input is also supported:

```bash
python3 .skills/story-info-collector/scripts/analyze_character_deviation.py \
  --source-text "Example Character keeps promises even under pressure." \
  --source-channel canon \
  --character "Example Character" \
  --scenario "postwar" \
  --offline
```

The CLI should be suitable for direct skill invocation and for tests. Output defaults to JSON and includes the deviation report, recommendations, character card, and source trace.

## Testing

Add pytest coverage for the required minimum behavior:

- multiple source assertions are retained separately and not prematurely merged;
- relationship conflicts for the same character can be detected;
- AU scenario conditioning adjusts variables without changing core invariants;
- three branch recommendation categories are returned, including a coherent long-tail branch;
- generated temporary character cards include source trace.

Tests use an offline or mock `LLMClient` and do not require network access or real DeepSeek calls. The real DeepSeek client is exercised through the CLI path when the environment is configured, not as a unit-test requirement.

## Project README

After implementation, add a workspace-level `README.md` describing the full project:

- story information collection;
- character deviation analysis;
- architecture and extension points;
- config and prompt customization;
- DeepSeek and Crawbase environment variables;
- CLI examples;
- testing instructions;
- source trace and audit philosophy.

## Non-goals

- Do not migrate the project to TypeScript in this iteration.
- Do not hardcode Genshin, any specific character, or any specific user prompt into core logic.
- Do not collapse contradictory evidence into one canonical answer.
- Do not make offline deterministic fallback the default when real LLM analysis is requested.
