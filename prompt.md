请在当前仓库中完成“阶段 1：故事资料收集 skill 构造”任务。

目标：
构造一个可被 Claude/Claude Code 加载的中文 skill。当用户需要写一个故事时，该 skill 能：
1. 接收用户对故事的自然语言描述。
2. 将描述拆分为一系列关键词。
3. 如果角色、作品、世界观、场景、信息来源或目标语言不清楚，先向用户追问。
4. 将关键词归类。
5. 在爬取前检查本地是否已经存在相关资料。
6. 按需调用三类采集器收集资料：
   - FandomScraper：用于 Fandom Wiki 角色/作品资料。
   - obcSpider：用于米游社官方角色语音、角色简介、wav 链接等资料。
   - Crawlbase：用于 Reddit 论坛讨论资料。
7. 对爬取得到的信息做文字提取和规范化存放。
8. 暂时不做断言提取、冲突检测、OOC 判断、三分支建议、人设卡生成；这些留给后续阶段。

重要语言要求：
- skill 描述文档、README、用户交互提示、配置说明必须使用中文。
- 搜索关键词可以使用英文。
- 存储的资料正文可以保留原文，也可以是英文。
- 代码注释可以中文优先，必要时英文。

参考来源：
- FandomScraper 仓库：https://github.com/dilaouid/FandomScraper
- obcSpider 仓库：https://github.com/Ray-Eldath/obcSpider
- Crawlbase：https://crawlbase.com/
- Crawlbase Reddit 教程中使用 Python crawlbase 包和 CrawlingAPI，通过 token 初始化，api.get(url, options) 抓取 Reddit 页面；可用 autoparse=true 获取 JSON 化结果。后续由用户填入 API key。

