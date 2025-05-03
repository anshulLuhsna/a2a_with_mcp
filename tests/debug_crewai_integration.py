#!/usr/bin/env python3
import os
import sys
import logging
import json
import uuid
import time

# Configure verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_crewai.log')
    ]
)
logger = logging.getLogger(__name__)

# Make sure all libraries log at DEBUG level
logging.getLogger('crewai').setLevel(logging.DEBUG)
logging.getLogger('sentiment_analysis_agent').setLevel(logging.DEBUG)

# Add the repo root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Monkey patch the fetch_reddit_data_tool to add debugging
from sentiment_analysis_agent.agent_core.agent import fetch_reddit_data_tool

original_fetch_reddit_data_tool = fetch_reddit_data_tool

def debug_fetch_reddit_data_tool(subreddit, limit=15, session_id=None):
    logger.debug(f"DEBUG WRAPPER: fetch_reddit_data_tool called with subreddit={subreddit}, limit={limit}, session_id={session_id}")
    try:
        # Add timestamp for timing the call
        start_time = time.time()
        result = original_fetch_reddit_data_tool(subreddit, limit, session_id)
        elapsed = time.time() - start_time
        
        # Log success or error
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict) and "error" in parsed:
                logger.error(f"DEBUG WRAPPER: fetch_reddit_data_tool error: {parsed['error']}")
            elif isinstance(parsed, list):
                logger.debug(f"DEBUG WRAPPER: fetch_reddit_data_tool succeeded with {len(parsed)} posts in {elapsed:.2f}s")
            else:
                logger.warning(f"DEBUG WRAPPER: fetch_reddit_data_tool returned unexpected format: {type(parsed)}")
        except json.JSONDecodeError:
            logger.error(f"DEBUG WRAPPER: fetch_reddit_data_tool returned invalid JSON: {result[:100]}...")
            
        return result
    except Exception as e:
        logger.exception(f"DEBUG WRAPPER: fetch_reddit_data_tool exception: {str(e)}")
        raise
        
# Replace the original function with our debug wrapper
import sentiment_analysis_agent.agent_core.agent
sentiment_analysis_agent.agent_core.agent.fetch_reddit_data_tool = debug_fetch_reddit_data_tool

def main():
    """Run a test of the SentimentAnalysisAgent with CrewAI integration"""
    logger.info("Starting CrewAI integration test")
    
    # Import the agent
    from sentiment_analysis_agent.agent_core.agent import SentimentAnalysisAgent
    
    # Create the agent
    agent = SentimentAnalysisAgent()
    logger.info("Created SentimentAnalysisAgent instance")
    
    # Test query and session ID
    test_query = json.dumps({
        "query": "Get latest sentiment for BTC from subreddit Bitcoin",
        "company": "BTC",
        "subreddit": "Bitcoin",
        "timeframe": "latest",
        "session_id": f"crewai-debug-test-{uuid.uuid4()}"
    })
    
    logger.info(f"Invoking agent with query: {test_query}")
    
    # Run the agent
    try:
        result = agent.invoke(test_query)
        logger.info(f"Agent returned result (truncated): {result[:200]}...")
    except Exception as e:
        logger.exception(f"Error invoking agent: {e}")
    
    logger.info("CrewAI integration test complete")

if __name__ == "__main__":
    main() 