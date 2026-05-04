# 阶段 1：故事资料收集器 Skill 实施计划

## 范围

本计划用于实现 `.skills/story-info-collector` 的阶段 1 最小可运行版本。实施目标是生成可追溯资料层：

```text
raw → extracted_document → source → evidence_chunk
```

不实现 Claim、KG、NLI、冲突检测、OOC 判断、三分支建议或人设卡。

## Step 1：创建目录结构和占位文件

创建以下目录：

- `.skills/story-info-collector/`
- `.skills/story-info-collector/prompts/`
- `.skills/story-info-collector/scripts/adapters/`
- `.skills/story-info-collector/scripts/utils/`
- `.skills/story-info-collector/schemas/`
- `docs/character-information/`
- `docs/world-information/`
- `docs/plot-information/`
- `docs/relationship-information/`
- `docs/voice-lines/`
- `docs/forum-analysis/`
- `docs/raw/fandom/`
- `docs/raw/obc/`
- `docs/raw/reddit/`
- `docs/manifests/`
- `docs/sources/`
- `docs/chunks/`

创建 `.gitkeep`：

- `docs/character-information/.gitkeep`
- `docs/world-information/.gitkeep`
- `docs/plot-information/.gitkeep`
- `docs/relationship-information/.gitkeep`
- `docs/voice-lines/.gitkeep`
- `docs/forum-analysis/.gitkeep`
- `docs/raw/fandom/.gitkeep`
- `docs/raw/obc/.gitkeep`
- `docs/raw/reddit/.gitkeep`
- `docs/manifests/.gitkeep`
- `docs/sources/.gitkeep`
- `docs/chunks/.gitkeep`

验收：目录存在，路径与 prompt.md 要求一致，并包含新增 Source / Chunk 目录。

## Step 2：编写配置文件

文件：`.skills/story-info-collector/config.example.yaml`

内容包含：

- `project.default_language`
- `project.allow_english_search`
- `project.docs_root`
- `cache.enabled`
- `cache.manifest_path`
- `cache.refresh_days`
- `cache.default_refresh`
- `fandom.enabled`
- `fandom.default_lang`
- `fandom.attrs`
- `obc.enabled`
- `obc.default_lang`
- `obc.games`
- `reddit.enabled`
- `reddit.token_env`
- `reddit.max_posts_per_query`
- `reddit.sort`
- `reddit.subreddits`
- `storage.categories`
- `storage.raw_*`
- `storage.sources`
- `storage.chunks`

验收：主脚本后续只从配置读取路径、来源开关和默认参数，不硬编码输出目录。

## Step 3：编写 JSON Schema

文件：

- `.skills/story-info-collector/schemas/keyword_plan.schema.json`
- `.skills/story-info-collector/schemas/source_manifest.schema.json`
- `.skills/story-info-collector/schemas/extracted_document.schema.json`
- `.skills/story-info-collector/schemas/source.schema.json`
- `.skills/story-info-collector/schemas/evidence_chunk.schema.json`

重点字段：

- keyword_plan：原始请求、检测角色、作品、世界、场景、关键词、信息需求、来源路由、追问状态、分类关键词。
- source_manifest：source 元数据、query_hash、raw/extracted/source/chunk 路径、状态。
- extracted_document：规范化文本、分类、来源类型、来源 URL。
- source：可追溯来源对象。
- evidence_chunk：后续 Claim 抽取输入。

验收：schema 能表达 prompt.md 中列出的必需字段；Source / Chunk schema 独立存在。

## Step 4：编写中文 skill 文档和 prompts

文件：

- `.skills/story-info-collector/SKILL.md`
- `.skills/story-info-collector/README.md`
- `.skills/story-info-collector/prompts/keyword-extraction.zh.md`
- `.skills/story-info-collector/prompts/clarification.zh.md`
- `.skills/story-info-collector/prompts/source-routing.zh.md`

`SKILL.md` 必须包含：

- skill 名称。
- 适用场景。
- 不适用场景。
- 输入格式。
- 输出格式。
- 追问规则。
- 关键词分类规则。
- 数据源路由规则。
- 缓存检查规则。
- 文件存储规则。
- 安全与合规限制。
- 示例对话。

`README.md` 必须包含：

