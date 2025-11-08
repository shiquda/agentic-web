# A2A Agent 调试指南

本指南介绍如何使用官方A2A Inspector工具来调试和验证你的Agent。

## A2A Inspector 简介

A2A Inspector是官方提供的Web界面调试工具，用于：

✅ **连接A2A Agent** - 指定agent的URL进行连接
✅ **查看Agent Card** - 查看agent的能力和配置
✅ **协议验证** - 实时验证是否符合A2A规范
✅ **交互式聊天** - 通过UI与agent对话
✅ **调试控制台** - 查看完整的JSON-RPC消息

## 安装 A2A Inspector

### 方法1: 使用Docker（推荐）

最简单的方式，无需配置本地环境：

```bash
# 拉取并运行
docker run -d -p 8080:8080 ghcr.io/a2aproject/a2a-inspector:latest

# 访问 http://127.0.0.1:8080
```

### 方法2: 本地开发安装

**前置要求：**
- Python 3.10+
- Node.js & npm
- uv包管理器

**安装步骤：**

```bash
# 1. 克隆仓库
git clone https://github.com/a2aproject/a2a-inspector.git
cd a2a-inspector

# 2. 安装后端依赖
uv sync

# 3. 安装前端依赖
cd frontend && npm install && cd ..

# 4. 运行（使用便捷脚本）
chmod +x scripts/run.sh
bash scripts/run.sh
```

或者手动运行两个终端：

**终端1 - 前端：**
```bash
cd frontend
npm run build -- --watch
```

**终端2 - 后端：**
```bash
cd backend
uv run app.py
```

访问: http://127.0.0.1:5001

## 调试我们的Echo Agent

### 步骤1: 启动Echo Agent

```bash
# 在项目目录
uv run main.py
```

服务器将运行在 `http://localhost:9999`

### 步骤2: 打开A2A Inspector

访问 http://127.0.0.1:5001 (本地) 或 http://127.0.0.1:8080 (Docker)

### 步骤3: 连接到Agent

在Inspector界面中输入：
```
http://localhost:9999
```

### 步骤4: 查看和验证

**Agent Card信息：**
- 名称: Echo Agent
- 版本: 1.0.0
- 技能: Echo
- 传输协议: JSONRPC
- 流式支持: ✓

**发送测试消息：**
1. 在聊天框中输入消息
2. 查看agent响应
3. 在调试控制台查看完整的JSON-RPC消息

**验证合规性：**
- Inspector会自动验证响应是否符合A2A规范
- 任何不符合规范的地方会高亮显示

## 调试控制台说明

调试控制台会显示完整的通信细节：

**请求示例：**
```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{"text": "Hello"}]
    }
  },
  "id": 1
}
```

**响应示例：**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "id": "task-123",
    "status": "completed",
    "output": [{
      "role": "agent",
      "parts": [{"text": "Echo Agent响应: Hello from Echo Agent!"}]
    }]
  },
  "id": 1
}
```

## 常见调试场景

### 1. 验证Agent Card

检查你的agent是否正确返回Agent Card：

```bash
curl http://localhost:9999/.well-known/agent-card.json | jq
```

### 2. 测试JSON-RPC端点

直接测试消息发送：

```bash
curl -X POST http://localhost:9999 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"text": "Hello"}]
      }
    },
    "id": 1
  }'
```

### 3. 检查服务器日志

查看服务器输出来发现错误：

```bash
uv run main.py
# 观察日志输出
```

## 其他调试工具

### A2A SDK自带的CLI客户端

```bash
# 安装samples
git clone https://github.com/a2aproject/a2a-samples.git
cd a2a-samples/samples/python/hosts/cli

# 连接到你的agent
uv run . --agent http://localhost:9999
```

### 使用Python脚本调试

我们已经有的`test_client.py`就是一个很好的调试工具：

```bash
uv run test_client.py
```

它会：
- 测试Agent Card获取
- 发送多条测试消息
- 验证响应格式
- 显示详细日志

## 最佳实践

1. **开发时始终运行Inspector** - 实时查看agent行为
2. **检查协议合规性** - Inspector会标记所有不符合规范的地方
3. **查看完整消息** - 使用调试控制台查看JSON-RPC细节
4. **测试边缘情况** - 发送各种输入测试agent的健壮性
5. **监控性能** - 注意响应时间和资源使用

## 故障排查

### Inspector无法连接

```bash
# 1. 检查agent是否运行
curl http://localhost:9999/.well-known/agent-card.json

# 2. 检查端口占用
netstat -ano | findstr :9999

# 3. 查看防火墙设置
```

### 协议验证失败

- 检查Agent Card格式是否正确
- 确保所有必需字段都存在
- 验证JSON-RPC响应格式
- 查看Inspector的错误提示

### 消息无响应

- 检查agent_executor.py中的execute方法
- 确保event_queue正确发送消息
- 查看服务器日志中的错误

## 扩展阅读

- [A2A Protocol官方文档](https://a2a-protocol.org/)
- [A2A Inspector GitHub](https://github.com/a2aproject/a2a-inspector)
- [A2A Python SDK文档](https://a2a-protocol.org/latest/sdk/python/api/)
- [A2A示例项目](https://github.com/a2aproject/a2a-samples)

## 总结

A2A Inspector是开发A2A agent的必备工具。它提供了：
- 🔍 实时调试界面
- ✅ 协议合规性验证
- 📊 详细的消息查看
- 💬 交互式测试

配合`test_client.py`和服务器日志，你可以全面了解agent的运行状况并快速定位问题。
