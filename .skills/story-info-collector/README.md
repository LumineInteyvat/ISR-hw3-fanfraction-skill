# 故事资料收集器

这是阶段 1 的中文 Claude / Claude Code skill，用于为故事写作收集资料并生成可追溯的资料层。

## 安装依赖

```bash
python3 -m venv .venv
.venv/bin/pip install pyyaml pytest crawlbase
npm install fandom-scraper tsx
```

obcSpider 请按其仓库说明安装。没有安装 obcSpider 时，dry-run 不受影响。

## Crawlbase Token

Reddit 采集需要用户自行设置环境变量：

```bash
export CRAWLBASE_TOKEN="你的 token"
```

未设置 token 时，Reddit 来源会被跳过，不影响 Fandom 和 obcSpider。

## Dry-run

```bash
python .skills/story-info-collector/scripts/collect_story_info.py \
  --request "我想写一个关于芙宁娜在现代AU中重新面对审判创伤的故事" \
  --config .skills/story-info-collector/config.example.yaml \
  --dry-run
```

## 正常运行

```bash
python .skills/story-info-collector/scripts/collect_story_info.py \
  --request "我想写一个关于芙宁娜在现代AU中重新面对审判创伤的故事" \
  --config .skills/story-info-collector/config.example.yaml
```

## 阶段边界

本阶段只生成 raw、extracted_document、Source 和 Evidence Chunk。不抽取 Claim，不生成 KG_Node / KG_Edge，不做冲突检测，不判断 OOC，不生成剧情建议或人设卡。
