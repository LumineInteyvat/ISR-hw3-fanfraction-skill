# 故事资料收集器

## 适用场景

当用户准备写故事、同人、AU、角色心理、关系线或世界观相关内容时，使用本 skill 收集可追溯资料。

## 不适用场景

本 skill 不做角色判断、不做 OOC 检测、不生成三分支建议、不生成人设卡、不抽取 Claim、不构建知识图谱。

## 输入格式

用户可以用自然语言描述故事需求，例如：

> 我想写一个关于芙宁娜在现代 AU 中重新面对审判创伤的故事。

也可以补充角色、作品、语言和资料范围。Claude Code 应优先通过 story profile 或 CLI 参数定制本次小说需求，而不是修改主脚本。

## Story Profile 定制

默认 profile 位于 `.skills/story-info-collector/profiles/genshin.story-profile.yaml`，用于配置作品、角色别名、场景关键词、信息需求、来源路由和 source_type。写作辅助时，如果用户换角色或换场景，优先修改 profile 副本或传入 `--character`、`--work`、`--scene`、`--include-reddit`。

## 输出格式

本 skill 输出 keyword_plan、必要追问、采集摘要、raw 路径、extracted_document 路径、Source 路径和 Evidence Chunk 路径。

## 追问规则

如果角色、作品、场景、采集范围或语言不明确，必须先问，不要直接采集：

- 角色不明确：你要写哪个角色？
- 作品不明确：这个角色来自哪个作品/世界观？
- 场景不明确：你希望分析正史、AU、恋爱线、战后、黑化、任务后续，还是其它场景？
- 采集范围不明确：是否需要论坛讨论，还是只要官方/百科资料？
- 语言不明确：资料优先中文、英文，还是都可以？

## 关键词分类规则

关键词至少归类为 character、work、canon_context、relationship、personality、worldbuilding、forum_topics、exclusions。

## 数据源路由规则

- Fandom：本项目当前作为主要/官方信息来源，用于角色资料、作品资料和世界观。
- obcSpider：默认关闭；本阶段不实现真实米游社采集。
- Crawlbase Reddit：公开 Reddit 论坛讨论、角色分析、任务解析和粉丝争议点。

## 缓存检查规则

采集前检查 manifest、raw、分类目录、sources 和 chunks。同一角色、作品、来源、语言和 query_hash 已存在时默认不重复采集。

## 文件存储规则

资料按 raw、extracted_document、Source、Evidence Chunk 分层保存。阶段 1 只生成资料层，不生成结论层。

## 安全与合规限制

- Crawlbase API key 只从环境变量 CRAWLBASE_TOKEN 读取。
- Reddit 只抓公开页面。
- 不处理登录态、私信、删除内容、验证码或访问控制绕过。
- 不下载音频文件，只保存 wav URL 和文本。
- 不把粉丝讨论当作正史。
- Fandom 在本项目中可作为主要/官方信息来源，但仍需保留 source_url 和 source_type 以便追溯。

## 示例对话

用户：我想写一个关于芙宁娜在现代 AU 中重新面对审判创伤的故事。

skill：根据 story profile 生成 keyword_plan，默认路由到 Fandom；如果需要论坛讨论则加入 Reddit，先检查缓存，再收集 raw、extracted_document、Source 和 Evidence Chunk。
