import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".skills" / "story-info-collector" / "scripts"


def load_module(name, relative_path):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_query_hash_is_stable_and_slug_is_ascii():
    cache = load_module("cache", ".skills/story-info-collector/scripts/utils/cache.py")

    assert cache.stable_query_hash("芙宁娜 trial") == cache.stable_query_hash("芙宁娜 trial")
    slug = cache.slugify("原神：芙宁娜 modern AU")

    assert slug == "yuan-shen-fu-zhu-na-modern-au"
    assert slug.isascii()


def test_manifest_upsert_is_idempotent(tmp_path):
    manifest_mod = load_module("manifest", ".skills/story-info-collector/scripts/utils/manifest.py")
    manifest = {"entries": []}
    entry = {
        "manifest_key": "furina|genshin|fandom|zh|abc123",
        "source_type": "structured_fan_knowledge",
        "source_name": "Fandom",
        "source_url": "https://example.invalid/furina",
        "query": "Furina personality",
        "query_hash": "abc123",
        "character": "芙宁娜",
        "work": "原神",
        "language": "zh",
        "collected_at": "2026-05-03T00:00:00Z",
        "raw_path": "docs/raw/fandom/raw.json",
        "extracted_path": "docs/character-information/doc.json",
        "source_path": "docs/sources/source.json",
        "chunk_paths": ["docs/chunks/chunk.json"],
        "status": "success",
        "notes": "dry-run",
    }

    manifest_mod.upsert_entry(manifest, entry)
    manifest_mod.upsert_entry(manifest, entry)

    assert len(manifest["entries"]) == 1
    assert manifest_mod.find_cached_entry(manifest, entry["manifest_key"])["character"] == "芙宁娜"


def test_text_extract_writes_markdown_source_and_chunks(tmp_path):
    text_extract = load_module("text_extract", ".skills/story-info-collector/scripts/utils/text_extract.py")
    raw = {
        "status": "success",
        "source_name": "Fandom dry-run",
        "source_url": "https://example.invalid/furina",
        "title": "芙宁娜",
        "sections": {
            "personality": "芙宁娜在公开场合表现夸张，但内心承受审判相关压力。",
            "relationships": "她与枫丹民众、那维莱特有复杂关系。",
        },
    }
    context = {
        "source_type": "structured_fan_knowledge",
        "source_name": "Fandom dry-run",
        "source_url": "https://example.invalid/furina",
        "language": "zh",
        "character": "芙宁娜",
        "work": "原神",
        "category": "character-information",
        "query": "芙宁娜 性格分析",
        "query_hash": "abc123",
        "adapter": "fandom",
        "raw_path": str(tmp_path / "raw.json"),
    }

    document = text_extract.extract_document(raw, context)
    source = text_extract.build_source(document, context, str(tmp_path / "doc.json"))
    chunks = text_extract.chunk_document(document, source, context)
    md_path = tmp_path / "doc.md"

    text_extract.write_markdown(document, md_path)

    assert "source_type: structured_fan_knowledge" in md_path.read_text(encoding="utf-8")
    assert "source_url: https://example.invalid/furina" in md_path.read_text(encoding="utf-8")
    assert source["source_id"].startswith("src_")
    assert chunks[0]["chunk_id"].startswith("chk_")
    assert chunks[0]["source_id"] == source["source_id"]


def test_obc_mappings_are_correct():
    obc = load_module("obc", ".skills/story-info-collector/scripts/adapters/obc_spider_adapter.py")

    assert obc.map_configuration_key("原神") == "genshin_impact"
    assert obc.map_configuration_key("Honkai Star Rail") == "honkai:_star_rail"
    assert obc.map_lang_id("zh") == 0
    assert obc.map_lang_id("ja") == 1
    assert obc.map_lang_id("ko") == 2
    assert obc.map_lang_id("en") == 3


