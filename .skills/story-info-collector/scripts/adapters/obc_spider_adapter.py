import argparse
import json
from pathlib import Path


def map_configuration_key(work: str) -> str:
    normalized = work.strip().lower()
    if normalized in {"原神", "genshin", "genshin impact"}:
        return "genshin_impact"
    if normalized in {"崩坏：星穹铁道", "崩坏:星穹铁道", "honkai star rail", "hsr"}:
        return "honkai:_star_rail"
    raise ValueError(f"不支持的作品: {work}")


def map_lang_id(language: str) -> int:
    mapping = {"zh": 0, "ja": 1, "ko": 2, "en": 3}
    if language not in mapping:
        raise ValueError(f"不支持的语言: {language}")
    return mapping[language]


def collect_obc(work: str, language: str, characters: list[str], output_dir, dry_run: bool = False) -> dict:
    configuration_key = map_configuration_key(work)
    lang_id = map_lang_id(language)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    if dry_run:
        return {
            "status": "success",
            "source_name": "obcSpider / 米游社 dry-run",
            "source_url": "https://bbs.mihoyo.com/",
            "configuration_key": configuration_key,
            "lang_id": lang_id,
            "title": f"{characters[0]} 角色语音",
            "sections": {
                "voice_lines": f"{characters[0]} 的官方语音文本示例。audio_url: https://example.invalid/{characters[0]}.wav"
            },
            "records": [
                {
                    "character_name": characters[0],
                    "summary": "dry-run 官方语音",
                    "title": "关于审判",
                    "line": f"{characters[0]} 的语音文本示例。",
                    "audio_url": "https://example.invalid/voice.wav",
                    "language": language,
                    "source_type": "official_reference",
                    "source_name": "obcSpider / 米游社",
                }
            ],
        }
    try:
        from obc import ObcSpider
    except ImportError:
        return {"status": "failed", "notes": "缺少 obcSpider 依赖，请安装后重试。"}
    spider = ObcSpider(configuration_key=configuration_key, lang_id=lang_id, include=characters)
    return {"status": "success", "source_name": "obcSpider / 米游社", "source_url": "https://bbs.mihoyo.com/", "records": spider.run()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--character", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = collect_obc(args.work, args.language, [args.character], Path(args.output).parent, args.dry_run)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
