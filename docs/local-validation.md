# 本地验证流程

本文档说明本项目在本地开发或交付前建议执行的验证步骤。

## 1. 检查依赖声明

先确认仓库是否提供依赖声明文件：

```bash
find . -maxdepth 3 \( \
  -name 'requirements.txt' -o \
  -name 'pyproject.toml' -o \
  -name 'poetry.lock' -o \
  -name 'uv.lock' \
\) -print
```

如果存在依赖声明文件，应优先使用项目声明的方式创建本地虚拟环境并安装依赖。不要直接全局安装依赖。

当前仓库没有固定依赖清单时，至少需要本地 Python 3；运行完整 pytest 还需要额外安装 `pytest` 和项目使用的 Python 依赖，例如 `pyyaml`。

## 2. 语法检查

当环境缺少 pytest 或不希望安装依赖时，至少执行 Python 语法检查：

```bash
if [ -d src ]; then
  python3 -m compileall src tests
else
  python3 -m compileall tests
fi
python3 -m compileall .skills/story-info-collector/scripts
```

预期结果：命令退出码为 0，输出只包含 `Listing` / `Compiling` 信息，没有 traceback。

## 3. 离线 CLI smoke test

角色偏离分析提供 deterministic offline 模式，不需要真实 LLM key：

```bash
python3 .skills/story-info-collector/scripts/analyze_character_deviation.py \
  --source-text "Example trusts Ally." \
  --source-channel canon \
  --character Example \
  --scenario modern_au \
  --offline \
  --output /tmp/character_card.json

python3 -m json.tool /tmp/character_card.json >/dev/null
```

预期结果：两个命令退出码均为 0，并生成合法 JSON。

## 4. 完整 pytest 验证

如果本地环境已安装 pytest 和必要依赖，执行：

```bash
python3 -m pytest tests/test_story_info_collector.py tests/test_character_deviation.py -q
```

预期结果：所有测试通过。

如果输出：

```text
/usr/bin/python3: No module named pytest
```

说明当前 Python 环境缺少 pytest。此时不要把单元测试标记为已通过，只能说明已完成 `compileall` 和 CLI smoke test 等替代验证。

## 5. 真实 DeepSeek LLM 验证

真实 LLM 分析需要设置环境变量：

```bash
export DEEPSEEK_API_KEY="..."
export FICTION_ASSISTANT_LLM_PROVIDER="deepseek"
```

然后运行不带 `--offline` 的命令：

```bash
python3 .skills/story-info-collector/scripts/analyze_character_deviation.py \
  --source-text "Example Character keeps promises even under pressure." \
  --source-channel canon \
  --character "Example Character" \
  --scenario postwar \
  --output /tmp/character_card.deepseek.json
```

预期结果：生成合法 JSON。若 DeepSeek 调用失败，CLI 会直接失败并输出明确错误；不会自动伪装成 offline 结果。

## 6. 提交前清理

提交前清理 Python 运行缓存，并查看状态：

```bash
find . -type d -name __pycache__ -prune -exec rm -rf {} +
git status --short
```

不要提交：

- `.claude/settings.local.json`
- API key 或 token
- `__pycache__`
- 临时输出文件，例如 `/tmp/character_card.json`

## 7. 最终报告建议格式

交付时明确列出：

- 是否运行 pytest；
- 如果 pytest 未运行，原因是什么；
- 已完成哪些替代验证；
- 仍有哪些未验证风险。

示例：

```text
pytest 未运行原因：当前环境缺少 pytest。
已完成替代验证：compileall 语法检查、offline CLI JSON smoke test。
未验证风险：单元测试未执行，真实 DeepSeek 网络调用未执行。
```
