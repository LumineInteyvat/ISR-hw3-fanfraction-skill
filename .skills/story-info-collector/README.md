# 故事资料收集器

这是阶段 1 的中文 Claude / Claude Code skill，用于为故事写作收集资料并生成可追溯的资料层。

## 安装依赖

```bash
python3 -m venv .venv
.venv/bin/pip install pyyaml pytest crawlbase
npm install fandom-scraper tsx
```

本项目当前将 Fandom 作为主要/官方信息来源；obcSpider 真实采集默认关闭，不作为本阶段必需能力。

## Crawlbase Token

Reddit 采集需要用户自行设置环境变量：

```bash
export CRAWLBASE_TOKEN="你的 token"
```

未设置 token 时，Reddit 来源会被跳过，不影响 Fandom。可以把 token 放在项目本地 Claude Code 配置 `.claude/settings.local.json` 的 `env.CRAWLBASE_TOKEN` 中；该文件不应提交。

## Story Profile 定制

默认配置使用：

```yaml
project:
  default_profile: .skills/story-info-collector/profiles/genshin.story-profile.yaml
```

Claude Code 辅助不同小说创作时，应优先复制或修改 profile，而不是改主脚本。profile 可定制作品、角色别名、场景关键词、信息需求、默认来源路由和 Fandom source_type。

示例：

```bash
python .skills/story-info-collector/scripts/collect_story_info.py \
  --request "我想写钟离在现代 AU 中处理契约创伤" \
  --config .skills/story-info-collector/config.example.yaml \
  --profile .skills/story-info-collector/profiles/genshin.story-profile.yaml \
  --include-reddit \
  --dry-run
```

也可以用 CLI 覆盖本次故事的部分字段：

```bash
python .skills/story-info-collector/scripts/collect_story_info.py \
  --request "我要写一个契约创伤故事" \
  --config .skills/story-info-collector/config.example.yaml \
  --profile .skills/story-info-collector/profiles/genshin.story-profile.yaml \
  --character 钟离 \
  --work 原神 \
  --scene "现代AU" \
  --include-reddit \
  --dry-run
```

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