def test_reddit_without_token_is_skipped(monkeypatch, tmp_path):
    reddit = load_module("reddit", ".skills/story-info-collector/scripts/adapters/crawlbase_reddit_adapter.py")
    monkeypatch.delenv("CRAWLBASE_TOKEN", raising=False)
    monkeypatch.delenv("CRAWLBASE_JS_TOKEN", raising=False)

    result = reddit.collect_reddit(
        query="Furina personality analysis",
        subreddits=["Genshin_Lore"],
        output_dir=tmp_path,
        token_env="CRAWLBASE_TOKEN",
        dry_run=False,
    )

    assert result["status"] == "skipped"
    assert "CRAWLBASE_TOKEN" in result["notes"]


def test_reddit_crawlbase_response_is_json_serializable(monkeypatch, tmp_path):
    reddit = load_module("reddit", ".skills/story-info-collector/scripts/adapters/crawlbase_reddit_adapter.py")
    monkeypatch.setenv("CRAWLBASE_TOKEN", "test-token")
    monkeypatch.setenv("CRAWLBASE_JS_TOKEN", "test-js-token")

    class FakeCrawlingAPI:
        def __init__(self, settings):
            self.settings = settings

        def get(self, url, options=None):
            return {"status_code": 200, "body": b"reddit html", "headers": {b"content-type": b"text/html"}}

    fake_module = Mock(CrawlingAPI=FakeCrawlingAPI)
    with patch.dict(sys.modules, {"crawlbase": fake_module}):
        result = reddit.collect_reddit("Furina analysis", ["Genshin_Lore"], tmp_path, dry_run=False)

    json.dumps(result)
    assert result["responses"][0]["body"] == "reddit html"
    assert result["sections"]["forum_discussion"]
    assert result["token_env"] == "CRAWLBASE_JS_TOKEN"
    assert result["crawlbase_mode"] == "javascript"


def test_fandom_uses_crawlbase_js_token(monkeypatch, tmp_path):
    fandom = load_module("fandom", ".skills/story-info-collector/scripts/adapters/fandom_adapter.py")
    monkeypatch.setenv("CRAWLBASE_TOKEN", "test-token")
    monkeypatch.setenv("CRAWLBASE_JS_TOKEN", "test-js-token")

    class FakeCrawlingAPI:
        def __init__(self, settings):
            self.settings = settings

        def get(self, url, options=None):
            return {"status_code": 200, "body": {"title": "Furina", "content": "Furina performs confidence before Fontaine."}}

    with patch.dict(sys.modules, {"crawlbase": Mock(CrawlingAPI=FakeCrawlingAPI)}):
        result = fandom.collect_fandom("genshin-impact", "Furina")

    assert result["status"] == "success"
    assert result["source_name"] == "Crawlbase Fandom"
    assert result["token_env"] == "CRAWLBASE_JS_TOKEN"
    assert result["crawlbase_mode"] == "javascript"
    assert result["source_url"] == "https://genshin-impact.fandom.com/wiki/Furina"
    assert "Furina performs confidence" in result["sections"]["page"]


def test_fandom_accepts_page_title_override(monkeypatch):
    fandom = load_module("fandom", ".skills/story-info-collector/scripts/adapters/fandom_adapter.py")
    monkeypatch.setenv("CRAWLBASE_JS_TOKEN", "test-js-token")

    class FakeCrawlingAPI:
        def __init__(self, settings):
            self.settings = settings

        def get(self, url, options=None):
            assert url == "https://genshin-impact.fandom.com/wiki/Furina"
            return {"status_code": 200, "body": {"title": "Furina", "content": "Furina performs confidence."}}

    with patch.dict(sys.modules, {"crawlbase": Mock(CrawlingAPI=FakeCrawlingAPI)}):
        result = fandom.collect_fandom("genshin-impact", "芙宁娜", page_title="Furina")

    assert result["status"] == "success"
    assert result["source_url"] == "https://genshin-impact.fandom.com/wiki/Furina"


