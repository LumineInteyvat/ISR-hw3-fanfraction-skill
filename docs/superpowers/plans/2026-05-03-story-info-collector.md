# Story Info Collector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Chinese Claude / Claude Code skill that collects story-writing source material and outputs traceable raw, extracted_document, Source, and Evidence Chunk files.

**Architecture:** Use a Python CLI as the orchestration entrypoint, small Python utility modules for cache/manifest/text extraction, and source-specific adapters for Fandom, obcSpider, and Crawlbase Reddit. Keep stage 1 file-based and deterministic: no database, no Claim extraction, no KG generation, and no OOC judgment.

**Tech Stack:** Python 3, PyYAML, pytest, JSON Schema documents, Markdown, TypeScript adapter stub for FandomScraper, optional crawlbase and obcSpider runtime dependencies.

---

## File Structure

Create and implement:

- `.skills/story-info-collector/SKILL.md` — Chinese skill behavior specification loaded by Claude / Claude Code.
- `.skills/story-info-collector/README.md` — Chinese user documentation for install, config, dry-run, and limitations.
- `.skills/story-info-collector/config.example.yaml` — example configuration with all paths and source options.
- `.skills/story-info-collector/prompts/keyword-extraction.zh.md` — Chinese prompt for keyword_plan generation.
- `.skills/story-info-collector/prompts/clarification.zh.md` — Chinese prompt for clarification questions.
- `.skills/story-info-collector/prompts/source-routing.zh.md` — Chinese prompt for source routing.
- `.skills/story-info-collector/scripts/collect_story_info.py` — main CLI orchestration script.
- `.skills/story-info-collector/scripts/adapters/fandom_scraper.ts` — FandomScraper adapter CLI with dry-run support.
- `.skills/story-info-collector/scripts/adapters/obc_spider_adapter.py` — obcSpider adapter with mapping and dry-run support.
- `.skills/story-info-collector/scripts/adapters/crawlbase_reddit_adapter.py` — Crawlbase Reddit adapter with token-safe skipped behavior.
- `.skills/story-info-collector/scripts/utils/cache.py` — slug, stable hash, path helper, and cache hit helpers.
- `.skills/story-info-collector/scripts/utils/manifest.py` — manifest load/save/cache/upsert helpers.
- `.skills/story-info-collector/scripts/utils/text_extract.py` — extraction, Markdown writing, Source building, and chunking.
- `.skills/story-info-collector/schemas/keyword_plan.schema.json` — keyword_plan schema.
- `.skills/story-info-collector/schemas/source_manifest.schema.json` — manifest schema.
- `.skills/story-info-collector/schemas/extracted_document.schema.json` — extracted_document schema.
- `.skills/story-info-collector/schemas/source.schema.json` — Source schema.
- `.skills/story-info-collector/schemas/evidence_chunk.schema.json` — Evidence Chunk schema.
- `tests/test_story_info_collector.py` — pytest coverage for dry-run, cache, mappings, frontmatter, keyword_plan, clarification, Source/Chunk.
- docs data directories with `.gitkeep` files.

## Task 1: Initialize repository and directory skeleton

**Files:**
- Create: `.skills/story-info-collector/.gitkeep`
- Create: `.skills/story-info-collector/prompts/.gitkeep`
- Create: `.skills/story-info-collector/scripts/adapters/.gitkeep`
- Create: `.skills/story-info-collector/scripts/utils/.gitkeep`
- Create: `.skills/story-info-collector/schemas/.gitkeep`
- Create: `docs/character-information/.gitkeep`
- Create: `docs/world-information/.gitkeep`
- Create: `docs/plot-information/.gitkeep`
- Create: `docs/relationship-information/.gitkeep`
- Create: `docs/voice-lines/.gitkeep`
- Create: `docs/forum-analysis/.gitkeep`
- Create: `docs/raw/fandom/.gitkeep`
- Create: `docs/raw/obc/.gitkeep`
- Create: `docs/raw/reddit/.gitkeep`
- Create: `docs/manifests/.gitkeep`
- Create: `docs/sources/.gitkeep`
- Create: `docs/chunks/.gitkeep`
- Create: `tests/.gitkeep`

- [ ] **Step 1: Initialize git repository**

Run:

```bash
git init
```

Expected: repository initialized in `/home/lumine/claude-workspace/ISR-fanfiction-skill/.git`.

- [ ] **Step 2: Create directories and .gitkeep files**

Run:

