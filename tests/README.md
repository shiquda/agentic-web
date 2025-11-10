# A2A Agent 测试工具使用文档

## 简介

`a2a_test.py` 是一个零配置的命令行测试工具，用于快速测试基于 A2A（Agent-to-Agent）协议的Agent。无需编写配置文件，直接通过命令行参数即可完成测试。

## 核心特性

- ✅ **零配置**：无需配置文件，直接运行
- ✅ **A2A协议完整测试**：自动验证Agent Card、JSON-RPC、协议合规性
- ✅ **灵活的测试参数**：支持自定义测试消息和期待关键词
- ✅ **自动发现**：自动发现本地运行的所有Agent
- ✅ **彩色输出**：清晰的控制台彩色输出
- ✅ **详细模式**：可选的详细输出，查看完整响应内容

## 安装

无需额外安装。工具位于 `tests/a2a_test.py`，使用项目的依赖即可运行。

## 基本使用

### 1. 测试单个Agent

```bash
# 基础测试 - 使用默认测试消息
uv run python tests/a2a_test.py http://localhost:9014

# 自定义测试消息
uv run python tests/a2a_test.py http://localhost:9014 -m "这是测试文本"

# 检查特定关键词（适用于需要验证响应内容的场景）
uv run python tests/a2a_test.py http://localhost:9014 -k "原文分析" "修改建议" "润色后文本"

# 详细模式 - 显示完整的响应内容
uv run python tests/a2a_test.py http://localhost:9014 -v
```

### 2. 自动发现并测试所有Agent

```bash
# 自动发现本地9001-9020端口的所有Agent并逐一测试
uv run python tests/a2a_test.py --discover
```

### 3. 调整超时时间

```bash
# 设置30秒超时（默认30秒）
uv run python tests/a2a_test.py http://localhost:9014 --timeout 30
```

## 测试项目

工具会自动执行以下4项测试：

### 1. Agent Card（Agent元数据）
- 验证 `/.well-known/agent-card.json` 端点
- 检查必需字段：`name`, `version`, `description`, `protocolVersion`
- 验证字段格式是否符合A2A规范

### 2. Protocol Compliance（协议合规性）
- 检查协议版本（0.x系列）
- 验证capabilities配置（如streaming支持）
- 检查provider信息完整性

### 3. Message Send（消息发送）
- 发送测试消息到Agent
- 验证JSON-RPC 2.0响应格式
- 检查响应是否包含有效内容
- 测量响应时间

### 4. Response Quality（响应质量）
- 检查响应长度（>10字符）
- 验证期待关键词（如果指定）
- 确认响应包含实际内容

## 输出说明

### 状态符号

- ✅ **PASS**（绿色）：测试通过
- ❌ **FAIL**（红色）：测试失败
- ⚠️ **WARN**（黄色）：测试通过但有警告
- ⏭️ **SKIP**（黄色）：测试跳过

### 输出示例

```
============================================================
Testing Agent: http://localhost:9014
============================================================

✅ Agent Card (0.02s)
   Agent: grammar-checker v1.0.0
✅ Protocol Compliance (0.01s)
   3/3 checks passed
✅ Message Send (7.38s)
   Received response (309 chars)
✅ Response Quality (6.45s)
   2/2 checks passed

============================================================
Test Summary:
  Total: 4 tests in 13.85s
  ✅ Passed: 4

Overall Status: PASSED
============================================================
```

## 常见使用场景

### 场景1：开发新Agent后快速验证

```bash
# grammar-checker Agent开发完成，快速测试基础功能
uv run python tests/a2a_test.py http://localhost:9014

# 验证特定功能（如grammar-checker的四个部分）
uv run python tests/a2a_test.py http://localhost:9014 \
    -k "原文分析" "修改建议" "润色后文本" "主要改进点"
```

### 场景2：调试Agent响应内容

```bash
# 使用详细模式查看完整响应
uv run python tests/a2a_test.py http://localhost:9014 -v \
    -m "测试文本"
```

### 场景3：批量测试所有Agent

```bash
# 一次性测试所有运行中的Agent
uv run python tests/a2a_test.py --discover
```

### 场景4：测试翻译Agent

```bash
# 测试translator Agent的翻译功能
uv run python tests/a2a_test.py http://localhost:9004 \
    -m "Translate to Chinese: Hello, world!" \
    -k "你好" "世界"
```

