"""
多端口服务器管理器

功能：
- 在单个进程中管理多个Agent服务器
- 每个Agent运行在独立端口
- 统一的生命周期管理
- 优雅的启动和关闭
"""

import asyncio
import logging
import signal
from typing import Callable

import uvicorn
from fastapi import FastAPI

from core.config import ConfigManager, AgentConfigModel


logger = logging.getLogger(__name__)


class ServerManager:
    """
    多端口服务器管理器

    使用示例:
        # 创建应用构建器
        def build_app(agent_config: AgentConfigModel) -> FastAPI:
            # 根据agent配置构建FastAPI应用
            ...

        # 创建管理器
        manager = ServerManager(config_manager, build_app)

        # 启动所有服务器
        await manager.start_all()
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        app_builder: Callable[[AgentConfigModel], FastAPI],
    ):
        """
        初始化服务器管理器

        Args:
            config_manager: 配置管理器
            app_builder: 应用构建函数，接受AgentConfigModel返回FastAPI应用
        """
        self.config_manager = config_manager
        self.app_builder = app_builder
        self.servers: dict[str, uvicorn.Server] = {}
        self._shutdown_event = asyncio.Event()

    def _create_server(self, agent_config: AgentConfigModel) -> uvicorn.Server:
        """
        为单个Agent创建服务器

        Args:
            agent_config: Agent配置

        Returns:
            uvicorn.Server实例
        """
        # 构建FastAPI应用
        app = self.app_builder(agent_config)

        # 创建uvicorn配置
        config = uvicorn.Config(
            app=app,
            host=agent_config.host,
            port=agent_config.port,
            log_level="info",
            access_log=True,
        )

        # 创建服务器
        server = uvicorn.Server(config)
        logger.info(
            f"Created server for agent '{agent_config.name}' "
            f"at {agent_config.host}:{agent_config.port}"
        )

        return server

    async def start_agent(self, agent_name: str):
        """
        启动单个Agent服务器

        Args:
            agent_name: Agent名称

        Raises:
            KeyError: Agent不存在
            RuntimeError: Agent已在运行
        """
        if agent_name in self.servers:
            raise RuntimeError(f"Agent '{agent_name}' is already running")

        agent_config = self.config_manager.get_agent(agent_name)
        server = self._create_server(agent_config)
        self.servers[agent_name] = server

        logger.info(f"Starting agent '{agent_name}'...")
        await server.serve()

    async def start_all(self):
        """
        并发启动所有Agent服务器

        这个方法会阻塞直到收到关闭信号
        """
        agents = self.config_manager.get_all_agents()

        if not agents:
            logger.warning("No agents configured, nothing to start")
            return

        logger.info(f"Starting {len(agents)} agent(s)...")

        # 为每个agent创建服务器
        tasks = []
        for agent_config in agents:
            server = self._create_server(agent_config)
            self.servers[agent_config.name] = server

            # 创建服务器运行任务
            task = asyncio.create_task(
                server.serve(),
                name=f"agent-{agent_config.name}"
            )
            tasks.append(task)

        # 设置信号处理
        self._setup_signal_handlers()

        logger.info("All agents started successfully")
        self._print_status()

        # 等待关闭信号
        try:
            await self._shutdown_event.wait()
        except asyncio.CancelledError:
            logger.info("Received cancellation, shutting down...")

        # 关闭所有服务器
        await self.shutdown_all()

    async def shutdown_agent(self, agent_name: str):
        """
        关闭单个Agent服务器

        Args:
            agent_name: Agent名称
        """
        if agent_name not in self.servers:
            logger.warning(f"Agent '{agent_name}' is not running")
            return

        server = self.servers[agent_name]
        logger.info(f"Shutting down agent '{agent_name}'...")

        server.should_exit = True
        await asyncio.sleep(0.1)  # 给服务器一点时间优雅关闭

        del self.servers[agent_name]
        logger.info(f"Agent '{agent_name}' shut down successfully")

    async def shutdown_all(self):
        """关闭所有Agent服务器"""
        logger.info("Shutting down all agents...")

        # 并发关闭所有服务器
        shutdown_tasks = []
        for name, server in self.servers.items():
            logger.info(f"Stopping agent '{name}'...")
            server.should_exit = True
            shutdown_tasks.append(asyncio.create_task(asyncio.sleep(0)))

        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

        self.servers.clear()
        logger.info("All agents shut down successfully")

    def _setup_signal_handlers(self):
        """设置信号处理器以支持优雅关闭"""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating shutdown...")
            self._shutdown_event.set()

        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _print_status(self):
        """打印所有运行中的Agent状态"""
        logger.info("=" * 60)
        logger.info("Agent Status:")
        logger.info("=" * 60)
        for name, server in self.servers.items():
            agent_config = self.config_manager.get_agent(name)
            logger.info(
                f"  - {name}: {agent_config.type} @ {agent_config.url}"
            )
        logger.info("=" * 60)

    def get_running_agents(self) -> list[str]:
        """获取所有正在运行的Agent名称列表"""
        return list(self.servers.keys())

    def is_agent_running(self, agent_name: str) -> bool:
        """检查指定Agent是否正在运行"""
        return agent_name in self.servers


class MultiAgentServer:
    """
    简化的多Agent服务器启动器

    使用示例:
        async def main():
            server = MultiAgentServer("config/agents.yaml", app_builder)
            await server.run()
    """

    def __init__(
        self,
        config_path: str,
        app_builder: Callable[[AgentConfigModel], FastAPI],
    ):
        """
        初始化多Agent服务器

        Args:
            config_path: 配置文件路径
            app_builder: 应用构建函数
        """
        from core.config import initialize_config

        # 加载配置
        self.config_manager = initialize_config(config_path)

        # 创建服务器管理器
        self.manager = ServerManager(self.config_manager, app_builder)

        # 配置日志
        self._configure_logging()

    def _configure_logging(self):
        """配置日志系统"""
        system_config = self.config_manager.get_system_config()

        logging.basicConfig(
            level=system_config.log_level,
            format=system_config.log_format,
        )

    async def run(self):
        """运行服务器（阻塞直到收到关闭信号）"""
        logger.info("Starting Multi-Agent Server...")
        await self.manager.start_all()
        logger.info("Multi-Agent Server stopped")

    async def stop(self):
        """停止服务器"""
        await self.manager.shutdown_all()