- Python 依赖安装方式。
- Node / TypeScript FandomScraper 依赖说明。
- obcSpider 使用说明。
- Crawlbase token 环境变量设置。
- dry-run 示例。
- 正常运行示例。
- 阶段边界说明。

验收：所有面向用户的文档和提示为中文；明确说明不做角色判断、OOC 检测或 Claim 抽取。

## Step 5：实现通用工具函数

### 5.1 `manifest.py`

职责：

- 加载 manifest，不存在时返回空结构。
- 按稳定 key 查询缓存。
- 幂等 upsert manifest entry。
- 保存 manifest。
- 记录 `source_path` 和 `chunk_paths`。

关键函数建议：

- `load_manifest(path)`
- `save_manifest(path, manifest)`
- `make_manifest_key(character, work, source_route, language, query_hash)`
- `find_cached_entry(manifest, key)`
- `upsert_entry(manifest, entry)`

验收：同一 key 重复写入不会产生重复 entry。

### 5.2 `cache.py`

职责：

- 生成稳定 `query_hash`。
- slug 化文件名片段。
- 组合 raw、extracted、source、chunk 输出路径。
- 检查 raw / extracted / source / chunks 是否存在。

关键函数建议：

- `stable_query_hash(query)`
- `slugify(value)`
- `build_base_filename(work, character, category, source_slug, query_hash)`
- `is_cache_hit(entry)`

验收：中文输入能生成安全 ASCII 文件名；同一 query 的 hash 稳定。

### 5.3 `text_extract.py`

职责：

- 从 Fandom raw、obc raw、Reddit raw 中抽取文本。
- 生成 extracted_document。
- 写 JSON 和 Markdown。
- 生成 Source。
- 将 extracted_document 切分为 Evidence Chunk。

关键函数建议：

- `extract_document(raw, context)`
- `write_extracted_document(document, paths)`
- `write_markdown(document, path)`
- `build_source(document, context)`
- `chunk_document(document, source, context)`
- `write_source(source, path)`
- `write_chunks(chunks, output_dir)`

验收：Markdown frontmatter 包含 `source_type`、`source_url`、`character`、`work`、`category`；chunk 不混合多个 source。

## Step 6：实现采集适配器

### 6.1 Fandom adapter

文件：`.skills/story-info-collector/scripts/adapters/fandom_scraper.ts`

职责：

- 接收 `wiki_name`、`lang`、`character_name`、`characters_page_url`、`attrs`、`dry_run`。
- dry-run 时输出将要执行的查询和模拟 raw 结构。
- 非 dry-run 时调用 FandomScraper。
- 优先 `findByName(character_name)`。
- 失败时回退 `findAll + 过滤`。
- 支持 `setCharactersPage(url)`。
- 将 raw JSON 写入 `docs/raw/fandom/`。

验收：dry-run 能生成可供 text_extract 消费的 raw JSON；实际调用失败时返回结构化错误。

### 6.2 obc adapter

文件：`.skills/story-info-collector/scripts/adapters/obc_spider_adapter.py`

职责：

- 实现游戏名到 `configuration_key` 的映射。
- 实现语言到 `lang_id` 的映射。
- 接收 include characters。
- dry-run 时输出模拟语音记录。
- 非 dry-run 时调用 `ObcSpider(configuration_key=..., lang_id=..., include=[...])`。
- 保存 raw JSON 到 `docs/raw/obc/`。

验收：`原神` 映射为 `genshin_impact`；`崩坏：星穹铁道` 映射为 `honkai:_star_rail`；zh/ja/ko/en 分别映射 0/1/2/3。

### 6.3 Crawlbase Reddit adapter

文件：`.skills/story-info-collector/scripts/adapters/crawlbase_reddit_adapter.py`

职责：

- 从 `CRAWLBASE_TOKEN` 读取 token。
- token 缺失时返回 skipped 状态，不抛出未处理异常。
- dry-run 时输出将访问的公开搜索 URL 和模拟帖子结构。
- 非 dry-run 时调用 Crawlbase。
- 使用 `autoparse=true`。
- 保存 raw JSON / HTML 到 `docs/raw/reddit/`。

验收：无 token 时 Reddit adapter 不崩溃；不影响 Fandom / obc 的执行。

