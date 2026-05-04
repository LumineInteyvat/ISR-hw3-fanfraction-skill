from pathlib import Path

import yaml


def load_story_profile(path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _matches(value: str, aliases: list[str]) -> bool:
    lowered = value.lower()
    return any(alias.lower() in lowered for alias in aliases)


def find_character(request: str, profile: dict | None, explicit_character: str | None = None) -> str | None:
    if explicit_character:
        return explicit_character
    if not profile:
        if "芙宁娜" in request or "Furina" in request:
            return "芙宁娜"
        return None
    for character in profile.get("characters", []):
        aliases = character.get("aliases", []) + [character.get("name", "")]
        if _matches(request, aliases):
            return character["name"]
    return None


def find_work(request: str, profile: dict | None, character: str | None = None, explicit_work: str | None = None) -> str | None:
    if explicit_work:
        return explicit_work
    if not profile:
        if character == "芙宁娜" or "原神" in request:
            return "原神"
        return None
    if character:
        for entry in profile.get("characters", []):
            if entry.get("name") == character:
                return entry.get("work")
    for work in profile.get("works", []):
        aliases = work.get("aliases", []) + [work.get("name", "")]
        if _matches(request, aliases):
            return work["name"]
    return None


def find_scenes(request: str, profile: dict | None, explicit_scene: str | None = None) -> list[str]:
    scenes = []
    if explicit_scene:
        for part in explicit_scene.replace("，", ",").split(","):
            cleaned = part.strip().replace("现代AU", "现代 AU")
            if cleaned and cleaned not in scenes:
                scenes.append(cleaned)
    if profile:
        for scene in profile.get("scenes", []):
            aliases = scene.get("aliases", []) + [scene.get("name", "")]
            if _matches(request, aliases) and scene["name"] not in scenes:
                scenes.append(scene["name"])
        return scenes
    for keyword in ["现代 AU", "现代AU", "审判创伤", "角色心理", "恋爱线", "战后", "黑化"]:
        if keyword in request:
            value = keyword.replace("现代AU", "现代 AU")
            if value not in scenes:
                scenes.append(value)
    return scenes


def routes_for(profile: dict | None, include_reddit: bool = False) -> list[str]:
    if not profile:
        return ["fandom", "obc", "reddit"]
    routes = list(profile.get("default_routes", []))
    if include_reddit:
        for route in profile.get("optional_routes", []):
            if route not in routes:
                routes.append(route)
    if not profile.get("source_policy", {}).get("obc_enabled", False):
        routes = [route for route in routes if route != "obc"]
    return routes


def keywords_for(character: str, work: str, scenes: list[str], profile: dict | None, language: str) -> dict:
    zh = []
    en = []
    if profile:
        for entry in profile.get("characters", []):
            if entry.get("name") == character:
                zh.extend(entry.get("search_keywords", {}).get("zh", []))
                en.extend(entry.get("search_keywords", {}).get("en", []))
                break
    if not zh:
        zh = [character, "性格分析"] if character else []
    if not en:
        en = [character, "character analysis"] if character else []
    for scene in scenes:
        if scene not in zh:
            zh.append(scene)
        if scene.isascii() and scene not in en:
            en.append(scene)
    return {"zh": zh, "en": en}


def worlds_for(work: str | None, profile: dict | None) -> list[str]:
    if profile and work:
        for entry in profile.get("works", []):
            if entry.get("name") == work:
                return entry.get("default_worlds", [])
    return ["提瓦特", "现代 AU"] if work else []


def source_type_for(route: str, profile: dict | None) -> str:
    if route == "fandom" and profile:
        return profile.get("source_policy", {}).get("fandom_source_type", "structured_fan_knowledge")
    if route == "reddit" and profile:
        return profile.get("source_policy", {}).get("reddit_source_type", "interpretive_fan_evidence")
    return {
        "fandom": "structured_fan_knowledge",
        "obc": "official_reference",
        "reddit": "interpretive_fan_evidence",
    }[route]
