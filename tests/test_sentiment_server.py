#!/usr/bin/env python3
import os
import sys
import logging
import json
import requests
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    """Test the sentiment analysis agent server API with a direct request"""
    logger.info("Testing sentiment analysis agent server API")
    
    # Server URL - modify if running on a different port
    server_url = "http://localhost:10000/api/agent/sentiment-analysis"
    
    # Test query
    test_query = {
        "query": "Get latest sentiment for BTC from subreddit Bitcoin",
        "company": "BTC",
        "subreddit": "Bitcoin",
        "timeframe": "latest",
        "session_id": f"api-test-{uuid.uuid4()}"
    }
    
    logger.info(f"Sending request to {server_url} with query: {json.dumps(test_query)}")
    
    # Make the API request
    try:
        response = requests.post(server_url, json=test_query, timeout=60)
        
        # Check if request was successful
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Server returned status code {response.status_code}")
            logger.info(f"Response (truncated): {json.dumps(result)[:200]}...")
        else:
            logger.error(f"Server returned error status code {response.status_code}")
            logger.error(f"Error: {response.text}")
    
    except Exception as e:
        logger.exception(f"Error calling server API: {e}")
    
    logger.info("Test completed")

if __name__ == "__main__":
    main() 