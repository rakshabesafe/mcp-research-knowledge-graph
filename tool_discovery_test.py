
import asyncio
import time
from fastmcp.client import Client
from fastmcp.client.transports import SSETransport
from fastmcp_server import mcp_server


async def main():
    """Connects to the MCP server and lists the available tools."""
    client = Client(transport=SSETransport(url="http://localhost:8000/tools/discover"))
    with mcp_server.run_in_thread():
        time.sleep(1)
        async with client:
            try:
                tools = await client.list_tools()
                if tools:
                    print("Discovered tools:")
                    for tool in tools:
                        print(f"- {tool.name}")
                else:
                    print("No tools discovered.")
            except Exception as e:
                print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
