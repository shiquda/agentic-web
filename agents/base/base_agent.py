"""
基础Agent抽象类

所有Agent的业务逻辑基类
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """
    Agent业务逻辑基类

    所有Agent都应继承此类并实现invoke方法

    使用示例:
        class MyAgent(BaseAgent):
            async def invoke(self, input_data: str) -> str:
                # 实现具体逻辑
                return f"Processed: {input_data}"
    """

    def __init__(self, name: str | None = None):
        """
        初始化Agent

        Args:
            name: Agent名称（可选）
        """
        self.name = name or self.__class__.__name__

    @abstractmethod
    async def invoke(self, input_data: Any = None) -> Any:
        """
        执行Agent的核心逻辑

        Args:
            input_data: 输入数据（可选）

        Returns:
            处理结果
        """
        pass

    async def initialize(self) -> None:
        """
        初始化Agent（可选重写）

        在Agent开始处理请求前调用，用于加载资源、初始化连接等
        """
        pass

    async def cleanup(self) -> None:
        """
        清理Agent资源（可选重写）

        在Agent停止时调用，用于释放资源、关闭连接等
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
