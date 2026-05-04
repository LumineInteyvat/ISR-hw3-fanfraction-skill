import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def extract_document(raw: dict, context: dict) -> dict:
    sections = raw.get("sections") or {}
    if isinstance(sections, dict):
        text = "\n\n".join(str(value) for value in sections.values() if value)
    else:
        text = str(raw.get("text") or raw.get("body") or "")
    if not text:
        text = json.dumps(raw, ensure_ascii=False, indent=2)
    document_id = _stable_id("doc", context.get("source_name", ""), context.get("query_hash", ""), text)
    return {
        "document_id": document_id,
        "source_type": context["source_type"],
        "source_name": raw.get("source_name") or context["source_name"],
        "source_url": raw.get("source_url") or context.get("source_url", ""),
        "language": context["language"],
        "character": context["character"],
        "work": context["work"],
        "category": context["category"],
        "title": raw.get("title") or context["character"],
        "text": text,
        "metadata": {"query": context.get("query", ""), "adapter": context.get("adapter", "")},
        "collected_at": context.get("collected_at") or utc_now(),
    }


def write_json(data: dict, path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(document: dict, path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = [
        f"document_id: {document['document_id']}",
        f"source_type: {document['source_type']}",
        f"source_name: {document['source_name']}",
        f"source_url: {document['source_url']}",
        f"language: {document['language']}",
        f"character: {document['character']}",
        f"work: {document['work']}",
        f"category: {document['category']}",
        f"collected_at: {document['collected_at']}",
        f"query: {document.get('metadata', {}).get('query', '')}",
    ]
    content = "\n".join(frontmatter) + f"\n\n# {document['title']}\n\n{document['text']}\n\n## 元数据\n\n- source_type: {document['source_type']}\n- source_name: {document['source_name']}\n- source_url: {document['source_url']}\n- query: {document.get('metadata', {}).get('query', '')}\n- language: {document['language']}\n"
    output_path.write_text(content, encoding="utf-8")


def build_source(document: dict, context: dict, extracted_path: str) -> dict:
    source_id = _stable_id("src", document["source_name"], document["source_url"], context.get("query_hash", ""))
    return {
        "source_id": source_id,
        "source_type": document["source_type"],
        "source_name": document["source_name"],
        "source_url": document["source_url"],
        "work": document["work"],
        "character": document["character"],
        "language": document["language"],
        "query": context.get("query", ""),
        "query_hash": context.get("query_hash", ""),
        "collected_at": document["collected_at"],
        "raw_path": context.get("raw_path", ""),
        "extracted_path": extracted_path,
        "chunk_paths": [],
        "metadata": {
            "adapter": context.get("adapter", ""),
            "category": document["category"],
            "status": context.get("status", "success"),
            "notes": context.get("notes", ""),
        },
    }


def _scope_for_category(category: str) -> str:
    return {
        "character-information": "personality",
        "relationship-information": "relationship",
        "voice-lines": "voice_line",
        "plot-information": "quest_context",
        "world-information": "worldbuilding",
        "forum-analysis": "forum_interpretation",
    }.get(category, "unknown")


def chunk_document(document: dict, source: dict, context: dict) -> list[dict]:
    paragraphs = [p.strip() for p in document["text"].split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [document["text"]]
    chunks = []
    for index, paragraph in enumerate(paragraphs):
        chunks.append({
            "chunk_id": _stable_id("chk", source["source_id"], str(index), paragraph),
            "source_id": source["source_id"],
            "source_type": source["source_type"],
            "source_name": source["source_name"],
            "source_url": source["source_url"],
            "work": document["work"],
            "character": document["character"],
            "language": document["language"],
            "category": document["category"],
            "chunk_index": index,
            "title": document["title"],
            "text": paragraph,
            "evidence_scope": _scope_for_category(document["category"]),
            "metadata": {
                "query": context.get("query", ""),
                "query_hash": context.get("query_hash", ""),
                "collected_at": document["collected_at"],
                "raw_path": context.get("raw_path", ""),
                "extracted_path": source["extracted_path"],
            },
        })
    return chunks


def write_source(source: dict, path) -> None:
    write_json(source, path)


def write_chunks(chunks: list[dict], output_dir, base_filename: str) -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for chunk in chunks:
        path = out / f"{base_filename}__chunk-{chunk['chunk_index']}.json"
        write_json(chunk, path)
        paths.append(str(path))
    return paths