已知工具事实：
- FandomScraper 是 TypeScript/NodeJS 库，用于抓取 Fandom Wiki 的角色列表和角色信息；支持 npm/yarn/pnpm 安装，使用 FandomScraper 类，支持 getAvailableWikis、setCharactersPage、findAll、findByName、attr、attrToArray、exec 等方法。
- obcSpider 是 Python 米游社语音爬虫，可抓取原神和崩坏：星穹铁道角色语音文本、wav 链接等信息；configuration_key 只支持 genshin_impact 和 honkai:_star_rail；lang_id 0 到 3 分别表示中文、日文、韩文、英文；include/exclude 可筛选角色。
- Crawlbase Python 包可通过 pip install crawlbase 安装，使用 from crawlbase import CrawlingAPI；初始化方式为 CrawlingAPI({"token": "..."}），再用 api.get(url, options={...}) 抓取。Reddit 抓取默认只做公开网页抓取，不处理登录态、私密内容、绕过权限、违规采集。

请实现的仓库结构：
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

阶段 1 的 skill 行为：

## 一、用户输入处理
当用户输入类似：
“我想写一个关于芙宁娜在现代 AU 中重新面对审判创伤的故事”
skill 应输出或内部生成 keyword_plan：

{
  "original_request": "...",
  "detected_characters": ["芙宁娜"],
  "detected_works": ["原神"],
  "detected_worlds": ["提瓦特", "现代 AU"],
  "detected_scenes": ["审判创伤", "现代 AU", "角色心理"],
  "search_keywords": {
    "zh": ["芙宁娜", "审判", "创伤", "现代 AU", "性格分析"],
    "en": ["Furina", "trial", "trauma", "modern AU", "character analysis"]
  },
  "information_needs": [
    "character_profile",
    "voice_lines",
    "story_or_quest_context",
    "relationship_context",
    "forum_interpretation"
  ],
  "source_routes": [
    "fandom",
    "obc",
    "reddit"
  ],
  "clarification_needed": false,
  "clarification_questions": []
}

如果不清楚，必须先问，不要直接爬：
- 角色不明确：你要写哪个角色？
- 作品不明确：这个角色来自哪个作品/世界观？
- 场景不明确：你希望分析正史、AU、恋爱线、战后、黑化、任务后续，还是其它场景？
- 采集范围不明确：是否需要论坛讨论，还是只要官方/百科资料？
- 语言不明确：资料优先中文、英文，还是都可以？

## 二、关键词归类
将关键词至少归为：

- character：角色名、别名、英文名、日文名等。
- work：作品名、游戏名、世界观。
- canon_context：剧情、任务、事件、章节、语音、角色故事。
- relationship：人物关系、CP、阵营、亲友、敌对。
- personality：性格剖析、价值观、行为模式、心理创伤。
- worldbuilding：世界观、组织、地点、制度、神话、规则。
- forum_topics：论坛检索词，如 character analysis、lore discussion、quest interpretation、personality analysis。
- exclusions：用户明确不想要的来源、角色、CP、剧透范围。

## 三、爬取前检查缓存
任何采集动作前，必须先检查：

- docs/manifests/source_manifest.json
- docs/raw/{source}/
- docs/{category}/

缓存命中规则：
- 同一角色 + 同一作品 + 同一 source_route + 同一 language + 同一 query_hash 已存在，则不要重复爬取。
- 如果已有资料但过旧，可提示用户是否刷新；默认阶段 1 不强制刷新。
- manifest 中必须记录：
  - source_type
  - source_name
  - source_url
  - query
  - query_hash
  - character
  - work
  - language
  - collected_at
  - raw_path
  - extracted_path
  - status
  - notes

## 四、FandomScraper 适配器要求
在 scripts/adapters/fandom_scraper.ts 中实现：

- 输入：wiki_name、lang、character_name、optional characters_page_url、attrs。
- 优先 findByName(character_name)。
- 如 findByName 不可用或失败，再尝试 findAll + 过滤。
- 支持 setCharactersPage(url)，用于用户指定 Fandom 分类页。
- 输出 raw JSON 到 docs/raw/fandom/。
- 提取文本到 docs/character-information/ 或 docs/world-information/。
- 对角色资料重点保留：
  - 外观
  - 性格
  - 角色文本描述
  - 剧情经历
  - 关系
  - 阵营/职业/身份
  - 图片 URL 或页面 URL，但不要强制下载图片

## 五、obcSpider 适配器要求
在 scripts/adapters/obc_spider_adapter.py 中实现：

- 输入：configuration_key、lang_id、include characters。
- configuration_key 映射：
  - 原神 / Genshin Impact -> genshin_impact
  - 崩坏：星穹铁道 / Honkai Star Rail -> honkai:_star_rail
- lang_id 映射：
  - zh -> 0
  - ja -> 1
  - ko -> 2
  - en -> 3
- 调用 ObcSpider(configuration_key=..., lang_id=..., include=[...])
- 输出 raw JSON 到 docs/raw/obc/。
- 提取文本到 docs/voice-lines/。
- 每条语音记录至少包含：
  - character_name
  - summary
  - title
  - line
  - audio_url
  - language
  - source_type: official_reference
  - source_name: obcSpider / 米游社

## 六、Crawlbase Reddit 适配器要求
在 scripts/adapters/crawlbase_reddit_adapter.py 中实现：

- 使用环境变量 CRAWLBASE_TOKEN，不能把 token 写死。
- 如果没有 token，输出明确错误并跳过 Reddit，不影响 Fandom/obc 采集。
- 使用 crawlbase 包：
  from crawlbase import CrawlingAPI
  api = CrawlingAPI({"token": token})
  response = api.get(url, options={"autoparse": "true"})
- 支持用户后续填入 API key。
- 支持配置 subreddit 列表，例如：
  reddit:
    enabled: true
    subreddits:
      - Genshin_Lore
      - Genshin_Impact
      - HonkaiStarRail
    max_posts_per_query: 20
    sort: relevance
- 构造 Reddit 检索 URL 时，优先使用公开搜索页，例如：
  https://www.reddit.com/r/{subreddit}/search/?q={encoded_query}&restrict_sr=1&sort=relevance
- 阶段 1 只抓公开论坛页面，不处理登录、私信、删除内容、绕过访问控制。
- 输出 raw JSON/HTML 到 docs/raw/reddit/。
- 提取文本到 docs/forum-analysis/。
- 重点提取：
  - post title
  - post url
  - subreddit
  - author 如果公开存在
  - timestamp 如果公开存在
  - score/upvotes 如果公开存在
  - post body
  - top comments 如果 autoparse 或页面内容能得到
  - query
  - character/work/context tags
- 论坛主要聚焦：
  - 角色性格剖析
  - 世界观
  - 任务解析
  - 角色关系解释
  - 粉丝争议点
- 不要在阶段 1 做结论判断，只保存讨论文本和来源元数据。

## 七、文字提取与存储规范

在 scripts/utils/text_extract.py 中实现统一抽取：

- 输入 raw 文档。
- 输出 extracted_document：
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
  "metadata": {...},
  "collected_at": "..."
}

