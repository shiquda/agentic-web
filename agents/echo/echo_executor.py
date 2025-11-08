"""
Echo Agent Executor

A2A协议执行器实现
"""

from agents.base import SimpleAgentExecutor
from agents.echo.echo_agent import EchoAgent


class EchoAgentExecutor(SimpleAgentExecutor):
    """
    Echo Agent的A2A执行器

    使用SimpleAgentExecutor简化实现
    """

    def __init__(self, name: str = "EchoAgent"):
        """
        初始化Echo Agent Executor

        Args:
            name: Agent名称
        """
        agent = EchoAgent(name=name)
        super().__init__(agent)


# 创建默认executor实例（用于向后兼容）
executor = EchoAgentExecutor()
