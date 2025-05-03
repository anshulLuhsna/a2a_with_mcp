#!/usr/bin/env python3
"""
Test script to verify MCP client connection works correctly.
This tests the connection without using asyncio.run() to ensure compatibility
with existing event loops.
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

async def test_mcp_connection():
    """Test the MCP client connection asynchronously."""
    logger.info("Starting MCP connection test...")
    
    try:
        # Create the client
        async with MultiServerMCPClient(MCP_SERVER_CONFIG) as client:
            # Get the tools
            tools = client.get_tools()
            logger.info(f"MCP client initialized successfully with tools: {[t.name for t in tools]}")
            
            # Test a call to one of the tools if any are available
            if tools:
                tool = tools[0]
                logger.info(f"Testing tool: {tool.name}")
                
                # Try a simple query to test connection
                try:
                    # Assuming the first tool is 'query' from postgres_mcp.py
                    # Adjust as needed for your actual tool
                    if tool.name == "query":
                        result = await tool.ainvoke({"sql": "SELECT version();"})
                        logger.info(f"Tool query result: {result}")
                    else:
                        logger.info(f"Tool {tool.name} available but not tested")
                except Exception as e:
                    logger.error(f"Error testing tool {tool.name}: {e}")
            else:
                logger.warning("No tools available to test")
            
            return tools
    except Exception as e:
        logger.error(f"Failed to initialize MCP client: {e}")
        return []

def main():
    """Main entry point for the test script."""
    loop = asyncio.new_event_loop()
    try:
        tools = loop.run_until_complete(test_mcp_connection())
        if tools:
            print(f"\n✅ SUCCESS: MCP client connected successfully with {len(tools)} tools")
            print(f"Available tools: {[t.name for t in tools]}")
        else:
            print("\n❌ FAILURE: MCP client failed to connect or no tools available")
    finally:
        loop.close()

if __name__ == "__main__":
    main() 