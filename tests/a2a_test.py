#!/usr/bin/env python3
"""
A2A Agent Testing Tool - 纯命令行Agent测试工具
无需配置文件，直接通过命令行参数进行测试

Usage:
    uv run python tests/a2a_test.py http://localhost:9014
    uv run python tests/a2a_test.py http://localhost:9014 -m "测试文本"
    uv run python tests/a2a_test.py --discover
"""

import argparse
import asyncio
import json
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

import httpx


class TestStatus(Enum):
    """测试状态"""
    PASS = "✅"
    FAIL = "❌"
    SKIP = "⏭️"
    WARN = "⚠️"


class Colors:
    """控制台颜色"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


@dataclass
class TestResult:
    """测试结果"""
    name: str
    status: TestStatus
    duration: float
    message: str = ""
    details: Dict[str, Any] = None


class A2AClient:
    """A2A协议客户端"""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout, verify=False)

    async def get_agent_card(self) -> Optional[Dict[str, Any]]:
        """获取Agent Card"""
        try:
            response = await self.client.get(f"{self.base_url}/.well-known/agent-card.json")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return None

    async def send_message(self, content: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """发送消息（非流式）"""
        import uuid

        payload = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [
                        {"type": "text", "text": content}
                    ]
                }
            },
            "id": 1
        }

        if session_id:
            payload["params"]["sessionId"] = session_id

        try:
            response = await self.client.post(
                f"{self.base_url}/",  # 使用根路径，而不是 /api/v1/message
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}


    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


class AgentTester:
    """Agent测试器"""

    def __init__(self, url: str, verbose: bool = False):
        self.url = url
        self.verbose = verbose
        self.client = A2AClient(url)
        self.results: List[TestResult] = []

    def print_header(self, text: str):
        """打印标题"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}\n")

    def print_result(self, result: TestResult):
        """打印测试结果"""
        status_color = {
            TestStatus.PASS: Colors.GREEN,
            TestStatus.FAIL: Colors.RED,
            TestStatus.SKIP: Colors.YELLOW,
            TestStatus.WARN: Colors.YELLOW,
        }[result.status]

        print(f"{status_color}{result.status.value}{Colors.RESET} "
              f"{result.name} "
              f"{Colors.CYAN}({result.duration:.2f}s){Colors.RESET}")

        if result.message:
            print(f"   {result.message}")

        if self.verbose and result.details:
            print(f"   {Colors.BLUE}Details:{Colors.RESET}")
            for key, value in result.details.items():
                print(f"   - {key}: {value}")

    async def test_agent_card(self) -> TestResult:
        """测试1: Agent Card验证"""
        start = time.time()
        card = await self.client.get_agent_card()
        duration = time.time() - start

        if not card:
            return TestResult(
                name="Agent Card",
                status=TestStatus.FAIL,
                duration=duration,
                message="Failed to retrieve Agent Card"
            )

        # 验证必需字段
        required_fields = ["name", "version", "description", "protocolVersion"]
        missing_fields = [f for f in required_fields if f not in card]

        if missing_fields:
            return TestResult(
                name="Agent Card",
                status=TestStatus.FAIL,
                duration=duration,
                message=f"Missing required fields: {', '.join(missing_fields)}",
                details=card
            )

        return TestResult(
            name="Agent Card",
            status=TestStatus.PASS,
            duration=duration,
            message=f"Agent: {card.get('name')} v{card.get('version')}",
            details=card if self.verbose else None
        )

    async def test_message_send(self, message: str) -> TestResult:
        """测试2: 消息发送"""
        start = time.time()
        response = await self.client.send_message(message)
        duration = time.time() - start

        if "error" in response:
            return TestResult(
                name="Message Send",
                status=TestStatus.FAIL,
                duration=duration,
                message=f"Error: {response['error']}",
                details=response
            )

        # 验证JSON-RPC响应格式
        if "result" not in response:
            return TestResult(
                name="Message Send",
                status=TestStatus.FAIL,
                duration=duration,
                message="Invalid JSON-RPC response: missing 'result'",
                details=response
            )

        result = response.get("result", {})
        # result 可能直接是消息对象，或者包含 message 键
        message_obj = result.get("message", result) if "message" in result else result
        parts = message_obj.get("parts", [])

        # 提取响应文本
        response_text = ""
        for part in parts:
            # 支持 kind 或 type 字段
            part_type = part.get("kind") or part.get("type")
            if part_type == "text":
                response_text += part.get("text", "")

        if not response_text:
            return TestResult(
                name="Message Send",
                status=TestStatus.WARN,
                duration=duration,
                message="Response is empty",
                details=response
            )

        return TestResult(
            name="Message Send",
            status=TestStatus.PASS,
            duration=duration,
            message=f"Received response ({len(response_text)} chars)",
            details={"response": response_text[:500]} if self.verbose else None
        )

    async def test_protocol_compliance(self) -> TestResult:
        """测试3: 协议合规性"""
        start = time.time()
        card = await self.client.get_agent_card()
        duration = time.time() - start

        if not card:
            return TestResult(
                name="Protocol Compliance",
                status=TestStatus.SKIP,
                duration=duration,
                message="Skipped (Agent Card not available)"
            )

        checks = []

        # 检查协议版本
        protocol_version = card.get("protocolVersion", "")
        if protocol_version.startswith("0."):
            checks.append(("Protocol version", True, protocol_version))
        else:
            checks.append(("Protocol version", False, f"Unsupported: {protocol_version}"))

        # 检查capabilities
        capabilities = card.get("capabilities", {})
        streaming = capabilities.get("streaming", False)
        checks.append(("Streaming support", True, f"Enabled: {streaming}"))

        # 检查provider信息
        provider = card.get("provider", {})
        has_provider = bool(provider.get("organization") or provider.get("name"))
        checks.append(("Provider info", has_provider, "Present" if has_provider else "Missing"))

        all_passed = all(check[1] for check in checks)

        return TestResult(
            name="Protocol Compliance",
            status=TestStatus.PASS if all_passed else TestStatus.WARN,
            duration=duration,
            message=f"{sum(1 for c in checks if c[1])}/{len(checks)} checks passed",
            details={check[0]: check[2] for check in checks} if self.verbose else None
        )

    async def test_response_quality(self, message: str, expected_keywords: List[str] = None) -> TestResult:
        """测试4: 响应质量检查"""
        start = time.time()
        response = await self.client.send_message(message)
        duration = time.time() - start

        if "error" in response or "result" not in response:
            return TestResult(
                name="Response Quality",
                status=TestStatus.SKIP,
                duration=duration,
                message="Skipped (message send failed)"
            )

        result = response.get("result", {})
        # result 可能直接是消息对象，或者包含 message 键
        message_obj = result.get("message", result) if "message" in result else result
        parts = message_obj.get("parts", [])

        # 提取响应文本
        response_text = ""
        for part in parts:
            # 支持 kind 或 type 字段
            part_type = part.get("kind") or part.get("type")
            if part_type == "text":
                response_text += part.get("text", "")

        checks = []

        # 检查响应长度
        if len(response_text) > 10:
            checks.append(("Response length", True, f"{len(response_text)} chars"))
        else:
            checks.append(("Response length", False, "Too short"))

        # 检查关键词（如果提供）
        if expected_keywords:
            found_keywords = [kw for kw in expected_keywords if kw in response_text]
            all_found = len(found_keywords) == len(expected_keywords)
            checks.append((
                "Expected keywords",
                all_found,
                f"{len(found_keywords)}/{len(expected_keywords)} found: {found_keywords}" if found_keywords else "None found"
            ))

        # 检查是否为有效文本
        has_content = bool(response_text.strip())
        checks.append(("Has content", has_content, "Yes" if has_content else "No"))

        all_passed = all(check[1] for check in checks)

        return TestResult(
            name="Response Quality",
            status=TestStatus.PASS if all_passed else TestStatus.WARN,
            duration=duration,
            message=f"{sum(1 for c in checks if c[1])}/{len(checks)} checks passed",
            details={check[0]: check[2] for check in checks} if self.verbose else None
        )

    async def run_all_tests(self, message: str = None, expected_keywords: List[str] = None):
        """运行所有测试"""
        self.print_header(f"Testing Agent: {self.url}")

        # 默认测试消息
        if not message:
            message = "这是一个测试文本它有一些语法问题和标点问题需要检查"

        # 执行测试
        tests = [
            self.test_agent_card(),
            self.test_protocol_compliance(),
            self.test_message_send(message),
            self.test_response_quality(message, expected_keywords),
        ]

        for test_coro in tests:
            result = await test_coro
            self.results.append(result)
            self.print_result(result)

        # 打印总结
        self.print_summary()

    def print_summary(self):
        """打印测试总结"""
        print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")

        passed = sum(1 for r in self.results if r.status == TestStatus.PASS)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAIL)
        warned = sum(1 for r in self.results if r.status == TestStatus.WARN)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIP)
        total = len(self.results)
        total_time = sum(r.duration for r in self.results)

        print(f"{Colors.BOLD}Test Summary:{Colors.RESET}")
        print(f"  Total: {total} tests in {total_time:.2f}s")
        print(f"  {Colors.GREEN}✅ Passed: {passed}{Colors.RESET}")
        if failed > 0:
            print(f"  {Colors.RED}❌ Failed: {failed}{Colors.RESET}")
        if warned > 0:
            print(f"  {Colors.YELLOW}⚠️  Warned: {warned}{Colors.RESET}")
        if skipped > 0:
            print(f"  {Colors.YELLOW}⏭️  Skipped: {skipped}{Colors.RESET}")

        # 整体状态
        if failed > 0:
            status_text = f"{Colors.RED}FAILED{Colors.RESET}"
        elif warned > 0:
            status_text = f"{Colors.YELLOW}PASSED (with warnings){Colors.RESET}"
        else:
            status_text = f"{Colors.GREEN}PASSED{Colors.RESET}"

        print(f"\n{Colors.BOLD}Overall Status: {status_text}{Colors.RESET}")
        print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")

    async def cleanup(self):
        """清理资源"""
        await self.client.close()