### 场景5：性能测试

```bash
# 使用较长文本测试性能
uv run python tests/a2a_test.py http://localhost:9014 \
    -m "这是一段很长的文本..." \
    --timeout 60
```

## 命令行参数完整说明

```
usage: a2a_test.py [-h] [-m MESSAGE] [-k KEYWORDS [KEYWORDS ...]] [-v]
                   [--discover] [--timeout TIMEOUT]
                   [url]

positional arguments:
  url                   Agent URL (例如: http://localhost:9014)

optional arguments:
  -h, --help            显示帮助信息
  -m MESSAGE, --message MESSAGE
                        测试消息内容（不指定则使用默认消息）
  -k KEYWORDS [KEYWORDS ...], --keywords KEYWORDS [KEYWORDS ...]
                        期待在响应中出现的关键词列表
  -v, --verbose         详细输出模式（显示完整响应内容）
  --discover            自动发现并测试本地所有Agent（9001-9020端口）
  --timeout TIMEOUT     请求超时时间（秒），默认30秒
```

## 与GUI测试的对比

| 特性 | GUI测试（Inspector） | a2a_test.py |
|------|---------------------|-------------|
| 启动速度 | 慢（需要启动浏览器） | 快（直接命令行） |
| 稳定性 | 中（可能遇到浏览器进程问题） | 高（无外部依赖） |
| 自动化 | 困难 | 容易 |
| 批量测试 | 不支持 | 支持（--discover） |
| CI/CD集成 | 困难 | 容易 |
| 详细报告 | 需要截图 | 结构化输出 |
| 学习成本 | 低（可视化） | 中（命令行） |

## 故障排除

### 问题1：Message Send失败（404）

**原因**：API端点路径错误

**解决方案**：确认Agent的消息端点是 `/`（根路径），而不是其他路径。

### 问题2：Response Quality警告

**原因**：响应为空或缺少期待关键词

**解决方案**：
1. 使用 `-v` 查看完整响应
2. 检查测试消息是否合适
3. 检查Agent的system_prompt是否正确

### 问题3：超时

**原因**：Agent处理时间过长

**解决方案**：使用 `--timeout` 增加超时时间

## 扩展和定制

### 作为Python模块使用

```python
from tests.a2a_test import AgentTester
import asyncio

async def test_my_agent():
    tester = AgentTester("http://localhost:9014", verbose=True)
    try:
        await tester.run_all_tests(
            message="自定义测试消息",
            expected_keywords=["关键词1", "关键词2"]
        )
    finally:
        await tester.cleanup()

asyncio.run(test_my_agent())
```

### 自定义测试用例

可以直接修改 `a2a_test.py` 添加新的测试方法：

```python
async def test_custom(self) -> TestResult:
    """自定义测试"""
    # 实现你的测试逻辑
    return TestResult(...)
```

## 最佳实践

1. **开发时频繁测试**：每次修改Agent后立即运行测试
2. **使用关键词验证**：对于有特定输出格式的Agent，使用 `-k` 参数验证
3. **详细模式调试**：遇到问题时使用 `-v` 查看完整输出
4. **批量测试**：使用 `--discover` 定期测试所有Agent
5. **CI集成**：在CI/CD流水线中添加测试步骤

## 示例：完整测试流程

```bash
# 1. 启动Agent服务器
uv run main.py &

# 2. 等待启动
sleep 5

# 3. 快速验证grammar-checker
uv run python tests/a2a_test.py http://localhost:9014

# 4. 详细测试grammar-checker的特定功能
uv run python tests/a2a_test.py http://localhost:9014 \
    -m "这是测试文本它有语法问题" \
    -k "原文分析" "修改建议" "润色后文本" "主要改进点" \
    -v

# 5. 测试所有Agent
uv run python tests/a2a_test.py --discover

# 6. 停止服务器
kill %1
```

## 相关文档

- A2A协议规范：https://github.com/a2aproject/a2a-protocol
- 项目文档：../CLAUDE.md
- 配置示例：../config/agents.example.yaml

## 支持

如果遇到问题或有改进建议，请：
1. 查看本文档的故障排除部分
2. 检查项目的CLAUDE.md文档
3. 提交Issue到项目仓库
