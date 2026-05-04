# 阶段 1：故事资料收集器 Skill 设计文档

## 目标

构造一个可被 Claude / Claude Code 加载的中文 skill：`story-info-collector`。当用户准备写同人或衍生故事时，该 skill 负责把自然语言创作需求转化为可追溯的资料收集任务，并产出后续 Claim 抽取可直接消费的 Source / Evidence Chunk 数据层。

阶段 1 的最终产物不是角色结论，而是资料层：

```text
raw → extracted_document → source → evidence_chunk
```

## 阶段边界

阶段 1 只做：

- 接收用户故事描述。
- 拆分和归类关键词。
- 在角色、作品、世界观、场景、采集范围或语言不明确时先追问。
- 检查本地缓存和 manifest。
- 按需调用 Fandom、obcSpider、Crawlbase Reddit 三类采集器。
- 保存 raw、规范化文本、Source、Evidence Chunk 与 manifest。
- 输出本次采集摘要和后续 Claim 抽取输入路径。

阶段 1 不做：

- Claim 抽取。
- KG_Node / KG_Edge 生成。
- Claim 冲突检测。
- NLI。
- OOC 判断。
- 三分支建议。
- 人设卡生成。
- 将 Reddit 讨论总结为结论。
- 将 Fandom 资料标记为官方正史。

## 交付目录

```text
.skills/
  story-info-collector/
    SKILL.md
    README.md
    config.example.yaml
    prompts/
      keyword-extraction.zh.md
      clarification.zh.md
      source-routing.zh.md
    scripts/
      collect_story_info.py
      adapters/
        fandom_scraper.ts
        obc_spider_adapter.py
        crawlbase_reddit_adapter.py
      utils/
        cache.py
        text_extract.py
        manifest.py
    schemas/
      keyword_plan.schema.json
      source_manifest.schema.json
      extracted_document.schema.json
      source.schema.json
      evidence_chunk.schema.json

docs/
  character-information/
  world-information/
  plot-information/
  relationship-information/
  voice-lines/
  forum-analysis/
  raw/
    fandom/
    obc/
    reddit/
  manifests/
  sources/
  chunks/
```

## Skill 文档层

`SKILL.md` 使用中文，作为 Claude / Claude Code 加载 skill 后看到的主说明。它必须包含：

- skill 名称：故事资料收集器。
- 适用场景：为故事写作收集角色、作品、世界观、语音和论坛讨论资料。
- 不适用场景：角色判断、OOC 检测、剧情建议、断言图或知识图谱生成。
- 输入格式：自然语言故事描述，可附带角色、作品、语言、来源范围。
- 输出格式：keyword_plan、采集摘要、输出路径。
- 追问规则。
- 关键词分类规则。
- 数据源路由规则。
- 缓存检查规则。
- 文件存储规则。
- 安全与合规限制。
- 示例对话。

`README.md` 面向使用者，说明依赖安装、配置、运行命令、dry-run、Crawlbase token 设置和阶段边界。

`config.example.yaml` 提供默认配置，所有路径、来源开关、语言偏好、缓存 manifest 路径、Reddit subreddit 和刷新策略都从配置读取。

`prompts/` 下三个中文 prompt 分别负责：

- `keyword-extraction.zh.md`：从故事描述生成 keyword_plan。
- `clarification.zh.md`：生成必要追问。
- `source-routing.zh.md`：决定 Fandom / obc / Reddit 的路由。

## 入口编排层

`collect_story_info.py` 是阶段 1 的可运行入口：

```bash
python .skills/story-info-collector/scripts/collect_story_info.py \
  --request "我想写一个关于芙宁娜在现代AU中重新面对审判创伤的故事" \
  --config .skills/story-info-collector/config.example.yaml
```

主流程：

1. 加载配置。
2. 根据用户请求生成 keyword_plan。
3. 如果 `clarification_needed=true`，打印追问并退出，不执行采集。
4. 根据 keyword_plan 和配置生成采集任务。
5. 在任何采集前检查 `docs/manifests/source_manifest.json`、raw 目录和分类目录。
6. 对缓存未命中的任务调用对应 adapter。
7. 保存 raw 文档。
8. 通过统一文本抽取工具生成 extracted_document。
9. 从 extracted_document 生成 Source 与 Evidence Chunk。
10. 幂等更新 manifest。
11. 输出摘要：缓存命中数量、新增资料数量、新增 source 数量、新增 chunk 数量、跳过来源、失败来源、输出路径、Claim 抽取输入路径。