分类存储：
- 角色外观、性格、身份、角色简介 -> docs/character-information/
- 世界观、组织、地点、设定 -> docs/world-information/
- 剧情、任务、事件 -> docs/plot-information/
- 人物关系 -> docs/relationship-information/
- 语音文本、音频链接 -> docs/voice-lines/
- Reddit/论坛分析讨论 -> docs/forum-analysis/

命名规则：
{work_slug}__{character_slug}__{category}__{source_slug}__{query_hash}.md
同时保存对应 JSON：
{work_slug}__{character_slug}__{category}__{source_slug}__{query_hash}.json

Markdown 文件格式：

document_id: ...
source_type: ...
source_name: ...
source_url: ...
language: ...
character: ...
work: ...
category: ...
collected_at: ...
query: ...

标题

正文文本。

元数据

- source_type:
- source_name:
- source_url:
- query:
- language:

### 新增要求：阶段 1 必须生成 Source / Chunk 数据层

除了保存 raw、Markdown 和 extracted_document JSON 外，阶段 1 还必须生成可供后续断言抽取使用的 Source / Chunk 文件。

原因：
后续阶段会从 evidence_chunk 中抽取 Claim，再由 Claim 生成 KG_Node / KG_Edge，并进一步生成 Claim Edges。知识图谱节点和边必须由断言支撑，不能从 AI 总结中直接凭空生成。

新增目录：
docs/sources/
docs/chunks/

新增 schema：
.skills/story-info-collector/schemas/source.schema.json
.skills/story-info-collector/schemas/evidence_chunk.schema.json

Source 数据结构：
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

Evidence Chunk 数据结构：
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

切分规则：
- 每个 chunk 应尽量保持语义完整。
- 不要把多个来源混进同一个 chunk。
- 不要把 Fandom、米游社、Reddit 的资料混合总结后再切分。
- 每个 chunk 必须保留 source_id、source_type、source_url。
- 每个 chunk 的 text 应该适合后续 LLM 抽取 Claim。
- 阶段 1 只生成 chunk，不抽取 Claim。

缓存规则补充：
- 如果 source_id 对应的 source 和 chunks 已存在，则默认不重复生成。
- 如果 raw 已存在但 chunks 缺失，可以只补做 text extraction 和 chunking。
- manifest 中要记录 source_path 和 chunk_paths。

输出摘要补充：
主脚本运行结束后，除原有统计外，还要输出：
- 新增 source 数量
- 新增 chunk 数量
- 缓存命中的 source 数量
- chunk 输出目录
- 后续可运行的 Claim 抽取输入路径

## 八、source_type 规则
阶段 1 必须给每条资料打 source_type：

- primary_canon：暂时预留，阶段 1 不强制抓。
- official_reference：米游社/官方资料/官方参考页；obcSpider 输出默认属于此类。
- structured_fan_knowledge：Fandom Wiki 等结构化粉丝资料。
- interpretive_fan_evidence：Reddit 等论坛讨论。
- unknown：无法判断时使用，但必须在 notes 中说明。

## 九、skill 文档 SKILL.md 要求
写中文 SKILL.md，内容包括：

- skill 名称：故事资料收集器
- 适用场景
- 不适用场景
- 输入格式
- 输出格式
- 追问规则
- 关键词分类规则
- 数据源路由规则
- 缓存检查规则
- 文件存储规则
- 安全与合规限制
- 示例对话

SKILL.md 必须明确说明：
- 该 skill 只做资料收集和文字提取。
- 不做角色判断。
- 不做 OOC 检测。
- 不把粉丝讨论当作正史。
- Reddit 只抓公开页面。
- Crawlbase API key 由用户后续填入环境变量 CRAWLBASE_TOKEN。

## 十、配置文件 config.example.yaml
请生成示例配置：
project:
  default_language: zh
  allow_english_search: true
  docs_root: docs

cache:
  enabled: true
  manifest_path: docs/manifests/source_manifest.json
  refresh_days: 30
  default_refresh: false

fandom:
  enabled: true
  default_lang: en
  attrs:
    - age
    - status
    - images
    - affiliation
    - occupations
    - personality
    - appearance
    - relationships
    - story

obc:
  enabled: true
  default_lang: zh
  games:
    genshin:
      configuration_key: genshin_impact
    hsr:
      configuration_key: "honkai:_star_rail"

reddit:
  enabled: true
  token_env: CRAWLBASE_TOKEN
  max_posts_per_query: 20
  sort: relevance
  subreddits:
    - Genshin_Lore
    - Genshin_Impact
    - HonkaiStarRail

