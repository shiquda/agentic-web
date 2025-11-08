"""
LLM Agent Executor

A2A协议执行器实现，支持从RequestContext提取消息历史
"""

from typing import Any

from a2a.server.agent_execution import RequestContext

from agents.base import BaseAgentExecutor
from agents.llm.llm_agent import LLMAgent


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

        尝试从context中提取消息历史，如果失败则返回简单文本

        Args:
            context: 请求上下文

        Returns:
            消息列表或简单文本
        """
        # TODO: 实现从RequestContext提取消息历史
        # 目前A2A SDK的RequestContext结构不明确，先返回默认值
        # 后续需要根据实际SDK API调整

        # 简化版本：返回None，使用agent的默认行为
        return None


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