```bash
mkdir -p .skills/story-info-collector/prompts .skills/story-info-collector/scripts/adapters .skills/story-info-collector/scripts/utils .skills/story-info-collector/schemas docs/character-information docs/world-information docs/plot-information docs/relationship-information docs/voice-lines docs/forum-analysis docs/raw/fandom docs/raw/obc docs/raw/reddit docs/manifests docs/sources docs/chunks tests && touch .skills/story-info-collector/.gitkeep .skills/story-info-collector/prompts/.gitkeep .skills/story-info-collector/scripts/adapters/.gitkeep .skills/story-info-collector/scripts/utils/.gitkeep .skills/story-info-collector/schemas/.gitkeep docs/character-information/.gitkeep docs/world-information/.gitkeep docs/plot-information/.gitkeep docs/relationship-information/.gitkeep docs/voice-lines/.gitkeep docs/forum-analysis/.gitkeep docs/raw/fandom/.gitkeep docs/raw/obc/.gitkeep docs/raw/reddit/.gitkeep docs/manifests/.gitkeep docs/sources/.gitkeep docs/chunks/.gitkeep tests/.gitkeep
```

Expected: command exits 0.

- [ ] **Step 3: Verify skeleton**

Run:

```bash
find .skills docs tests -maxdepth 4 -type d | sort
```

Expected output includes `.skills/story-info-collector`, `docs/sources`, `docs/chunks`, and `tests`.

- [ ] **Step 4: Commit skeleton**

```bash
git add .skills docs tests
git commit -m "chore: initialize story collector skeleton"
```

## Task 2: Add schemas and configuration

**Files:**
- Create: `.skills/story-info-collector/config.example.yaml`
- Create: `.skills/story-info-collector/schemas/keyword_plan.schema.json`
- Create: `.skills/story-info-collector/schemas/source_manifest.schema.json`
- Create: `.skills/story-info-collector/schemas/extracted_document.schema.json`
- Create: `.skills/story-info-collector/schemas/source.schema.json`
- Create: `.skills/story-info-collector/schemas/evidence_chunk.schema.json`

- [ ] **Step 1: Write config.example.yaml**

Create `.skills/story-info-collector/config.example.yaml` with:

```yaml
project:
  default_language: zh
  allow_english_search: true
  docs_root: docs

cache:
  enabled: true
  manifest_path: docs/manifests/source_manifest.json
  refresh_days: 30
  default_refresh: false

fandom:
  enabled: true
  default_lang: en
  attrs:
    - age
    - status
    - images
    - affiliation
    - occupations
    - personality
    - appearance
    - relationships
    - story

obc:
  enabled: true
  default_lang: zh
  games:
    genshin:
      configuration_key: genshin_impact
    hsr:
      configuration_key: "honkai:_star_rail"

reddit:
  enabled: true
  token_env: CRAWLBASE_TOKEN
  max_posts_per_query: 20
  sort: relevance
  subreddits:
    - Genshin_Lore
    - Genshin_Impact
    - HonkaiStarRail

storage:
  categories:
    character_information: docs/character-information
    world_information: docs/world-information
    plot_information: docs/plot-information
    relationship_information: docs/relationship-information
    voice_lines: docs/voice-lines
    forum_analysis: docs/forum-analysis
  raw_fandom: docs/raw/fandom
  raw_obc: docs/raw/obc
  raw_reddit: docs/raw/reddit
  manifests: docs/manifests
  sources: docs/sources
  chunks: docs/chunks
```

- [ ] **Step 2: Write keyword_plan schema**

Create `.skills/story-info-collector/schemas/keyword_plan.schema.json` with a Draft 2020-12 JSON schema requiring `original_request`, detected arrays, `search_keywords`, `information_needs`, `source_routes`, `clarification_needed`, `clarification_questions`, and `classified_keywords`.

- [ ] **Step 3: Write source manifest schema**

Create `.skills/story-info-collector/schemas/source_manifest.schema.json` with an object containing `entries`, where each entry requires `manifest_key`, `source_type`, `source_name`, `source_url`, `query`, `query_hash`, `character`, `work`, `language`, `collected_at`, `raw_path`, `extracted_path`, `source_path`, `chunk_paths`, `status`, and `notes`.

- [ ] **Step 4: Write extracted_document schema**

Create `.skills/story-info-collector/schemas/extracted_document.schema.json` requiring `document_id`, `source_type`, `source_name`, `source_url`, `language`, `character`, `work`, `category`, `title`, `text`, `metadata`, and `collected_at`.

- [ ] **Step 5: Write source schema**

