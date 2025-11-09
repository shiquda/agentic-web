"""
MCP Agent Executor

A2A协议执行器实现，支持MCP工具调用和流式响应
"""

import logging
import traceback
from typing import Any

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, TaskState, TextPart
from a2a.utils import new_agent_text_message

from agents.base import BaseAgentExecutor
from agents.mcp.mcp_agent import MCPAgent


logger = logging.getLogger(__name__)


class MCPAgentExecutor(BaseAgentExecutor):
    """
    MCP Agent的A2A执行器

    支持从RequestContext提取消息并执行流式响应的ReAct循环
    在每个步骤发送中间消息，避免客户端超时
    """

    def __init__(self, agent: MCPAgent):
        """
        初始化MCP Agent Executor

        Args:
            agent: MCPAgent实例
        """
        super().__init__(agent)

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        执行Agent逻辑（流式响应版本）

        在ReAct循环的每个步骤发送中间消息事件，
        确保客户端及时收到响应，避免超时

        Args:
            context: 请求上下文
            event_queue: 事件队列
        """
        try:
            # 创建 TaskUpdater 用于发送中间状态更新
            updater = TaskUpdater(event_queue, context.task_id, context.context_id)

            # 确保工具已加载（懒加载）
            await self.agent._ensure_tools_loaded()

            # 从context提取输入
            user_message = await self.prepare_input(context)

            if not user_message:
                # 发送错误消息（使用 TaskUpdater 标记任务失败，符合 A2A 协议）
                error_message = updater.new_agent_message(
                    parts=[Part(root=TextPart(text="No message content found"))]
                )
                await updater.failed(error_message)
                return

            logger.info(f"MCP Agent '{self.agent.name}' processing: {user_message[:100]}...")

            # 立即发送初始状态更新，避免客户端超时
            initial_message = updater.new_agent_message(
                parts=[Part(root=TextPart(text="🔄 Processing your request..."))]
            )
            await updater.update_status(
                TaskState.working,
                message=initial_message,
                final=False
            )

            # 检查是否使用原生tool calling
            use_native_mode = (
                self.agent.llm_manager.config.tool_calling_enabled
                and self.agent.llm_manager.config.tool_calling_mode == "native"
            )

            if use_native_mode:
                logger.info(f"MCP Agent '{self.agent.name}' using NATIVE tool calling mode")
                result = await self._execute_native_mode(user_message, updater)
            else:
                logger.info(f"MCP Agent '{self.agent.name}' using PROMPT tool calling mode")
                result = await self._execute_prompt_mode(user_message, updater)

            # 发送最终答案（使用 add_artifact + complete，符合 A2A 最佳实践）
            logger.info(f"Sending final result as artifact...")

            # 1. 添加最终结果作为 artifact（实际内容）
            await updater.add_artifact(
                parts=[Part(root=TextPart(text=result))],
                name="mcp_agent_result",
                last_chunk=True
            )
            logger.info(f"Final result added as artifact")

            # 2. 标记任务完成（描述性消息）
            completion_message = updater.new_agent_message(
                parts=[Part(root=TextPart(text="✅ Task completed successfully!"))]
            )
            await updater.complete(completion_message)
            logger.info(f"Task marked as completed")
            return

        except Exception as e:
            logger.error(
                f"Error in MCP Agent '{self.agent.name}' execution: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            # 发送错误消息给客户端（使用 TaskUpdater 标记任务失败，符合 A2A 协议）
            error_message = updater.new_agent_message(
                parts=[Part(root=TextPart(text=f"Sorry, an error occurred while processing your request: {str(e)}"))]
            )
            await updater.failed(error_message)
            raise

    async def _execute_native_mode(self, user_message: str, updater: TaskUpdater) -> str:
        """
        执行 Native Tool Calling 模式（带进度更新）

        Args:
            user_message: 用户消息
            updater: 任务更新器（用于发送进度）

        Returns:
            最终响应
        """
        from agents.mcp.mcp_agent_tools import convert_mcp_tools_to_openai, execute_mcp_tool_native
        import json

        # 准备系统提示词
        system_prompt = self.agent.mcp_config.system_prompt or "You are a helpful AI assistant with access to tools."

        # 准备消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        # 将MCP工具转换为OpenAI格式
        openai_tools = convert_mcp_tools_to_openai(self.agent._tools_cache)

        # ReAct循环
        for iteration in range(1, self.agent.mcp_config.max_tool_calls + 2):
            logger.info(f"MCP Agent '{self.agent.name}' starting iteration {iteration}/{self.agent.mcp_config.max_tool_calls + 1}")

            # 调用LLM（传入tools）
            response = await self.agent.llm_manager.chat(messages, tools=openai_tools)

            logger.debug(
                f"LLM response (iteration {iteration}): "
                f"content={response.content[:100] if response.content else 'None'}..., "
                f"tool_calls={len(response.tool_calls) if response.tool_calls else 0}"
            )

            # 如果没有工具调用，返回响应
            if not response.tool_calls:
                logger.info(
                    f"MCP Agent '{self.agent.name}' got final answer (iteration {iteration}, length: {len(response.content or '')} chars)"
                )
                return response.content or "No response content"

            # 发送思考进度
            thinking_text = f"🤔 Thinking... (calling {len(response.tool_calls)} tool(s))"
            thinking_message = updater.new_agent_message(
                parts=[Part(root=TextPart(text=thinking_text))]
            )
            await updater.update_status(
                TaskState.working,
                message=thinking_message,
                final=False
            )

            # 有工具调用，添加助手消息到历史
            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in response.tool_calls
                ]
            })

            logger.info(f"Executing {len(response.tool_calls)} tool call(s)...")

            # 执行所有工具调用
            for tool_call in response.tool_calls:
                # 解析工具名（OpenAI格式：server:tool_name）
                tool_key = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                logger.info(f"Executing tool call: tool='{tool_key}', arguments={arguments}")

                # 执行MCP工具
                result = await execute_mcp_tool_native(
                    tool_key, arguments, self.agent._tools_cache, self.agent.mcp_pool
                )

                # 将结果添加到消息历史
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

                logger.debug(f"Tool '{tool_key}' executed, result length: {len(result)} chars")

                # 发送工具执行进度
                progress_text = f"✓ Tool '{tool_key}' executed"
                progress_message = updater.new_agent_message(
                    parts=[Part(root=TextPart(text=progress_text))]
                )
                await updater.update_status(
                    TaskState.working,
                    message=progress_message,
                    final=False
                )

        # 达到最大迭代次数
        logger.warning(
            f"MCP Agent '{self.agent.name}' reached max iterations ({self.agent.mcp_config.max_tool_calls})"
        )
        return "Sorry, I couldn't complete the task within the allowed tool calls."

    async def _execute_prompt_mode(self, user_message: str, updater: TaskUpdater) -> str:
        """
        执行 Prompt 模式（带进度更新）

        Args:
            user_message: 用户消息
            updater: 任务更新器（用于发送进度）

        Returns:
            最终响应
        """
        # 准备对话历史
        messages = self.agent._build_initial_messages(user_message)

        # ReAct循环
        for iteration in range(self.agent.mcp_config.max_tool_calls + 1):
            logger.info(
                f"MCP Agent '{self.agent.name}' starting iteration {iteration + 1}/"
                f"{self.agent.mcp_config.max_tool_calls + 1}"
            )

            # LLM推理（不传入tools）
            response = await self.agent.llm_manager.chat(messages)
            assistant_message = response.content

            logger.debug(
                f"LLM response (iteration {iteration + 1}): "
                f"{assistant_message[:200]}..."
            )

            # 检查是否需要调用工具（解析JSON）
            tool_calls = self.agent._parse_tool_calls(assistant_message)

            logger.info(f"Parsed {len(tool_calls)} tool call(s) from LLM response")

            if not tool_calls:
                # 没有工具调用，直接返回响应
                logger.info(
                    f"MCP Agent '{self.agent.name}' got final answer (iteration {iteration + 1}, length: {len(assistant_message)} chars)"
                )
                return assistant_message

            # 发送思考进度
            thinking_text = f"🤔 Thinking... (calling {len(tool_calls)} tool(s))"
            thinking_message = updater.new_agent_message(
                parts=[Part(root=TextPart(text=thinking_text))]
            )
            await updater.update_status(
                TaskState.working,
                message=thinking_message,
                final=False
            )

            # 执行工具调用
            logger.info(
                f"MCP Agent '{self.agent.name}' executing {len(tool_calls)} tool call(s) "
                f"(iteration {iteration + 1})"
            )

            # 将助手消息添加到历史
            messages.append({"role": "assistant", "content": assistant_message})

            # 调用工具并收集结果
            tool_results = []
            for tool_call in tool_calls:
                result = await self.agent._execute_tool_call(tool_call)
                tool_results.append(result)

                # 发送工具执行进度
                tool_name = tool_call.get("tool", "unknown")
                if "error" in result:
                    progress_text = f"❌ Tool '{tool_name}' failed: {result['error']}"
                else:
                    progress_text = f"✓ Tool '{tool_name}' executed"

                progress_message = updater.new_agent_message(
                    parts=[Part(root=TextPart(text=progress_text))]
                )
                await updater.update_status(
                    TaskState.working,
                    message=progress_message,
                    final=False
                )

            # 将工具结果添加到历史
            tool_message = self.agent._format_tool_results(tool_results)
            messages.append({"role": "user", "content": tool_message})

        # 达到最大迭代次数
        logger.warning(
            f"MCP Agent '{self.agent.name}' reached max iterations "
            f"({self.agent.mcp_config.max_tool_calls})"
        )
        return "Sorry, I couldn't complete the task within the allowed tool calls."

    async def prepare_input(self, context: RequestContext) -> Any:
        """
        从RequestContext提取消息作为输入

        从context中提取当前用户消息（MCP Agent内部会维护ReAct循环）

        Args:
            context: 请求上下文

        Returns:
            用户消息字符串
        """
        # 提取当前用户消息
        if context.message and context.message.parts:
            current_text = ""
            for part in context.message.parts:
                # 提取文本内容
                if hasattr(part, "text") and part.text:
                    current_text += part.text
                elif hasattr(part, "root") and hasattr(part.root, "text"):
                    current_text += part.root.text

            if current_text:
                logger.debug(f"Extracted message: {current_text[:100]}...")
                return current_text

        logger.debug("No message content found in context")
        return None