## keyword_plan 设计

keyword_plan 是采集前的规划对象，至少包含：

- `original_request`
- `detected_characters`
- `detected_works`
- `detected_worlds`
- `detected_scenes`
- `search_keywords.zh`
- `search_keywords.en`
- `information_needs`
- `source_routes`
- `clarification_needed`
- `clarification_questions`
- `classified_keywords`

`classified_keywords` 至少包含：

- `character`
- `work`
- `canon_context`
- `relationship`
- `personality`
- `worldbuilding`
- `forum_topics`
- `exclusions`

如果角色、作品、场景、采集范围或语言不明确，keyword_plan 必须进入追问状态，主脚本不得直接采集。

## 数据源路由

### FandomScraper

用途：抓取 Fandom Wiki 中的角色、作品、世界观和结构化粉丝资料。

输入：

- `wiki_name`
- `lang`
- `character_name`
- 可选 `characters_page_url`
- 可选 `attrs`

行为：

1. 优先调用 `findByName(character_name)`。
2. 失败时回退到 `findAll + 过滤`。
3. 支持 `setCharactersPage(url)`。
4. raw JSON 写入 `docs/raw/fandom/`。
5. 抽取文本写入 `docs/character-information/` 或 `docs/world-information/`。
6. source_type 为 `structured_fan_knowledge`。

保留重点：外观、性格、角色文本描述、剧情经历、关系、阵营、职业、身份、图片 URL 或页面 URL。不强制下载图片。

### obcSpider

用途：抓取米游社官方角色语音、简介和 wav 链接。

输入：

- `configuration_key`
- `lang_id`
- `include characters`

映射规则：

- 原神 / Genshin Impact → `genshin_impact`
- 崩坏：星穹铁道 / Honkai Star Rail → `honkai:_star_rail`
- zh → 0
- ja → 1
- ko → 2
- en → 3

行为：

1. 调用 `ObcSpider(configuration_key=..., lang_id=..., include=[...])`。
2. raw JSON 写入 `docs/raw/obc/`。
3. 抽取语音文本写入 `docs/voice-lines/`。
4. source_type 为 `official_reference`。
5. 保存音频 URL，不下载音频文件。

### Crawlbase Reddit

用途：抓取公开 Reddit 页面中的论坛讨论资料。

输入：

- 环境变量 `CRAWLBASE_TOKEN`
- subreddit 列表
- query
- `max_posts_per_query`
- sort

行为：

1. 如果没有 `CRAWLBASE_TOKEN`，输出明确错误并跳过 Reddit，不影响其他来源。
2. 使用 `CrawlingAPI({"token": token})` 初始化。
3. 调用 `api.get(url, options={"autoparse": "true"})`。
4. 构造公开搜索 URL：`https://www.reddit.com/r/{subreddit}/search/?q={encoded_query}&restrict_sr=1&sort=relevance`。
5. raw JSON / HTML 写入 `docs/raw/reddit/`。
6. 抽取文本写入 `docs/forum-analysis/`。
7. source_type 为 `interpretive_fan_evidence`。

限制：只抓公开页面，不处理登录态、私信、删除内容、验证码、绕过访问控制或权限规避。

## 缓存与 manifest

采集前必须检查：

- `docs/manifests/source_manifest.json`
- `docs/raw/{source}/`
- `docs/{category}/`
- `docs/sources/`
- `docs/chunks/`

缓存命中条件：

```text
同一角色 + 同一作品 + 同一 source_route + 同一 language + 同一 query_hash 已存在
```

补充规则：

- 如果 source 与 chunks 均存在，默认不重复采集。
- 如果 raw 已存在但 extracted/source/chunks 缺失，可只补做 text extraction 和 chunking。
- 如果已有资料过旧，可提示用户是否刷新；阶段 1 默认不强制刷新。
- manifest 更新必须幂等。

manifest 记录字段：

- `source_type`
- `source_name`
- `source_url`
- `query`
- `query_hash`
- `character`
- `work`
- `language`
- `collected_at`
- `raw_path`
- `extracted_path`
- `source_path`
- `chunk_paths`
- `status`
- `notes`

## 规范化存储

### extracted_document

统一结构：

```json
{
  "document_id": "...",
  "source_type": "structured_fan_knowledge | official_reference | interpretive_fan_evidence",
  "source_name": "...",
  "source_url": "...",
  "language": "...",
  "character": "...",
  "work": "...",
  "category": "character-information | voice-lines | forum-analysis | world-information | plot-information | relationship-information",
  "title": "...",
  "text": "...",
  "metadata": {},
  "collected_at": "..."
}
```

