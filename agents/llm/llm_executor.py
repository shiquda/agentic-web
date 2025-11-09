"""
LLM Agent Executor

A2A协议执行器实现，支持从RequestContext提取消息历史
"""

import logging
from typing import Any

from a2a.server.agent_execution import RequestContext

from agents.base import BaseAgentExecutor
from agents.llm.llm_agent import LLMAgent


logger = logging.getLogger(__name__)


class LLMAgentExecutor(BaseAgentExecutor):
    """
    LLM Agent的A2A执行器

    支持从RequestContext提取消息历史并传递给LLM
    """

    def __init__(self, agent: LLMAgent):
        """
        初始化LLM Agent Executor

        Args:
            agent: LLMAgent实例
        """
        super().__init__(agent)

    async def prepare_input(self, context: RequestContext) -> Any:
        """
        从RequestContext提取消息作为输入

        从context中提取消息历史和当前消息，构建完整的对话上下文

        Args:
            context: 请求上下文

        Returns:
            消息列表，格式为 [{"role": "user/agent", "content": "..."}]
        """
        messages = []

        # 从 task history 中提取历史消息
        if context.current_task and context.current_task.history:
            logger.debug(
                f"Found task history with {len(context.current_task.history)} messages"
            )
            for msg in context.current_task.history:
                # 提取消息的文本内容
                text_content = ""
                if msg.parts:
                    for part in msg.parts:
                        # 检查 part 的类型并提取文本
                        if hasattr(part, "text") and part.text:
                            text_content += part.text
                        elif hasattr(part, "root") and hasattr(part.root, "text"):
                            text_content += part.root.text

                if text_content:
                    role = msg.role if msg.role == "user" else "assistant"
                    messages.append({"role": role, "content": text_content})
                    logger.debug(f"Added history message: role={role}, content={text_content[:50]}...")

        # 添加当前用户消息
        if context.message and context.message.parts:
            current_text = ""
            for part in context.message.parts:
                # 提取文本内容
                if hasattr(part, "text") and part.text:
                    current_text += part.text
                elif hasattr(part, "root") and hasattr(part.root, "text"):
                    current_text += part.root.text

            if current_text:
                messages.append({"role": "user", "content": current_text})
                logger.debug(f"Added current message: content={current_text[:50]}...")

        logger.info(f"Prepared {len(messages)} messages for LLM")

        # 如果没有提取到任何消息，返回 None 使用 agent 的默认行为
        return messages if messages else None


def create_llm_executor(
    llm_manager,
    name: str = "LLMAgent",
    system_prompt: str | None = None,
) -> LLMAgentExecutor:
    """
    创建LLM Agent Executor的便捷函数

    Args:
        llm_manager: LLM管理器实例
        name: Agent名称
        system_prompt: 系统提示词

    Returns:
        LLMAgentExecutor实例
    """
    agent = LLMAgent(
        llm_manager=llm_manager,
        name=name,
        system_prompt=system_prompt,
    )
    return LLMAgentExecutor(agent)
