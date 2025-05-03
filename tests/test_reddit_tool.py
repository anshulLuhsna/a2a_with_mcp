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
    """Test the RedditDataTool directly without the agent framework"""
    logger.info("Starting direct test of MCP server for Reddit")
    
    # Import needed modules
    import os
    import sys
    import json
    import socket
    import subprocess
    import time
    from contextlib import ExitStack
    
    # Script location - hardcoded to avoid import issues
    script_path = os.path.abspath("sentiment_analysis_agent/mcp-server-reddit/src/mcp_server_reddit/__main__.py")
    src_dir = os.path.abspath("sentiment_analysis_agent/mcp-server-reddit/src")
    
    logger.info(f"Using script path: {script_path}")
    logger.info(f"Using src directory: {src_dir}")
    
    # Start the MCP server directly
    env = os.environ.copy()
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{src_dir}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = src_dir
    
    # Change to src directory and start the server
    os.chdir(src_dir)
    logger.info(f"Changed working directory to: {os.getcwd()}")
    
    # Port to use
    port = 10101
    
    # Check if port is already in use
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            logger.warning(f"Port {port} is already in use!")
            # Try to make a health check request
            try:
                import requests
                response = requests.get(f"http://localhost:{port}/health", timeout=2)
                if response.status_code == 200:
                    logger.info("Existing server seems to be an MCP server (health check passed)")
                else:
                    logger.error(f"Port is in use but not by MCP server (status {response.status_code})")
                    return
            except Exception as e:
                logger.error(f"Port is in use but could not connect to check health: {e}")
                return
        else:
            logger.info(f"Port {port} is available")
    except Exception as e:
        logger.error(f"Error checking port: {e}")
    
    # Start the server as a process
    logger.info("Starting MCP server process")
    cmd = ["python", "-m", "mcp_server_reddit", "--debug"]
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    
    # Give the server some time to start
    logger.info("Waiting for server to start...")
    time.sleep(5)
    
    # Try to make a health check request
    try:
        import requests
        for attempt in range(5):
            try:
                logger.info(f"Attempt {attempt+1}/5 to check server health")
                response = requests.get(f"http://localhost:{port}/health", timeout=2)
                if response.status_code == 200:
                    logger.info("Health check passed - server is running!")
                    break
            except requests.exceptions.ConnectionError:
                logger.warning("Connection error - server might not be ready yet")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error checking server health: {e}")
                time.sleep(1)
        
        # Test an actual API call
        logger.info("Testing API call to get_subreddit_new_posts")
        
        # Create RPC request
        request = {
            "jsonrpc": "2.0",
            "id": "test-call",
            "method": "call_tool",
            "params": {
                "name": "get_subreddit_new_posts",
                "arguments": {
                    "subreddit_name": "Bitcoin",
                    "limit": 5,
                    "session_id": "test-123"
                }
            }
        }
        
        # Send the request
        logger.info(f"Sending request: {json.dumps(request)}")
        response = requests.post(
            f"http://localhost:{port}",
            json=request,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        # Check the response
        logger.info(f"Received status code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Received result: {json.dumps(result)[:100]}...")
            
            # Check if there are any posts
            if "result" in result and isinstance(result["result"], list):
                logger.info(f"Successfully retrieved {len(result['result'])} posts!")
        else:
            logger.error(f"API call failed with status {response.status_code}: {response.text}")
    
    except Exception as e:
        logger.exception(f"Error during API testing: {e}")
    finally:
        # Clean up the process
        if process:
            logger.info("Terminating MCP server process")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Process didn't terminate - killing it")
                process.kill()
            logger.info(f"Process exited with code {process.returncode}")

if __name__ == "__main__":
    main() 