"""Run with the installed distribution's interpreter, outside the checkout."""

import argparse
import faulthandler
import importlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import sys
import sysconfig


async def check_mcp(executable: Path) -> None:
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from k_commerce_cli.services.tools import list_tool_names

    with anyio.fail_after(30):
        async with stdio_client(StdioServerParameters(command=str(executable))) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert sorted(t.name for t in tools.tools) == sorted(list_tool_names())
                detail = next(t for t in tools.tools if t.name == "product_detail")
                assert set(detail.inputSchema["properties"]) == {"provider", "url"}
                assert set(detail.inputSchema["required"]) == {"provider", "url"}
                providers = await session.call_tool("get_providers", {})
                assert not providers.isError
                assert providers.structuredContent == {"result": ["coupang"]}
                failure = await session.call_tool("product_detail", {"provider": "coupang", "url": "https://example.invalid/not-a-product"})
                payload = failure.structuredContent
                if payload is None:
                    payload = json.loads(next(block.text for block in failure.content if block.type == "text"))
                assert payload["success"] is False
                assert payload["error_code"] == "invalid_url"
                assert payload["retryable"] is False
                assert payload["next_tools"] == []
    print("MCP initialize, list_tools, get_providers, invalid product URL, and shutdown: passed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--python-version", required=True)
    args = parser.parse_args()
    assert f"{sys.version_info.major}.{sys.version_info.minor}" == args.python_version
    assert version("k-commerce") == args.version
    installed_root = Path(sysconfig.get_path("purelib")).resolve()
    for name in ("k_commerce_cli.cli", "k_commerce_cli.services.tools.serialization", "k_commerce_mcp.server"):
        print(f"Importing {name}", flush=True)
        module = importlib.import_module(name)
        assert Path(module.__file__).resolve().is_relative_to(installed_root), module.__file__
    bin_dir = Path(sysconfig.get_path("scripts"))
    subprocess.run([str(bin_dir / "k-commerce"), "--help"], check=True, timeout=15)
    import anyio
    anyio.run(check_mcp, bin_dir / "k-commerce-mcp")
    print(f"Installed k-commerce {args.version} on Python {args.python_version}: passed")


if __name__ == "__main__":
    faulthandler.dump_traceback_later(45)
    main()
    faulthandler.cancel_dump_traceback_later()
