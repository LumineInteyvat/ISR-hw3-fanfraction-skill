# 故事资料收集器

## 适用场景

当用户准备写故事、同人、AU、角色心理、关系线或世界观相关内容时，使用本 skill 收集可追溯资料。

## 不适用场景

本 skill 不做角色判断、不做 OOC 检测、不生成三分支建议、不生成人设卡、不抽取 Claim、不构建知识图谱。

## 输入格式

用户可以用自然语言描述故事需求，例如：

> 我想写一个关于芙宁娜在现代 AU 中重新面对审判创伤的故事。

也可以补充角色、作品、语言和资料范围。

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

- Fandom：角色资料、作品资料、世界观和结构化粉丝百科。
- obcSpider：米游社官方角色语音、角色简介和 wav 链接。
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
- 不把 Fandom 资料标记为官方正史。

## 示例对话

用户：我想写一个关于芙宁娜在现代 AU 中重新面对审判创伤的故事。

skill：生成 keyword_plan，路由到 Fandom、obcSpider 和 Reddit，先检查缓存，再收集 raw、extracted_document、Source 和 Evidence Chunk。