Create `.skills/story-info-collector/schemas/source.schema.json` requiring `source_id`, `source_type`, `source_name`, `source_url`, `work`, `character`, `language`, `query`, `query_hash`, `collected_at`, `raw_path`, `extracted_path`, `chunk_paths`, and `metadata`.

- [ ] **Step 6: Write evidence_chunk schema**

Create `.skills/story-info-collector/schemas/evidence_chunk.schema.json` requiring `chunk_id`, `source_id`, `source_type`, `source_name`, `source_url`, `work`, `character`, `language`, `category`, `chunk_index`, `title`, `text`, `evidence_scope`, and `metadata`.

- [ ] **Step 7: Commit schemas and config**

```bash
git add .skills/story-info-collector/config.example.yaml .skills/story-info-collector/schemas
git commit -m "feat: add story collector schemas and config"
```

## Task 3: Add Chinese skill documentation and prompts

**Files:**
- Create: `.skills/story-info-collector/SKILL.md`
- Create: `.skills/story-info-collector/README.md`
- Create: `.skills/story-info-collector/prompts/keyword-extraction.zh.md`
- Create: `.skills/story-info-collector/prompts/clarification.zh.md`
- Create: `.skills/story-info-collector/prompts/source-routing.zh.md`

- [ ] **Step 1: Write SKILL.md**

Create Chinese `SKILL.md` covering name, applicable scenarios, non-applicable scenarios, input/output, clarification, keyword classification, routing, cache, storage, safety, and sample dialog. It must state that the skill only collects material and extracts text; does not judge characters, detect OOC, treat fan discussion as canon, or crawl private Reddit pages.

- [ ] **Step 2: Write README.md**

Create Chinese `README.md` with installation commands:

```bash
pip install pyyaml pytest crawlbase
npm install fandom-scraper tsx
```

Include dry-run command, normal command, and `export CRAWLBASE_TOKEN="..."` setup.

- [ ] **Step 3: Write keyword extraction prompt**

Create `keyword-extraction.zh.md` instructing the model to output only JSON keyword_plan and to ask for clarification when role/work/context/language/source scope is unclear.

- [ ] **Step 4: Write clarification prompt**

Create `clarification.zh.md` listing the five clarification cases from prompt.md and requiring short Chinese questions.

- [ ] **Step 5: Write source routing prompt**

Create `source-routing.zh.md` mapping character/profile/worldbuilding to Fandom, official voice lines to obc, and forum interpretation to Reddit.

- [ ] **Step 6: Commit docs and prompts**

```bash
git add .skills/story-info-collector/SKILL.md .skills/story-info-collector/README.md .skills/story-info-collector/prompts
git commit -m "docs: describe story collector skill"
```

## Task 4: Implement utility modules with tests

**Files:**
- Create: `.skills/story-info-collector/scripts/utils/cache.py`
- Create: `.skills/story-info-collector/scripts/utils/manifest.py`
- Create: `.skills/story-info-collector/scripts/utils/text_extract.py`
- Create: `.skills/story-info-collector/scripts/__init__.py`
- Create: `.skills/story-info-collector/scripts/utils/__init__.py`
- Create: `tests/test_story_info_collector.py`

- [ ] **Step 1: Write failing utility tests**

Create tests for stable query hash, ASCII slug, manifest idempotent upsert, Markdown frontmatter, and chunk generation.

- [ ] **Step 2: Run failing tests**

Run:

```bash
pytest tests/test_story_info_collector.py -q
```

Expected: FAIL because modules do not exist.

- [ ] **Step 3: Implement cache.py**

Implement `stable_query_hash`, `slugify`, `build_base_filename`, and `is_cache_hit`.

- [ ] **Step 4: Implement manifest.py**

Implement `load_manifest`, `save_manifest`, `make_manifest_key`, `find_cached_entry`, and `upsert_entry`.

- [ ] **Step 5: Implement text_extract.py**

Implement extraction for dry-run shaped raw documents, Markdown writing, Source construction, semantic-ish paragraph chunking, and JSON writers.

- [ ] **Step 6: Run utility tests**

Run:

```bash
pytest tests/test_story_info_collector.py -q
```

Expected: utility tests PASS.

- [ ] **Step 7: Commit utilities**

```bash
git add .skills/story-info-collector/scripts tests/test_story_info_collector.py
git commit -m "feat: add story collector utility layer"
```

## Task 5: Implement adapters with tests

**Files:**
- Create: `.skills/story-info-collector/scripts/adapters/__init__.py`
- Create: `.skills/story-info-collector/scripts/adapters/obc_spider_adapter.py`
- Create: `.skills/story-info-collector/scripts/adapters/crawlbase_reddit_adapter.py`
- Create: `.skills/story-info-collector/scripts/adapters/fandom_scraper.ts`
- Modify: `tests/test_story_info_collector.py`

