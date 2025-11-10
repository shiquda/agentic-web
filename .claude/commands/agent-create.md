# Agent 创建命令

使用此命令快速创建新的 A2A Agent。

## 使用方式

**MCP 服务器调研（第一步）**：
```
调研 [MCP服务器仓库URL或名称]
需要了解：
1. 通信方式（stdio/http/sse）
2. 启动命令和参数
3. 环境变量要求
4. 提供的工具列表和功能

使用子代理完成调研，避免上下文污染。
```

**LLM Agent（翻译/文本处理/问答等）**：
```
创建一个[功能描述]Agent，使用[LLM]接口，功能是[详细说明]。
推荐流程：1.设计提示词 2.备份agents.yaml 3.编辑配置 4.重启服务器 5.测试验证
```

**MCP Agent（工具型Agent）**：
```
我需要创建一个使用[MCP服务器名称]的Agent。
先帮我调研这个MCP服务器的：1.通信方式 2.配置要求 3.提供的工具
然后按标准流程创建Agent。
```

---

## 流程A：LLM Agent

### 步骤总览
1. 设计系统提示词
2. 备份配置文件（时间戳）
3. 编辑agents.yaml添加Agent
4. 重启服务器
5. 运行测试验证

### 配置模板
```yaml
agents:
  - name: your-agent
    description: "Agent功能描述"
    type: llm
    host: 0.0.0.0
    port: 9015                    # 使用未占用端口
    llm_provider: deepseek
    provider:
      organization: "3-ChenZhiyu"
      url: "https://github.com/shiquda"
    extra:
      system_prompt: |
        你是一个专业的[角色]助手。

        CAPABILITIES:
        - [能力1]
        - [能力2]

        OUTPUT FORMAT:
        [输出格式要求]

        GUIDELINES:
        [交互指南]
```

### 测试命令
```bash
# 基础测试
uv run python tests/a2a_test.py http://localhost:9015

# 关键词验证
uv run python tests/a2a_test.py http://localhost:9015 -k "关键词1" "关键词2"

# 详细输出
uv run python tests/a2a_test.py http://localhost:9015 -v
```

### API端点
```bash
# Agent Card (A2A协议标准端点)
curl http://localhost:9015/.well-known/agent-card.json

# 发送消息 (A2A协议)
curl -X POST http://localhost:9015/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": {
      "type": "text",
      "text": "你的测试消息"
    }
  }'
```

---

## 流程B：MCP Agent

### 步骤总览
0. **MCP调研**（必需！）- 调研通信方式和配置
1. 设计系统提示词（含工具使用指南）
2. 备份配置文件
3. 编辑agents.yaml添加MCP服务器和Agent
4. 重启服务器
5. 运行测试验证

### MCP调研请求模板
```
我需要创建一个使用[MCP服务器名称]的Agent。请帮我调研：
1. 通信方式（stdio/http/sse/streamable_http）
2. 具体配置（URL/命令/参数）
3. 环境变量或API密钥要求
4. 提供的工具列表
```

### MCP服务器配置模板

**HTTP类型**：
```yaml
mcp_servers:
  your-mcp-server:
    transport: http
    url: "https://api.example.com/mcp"
    verify_ssl: false
    use_proxy: false
```

**stdio类型**：
```yaml
mcp_servers:
  your-mcp-server:
    transport: stdio
    command: node
    args: ["/path/to/server.js"]
    env:
      API_KEY: "${YOUR_API_KEY}"
```

**SSE类型**：
```yaml
mcp_servers:
  your-mcp-server:
    transport: sse
    url: "https://api.example.com/mcp/sse"
```

### MCP Agent配置模板
```yaml
agents:
  - name: your-mcp-agent
    description: "Agent功能描述"
    type: mcp                     # 注意类型是mcp
    host: 0.0.0.0
    port: 9015
    llm_provider: deepseek
    provider:
      organization: "3-ChenZhiyu"
      url: "https://github.com/shiquda"
    extra:
      mcp_config:
        servers:
          - your-mcp-server       # 引用MCP服务器名称
        max_tool_calls: 10
        tool_choice: auto         # auto/required/none
        system_prompt: |
          你是一个[功能]助手，具有[MCP工具]能力。

          AVAILABLE TOOLS:
          - [工具1]: [功能描述]
          - [工具2]: [功能描述]

          TOOL USAGE:
          1. 何时使用工具
          2. 如何组合工具
          3. 错误处理方式
```

### 验证MCP连接
检查启动日志应看到：
```
MCP client 'your-mcp-server' found X tools: [...]
MCP Agent 'your-agent' loaded X tools from 1 servers
```

---

## 端口分配

端口分配信息记录在项目根目录的 `PORTS.md` 文件中。

**添加新Agent时**:
1. 查看 `PORTS.md` 获取下一个可用端口
2. 在配置中使用该端口
3. 更新 `PORTS.md`,添加新Agent记录并更新"下一个可用端口"

---

## 快速示例

### 示例1：语法检查Agent（LLM）
```
创建一个语法检查与润色Agent，使用deepseek接口，
功能是对文本进行语法检查与润色，输出格式包含：
原文分析、修改建议、润色后文本、主要改进点。
推荐流程：1.设计提示词 2.备份agents.yaml 3.编辑配置 4.重启服务器 5.测试验证
```

测试：
```bash
uv run python tests/a2a_test.py http://localhost:9015 \
    -k "原文分析" "修改建议" "润色后文本" "主要改进点"
```

### 示例2：网络搜索Agent（MCP）
```
我需要创建一个使用Tavily Search MCP服务器的Agent。
先帮我调研这个MCP服务器的配置方式。
然后创建一个网络搜索Agent。
```

---

## 常见问题速查

**Q: 测试失败怎么办？**
- Agent Card失败 → 检查YAML格式
- Message Send失败 → 检查LLM配置和API密钥
- Response Quality警告 → 使用`-v`查看详细输出

**Q: MCP Agent工具未加载？**
- 检查transport类型是否正确
- 检查URL/命令路径是否正确
- 检查环境变量是否设置
- 查看启动日志的错误信息

**Q: 如何查看完整响应？**
```bash
uv run python tests/a2a_test.py http://localhost:9015 -v
```

---

## 完整文档

详细文档见：`docs/AGENT_DEVELOPMENT_WORKFLOW.md`
测试工具文档：`tests/README.md`
