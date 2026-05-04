import json
from pathlib import Path


def load_manifest(path) -> dict:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return {"entries": []}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def save_manifest(path, manifest: dict) -> None:
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def make_manifest_key(character: str, work: str, source_route: str, language: str, query_hash: str) -> str:
    return "|".join([character, work, source_route, language, query_hash])


def find_cached_entry(manifest: dict, key: str):
    for entry in manifest.get("entries", []):
        if entry.get("manifest_key") == key:
            return entry
    return None


def upsert_entry(manifest: dict, entry: dict) -> dict:
    entries = manifest.setdefault("entries", [])
    for index, existing in enumerate(entries):
        if existing.get("manifest_key") == entry.get("manifest_key"):
            entries[index] = entry
            return entry
    entries.append(entry)
    return entry
