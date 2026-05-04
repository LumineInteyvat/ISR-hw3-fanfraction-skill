# Story Profile Customization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make story-info-collector configurable per story prompt through profile files, persist Crawlbase token locally, and treat Fandom as the primary official information source while skipping real obcSpider implementation.

**Architecture:** Add a story profile layer loaded by the CLI and used by keyword planning instead of hard-coded character/work logic. Keep secrets outside git in `.claude/settings.local.json`; keep obc route disabled/skipped by default while Fandom and Reddit remain configurable.

**Tech Stack:** Python 3, PyYAML, pytest, Claude Code settings JSON, YAML profile files, existing story-info-collector scripts.

---

## File Structure

- Modify: `.gitignore` — ignore `tmp/` and `.claude/settings.local.json`.
- Create: `.claude/settings.local.json` — local untracked environment containing `CRAWLBASE_TOKEN` copied from `tmp/key.txt`.
- Create: `.skills/story-info-collector/profiles/genshin.story-profile.yaml` — default Genshin profile with works, characters, scene keywords, routes, and source-type policy.
- Create: `.skills/story-info-collector/schemas/story_profile.schema.json` — schema for profile data.
- Create: `.skills/story-info-collector/scripts/utils/profile.py` — profile loading and keyword-plan helpers.
- Modify: `.skills/story-info-collector/scripts/collect_story_info.py` — add `--profile`, `--character`, `--work`, `--scene`, `--include-reddit`, and `--exclude` options; use profile-based planning.
- Modify: `.skills/story-info-collector/config.example.yaml` — add default profile path and disable obc by default.
- Modify: `.skills/story-info-collector/README.md` — document profile customization and local token persistence.
- Modify: `.skills/story-info-collector/SKILL.md` — document profile-driven customization.
- Modify: `tests/test_story_info_collector.py` — cover profile-driven character detection, CLI overrides, obc disabled, and Reddit env availability behavior.

## Task 1: Persist local Crawlbase token safely

- [ ] **Step 1: Read tmp/key.txt without printing the secret**

Run a Python command that loads `tmp/key.txt`, strips whitespace, and writes only metadata to stdout.

- [ ] **Step 2: Write `.claude/settings.local.json`**

Create `.claude/settings.local.json` with:

```json
{
  "env": {
    "CRAWLBASE_TOKEN": "<token copied from tmp/key.txt>"
  }
}
```

Do not print the token.

- [ ] **Step 3: Update `.gitignore`**

Ensure `.gitignore` contains:

```gitignore
tmp/
.claude/settings.local.json
```

- [ ] **Step 4: Verify settings file is ignored**

Run:

```bash
git check-ignore -q .claude/settings.local.json && git check-ignore -q tmp/key.txt
```

Expected: exit 0.

## Task 2: Add profile tests first

- [ ] **Step 1: Add failing tests**

Modify `tests/test_story_info_collector.py` to assert:

- `profile.load_story_profile()` loads `genshin.story-profile.yaml`.
- `generate_keyword_plan("我想写钟离在现代 AU 中处理契约创伤", "zh", profile)` detects character `钟离`, work `原神`, scene `现代 AU`, and routes `fandom` and `reddit`, not `obc` by default.
- CLI `--character 钟离 --work 原神 --scene 现代AU --profile ... --dry-run` generates source/chunk files.

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_story_info_collector.py -q
```

Expected: FAIL because `profile.py`, profile file, and CLI args do not exist.

## Task 3: Implement profile layer

- [ ] **Step 1: Create `profile.py`**

Implement:

- `load_story_profile(path)`
- `find_character(request, profile, explicit_character=None)`
- `find_work(request, profile, character=None, explicit_work=None)`
- `find_scenes(request, profile, explicit_scene=None)`
- `routes_for(profile, include_reddit=False)`
- `keywords_for(character, work, scenes, profile, language)`

- [ ] **Step 2: Create `genshin.story-profile.yaml`**

Include at least `芙宁娜`, `钟离`, and `纳西妲`; map aliases and English names; set Fandom as `official_reference`; disable obc by default; enable Reddit optionally.

- [ ] **Step 3: Create `story_profile.schema.json`**

Define works, characters, scenes, source_policy, and default_routes.

- [ ] **Step 4: Run tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_story_info_collector.py -q
```

Expected: profile unit tests pass, CLI tests may still fail until Task 4.

## Task 4: Wire profile into CLI

- [ ] **Step 1: Modify `collect_story_info.py`**

Add args:

```text
--profile
--character
--work
--scene
--include-reddit
--exclude
```

Change `generate_keyword_plan()` to accept `profile`, `explicit_character`, `explicit_work`, `explicit_scene`, `include_reddit`, and `exclusions`.

- [ ] **Step 2: Treat Fandom as official source by policy**

When profile `source_policy.fandom_source_type` is `official_reference`, `_context_for_route()` must set Fandom `source_type` to `official_reference` instead of `structured_fan_knowledge`.

- [ ] **Step 3: Disable obc by default**

`config.example.yaml` and profile default routes should omit `obc`. If `obc` appears, current dry-run behavior may remain, but real implementation is not required.

- [ ] **Step 4: Run tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_story_info_collector.py -q
```

Expected: all tests pass.

## Task 5: Update docs and verify behavior

- [ ] **Step 1: Update README and SKILL.md**

Document:

- How to use `--profile`.
- How Claude Code can customize per-story behavior by editing a profile copy or passing CLI overrides.
- Fandom is treated as official/primary information for this project.
- obc real crawling is intentionally not implemented in this step.
- API key is stored in local Claude Code settings, not committed.

- [ ] **Step 2: Run dry-run with Zhongli**

Run:

```bash
.venv/bin/python .skills/story-info-collector/scripts/collect_story_info.py \
  --request "我想写钟离在现代 AU 中处理契约创伤" \
  --config .skills/story-info-collector/config.example.yaml \
  --profile .skills/story-info-collector/profiles/genshin.story-profile.yaml \
  --include-reddit \
  --dry-run
```

Expected: source and chunk outputs for fandom and reddit; no obc output.

- [ ] **Step 3: Run non-dry-run Reddit smoke if dependency/token available**

Run adapter-level smoke with Crawlbase token from Claude Code env if available. If dependency is absent, report that package installation is needed; do not print token.

- [ ] **Step 4: Final verification**

Run:

```bash
.venv/bin/python -m pytest tests/test_story_info_collector.py -q
git status --short
```

Expected: tests pass; only intended tracked changes and ignored local secret files.

## Self-Review

- Spec coverage: covers safe token persistence, no obc real implementation, Fandom official policy, profile customization, CLI overrides, tests, docs.
- Placeholder scan: no unresolved implementation placeholders; only `<token copied from tmp/key.txt>` is an instruction not committed content.
- Type consistency: profile functions and CLI args are named consistently across tasks.
