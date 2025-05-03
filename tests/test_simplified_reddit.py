#!/usr/bin/env python3
import os
import sys
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Test the RedditDataTool with our new simplified MCP session"""
    logger.info("Testing the simplified MCP implementation with the RedditDataTool")
    
    # Import the tool directly
    from sentiment_analysis_agent.agent_core.agent import fetch_reddit_data_tool
    
    # Test parameters
    subreddit = "Bitcoin"
    limit = 5
    session_id = "test-session-456"
    
    logger.info(f"Fetching data for r/{subreddit} with limit={limit}")
    
    try:
        # Call the tool
        result = fetch_reddit_data_tool(
            subreddit=subreddit,
            limit=limit,
            session_id=session_id
        )
        
        logger.info(f"Tool returned result: {result[:100]}...")
        
        # Parse the result
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict) and "error" in parsed:
                logger.error(f"Tool returned error: {parsed['error']}")
            elif isinstance(parsed, list):
                logger.info(f"Successfully retrieved {len(parsed)} posts!")
                # Print first post title as proof
                if len(parsed) > 0:
                    logger.info(f"First post title: {parsed[0].get('title', 'No title')}")
            else:
                logger.warning(f"Unexpected result format: {type(parsed)}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse result as JSON: {result[:100]}...")
            
    except Exception as e:
        logger.exception(f"Error calling RedditDataTool: {e}")

if __name__ == "__main__":
    main() 