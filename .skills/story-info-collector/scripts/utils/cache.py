import hashlib
import re
from pathlib import Path

_PINYIN = {
    "原": "yuan",
    "神": "shen",
    "芙": "fu",
    "宁": "zhu",
    "娜": "na",
    "崩": "beng",
    "坏": "huai",
    "星": "xing",
    "穹": "qiong",
    "铁": "tie",
    "道": "dao",
}


def stable_query_hash(query: str) -> str:
    return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:12]


def slugify(value: str) -> str:
    parts = []
    for char in value.strip():
        if char.isascii() and char.isalnum():
            parts.append(char.lower())
        elif char in _PINYIN:
            parts.append(f"-{_PINYIN[char]}-")
        else:
            parts.append("-")
    slug = "".join(parts)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "unknown"


def build_base_filename(work: str, character: str, category: str, source_slug: str, query_hash: str) -> str:
    return "__".join([
        slugify(work),
        slugify(character),
        slugify(category),
        slugify(source_slug),
        query_hash,
    ])


def is_cache_hit(entry: dict) -> bool:
    if not entry or entry.get("status") not in {"success", "cached"}:
        return False
    paths = [entry.get("raw_path"), entry.get("extracted_path"), entry.get("source_path")]
    paths.extend(entry.get("chunk_paths") or [])
    return all(path and Path(path).exists() for path in paths)
