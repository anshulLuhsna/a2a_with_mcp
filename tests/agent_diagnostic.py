#!/usr/bin/env python3
import os
import sys
import logging
import json
import uuid

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add necessary paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Test the agent's get_reddit_data function directly"""
    logger.info("Starting diagnostic test for SentimentAnalysisAgent.get_reddit_data")
    
    # Import the function directly from agent.py
    from sentiment_analysis_agent.agent_core.agent import get_reddit_data
    
    # Test parameters
    subreddit = "Bitcoin"
    limit = 5
    session_id = f"diagnostic-test-{uuid.uuid4()}"
    
    logger.info(f"Calling get_reddit_data(subreddit='{subreddit}', limit={limit}, session_id='{session_id}')")
    
    # Call the function
    result = get_reddit_data(subreddit, limit, session_id)
    
    # Process the result
    try:
        logger.info(f"Function returned result (first 200 chars): {result[:200]}...")
        
        parsed = json.loads(result)
        if isinstance(parsed, dict) and "error" in parsed:
            logger.error(f"Function returned error: {parsed['error']}")
        elif isinstance(parsed, list):
            logger.info(f"Successfully retrieved {len(parsed)} posts!")
            if len(parsed) > 0:
                logger.info(f"First post title: {parsed[0].get('title', 'No title')}")
                logger.info(f"First post ID: {parsed[0].get('id', 'No ID')}")
        else:
            logger.warning(f"Unexpected result format: {type(parsed)}")
    except json.JSONDecodeError:
        logger.error(f"Failed to parse result as JSON: {result[:200]}...")

    logger.info("Diagnostic test complete")

if __name__ == "__main__":
    main() 