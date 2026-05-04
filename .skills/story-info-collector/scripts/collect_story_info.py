import argparse
import json
import sys
from pathlib import Path

import yaml

CURRENT = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT))

from adapters.crawlbase_reddit_adapter import collect_reddit
from adapters.obc_spider_adapter import collect_obc
from utils.cache import build_base_filename, is_cache_hit, stable_query_hash
from utils.manifest import find_cached_entry, load_manifest, make_manifest_key, save_manifest, upsert_entry
from utils.profile import find_character, find_scenes, find_work, keywords_for, load_story_profile, routes_for, source_type_for, worlds_for
from utils.text_extract import build_source, chunk_document, extract_document, write_chunks, write_json, write_markdown, write_source


def generate_keyword_plan(request: str, language: str = "zh", profile: dict | None = None, explicit_character: str | None = None, explicit_work: str | None = None, explicit_scene: str | None = None, include_reddit: bool = False, exclusions: list[str] | None = None) -> dict:
    character = find_character(request, profile, explicit_character)
    work = find_work(request, profile, character, explicit_work)
    scenes = find_scenes(request, profile, explicit_scene)
    characters = [character] if character else []
    works = [work] if work else []
    questions = []
    if not characters:
        questions.append("你要写哪个角色？")
    if not works:
        questions.append("这个角色来自哪个作品/世界观？")
    if not scenes:
        questions.append("你希望分析正史、AU、恋爱线、战后、黑化、任务后续，还是其它场景？")
    search_keywords = keywords_for(character or "", work or "", scenes, profile, language)
    source_routes = routes_for(profile, include_reddit) if characters and works else []
    return {
        "original_request": request,
        "detected_characters": characters,
        "detected_works": works,
        "detected_worlds": worlds_for(work, profile),
        "detected_scenes": scenes,
        "search_keywords": search_keywords,
        "information_needs": profile.get("information_needs", ["character_profile", "voice_lines", "story_or_quest_context", "relationship_context", "forum_interpretation"]) if profile else ["character_profile", "voice_lines", "story_or_quest_context", "relationship_context", "forum_interpretation"],
        "source_routes": source_routes,
        "clarification_needed": bool(questions),
        "clarification_questions": questions,
        "classified_keywords": {
            "character": characters,
            "work": works,
            "canon_context": [scene for scene in scenes if "任务" in scene or "审判" in scene or "契约" in scene],
            "relationship": ["人物关系"] if characters else [],
            "personality": [keyword for keyword in [*scenes, "性格分析", "角色心理"] if characters],
            "worldbuilding": worlds_for(work, profile),
            "forum_topics": ["character analysis", "lore discussion", "quest interpretation", "personality analysis"] if characters else [],
            "exclusions": exclusions or [],
        },
    }