- [ ] **Step 1: Add failing adapter tests**

Add tests for obc game mapping, lang_id mapping, Reddit token missing returns skipped, and Fandom dry-run raw shape through output file existence.

- [ ] **Step 2: Run failing adapter tests**

Run:

```bash
pytest tests/test_story_info_collector.py -q
```

Expected: FAIL because adapters are missing.

- [ ] **Step 3: Implement obc_spider_adapter.py**

Implement `map_configuration_key`, `map_lang_id`, `collect_obc`, and CLI dry-run behavior.

- [ ] **Step 4: Implement crawlbase_reddit_adapter.py**

Implement `build_reddit_search_url`, `collect_reddit`, skipped behavior without token, and CLI dry-run behavior.

- [ ] **Step 5: Implement fandom_scraper.ts**

Implement a TypeScript CLI that supports `--dry-run`, writes raw JSON to the requested output path, and contains the real FandomScraper flow behind non-dry-run mode.

- [ ] **Step 6: Run adapter tests**

Run:

```bash
pytest tests/test_story_info_collector.py -q
```

Expected: adapter tests PASS.

- [ ] **Step 7: Commit adapters**

```bash
git add .skills/story-info-collector/scripts/adapters tests/test_story_info_collector.py
git commit -m "feat: add story collector adapters"
```

## Task 6: Implement main CLI orchestration with tests

**Files:**
- Create: `.skills/story-info-collector/scripts/collect_story_info.py`
- Modify: `tests/test_story_info_collector.py`

- [ ] **Step 1: Add failing CLI tests**

Add tests that run dry-run CLI with the Furina example and assert generated manifest, Source, Chunk, and Markdown files exist. Add a test where the request lacks a character and assert clarification questions are printed.

- [ ] **Step 2: Run failing CLI tests**

Run:

```bash
pytest tests/test_story_info_collector.py -q
```

Expected: FAIL because CLI is missing.

- [ ] **Step 3: Implement collect_story_info.py**

Implement argument parsing, YAML config loading, heuristic keyword_plan generation, clarification exit, task routing, cache checking, adapter calls, extraction, Source/Chunk writing, manifest upsert, and summary output.

- [ ] **Step 4: Run CLI tests**

Run:

```bash
pytest tests/test_story_info_collector.py -q
```

Expected: CLI tests PASS.

- [ ] **Step 5: Run manual dry-run command**

Run:

```bash
python .skills/story-info-collector/scripts/collect_story_info.py --request "我想写一个关于芙宁娜在现代AU中重新面对审判创伤的故事" --config .skills/story-info-collector/config.example.yaml --dry-run
```

Expected output includes `新增 source 数量`, `新增 chunk 数量`, and `Claim 抽取输入路径`.

- [ ] **Step 6: Commit CLI**

```bash
git add .skills/story-info-collector/scripts/collect_story_info.py tests/test_story_info_collector.py docs
git commit -m "feat: add story collector CLI"
```

## Task 7: Final verification and cleanup

**Files:**
- Modify as needed based on verification.

- [ ] **Step 1: Run full test suite**

Run:

```bash
pytest -q
```

Expected: all tests PASS.

- [ ] **Step 2: Run dry-run twice to verify cache hit**

Run the dry-run command from Task 6 twice.

Expected: second run reports at least one cache hit and does not duplicate manifest entries.

- [ ] **Step 3: Check no forbidden stage 1 outputs exist**

Run:

```bash
find docs -type f | grep -E 'claim|kg|ooc|persona|conflict' || true
```

Expected: no stage-1 generated Claim/KG/OOC/persona/conflict artifacts.

- [ ] **Step 4: Check git status**

Run:

```bash
git status --short
```

Expected: clean or only intentional changes.

- [ ] **Step 5: Commit final fixes if any**

```bash
git add .
git commit -m "test: verify story collector dry run"
```

Only run this commit if Step 4 shows intentional uncommitted changes.

## Self-Review

- Spec coverage: plan covers skill docs, README, config, prompts, schemas, adapters, utilities, CLI, docs directories, cache, manifest, Source, Chunk, dry-run, and tests.
- Placeholder scan: no TBD/TODO placeholders remain in execution steps; high-level content tasks point to exact files and required sections.
- Type consistency: names used across plan are stable: keyword_plan, extracted_document, Source, Evidence Chunk, manifest entry, `source_path`, `chunk_paths`, `source_type`, `source_url`, `query_hash`.
