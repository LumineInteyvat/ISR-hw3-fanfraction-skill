import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote


def build_reddit_search_url(subreddit: str, query: str, sort: str = "relevance") -> str:
    return f"https://www.reddit.com/r/{subreddit}/search/?q={quote(query)}&restrict_sr=1&sort={sort}"


def collect_reddit(query: str, subreddits: list[str], output_dir, token_env: str = "CRAWLBASE_TOKEN", dry_run: bool = False, sort: str = "relevance", max_posts_per_query: int = 20) -> dict:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    urls = [build_reddit_search_url(subreddit, query, sort) for subreddit in subreddits]
    if dry_run:
        return {
            "status": "success",
            "source_name": "Crawlbase Reddit dry-run",
            "source_url": urls[0] if urls else "",
            "title": f"Reddit discussion: {query}",
            "sections": {
                "forum_discussion": f"公开 Reddit 页面中关于 {query} 的角色性格剖析、任务解析和粉丝争议点示例。"
            },
            "posts": [
                {
                    "post title": f"Discussion about {query}",
                    "post url": urls[0] if urls else "",
                    "subreddit": subreddits[0] if subreddits else "",
                    "author": "public_user",
                    "timestamp": "2026-05-03T00:00:00Z",
                    "score": 1,
                    "post body": f"Dry-run discussion for {query}",
                    "top comments": [],
                }
            ],
        }
    token = os.environ.get(token_env)
    if not token:
        return {"status": "skipped", "source_name": "Crawlbase Reddit", "source_url": urls[0] if urls else "", "notes": f"缺少 {token_env}，跳过 Reddit。"}
    try:
        from crawlbase import CrawlingAPI
    except ImportError:
        return {"status": "failed", "source_name": "Crawlbase Reddit", "source_url": urls[0] if urls else "", "notes": "缺少 crawlbase 包，请安装后重试。"}
    api = CrawlingAPI({"token": token})
    responses = [api.get(url, options={"autoparse": "true"}) for url in urls[:max_posts_per_query]]
    return {"status": "success", "source_name": "Crawlbase Reddit", "source_url": urls[0] if urls else "", "responses": responses}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--subreddits", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--token-env", default="CRAWLBASE_TOKEN")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = collect_reddit(args.query, args.subreddits, Path(args.output).parent, args.token_env, args.dry_run)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