def load_config(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def ensure_dirs(config: dict) -> None:
    storage = config.get("storage", {})
    for path in list(storage.get("categories", {}).values()) + [storage.get("raw_fandom"), storage.get("raw_obc"), storage.get("raw_reddit"), storage.get("manifests"), storage.get("sources"), storage.get("chunks")]:
        if path:
            Path(path).mkdir(parents=True, exist_ok=True)


def _raw_for_route(route: str, config: dict, character: str, work: str, language: str, query: str, dry_run: bool) -> tuple[dict, str]:
    storage = config["storage"]
    if route == "fandom":
        raw = {
            "status": "success",
            "source_name": "FandomScraper dry-run" if dry_run else "FandomScraper",
            "source_url": f"https://genshin-impact.fandom.com/wiki/{character}",
            "title": character,
            "sections": {
                "appearance": f"{character} 的外观资料示例。",
                "personality": f"{character} 在公开场合表现戏剧化，同时与审判创伤相关的心理主题值得收集。",
                "relationships": f"{character} 与枫丹角色和民众存在复杂关系。",
                "story": f"{character} 的剧情经历与审判、身份和责任相关。",
            },
        }
        return raw, storage["raw_fandom"]
    if route == "obc":
        return collect_obc(work, language, [character], storage["raw_obc"], dry_run), storage["raw_obc"]
    return collect_reddit(query, config.get("reddit", {}).get("subreddits", []), storage["raw_reddit"], config.get("reddit", {}).get("token_env", "CRAWLBASE_TOKEN"), dry_run, config.get("reddit", {}).get("sort", "relevance"), config.get("reddit", {}).get("max_posts_per_query", 20)), storage["raw_reddit"]


def _context_for_route(route: str, character: str, work: str, language: str, query: str, query_hash: str, raw_path: str, profile: dict | None = None) -> dict:
    mapping = {
        "fandom": (source_type_for("fandom", profile), "FandomScraper", "character-information"),
        "obc": (source_type_for("obc", profile), "obcSpider / 米游社", "voice-lines"),
        "reddit": (source_type_for("reddit", profile), "Crawlbase Reddit", "forum-analysis"),
    }
    source_type, source_name, category = mapping[route]
    return {
        "source_type": source_type,
        "source_name": source_name,
        "source_url": "",
        "language": language,
        "character": character,
        "work": work,
        "category": category,
        "query": query,
        "query_hash": query_hash,
        "adapter": route,
        "raw_path": raw_path,
    }


def collect(request: str, config: dict, dry_run: bool = False, language_override: str | None = None, refresh: bool = False, profile_path: str | None = None, explicit_character: str | None = None, explicit_work: str | None = None, explicit_scene: str | None = None, include_reddit: bool = False, exclusions: list[str] | None = None) -> int:
    ensure_dirs(config)
    language = language_override or config.get("project", {}).get("default_language", "zh")
    selected_profile_path = profile_path or config.get("project", {}).get("default_profile")
    profile = load_story_profile(selected_profile_path) if selected_profile_path else None
    keyword_plan = generate_keyword_plan(request, language, profile, explicit_character, explicit_work, explicit_scene, include_reddit, exclusions)
    if keyword_plan["clarification_needed"]:
        print("需要补充信息：")
        for question in keyword_plan["clarification_questions"]:
            print(f"- {question}")
        return 0
    manifest_path = config.get("cache", {}).get("manifest_path", "docs/manifests/source_manifest.json")
    manifest = load_manifest(manifest_path)
    storage = config["storage"]
    character = keyword_plan["detected_characters"][0]
    work = keyword_plan["detected_works"][0]
    cached = 0
    added_docs = 0
    added_sources = 0
    added_chunks = 0
    skipped = []
    failed = []
    output_paths = []
    for route in keyword_plan["source_routes"]:
        query = " ".join(keyword_plan["search_keywords"]["zh" if language == "zh" else "en"] + [route])
        query_hash = stable_query_hash(query)
        key = make_manifest_key(character, work, route, language, query_hash)
        existing = find_cached_entry(manifest, key)
        if existing and not refresh and is_cache_hit(existing):
            cached += 1
            continue
        raw, raw_dir = _raw_for_route(route, config, character, work, language, query, dry_run)
        base = build_base_filename(work, character, _context_for_route(route, character, work, language, query, query_hash, "", profile)["category"], route, query_hash)
        raw_path = str(Path(raw_dir) / f"{base}.json")
        write_json(raw, raw_path)
        context = _context_for_route(route, character, work, language, query, query_hash, raw_path, profile)
        if raw.get("status") == "skipped":
            skipped.append(route)
            status = "skipped"
        elif raw.get("status") == "failed":
            failed.append(route)
            status = "failed"
        else:
            status = "success"
        if status != "success":
            entry = {
                "manifest_key": key,
                "source_type": context["source_type"],
                "source_name": raw.get("source_name", context["source_name"]),
                "source_url": raw.get("source_url", ""),
                "query": query,
                "query_hash": query_hash,
                "character": character,
                "work": work,
                "language": language,
                "collected_at": "",
                "raw_path": raw_path,
                "extracted_path": "",
                "source_path": "",
                "chunk_paths": [],
                "status": status,
                "notes": raw.get("notes", ""),
            }
            upsert_entry(manifest, entry)
            continue
        document = extract_document(raw, context)
        category_dir = storage["categories"][context["category"].replace("-", "_")]
        extracted_json_path = str(Path(category_dir) / f"{base}.json")
        extracted_md_path = str(Path(category_dir) / f"{base}.md")
        write_json(document, extracted_json_path)
        write_markdown(document, extracted_md_path)
        source = build_source(document, context, extracted_json_path)
        chunks = chunk_document(document, source, context)
        chunk_paths = write_chunks(chunks, storage["chunks"], base)
        source["chunk_paths"] = chunk_paths
        source_path = str(Path(storage["sources"]) / f"{base}.json")
        write_source(source, source_path)
        entry = {
            "manifest_key": key,
            "source_type": source["source_type"],
            "source_name": source["source_name"],
            "source_url": source["source_url"],
            "query": query,
            "query_hash": query_hash,
            "character": character,
            "work": work,
            "language": language,
            "collected_at": source["collected_at"],
            "raw_path": raw_path,
            "extracted_path": extracted_json_path,
            "source_path": source_path,
            "chunk_paths": chunk_paths,
            "status": "success",
            "notes": "dry-run" if dry_run else "",
        }
        upsert_entry(manifest, entry)
        added_docs += 1
        added_sources += 1
        added_chunks += len(chunks)
        output_paths.extend([extracted_md_path, extracted_json_path, source_path, *chunk_paths])
    save_manifest(manifest_path, manifest)
    print(f"已命中缓存数量: {cached}")
    print(f"新增资料数量: {added_docs}")
    print(f"新增 source 数量: {added_sources}")
    print(f"新增 chunk 数量: {added_chunks}")
    print(f"跳过来源: {', '.join(skipped) if skipped else '无'}")
    print(f"失败来源: {', '.join(failed) if failed else '无'}")
    print(f"输出路径: {', '.join(output_paths) if output_paths else '无'}")
    print(f"chunk 输出目录: {storage['chunks']}")
    print(f"Claim 抽取输入路径: {storage['chunks']}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--language")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--profile")
    parser.add_argument("--character")
    parser.add_argument("--work")
    parser.add_argument("--scene")
    parser.add_argument("--include-reddit", action="store_true")
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()
    raise SystemExit(collect(args.request, load_config(args.config), args.dry_run, args.language, args.refresh, args.profile, args.character, args.work, args.scene, args.include_reddit, args.exclude))


if __name__ == "__main__":
    main()