分类规则：

- 角色外观、性格、身份、角色简介 → `docs/character-information/`
- 世界观、组织、地点、设定 → `docs/world-information/`
- 剧情、任务、事件 → `docs/plot-information/`
- 人物关系 → `docs/relationship-information/`
- 语音文本、音频链接 → `docs/voice-lines/`
- Reddit / 论坛分析讨论 → `docs/forum-analysis/`

命名规则：

```text
{work_slug}__{character_slug}__{category}__{source_slug}__{query_hash}.md
{work_slug}__{character_slug}__{category}__{source_slug}__{query_hash}.json
```

文件名必须 slug 化，避免中文路径问题。同一 query 必须生成稳定 query_hash。

### Source

Source 表示一个可追溯资料来源，不是 AI 总结。

```json
{
  "source_id": "src_...",
  "source_type": "primary_canon | official_reference | structured_fan_knowledge | interpretive_fan_evidence | unknown",
  "source_name": "...",
  "source_url": "...",
  "work": "...",
  "character": "...",
  "language": "...",
  "query": "...",
  "query_hash": "...",
  "collected_at": "...",
  "raw_path": "...",
  "extracted_path": "...",
  "chunk_paths": [],
  "metadata": {
    "adapter": "fandom | obc | reddit",
    "category": "...",
    "status": "success | skipped | failed | cached",
    "notes": "..."
  }
}
```

### Evidence Chunk

Evidence Chunk 是后续 Claim 抽取的输入。

```json
{
  "chunk_id": "chk_...",
  "source_id": "src_...",
  "source_type": "...",
  "source_name": "...",
  "source_url": "...",
  "work": "...",
  "character": "...",
  "language": "...",
  "category": "character-information | world-information | plot-information | relationship-information | voice-lines | forum-analysis",
  "chunk_index": 0,
  "title": "...",
  "text": "...",
  "evidence_scope": "appearance | personality | relationship | voice_line | quest_context | worldbuilding | forum_interpretation | unknown",
  "metadata": {
    "query": "...",
    "query_hash": "...",
    "collected_at": "...",
    "raw_path": "...",
    "extracted_path": "..."
  }
}
```

切分规则：

- 每个 chunk 保持语义完整。
- 不把多个来源混进同一个 chunk。
- 不把 Fandom、米游社、Reddit 的资料混合总结后再切分。
- 每个 chunk 必须保留 `source_id`、`source_type`、`source_url`。
- `text` 应适合后续 LLM 抽取 Claim。
- 阶段 1 只生成 chunk，不抽取 Claim。

## 安全与合规

- 不硬编码 API key。
- Crawlbase token 只从 `CRAWLBASE_TOKEN` 环境变量读取。
- Reddit 只抓公开页面。
- 不绕过登录、权限、验证码或访问控制。
- 不下载音频文件，只保存 wav URL 和文本。
- 网络错误应被记录为失败或跳过，不导致整个采集流程崩溃。
- 粉丝资料和论坛讨论必须保留 source_type，不得混同为官方资料。

## 测试与验收

最小验收覆盖：

- 无 token 时 Reddit adapter 不崩溃，只提示 `CRAWLBASE_TOKEN` 缺失。
- 已有 manifest 命中时，不重复抓取。
- obc 游戏名映射正确。
- lang_id 映射正确。
- Fandom 输出能写入 `docs/character-information/`。
- Markdown frontmatter 存在 `source_type`、`source_url`、`character`、`work`、`category`。
- keyword_plan 对“角色 + 场景 + 作品”能生成合理分类。
- 不清楚角色时，会生成 `clarification_questions`。
- source 文件和 chunk 文件能生成，并且 manifest 记录 `source_path` 与 `chunk_paths`。

## 设计决策

采用单入口编排、三 adapter 分离、统一 text_extract 与 manifest 工具的结构。这样可以让每个 adapter 只负责对应来源的采集细节，主脚本只负责任务编排和缓存控制，Source / Chunk 生成逻辑则集中在统一工具中，避免不同来源输出不一致。

阶段 1 不引入数据库，全部使用文件系统和 JSON / Markdown。原因是当前目标是构造可运行的最小资料层，文件制品更容易检查、提交和作为后续 Claim 抽取输入。后续阶段如需要 Claim Graph 或 Knowledge Graph，再引入数据库或图存储。