## Step 7：实现主脚本

文件：`.skills/story-info-collector/scripts/collect_story_info.py`

CLI 参数：

- `--request`：用户故事描述。
- `--config`：配置文件路径。
- `--dry-run`：不执行真实网络抓取。
- 可选 `--language`：覆盖默认语言。
- 可选 `--refresh`：忽略默认缓存。

主流程实现：

1. 解析参数。
2. 加载 YAML 配置。
3. 生成 keyword_plan。
4. 如果需要追问，打印问题并退出 0。
5. 构建 source tasks。
6. 对每个 task 生成 query_hash 并检查 manifest。
7. 命中缓存时记录 cached。
8. 未命中时调用 adapter。
9. adapter skipped / failed 时记录状态并继续。
10. 成功 raw 进入 text_extract。
11. 写 extracted_document、Markdown、Source、Chunks。
12. 更新 manifest。
13. 输出摘要。

keyword_plan 最小实现策略：

- 先用规则启发式支持 prompt.md 示例和常见“角色 + 作品 + 场景”输入。
- 若无法识别角色或作品，进入追问。
- 搜索关键词同时生成 zh / en；英文可以基于内置常见角色别名映射和原词保留。
- 不调用 LLM API，避免额外依赖。

验收：示例命令能在 dry-run 下完成完整链路并生成文件。

## Step 8：添加最小测试或 dry-run 验收

优先实现轻量 Python 测试或 dry-run 检查脚本。覆盖：

- 无 token 时 Reddit adapter 不崩溃。
- manifest 命中时不重复采集。
- obc 游戏名映射正确。
- lang_id 映射正确。
- Fandom dry-run 输出能写入 `docs/character-information/`。
- Markdown frontmatter 存在必要字段。
- keyword_plan 对“芙宁娜 + 原神 + 现代 AU + 审判创伤”生成合理分类。
- 角色不明确时生成 `clarification_questions`。
- Source 和 Evidence Chunk 文件生成，manifest 记录路径。

验收命令建议：

```bash
python .skills/story-info-collector/scripts/collect_story_info.py \
  --request "我想写一个关于芙宁娜在现代AU中重新面对审判创伤的故事" \
  --config .skills/story-info-collector/config.example.yaml \
  --dry-run
```

成功输出应包含：

- 已命中缓存数量。
- 新增资料数量。
- 新增 source 数量。
- 新增 chunk 数量。
- 跳过来源。
- 失败来源。
- 输出路径。
- Claim 抽取输入路径。

## Step 9：最终人工验收清单

实施完成后检查：

- `.skills/story-info-collector/SKILL.md` 为中文且能解释 skill 行为。
- `.skills/story-info-collector/README.md` 为中文且包含运行方式。
- `config.example.yaml` 不包含真实 API key。
- Crawlbase token 只从环境变量读取。
- 所有 adapter 支持 dry-run。
- 所有输出路径从配置读取。
- manifest 更新幂等。
- 文件名已 slug 化。
- query_hash 稳定。
- Source / Chunk 数据层已生成。
- 阶段 1 没有实现 Claim、KG、冲突检测、OOC 或人设卡。

## 风险与处理

### FandomScraper 为 TypeScript，而主脚本为 Python

处理方式：Fandom adapter 作为独立 TypeScript CLI，由 Python 主脚本通过子进程调用；dry-run 可先使用模拟 raw，保证 Python 链路可验收。

### obcSpider 依赖可能未安装

处理方式：adapter 捕获 ImportError，提示安装方式；dry-run 不要求依赖存在。

### Crawlbase token 缺失

处理方式：返回 skipped，记录 notes，不影响其他来源。

### 自动 keyword_plan 识别能力有限

处理方式：阶段 1 采用启发式最小实现；识别不明确时追问，不猜测采集。

### 网络采集失败

处理方式：单来源失败不终止整体流程；manifest 记录 failed，摘要中列出失败来源。

## 推荐实施顺序

1. 目录和配置。
2. schema。
3. 文档和 prompts。
4. cache / manifest / text_extract。
5. dry-run adapter。
6. 主脚本完整 dry-run 链路。
7. 接入真实 Fandom / obc / Crawlbase 调用。
8. 最小测试与验收修正。