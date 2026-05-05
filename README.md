# ISR Fanfiction Skill

本项目是一个面向小说写作辅助的 Claude skill 工作区，当前包含两条可组合能力：

1. **Story Info Collector / 故事资料采集**：按作品、角色、场景和信息需求采集并整理资料。
2. **Character Deviation Analysis / 角色原著设定偏离检测与创作辅助**：基于来源感知证据提取角色断言、检测冲突、按写作场景调节、推荐创作分支，并生成临时人设卡。

项目目标是让后续不同作品、角色、场景和 user prompt 的定制尽量通过配置、prompt template 或少量 adapter 完成，而不是修改核心 pipeline。

## 目录概览

```text
.skills/story-info-collector/
  SKILL.md
  README.md
  config.example.yaml
  profiles/
    genshin.story-profile.yaml
  config/character_deviation/
    assertion_types.yaml
    source_channels.yaml
    conflict_types.yaml
    scenario_adapters.yaml
    output_formats.yaml
    prompts/
  scripts/
    collect_story_info.py
    analyze_character_deviation.py
    character_deviation/
      schemas.py
      config_loader.py
      prompt_renderer.py
      llm_client.py
      graph_store.py
      reranker.py
      pipeline.py
  schemas/

tests/
  test_story_info_collector.py
  test_character_deviation.py

docs/superpowers/
  specs/
  plans/
```

## 故事资料采集

`collect_story_info.py` 是现有采集入口。它使用 profile 驱动关键词、路线、source policy 和存储位置，阶段边界是“采集与归一化资料”，不在该阶段做角色推理或断言合并。

当前 Fandom 与 Reddit 公开资料采集都通过 Crawlbase adapter 执行：

- Fandom 使用 `Crawlbase Fandom` 路线抓取角色 wiki 页面，并从 profile 中优先选择英文/ASCII alias 作为页面标题；
- Reddit 使用 `Crawlbase Reddit` 路线抓取公开 subreddit 搜索结果；
- 两条路线都会把 Crawlbase 返回体归一化为 JSON 安全结构，并把验证码页、空内容和 `original_status >= 400` 视为失败，而不是误报成功；
- 采集成功后会写出 raw、extracted JSON/Markdown、source metadata、chunk 和 manifest，供后续 claim 抽取使用。

真实采集示例：

```bash
python3 .skills/story-info-collector/scripts/collect_story_info.py \
  --request "我想要撰写一篇芙宁娜和那维莱特的校园现代风格文章。" \
  --config .skills/story-info-collector/config.example.yaml \
  --profile .skills/story-info-collector/profiles/genshin.story-profile.yaml \
  --include-reddit \
  --refresh
```

离线 dry-run 示例：

```bash
python3 .skills/story-info-collector/scripts/collect_story_info.py \
  --request "我想要撰写一篇芙宁娜和那维莱特的校园现代风格文章。" \
  --config .skills/story-info-collector/config.example.yaml \
  --profile .skills/story-info-collector/profiles/genshin.story-profile.yaml \
  --include-reddit \
  --dry-run
```

## 角色偏离检测与创作辅助

`analyze_character_deviation.py` 是新增分析入口。它支持两类输入：

- story-info-collector 产出的 JSON/JSONL source 或 evidence chunk；
- 直接传入的一段文本或 JSON source。

Pipeline 阶段：

1. input normalization：统一为 `SourceDocument`；
2. assertion extraction：用 LLM 抽取统一 `Assertion`；
3. source-aware claim graph：构建来源感知断言图，不提前合并多来源结论；
4. conflict detection：检测人格、关系、时间线、世界观、动机冲突；
5. scenario conditioning：保留 core invariants，只调整场景变量；
6. branch recommendation：输出 `canon_safe`、`fanon_consensus`、`niche_but_coherent`；
7. character card generation：生成临时 JSON 人设卡并保留 source trace。

离线示例：

```bash
python3 .skills/story-info-collector/scripts/analyze_character_deviation.py \
  --source-text "Example Character keeps promises even under pressure." \
  --source-channel canon \
  --character "Example Character" \
  --scenario modern_au \
  --offline \
  --output /tmp/character_card.json
```