def test_raw_for_fandom_uses_ascii_profile_alias(monkeypatch, tmp_path):
    cli = load_module("collect_story_info", ".skills/story-info-collector/scripts/collect_story_info.py")
    captured = {}

    def fake_collect_fandom(wiki_name, character, language, page_title=None):
        captured["wiki_name"] = wiki_name
        captured["character"] = character
        captured["page_title"] = page_title
        return {"status": "success", "source_name": "Crawlbase Fandom", "source_url": "https://genshin-impact.fandom.com/wiki/Furina", "title": "Furina", "sections": {"page": "Furina text"}}

    monkeypatch.setattr(cli, "collect_fandom", fake_collect_fandom)
    config = {"storage": {"raw_fandom": str(tmp_path)}, "profile": {"works": [{"name": "原神", "wiki_name": "genshin-impact"}], "characters": [{"name": "芙宁娜", "aliases": ["芙宁娜", "Furina"]}]}}

    cli._raw_for_route("fandom", config, "芙宁娜", "原神", "zh", "query", False)

    assert captured == {"wiki_name": "genshin-impact", "character": "芙宁娜", "page_title": "Furina"}


def test_reddit_verification_page_is_failed(monkeypatch, tmp_path):
    reddit = load_module("reddit", ".skills/story-info-collector/scripts/adapters/crawlbase_reddit_adapter.py")
    monkeypatch.setenv("CRAWLBASE_TOKEN", "test-token")

    class FakeCrawlingAPI:
        def __init__(self, settings):
            self.settings = settings

        def get(self, url, options=None):
            return {"status_code": 200, "body": {"title": "Reddit - Please wait for verification", "content": ""}}

    with patch.dict(sys.modules, {"crawlbase": Mock(CrawlingAPI=FakeCrawlingAPI)}):
        result = reddit.collect_reddit("Furina analysis", ["Genshin_Lore"], tmp_path, dry_run=False)

    assert result["status"] == "failed"
    assert "verification" in result["notes"]


def test_fandom_transport_error_is_failed(monkeypatch):
    fandom = load_module("fandom", ".skills/story-info-collector/scripts/adapters/fandom_adapter.py")
    monkeypatch.setenv("CRAWLBASE_TOKEN", "test-token")

    class FakeCrawlingAPI:
        def __init__(self, settings):
            self.settings = settings

        def get(self, url, options=None):
            raise RuntimeError("blocked")

    with patch.dict(sys.modules, {"crawlbase": Mock(CrawlingAPI=FakeCrawlingAPI)}):
        result = fandom.collect_fandom("genshin-impact", "Furina")

    assert result["status"] == "failed"
    assert result["source_name"] == "Crawlbase Fandom"
    assert "blocked" in result["notes"]


def test_fandom_original_404_is_failed(monkeypatch):
    fandom = load_module("fandom", ".skills/story-info-collector/scripts/adapters/fandom_adapter.py")
    monkeypatch.setenv("CRAWLBASE_JS_TOKEN", "test-js-token")

    class FakeCrawlingAPI:
        def __init__(self, settings):
            self.settings = settings

        def get(self, url, options=None):
            return {"status_code": 200, "body": {"original_status": 404, "body": {"title": "Furina", "content": "not found page"}}}

    with patch.dict(sys.modules, {"crawlbase": Mock(CrawlingAPI=FakeCrawlingAPI)}):
        result = fandom.collect_fandom("genshin-impact", "Furina")

    assert result["status"] == "failed"
    assert "404" in result["notes"]


def test_fandom_original_404_in_string_body_is_failed(monkeypatch):
    fandom = load_module("fandom", ".skills/story-info-collector/scripts/adapters/fandom_adapter.py")
    monkeypatch.setenv("CRAWLBASE_JS_TOKEN", "test-js-token")

    class FakeCrawlingAPI:
        def __init__(self, settings):
            self.settings = settings

        def get(self, url, options=None):
            return {"status_code": 200, "body": '{"original_status":404,"body":{"title":"Furina","content":"not found page"}}'}

    with patch.dict(sys.modules, {"crawlbase": Mock(CrawlingAPI=FakeCrawlingAPI)}):
        result = fandom.collect_fandom("genshin-impact", "Furina")

    assert result["status"] == "failed"
    assert "404" in result["notes"]


