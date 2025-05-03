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

# Set logging levels for specific modules
logging.getLogger('sentiment_analysis_agent').setLevel(logging.DEBUG)
logging.getLogger('crewai').setLevel(logging.INFO)  # Keep CrewAI at INFO to reduce noise
logging.getLogger('httpx').setLevel(logging.WARNING)  # Reduce HTTP request logging
logging.getLogger('httpcore').setLevel(logging.WARNING)  # Reduce HTTP request logging

# Add the repo root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Test the fixed SentimentAnalysisAgent with the new RedditDataTool"""
    logger.info("Testing fixed SentimentAnalysisAgent")
    
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
        "session_id": f"fixed-agent-test-{uuid.uuid4()}"
    })
    
    logger.info(f"Invoking agent with query: {test_query}")
    
    # Run the agent
    try:
        result = agent.invoke(test_query)
        logger.info(f"Agent returned result (truncated): {result[:200]}...")
    except Exception as e:
        logger.exception(f"Error invoking agent: {e}")
    
    logger.info("Test completed")

if __name__ == "__main__":
    main() 