async def discover_agents(start_port: int = 9001, end_port: int = 9020) -> List[str]:
    """自动发现本地Agent"""
    print(f"{Colors.CYAN}🔍 Discovering agents on localhost:{start_port}-{end_port}...{Colors.RESET}\n")

    discovered = []
    async with httpx.AsyncClient(timeout=2) as client:
        for port in range(start_port, end_port + 1):
            url = f"http://localhost:{port}"
            try:
                response = await client.get(f"{url}/.well-known/agent-card.json")
                if response.status_code == 200:
                    card = response.json()
                    agent_name = card.get("name", "unknown")
                    print(f"  {Colors.GREEN}✅{Colors.RESET} Found: {agent_name} at {url}")
                    discovered.append(url)
            except:
                pass

    print(f"\n{Colors.CYAN}Found {len(discovered)} agent(s){Colors.RESET}\n")
    return discovered


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="A2A Agent Testing Tool - 命令行Agent测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 测试单个Agent
  python a2a_test.py http://localhost:9014

  # 带自定义测试消息
  python a2a_test.py http://localhost:9014 -m "测试文本"

  # 检查特定关键词
  python a2a_test.py http://localhost:9014 -k "原文分析" "修改建议"

  # 详细模式
  python a2a_test.py http://localhost:9014 -v

  # 自动发现并测试所有Agent
  python a2a_test.py --discover
        """
    )

    parser.add_argument(
        "url",
        nargs="?",
        help="Agent URL (e.g., http://localhost:9014)"
    )
    parser.add_argument(
        "-m", "--message",
        help="Test message to send",
        default=None
    )
    parser.add_argument(
        "-k", "--keywords",
        nargs="+",
        help="Expected keywords in response",
        default=None
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Auto-discover and test all local agents"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )

    args = parser.parse_args()

    # 自动发现模式
    if args.discover:
        urls = await discover_agents()
        if not urls:
            print(f"{Colors.RED}No agents found{Colors.RESET}")
            return

        for i, url in enumerate(urls, 1):
            if i > 1:
                print("\n" + "=" * 60 + "\n")
            tester = AgentTester(url, verbose=args.verbose)
            try:
                await tester.run_all_tests(args.message, args.keywords)
            finally:
                await tester.cleanup()
        return

    # 单Agent测试模式
    if not args.url:
        parser.print_help()
        return

    tester = AgentTester(args.url, verbose=args.verbose)
    try:
        await tester.run_all_tests(args.message, args.keywords)
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