def test_keyword_plan_detects_furina_example():
    cli = load_module("collect_story_info", ".skills/story-info-collector/scripts/collect_story_info.py")

    plan = cli.generate_keyword_plan("我想写一个关于芙宁娜在现代AU中重新面对审判创伤的故事", "zh")

    assert plan["clarification_needed"] is False
    assert plan["detected_characters"] == ["芙宁娜"]
    assert plan["detected_works"] == ["原神"]
    assert "reddit" in plan["source_routes"]
    assert "personality" in plan["classified_keywords"]


def test_keyword_plan_detects_school_modern_furina_neuvillette_prompt():
    profile_mod = load_module("profile", ".skills/story-info-collector/scripts/utils/profile.py")
    cli = load_module("collect_story_info", ".skills/story-info-collector/scripts/collect_story_info.py")
    profile = profile_mod.load_story_profile(ROOT / ".skills/story-info-collector/profiles/genshin.story-profile.yaml")

    plan = cli.generate_keyword_plan("我想要撰写一篇芙宁娜和那维莱特的校园现代风格文章。", "zh", profile=profile, include_reddit=True)

    assert plan["clarification_needed"] is False
    assert plan["detected_characters"] == ["芙宁娜", "那维莱特"]
    assert plan["detected_works"] == ["原神"]
    assert "校园现代" in plan["detected_scenes"]
    assert "那维莱特" in plan["search_keywords"]["zh"]
    assert "Neuvillette" in plan["search_keywords"]["en"]
    assert plan["source_routes"] == ["fandom", "reddit"]


def test_keyword_plan_asks_when_character_unclear():
    cli = load_module("collect_story_info", ".skills/story-info-collector/scripts/collect_story_info.py")

    plan = cli.generate_keyword_plan("我想写一个现代 AU 审判创伤故事", "zh")

    assert plan["clarification_needed"] is True
    assert "你要写哪个角色？" in plan["clarification_questions"]


def test_story_profile_detects_zhongli_and_skips_obc_by_default():
    profile_mod = load_module("profile", ".skills/story-info-collector/scripts/utils/profile.py")
    cli = load_module("collect_story_info", ".skills/story-info-collector/scripts/collect_story_info.py")
    profile = profile_mod.load_story_profile(ROOT / ".skills/story-info-collector/profiles/genshin.story-profile.yaml")

    plan = cli.generate_keyword_plan("我想写钟离在现代 AU 中处理契约创伤", "zh", profile=profile, include_reddit=True)

    assert plan["clarification_needed"] is False
    assert plan["detected_characters"] == ["钟离"]
    assert plan["detected_works"] == ["原神"]
    assert "现代 AU" in plan["detected_scenes"]
    assert plan["source_routes"] == ["fandom", "reddit"]
    assert "obc" not in plan["source_routes"]