storage:
  categories:
    character_information: docs/character-information
    world_information: docs/world-information
    plot_information: docs/plot-information
    relationship_information: docs/relationship-information
    voice_lines: docs/voice-lines
    forum_analysis: docs/forum-analysis
    raw_fandom: docs/raw/fandom
    raw_obc: docs/raw/obc
    raw_reddit: docs/raw/reddit

## 十一、主脚本 collect_story_info.py
实现一个可运行入口：
python scripts/collect_story_info.py --request "我想写一个关于芙宁娜在现代AU中重新面对审判创伤的故事" --config .skills/story-info-collector/config.example.yaml

主脚本流程：
1. 加载配置。
2. 生成 keyword_plan。
3. 如果 clarification_needed=true，打印追问并退出。
4. 检查 manifest 和本地资料。
5. 对未命中的 source_route 调用对应 adapter。
6. 做文字提取。
7. 保存 raw、json、md。
8. 更新 manifest。
9. 输出本次收集摘要：
   - 已命中缓存数量
   - 新增资料数量
   - 跳过来源
   - 失败来源
   - 输出路径

## 十二、测试/验收
请添加最小测试或 dry-run：

- 无 token 时 Reddit adapter 不崩溃，只提示 CRAWLBASE_TOKEN 缺失。
- 已有 manifest 命中时，不重复抓取。
- obc 游戏名映射正确。
- lang_id 映射正确。
- Fandom 输出能写入 docs/character-information。
- Markdown frontmatter 存在 source_type、source_url、character、work、category。
- keyword_plan 对“角色 + 场景 + 作品”能生成合理分类。
- 不清楚角色时，会生成 clarification_questions。

## 十三、不要做的事情

- 不要实现断言图。
- 不要实现 NLI。
- 不要实现冲突检测。
- 不要实现三分支建议。
- 不要实现人设卡。
- 不要把 Reddit 讨论总结成结论。
- 不要把 Fandom 资料标记为官方正史。
- 不要硬编码 API key。
- 不要绕过网站权限、登录、验证码或访问控制。
- 不要下载音频文件，阶段 1 只保存 wav URL 和语音文本。

## 十四、交付物
请完成以下文件：

- .skills/story-info-collector/SKILL.md
- .skills/story-info-collector/README.md
- .skills/story-info-collector/config.example.yaml
- .skills/story-info-collector/prompts/keyword-extraction.zh.md
- .skills/story-info-collector/prompts/clarification.zh.md
- .skills/story-info-collector/prompts/source-routing.zh.md
- .skills/story-info-collector/scripts/collect_story_info.py
- .skills/story-info-collector/scripts/adapters/fandom_scraper.ts
- .skills/story-info-collector/scripts/adapters/obc_spider_adapter.py
- .skills/story-info-collector/scripts/adapters/crawlbase_reddit_adapter.py
- .skills/story-info-collector/scripts/utils/cache.py
- .skills/story-info-collector/scripts/utils/text_extract.py
- .skills/story-info-collector/scripts/utils/manifest.py
- .skills/story-info-collector/schemas/keyword_plan.schema.json
- .skills/story-info-collector/schemas/source_manifest.schema.json
- .skills/story-info-collector/schemas/extracted_document.schema.json
- docs/character-information/.gitkeep
- docs/world-information/.gitkeep
- docs/plot-information/.gitkeep
- docs/relationship-information/.gitkeep
- docs/voice-lines/.gitkeep
- docs/forum-analysis/.gitkeep
- docs/raw/fandom/.gitkeep
- docs/raw/obc/.gitkeep
- docs/raw/reddit/.gitkeep
- docs/manifests/.gitkeep

## 十五、实现风格

- 优先可运行的最小实现。
- 对网络抓取失败要有错误处理。
- 所有 adapter 都要支持 dry_run。
- 所有输出路径都从配置读取。
- 代码不要假设用户已经填入 Crawlbase token。
- manifest 更新要幂等。
- 文件名要 slug 化，避免中文路径问题。
- 对同一 query 生成稳定 query_hash。
- README 中写清楚安装依赖和运行方式。

## 阶段边界再次强调：
本阶段的最终产物不是“角色结论”，而是可追溯的资料层：
raw → extracted_document → source → evidence_chunk。

不得在阶段 1 中：
- 抽取 Claim
- 生成 KG_Node
- 生成 KG_Edge
- 检测 Claim 冲突
- 合成角色判断
- 判断 OOC
- 输出三分支建议
- 生成人设卡

但必须为这些后续步骤预留 source_id、chunk_id、source_type、source_url、category、character、work、language 等字段。