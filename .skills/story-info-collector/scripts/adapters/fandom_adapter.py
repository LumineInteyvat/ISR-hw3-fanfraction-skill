import html
import json
import os
import re
from urllib.parse import quote


def _plain_text(value: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _json_safe(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(_json_safe(key)): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _select_token(token_env: str = "CRAWLBASE_TOKEN", js_token_env: str = "CRAWLBASE_JS_TOKEN") -> tuple[str | None, str, str]:
    js_token = os.environ.get(js_token_env)
    if js_token:
        return js_token, js_token_env, "javascript"
    token = os.environ.get(token_env)
    return token, token_env, "normal"


def _decoded_body(response):
    body = response.get("body") if isinstance(response, dict) else response
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body
    return body


def _payload_body(response):
    body = _decoded_body(response)
    if isinstance(body, dict) and "body" in body and isinstance(body["body"], dict):
        return body["body"]
    return body


def _original_status(response) -> int | None:
    if not isinstance(response, dict):
        return None
    body = _decoded_body(response)
    status = response.get("original_status") or (body.get("original_status") if isinstance(body, dict) else None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _extract_body_text(response) -> tuple[str, str]:
    body = _payload_body(response)
    if isinstance(body, dict):
        title = str(body.get("title") or "")
        text = body.get("content") or body.get("text") or body.get("html") or body.get("body") or ""
        return title, _plain_text(str(text))
    return "", _plain_text(str(body or ""))


def _contains_blocker(value) -> bool:
    if isinstance(value, dict):
        return any(_contains_blocker(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_blocker(item) for item in value)
    text = str(value).lower()
    return "please wait for verification" in text or "captcha" in text or "access denied" in text


def collect_fandom(wiki_name: str, character: str, language: str = "zh", timeout: int = 30, token_env: str = "CRAWLBASE_TOKEN", js_token_env: str = "CRAWLBASE_JS_TOKEN", page_title: str | None = None) -> dict:
    page = quote((page_title or character).replace(" ", "_"))
    source_url = f"https://{wiki_name}.fandom.com/wiki/{page}"
    token, selected_token_env, crawlbase_mode = _select_token(token_env, js_token_env)
    if not token:
        return {
            "status": "skipped",
            "source_name": "Crawlbase Fandom",
            "source_url": source_url,
            "title": character,
            "notes": f"缺少 {token_env} 或 {js_token_env}，跳过 Fandom。",
        }
    try:
        from crawlbase import CrawlingAPI
    except ImportError:
        return {"status": "failed", "source_name": "Crawlbase Fandom", "source_url": source_url, "title": character, "notes": "缺少 crawlbase 包，请安装后重试。"}
    try:
        response = _json_safe(CrawlingAPI({"token": token}).get(source_url, options={"autoparse": "true"}))
    except Exception as error:
        return {
            "status": "failed",
            "source_name": "Crawlbase Fandom",
            "source_url": source_url,
            "title": character,
            "notes": str(error),
            "token_env": selected_token_env,
            "crawlbase_mode": crawlbase_mode,
        }
    title, text = _extract_body_text(response)
    status = _original_status(response)
    if status and status >= 400:
        return {
            "status": "failed",
            "source_name": "Crawlbase Fandom",
            "source_url": source_url,
            "title": title or character,
            "notes": f"Fandom original status was {status} through Crawlbase.",
            "token_env": selected_token_env,
            "crawlbase_mode": crawlbase_mode,
            "response": response,
        }
    if _contains_blocker(response) or not text:
        return {
            "status": "failed",
            "source_name": "Crawlbase Fandom",
            "source_url": source_url,
            "title": title or character,
            "notes": "Fandom returned no usable page content through Crawlbase.",
            "token_env": selected_token_env,
            "crawlbase_mode": crawlbase_mode,
            "response": response,
        }
    return {
        "status": "success",
        "source_name": "Crawlbase Fandom",
        "source_url": source_url,
        "title": title or character,
        "sections": {"page": text},
        "token_env": selected_token_env,
        "crawlbase_mode": crawlbase_mode,
        "response": response,
    }
