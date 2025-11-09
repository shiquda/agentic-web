"""
MCP Agent 工具转换辅助函数

将MCP工具格式转换为OpenAI工具格式
"""

import json
import logging
from typing import Any


logger = logging.getLogger(__name__)


def convert_mcp_tools_to_openai(tools_cache: dict[str, Any]) -> list[dict]:
    """
    将MCP工具转换为OpenAI tools格式

    Args:
        tools_cache: MCP工具缓存（格式：tool_key -> {server, tool}）

    Returns:
        OpenAI tools格式的工具列表
    """
    openai_tools = []

    for tool_key, tool_info in tools_cache.items():
        tool = tool_info["tool"]

        # 构建OpenAI tool格式
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool_key,  # 使用 "server:tool_name" 作为函数名
                "description": tool.description or f"Tool: {tool_key}",
            }
        }

        # 添加参数schema（如果有）
        if hasattr(tool, "inputSchema") and tool.inputSchema:
            # MCP的inputSchema已经是JSON Schema格式，可以直接使用
            openai_tool["function"]["parameters"] = tool.inputSchema
        else:
            # 没有schema，使用空对象
            openai_tool["function"]["parameters"] = {
                "type": "object",
                "properties": {},
            }

        openai_tools.append(openai_tool)

    logger.debug(f"Converted {len(openai_tools)} MCP tools to OpenAI format")
    return openai_tools


async def execute_mcp_tool_native(
    tool_key: str,
    arguments: dict,
    tools_cache: dict[str, Any],
    mcp_pool: Any
) -> str:
    """
    执行MCP工具并返回字符串结果（用于native mode）

    Args:
        tool_key: 工具键（格式：server:tool_name）
        arguments: 工具参数
        tools_cache: MCP工具缓存
        mcp_pool: MCP管理器池

    Returns:
        工具执行结果（字符串格式）
    """
    if tool_key not in tools_cache:
        error_msg = f"Tool '{tool_key}' not found in cache"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

    tool_info = tools_cache[tool_key]
    server_name = tool_info["server"]
    tool_name = tool_info["tool"].name

    logger.info(f"Executing MCP tool: server='{server_name}', tool='{tool_name}', args={arguments}")

    try:
        client = mcp_pool.get_client(server_name)
        result = await client.call_tool(tool_name, arguments)

        # 提取结果内容
        if result.structuredContent:
            content = result.structuredContent
        elif result.content:
            text_parts = []
            for item in result.content:
                if hasattr(item, "text"):
                    text_parts.append(item.text)
            content = "\n".join(text_parts) if text_parts else "Tool executed successfully"
        else:
            content = "Tool executed successfully (no output)"

        # 转换为字符串
        if isinstance(content, str):
            return content
        else:
            return json.dumps(content, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error executing MCP tool '{tool_key}': {e}", exc_info=True)
        return json.dumps({"error": str(e)})
