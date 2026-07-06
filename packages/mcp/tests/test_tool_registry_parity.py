import pytest
from k_commerce_cli.services.tools import get_tool_definition, list_tool_names
from k_commerce_mcp.server import create_mcp_server


@pytest.mark.anyio
async def test_mcp_tool_names_match_shared_registry_exactly() -> None:
    mcp_server = create_mcp_server()

    tools = await mcp_server.list_tools()
    names = sorted(tool.name for tool in tools)

    assert names == sorted(list_tool_names())
    assert len(names) == 21


@pytest.mark.anyio
async def test_mcp_tool_descriptions_match_shared_registry() -> None:
    mcp_server = create_mcp_server()

    tools = await mcp_server.list_tools()
    descriptions = {tool.name: tool.description for tool in tools}

    assert descriptions == {
        name: get_tool_definition(name).description for name in list_tool_names()
    }


@pytest.mark.anyio
async def test_product_detail_tool_schema_does_not_expose_ocr_choice() -> None:
    mcp_server = create_mcp_server()

    tools = await mcp_server.list_tools()
    product_detail_tool = next(tool for tool in tools if tool.name == "product_detail")
    properties = product_detail_tool.inputSchema["properties"]

    assert set(properties) == {"provider", "url"}
    assert "include_ocr" not in properties
    assert "ocr_scope" not in properties
    assert "max_detail_images" not in properties
