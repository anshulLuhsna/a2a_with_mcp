#!/usr/bin/env python3
"""
Test script for async MCP tool invocation.
This directly tests the async tool invocation without the full LangGraph workflow.
"""
import asyncio
import logging
from langchain_mcp_adapters.client import MultiServerMCPClient

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure the Postgres MCP server
MCP_SERVER_CONFIG = {
    "postgres": {
        "command": "python3",
        "args": ["MCP-servers/postgres_mcp.py"],
        "transport": "stdio",
    }
}

async def test_async_tool_invocation():
    """Test async invocation of MCP tools."""
    logger.info("Starting async MCP tool invocation test...")
    
    try:
        # Create the MCP client
        async with MultiServerMCPClient(MCP_SERVER_CONFIG) as client:
            # Get the tools
            tools = client.get_tools()
            logger.info(f"MCP client initialized with tools: {[t.name for t in tools]}")
            
            # Test each tool directly
            for tool in tools:
                logger.info(f"Testing tool: {tool.name}")
                
                try:
                    if tool.name == "query":
                        # Test the query tool with a simple SQL query
                        sql_query = "SELECT 'test' AS result;"
                        # Directly await the tool's ainvoke method
                        result = await tool.ainvoke({"sql": sql_query})
                        logger.info(f"Query result: {result}")
                    elif tool.name == "fetch_financial_snapshot":
                        # Test the fetch_financial_snapshot tool
                        # Directly await the tool's ainvoke method
                        result = await tool.ainvoke({})
                        logger.info(f"Financial snapshot result: {result}")
                    else:
                        logger.info(f"Skipping tool {tool.name} - no test case defined")
                except Exception as e:
                    logger.error(f"Error testing tool {tool.name}: {e}")
            
            return tools
    except Exception as e:
        logger.error(f"Failed to initialize MCP client: {e}")
        return []

def main():
    """Main entry point for the test script."""
    loop = asyncio.new_event_loop()
    try:
        tools = loop.run_until_complete(test_async_tool_invocation())
        if tools:
            print(f"\n✅ SUCCESS: MCP client async tool invocation tested with {len(tools)} tools")
            print(f"Available tools: {[t.name for t in tools]}")
        else:
            print("\n❌ FAILURE: MCP client failed to connect or no tools available")
    finally:
        loop.close()

if __name__ == "__main__":
    main() 