使用采集 chunk 生成图谱与角色卡示例：

```bash
python3 .skills/story-info-collector/scripts/analyze_character_deviation.py \
  --input docs/chunks/yuan-shen__fu-zhu-na__character-information__fandom__7242c3a68999__chunk-0.json \
  --input docs/chunks/yuan-shen__fu-zhu-na__forum-analysis__reddit__4b6461e82484__chunk-0.json \
  --input docs/chunks/yuan-shen__fu-zhu-na__forum-analysis__reddit__4b6461e82484__chunk-1.json \
  --input docs/chunks/yuan-shen__fu-zhu-na__forum-analysis__reddit__4b6461e82484__chunk-2.json \
  --character 芙宁娜 \
  --scenario campus_modern \
  --offline \
  --output /tmp/furina_deviation_validation.json
```

真实 LLM 示例：

```bash
python3 .skills/story-info-collector/scripts/analyze_character_deviation.py \
  --input docs/chunks/yuan-shen__fu-zhu-na__character-information__fandom__7242c3a68999__chunk-0.json \
  --character 芙宁娜 \
  --scenario campus_modern \
  --output /tmp/character_card.json
```

## 配置扩展方式

角色偏离分析的领域知识集中在：

- `assertion_types.yaml`：断言类型与字段提示；
- `source_channels.yaml`：正史、官方参考、粉丝结构化知识、粉丝讨论/同人文等来源 channel；
- `conflict_types.yaml`：冲突类型与严重度规则；
- `scenario_adapters.yaml`：现代 AU、战后、if 线、黑化、恋爱线等场景调节；
- `output_formats.yaml`：输出格式和 Character Card V2 预留字段；
- `prompts/*.md`：所有 LLM prompt template。

核心 Python 代码只依赖 schema 和 config，不直接依赖具体作品、角色、场景或 prompt 文本。

## DeepSeek 与 Crawlbase 环境变量（可自行使用其它替换）

本地运行真实 LLM 分析需要：

```bash
export DEEPSEEK_API_KEY="..."
export FICTION_ASSISTANT_LLM_PROVIDER="deepseek"
```

如果使用 Crawlbase Fandom 或 Reddit 采集，需要至少配置一个 Crawlbase token：

```bash
export CRAWLBASE_TOKEN="..."
export CRAWLBASE_JS_TOKEN="..."
```

`CRAWLBASE_JS_TOKEN` 是真实浏览器/JavaScript token；当它存在时，Fandom 与 Reddit adapter 会优先使用它，否则回退到 `CRAWLBASE_TOKEN`。

## 输出与审计

角色分析输出默认是 JSON，包含：

- `assertions`
- `claim_graph`
- `deviation_report`
- `scenario_conditioning`
- `recommendations`
- `character_card`

每条 assertion 和人设卡都保留 `source_trace`，包括 `source_id`、`source_type`、`source_channel`、原文 quote 和 version。设计上禁止把矛盾证据平均成单一答案，便于审计正史、官方参考、粉丝共识和小众解释之间的差异。

## 测试与验证

常规测试命令：

```bash
python3 -m pytest tests/test_story_info_collector.py tests/test_character_deviation.py -q
```

如果当前环境没有安装 pytest，可至少运行语法检查：

```bash
python3 -m compileall .skills tests
```

本功能已用示例 prompt `我想要撰写一篇芙宁娜和那维莱特的校园现代风格文章。` 验证过以下链路：

1. prompt 拆解识别 `芙宁娜`、`那维莱特`、`校园现代`；
2. Crawlbase Fandom 与 Crawlbase Reddit 真实采集成功，输出 2 个 source 和 4 个 chunk；
3. raw 输出使用 `CRAWLBASE_JS_TOKEN` / `javascript` 模式，结构化 `original_status` 为 200，且未命中验证码页；
4. 离线角色偏离分析可从上述 chunk 生成 assertion、claim graph 和临时 character card，并保留 source trace。

最近一次本地验证命令：

```bash
.venv/bin/python -m pytest tests/test_story_info_collector.py tests/test_character_deviation.py
.venv/bin/python -m compileall .skills tests
```
