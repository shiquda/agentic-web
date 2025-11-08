"""
Echo Agent实现

简单的回声Agent，演示基础Agent的使用
"""

from agents.base import BaseAgent


class EchoAgent(BaseAgent):
    """
    Echo Agent - 简单回声Agent

    接收任何输入，返回固定的欢迎消息
    """

    async def invoke(self, input_data=None) -> str:
        """
        执行Echo逻辑

        Args:
            input_data: 输入数据（此Agent忽略输入）

        Returns:
            固定的欢迎消息
        """
        return f"Echo Agent ({self.name}) 响应: Hello from Echo Agent!"