def test_profile_cli_overrides_generate_zhongli_sources_without_obc(tmp_path):
    config_path = tmp_path / "config.yaml"
    docs_root = tmp_path / "docs"
    config_path.write_text(
        f"""
project:
  default_language: zh
  allow_english_search: true
  docs_root: {docs_root}
  default_profile: {ROOT}/.skills/story-info-collector/profiles/genshin.story-profile.yaml
cache:
  enabled: true
  manifest_path: {docs_root}/manifests/source_manifest.json
fandom:
  enabled: true
obc:
  enabled: false
reddit:
  enabled: true
  token_env: CRAWLBASE_TOKEN
  max_posts_per_query: 20
  sort: relevance
  subreddits: [Genshin_Lore]
storage:
  categories:
    character_information: {docs_root}/character-information
    world_information: {docs_root}/world-information
    plot_information: {docs_root}/plot-information
    relationship_information: {docs_root}/relationship-information
    voice_lines: {docs_root}/voice-lines
    forum_analysis: {docs_root}/forum-analysis
  raw_fandom: {docs_root}/raw/fandom
  raw_obc: {docs_root}/raw/obc
  raw_reddit: {docs_root}/raw/reddit
  manifests: {docs_root}/manifests
  sources: {docs_root}/sources
  chunks: {docs_root}/chunks
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "collect_story_info.py"),
            "--request",
            "我要写一个契约创伤故事",
            "--config",
            str(config_path),
            "--profile",
            str(ROOT / ".skills/story-info-collector/profiles/genshin.story-profile.yaml"),
            "--character",
            "钟离",
            "--work",
            "原神",
            "--scene",
            "现代AU",
            "--include-reddit",
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    manifest = json.loads((docs_root / "manifests" / "source_manifest.json").read_text(encoding="utf-8"))

    assert "新增 source 数量: 2" in result.stdout
    assert {entry["source_type"] for entry in manifest["entries"]} == {"official_reference", "interpretive_fan_evidence"}
    source_names = {entry["source_name"] for entry in manifest["entries"]}
    assert any(name.startswith("Crawlbase Fandom") for name in source_names)
    assert any(name.startswith("Crawlbase Reddit") for name in source_names)
    assert not list((docs_root / "voice-lines").glob("*.md"))


def test_cli_dry_run_generates_manifest_sources_chunks_and_cache(tmp_path):
    config_path = tmp_path / "config.yaml"
    docs_root = tmp_path / "docs"
    config_path.write_text(
        f"""
project:
  default_language: zh
  allow_english_search: true
  docs_root: {docs_root}
cache:
  enabled: true
  manifest_path: {docs_root}/manifests/source_manifest.json
  refresh_days: 30
  default_refresh: false
fandom:
  enabled: true
  default_lang: en
  attrs: [personality, appearance, relationships, story]
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
  subreddits: [Genshin_Lore]
storage:
  categories:
    character_information: {docs_root}/character-information
    world_information: {docs_root}/world-information
    plot_information: {docs_root}/plot-information
    relationship_information: {docs_root}/relationship-information
    voice_lines: {docs_root}/voice-lines
    forum_analysis: {docs_root}/forum-analysis
  raw_fandom: {docs_root}/raw/fandom
  raw_obc: {docs_root}/raw/obc
  raw_reddit: {docs_root}/raw/reddit
  manifests: {docs_root}/manifests
  sources: {docs_root}/sources
  chunks: {docs_root}/chunks
""",
        encoding="utf-8",
    )
    command = [
        sys.executable,
        str(SCRIPTS / "collect_story_info.py"),
        "--request",
        "我想写一个关于芙宁娜在现代AU中重新面对审判创伤的故事",
        "--config",
        str(config_path),
        "--dry-run",
    ]

    first = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
    second = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
    manifest = json.loads((docs_root / "manifests" / "source_manifest.json").read_text(encoding="utf-8"))

    assert "新增 source 数量" in first.stdout
    assert "Claim 抽取输入路径" in first.stdout
    assert "已命中缓存数量: 3" in second.stdout
    assert len(manifest["entries"]) == 3
    assert list((docs_root / "sources").glob("*.json"))
    assert list((docs_root / "chunks").glob("*.json"))
    assert list((docs_root / "character-information").glob("*.md"))


def test_cli_prints_clarification_and_does_not_collect(tmp_path):
    config_path = tmp_path / "config.yaml"
    docs_root = tmp_path / "docs"
    config_path.write_text(
        f"""
project:
  default_language: zh
  allow_english_search: true
  docs_root: {docs_root}
cache:
  enabled: true
  manifest_path: {docs_root}/manifests/source_manifest.json
fandom:
  enabled: true
obc:
  enabled: true
reddit:
  enabled: true
storage:
  categories:
    character_information: {docs_root}/character-information
    world_information: {docs_root}/world-information
    plot_information: {docs_root}/plot-information
    relationship_information: {docs_root}/relationship-information
    voice_lines: {docs_root}/voice-lines
    forum_analysis: {docs_root}/forum-analysis
  raw_fandom: {docs_root}/raw/fandom
  raw_obc: {docs_root}/raw/obc
  raw_reddit: {docs_root}/raw/reddit
  manifests: {docs_root}/manifests
  sources: {docs_root}/sources
  chunks: {docs_root}/chunks
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "collect_story_info.py"),
            "--request",
            "我想写一个现代 AU 审判创伤故事",
            "--config",
            str(config_path),
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "需要补充信息" in result.stdout
    assert "你要写哪个角色？" in result.stdout
    assert not (docs_root / "manifests" / "source_manifest.json").exists()
