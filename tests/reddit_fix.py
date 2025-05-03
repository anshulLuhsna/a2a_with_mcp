#!/usr/bin/env python3
import os
import sys
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_reddit_data(subreddit, limit=15, session_id=None):
    """Direct implementation of Reddit data fetching without using CrewAI tools
    
    Args:
        subreddit: Subreddit name to fetch posts from
        limit: Maximum number of posts to fetch
        session_id: Optional session ID for tracking
        
    Returns:
        JSON string with post data or error
    """
    # Import our simplified MCP session
    from sentiment_analysis_agent.agent_core.mcp_session import SimpleMCPSession
    
    # Validate subreddit parameter
    if not subreddit or not isinstance(subreddit, str) or len(subreddit.strip()) == 0:
        error_msg = "Missing or invalid subreddit parameter"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    
    # Remove any 'r/' prefix to ensure consistent handling
    if subreddit.startswith('r/'):
        subreddit = subreddit[2:]
        logger.info(f"Removed 'r/' prefix from subreddit name, now using: {subreddit}")
    
    # Use a session ID for tracking or generate one if not provided
    if session_id is None:
        import uuid
        session_id = str(uuid.uuid4())
        logger.info(f"Generated new session ID: {session_id}")
    
    try:
        # Use the SimpleMCPSession to communicate with the server
        with SimpleMCPSession() as mcp_session:
            logger.info(f"MCP Session initialized successfully")
            
            # Call the get_subreddit_new_posts tool
            tool_name = "get_subreddit_new_posts"
            logger.info(f"Calling MCP tool '{tool_name}' for r/{subreddit} with limit={limit}")
            
            result = mcp_session.call(
                tool_name,
                {
                    "subreddit_name": subreddit,
                    "limit": limit,
                    "session_id": session_id
                }
            )
            
            logger.info(f"MCP tool call completed")
            # Log the raw result (but truncate if too large)
            if len(result) > 1000:
                logger.debug(f"Raw result (first 1000 chars): {result[:1000]}...")
            else:
                logger.debug(f"Raw result: {result}")
                
            return result
        
    except Exception as e:
        error_msg = f"Failed to fetch data from r/{subreddit}: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})

def main():
    """Test our direct Reddit data fetching implementation"""
    logger.info("Testing direct Reddit data fetching")
    
    # Test parameters
    subreddit = "Bitcoin"
    limit = 5
    session_id = "test-session-789"
    
    logger.info(f"Fetching data for r/{subreddit} with limit={limit}")
    
    # Call our function
    result = get_reddit_data(subreddit, limit, session_id)
    
    # Process the result
    try:
        truncated_result = result[:100] + "..." if len(result) > 100 else result
        logger.info(f"Function returned result (truncated): {truncated_result}")
        
        parsed = json.loads(result)
        if isinstance(parsed, dict) and "error" in parsed:
            logger.error(f"Function returned error: {parsed['error']}")
        elif isinstance(parsed, list):
            logger.info(f"Successfully retrieved {len(parsed)} posts!")
            # Print first post title as proof
            if len(parsed) > 0:
                logger.info(f"First post title: {parsed[0].get('title', 'No title')}")
                logger.info(f"First post author: {parsed[0].get('author', 'No author')}")
                logger.info(f"First post ID: {parsed[0].get('id', 'No ID')}")
        else:
            logger.warning(f"Unexpected result format: {type(parsed)}")
    except json.JSONDecodeError:
        logger.error(f"Failed to parse result as JSON: {result[:100]}...")

if __name__ == "__main__":
    main() 