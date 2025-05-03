"""Crew AI based sample for A2A protocol.

Handles the agents and also presents the tools required.
"""

import asyncio
import contextlib
from contextlib import AsyncExitStack, ExitStack
import logging
import os
import re
import sys
import threading
from typing import Any, AsyncIterable, Dict, List, Optional, Sequence

# Explicitly import from the installed package by using the full path
# to avoid confusing with the local directory
import sys
import importlib.util

# Check if crewai is installed in the system
if importlib.util.find_spec("crewai") is not None:
    # Import from the system crewai package
    from crewai.agent import Agent as CrewAIAgent
    from crewai.crew import Crew as CrewAICrew
    from crewai.task import Task as CrewAITask
    # Updated import - LLM is now in the root module
    from crewai import LLM as CrewAILLM
    from crewai.process import Process as CrewAIProcess
    # Import the tool decorator
    from crewai.tools import tool
else:
    print("Error: crewai package not found. Please install it with 'pip install crewai'")
    sys.exit(1)

from dotenv import load_dotenv
from google import generativeai as genai
import json
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession
from mcp.types import TextContent
from pydantic import BaseModel
import uuid
import subprocess
import time
import requests
import queue
import socket

# Change to explicitly import from the installed crewai package
import crewai.agent
import crewai.crew
import crewai.task
# Use these as: crewai.agent.Agent, crewai.crew.Crew, etc.

logger = logging.getLogger(__name__)

class SentimentAnalysisResult(BaseModel):
  """Represents sentiment analysis results.

  Attributes:
    overall_sentiment: Overall sentiment score (-1 to 1 scale).
    positive_count: Number of positive posts/comments.
    negative_count: Number of negative posts/comments.
    neutral_count: Number of neutral posts/comments.
    summary: Text summary of the sentiment analysis.
    topics: Key topics discussed in the data.
  """
  overall_sentiment: float
  positive_count: int
  negative_count: int
  neutral_count: int
  summary: str
  topics: List[str]

def get_api_key() -> str:
  """Helper method to handle API Key."""
  load_dotenv()
  return os.getenv("GOOGLE_API_KEY")

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
    from .mcp_session import SimpleMCPSession
    
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
    if session_id is None or session_id.strip() == "":
        session_id = str(uuid.uuid4())
        logger.info(f"Generated new session ID: {session_id}")
    else:
        logger.info(f"Using provided session ID: {session_id}")
    
    try:
        # Use the SimpleMCPSession to communicate with the server
        with SimpleMCPSession() as mcp_session:
            logger.info(f"MCP Session initialized successfully")
            
            # Call the get_subreddit_new_posts tool
            tool_name = "get_subreddit_new_posts"
            logger.info(f"Calling MCP tool '{tool_name}' for r/{subreddit} with limit={limit} and session_id={session_id}")
            
            result = mcp_session.call(
                tool_name,
                {
                    "subreddit_name": subreddit,
                    "limit": limit,
                    "session_id": session_id
                }
            )
            
            logger.info(f"MCP tool call completed")
            return result
        
    except Exception as e:
        error_msg = f"Failed to fetch data from r/{subreddit}: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})

# Reintroduce the function-based tool
@tool("RedditDataTool")
def fetch_reddit_data_tool(subreddit: str, session_id: str, limit: int = 15) -> str:
  """Fetch recent posts from a specified subreddit using MCP.

  Args:
    subreddit: The name of the subreddit to fetch posts from (e.g., 'Bitcoin', 'ethereum').
    session_id: Session identifier (for tracking purposes). This argument is REQUIRED.
    limit: Maximum number of posts to fetch. Defaults to 15 if not specified by the agent.

  Returns:
    JSON string containing post data or an error message in JSON format: {"error": "description"}.
  """
  logger.info(f"fetch_reddit_data_tool invoked with subreddit={subreddit}, limit={limit}, session_id={session_id}")
  
  # Call the direct implementation which now handles session_id correctly
  return get_reddit_data(subreddit, limit, session_id)

class SentimentAnalysisAgent:
  """Agent that analyzes Bitcoin sentiment based on Reddit data."""

  def __init__(self):
    self.model = CrewAILLM(model="gemini/gemini-2.0-flash", api_key=get_api_key())
    
    # --- Define Templates for dynamic roles/goals/tasks ---
    self.agent_role_template = "{crypto_name} Sentiment Analyst"
    self.agent_goal_template = (
        "Analyze Reddit data from r/{subreddit} to determine the current sentiment around {crypto_name}. "
        "Provide a comprehensive analysis of how the {crypto_name} community is feeling "
        "and what key topics are being discussed."
    )
    self.agent_backstory_template = (
        "You are a financial sentiment analyst specializing in cryptocurrency markets. "
        "You're skilled at analyzing social media content from subreddits like r/{subreddit} to gauge market sentiment "
        "and identify emerging trends in the {crypto_name} ecosystem. Your analysis helps "
        "traders and investors understand the current mood of the community."
    )
    self.task_description_template = (
        "Analyze recent {crypto_name} discussions on Reddit from r/{subreddit} to determine overall sentiment. "
        "To perform this analysis, you first need to gather recent posts from r/{subreddit}. "
        "Use the RedditDataTool to fetch this data. IMPORTANT: You MUST provide the 'session_id' argument when calling the tool. "
        "The required session_id is available in the inputs provided to this task. "
        "The tool will return a JSON string list of posts. Analyze the post titles, content, and metadata "
        "to determine whether each post expresses positive, negative, or neutral sentiment about {crypto_name}. "
        "If the tool failed to retrieve data (indicated by an error message in the result), report the failure clearly. "
        "Otherwise, categorize posts by common themes or topics being discussed. "
        "Calculate an overall sentiment score and provide a summary of the current "
        "{crypto_name} community sentiment. "
        "Identify key topics of discussion and any notable trends.\\n\\n"
        "IMPORTANT: DO NOT return the raw JSON data in your response. Instead, provide a "
        "comprehensive analysis in the following format:\\n\\n"
        "# {crypto_name} Sentiment Analysis (from r/{subreddit})\\n\\n"
        "## Overall Sentiment: [Positive/Negative/Neutral]\n\n"
        "- **Sentiment Score**: [score] (on a scale from -1 to 1)\n"
        "- **Positive Posts**: [count]\n"
        "- **Negative Posts**: [count]\n"
        "- **Neutral Posts**: [count]\n"
        "- **Total Posts Analyzed**: [count]\n\n"
        "## Key Topics:\n"
        "[List of key topics relevant to {crypto_name}]\n\n"
        "## Recent Discussion Topics:\n"
        "[List of interesting post titles from r/{subreddit}]\n\n"
        "## Summary:\n"
        "[A paragraph summary of the overall sentiment and key findings for {crypto_name} based on r/{subreddit}]"
    )
    self.task_expected_output_template = (
        "A comprehensive sentiment analysis of {crypto_name}-related discussions on Reddit (from r/{subreddit}), "
        "including overall sentiment (positive, negative, or neutral), key topics, "
        "and a summary of the community's current outlook. If data fetching failed, the output should state the error encountered."
    )
    # ----------------------------------------------------------

  def agent_kickoff(self, user_prompt, session_id, crypto_name, subreddit):
    """Create and execute the CrewAI sentiment analysis workflow"""
    # --- Dynamically create Agent and Task --- 
    dynamic_role = self.agent_role_template.format(crypto_name=crypto_name)
    dynamic_goal = self.agent_goal_template.format(crypto_name=crypto_name, subreddit=subreddit)
    dynamic_backstory = self.agent_backstory_template.format(crypto_name=crypto_name, subreddit=subreddit)
    dynamic_description = self.task_description_template.format(crypto_name=crypto_name, subreddit=subreddit)
    dynamic_expected_output = self.task_expected_output_template.format(crypto_name=crypto_name, subreddit=subreddit)
    
    sentiment_analyst_agent = CrewAIAgent(
        role=dynamic_role,
        goal=dynamic_goal,
        backstory=dynamic_backstory,
        verbose=False,
        allow_delegation=False,
        tools=[fetch_reddit_data_tool], # Use the function tool
        llm=self.model,
    )

    sentiment_analysis_task = CrewAITask(
        description=dynamic_description,
        expected_output=dynamic_expected_output,
        agent=sentiment_analyst_agent,
    )

    sentiment_crew = CrewAICrew(
        agents=[sentiment_analyst_agent],
        tasks=[sentiment_analysis_task],
        process=CrewAIProcess.sequential,
        verbose=True, # Enable verbose logging to see internal planning
    )
    # -----------------------------------------

    # Use parsed values in kickoff inputs
    inputs = {
      "user_prompt": user_prompt, # Original query for context
      "session_id": session_id,
      "crypto_name": crypto_name,
      "subreddit": subreddit
    }

    print(f"Starting sentiment analysis on r/{subreddit} for {crypto_name}")

    # Use the dynamically created crew
    response = sentiment_crew.kickoff(inputs)
    
    # Access the .raw attribute for the string result
    response_text = response.raw if response and hasattr(response, 'raw') else str(response)
    
    # --- Basic Error Handling --- 
    try:
        # Attempt to parse the raw response as JSON to check for error messages
        parsed_response = json.loads(response_text)
        if isinstance(parsed_response, dict) and 'error' in parsed_response:
            logger.error(f"Detected error JSON in CrewAI response: {parsed_response['error']}")
            # Return a user-friendly error message
            return f"""# {crypto_name} Sentiment Analysis

## Error retrieving data

Unable to retrieve sentiment data: {parsed_response['error']}

Please try again later or try a different cryptocurrency/subreddit.
"""
    except json.JSONDecodeError:
        # Not JSON, which is expected for normal responses
        pass
    except Exception as e:
        logger.exception(f"Error processing CrewAI response: {e}")
    
    # If we made it here, the response is likely valid and not an error JSON
    # Let's examine the response to see if it still contains indicators of failures
    # We'll be more careful with these checks to avoid false positives
    
    # Enhanced error detection with specific context to avoid false positives
    error_patterns = [
        ("Unable to Determine", "could not collect enough data"),
        ("Failed to fetch", "connection issue"),
        ("Error fetching", "API access problem"),
        ("No posts retrieved", "empty data returned"),
        ("couldn't retrieve", "data unavailable"),
        ("couldn't access", "access denied"),
        ("couldn't fetch", "retrieval failed")
    ]
    
    # Only return the fallback if we find specific error phrases in context
    contains_error = False
    for pattern, context in error_patterns:
        if pattern.lower() in response_text.lower():
            # Check the surrounding context - only flag if it appears to be a genuine error about data retrieval and not analysis
            # For example, if the text is "couldn't retrieve enough positive posts" that's not a tool error
            error_index = response_text.lower().find(pattern.lower())
            # Get surrounding context (up to 30 chars before and after)
            start_idx = max(0, error_index - 30)
            end_idx = min(len(response_text), error_index + len(pattern) + 30)
            error_context = response_text[start_idx:end_idx].lower()
            
            # Only count as error if the context suggests it's about Reddit data retrieval and not analysis
            if ("reddit" in error_context and ("data" in error_context or "post" in error_context)) or \
               ("api" in error_context) or ("tool" in error_context) or (context in error_context):
                logger.warning(f"Detected error pattern '{pattern}' in context: '{error_context}'")
                contains_error = True
                break
    
    if contains_error:
        # Provide a more user-friendly fallback response
        fallback_response = f"""
# {crypto_name} Sentiment Analysis

## Unable to retrieve sentiment data

I'm sorry, but I couldn't retrieve the latest posts from r/{subreddit} to analyze sentiment. This could be due to:

1. The subreddit may be private, restricted, or doesn't exist
2. There might be a temporary issue with the Reddit API
3. There might be network connectivity issues

Please try again later or try a different cryptocurrency/subreddit.
"""
        logger.warning(f"Returning fallback response due to detected error patterns")
        return fallback_response
    
    logger.info(f"CrewAI kickoff completed. Raw response (first 100 chars): {response_text[:100]}")
    return response_text

  def invoke(self, query: str, session_id: str = None) -> str:
    """Process input and return sentiment analysis results."""
    logger.info(f"SentimentAnalysisAgent invoked with session_id: {session_id}")
    
    # Extract key values and provide defaults if not present
    input_dict = json.loads(query) if isinstance(query, str) and query.strip().startswith('{') else {}
    
    # Extract the original query text (could be the raw string or the 'query' field from JSON)
    user_query = input_dict.get('query', query) if isinstance(input_dict, dict) else query
    
    # Extract session_id from the input dictionary or use the one passed directly
    session_id_from_input = input_dict.get('session_id') if isinstance(input_dict, dict) else None
    if session_id_from_input:
        logger.info(f"Using session_id from input dictionary: {session_id_from_input}")
        session_id = session_id_from_input
        
    # Final session_id validation - ensure we have one
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"No session_id provided, generated new one: {session_id}")
    
    # Process the query to extract key entities (asset name and subreddit)
    query_lower = user_query.lower()
    
    # Default values
    crypto = None
    subreddit = None
    found_crypto = False
    
    # First, look for cryptocurrency names and set default values
    # Only common, high cap cryptocurrencies are supported in this demo
    if 'bitcoin' in query_lower or ' btc' in query_lower or 'btc ' in query_lower:
        crypto = 'Bitcoin'
        subreddit = 'Bitcoin'  # Default subreddit for Bitcoin
        found_crypto = True
        logger.info(f"Found crypto 'bitcoin', setting defaults: Crypto={crypto}, Subreddit={subreddit}")
    elif 'ethereum' in query_lower or ' eth' in query_lower or 'eth ' in query_lower:
        crypto = 'Ethereum'
        subreddit = 'ethereum'  # Default subreddit for Ethereum
        found_crypto = True
        logger.info(f"Found crypto 'ethereum', setting defaults: Crypto={crypto}, Subreddit={subreddit}")
    elif 'solana' in query_lower or ' sol' in query_lower or 'sol ' in query_lower:
        crypto = 'Solana'
        subreddit = 'solana'  # Default subreddit for Solana
        found_crypto = True
        logger.info(f"Found crypto 'solana', setting defaults: Crypto={crypto}, Subreddit={subreddit}")
    
    # Now, try to find an *explicit* subreddit mention to override the default
    subreddit_match = re.search(r"(?:subreddit|r/)[\\s:]*([a-zA-Z0-9_.-]+)", query_lower)
    if subreddit_match:
        parsed_subreddit = subreddit_match.group(1).strip()
        # Remove 'r/' prefix if it's still part of the parsed subreddit
        if parsed_subreddit.startswith('r/'):
            parsed_subreddit = parsed_subreddit[2:]
        subreddit = parsed_subreddit
        logger.info(f"Found explicit subreddit mention, overriding default: Subreddit='{subreddit}'")
    elif not found_crypto:
        # If no crypto keyword or explicit subreddit was found, try extracting from company field
        company = input_dict.get('company', '') if isinstance(input_dict, dict) else ''
        if company:
            company_lower = company.lower()
            if company_lower in ['btc', 'bitcoin']:
                crypto = 'Bitcoin'
                subreddit = 'Bitcoin'
                found_crypto = True
            elif company_lower in ['eth', 'ethereum']:
                crypto = 'Ethereum'
                subreddit = 'ethereum'
                found_crypto = True
            elif company_lower in ['sol', 'solana']:
                crypto = 'Solana'
                subreddit = 'solana'
                found_crypto = True
                
            if found_crypto:
                logger.info(f"Extracted crypto from company field: Crypto={crypto}, Subreddit={subreddit}")
                
        # Extract subreddit from input dict if present
        subreddit_from_input = input_dict.get('subreddit', '') if isinstance(input_dict, dict) else ''
        if subreddit_from_input:
            # Clean up the subreddit name
            if subreddit_from_input.startswith('r/'):
                subreddit_from_input = subreddit_from_input[2:]
            subreddit = subreddit_from_input
            logger.info(f"Using subreddit from input dictionary: Subreddit='{subreddit}'")
    
    # If no data could be extracted, return a helpful error
    if not crypto or not subreddit:
        error_message = "Could not determine which cryptocurrency or subreddit to analyze. Please specify a cryptocurrency (e.g., Bitcoin, Ethereum, Solana) and optionally a subreddit."
        logger.warning(error_message)
        return error_message
    
    logger.info(f"Final Parsed Values: Crypto={crypto}, Subreddit={subreddit}")
    
    try:
        # Run the CrewAI workflow
        user_prompt = user_query if not isinstance(input_dict, dict) else input_dict.get('query', user_query)
        
        logger.info(f"Invoking CrewAI with inputs: {{'user_prompt': '{user_prompt}', 'session_id': '{session_id}', 'crypto_name': '{crypto}', 'subreddit': '{subreddit}'}}")
        
        try:
            result = self.agent_kickoff(
                user_prompt, 
                session_id,
                crypto_name=crypto,
                subreddit=subreddit
            )
            
            # The agent_kickoff method now has improved error detection and provides appropriate fallback responses
            # So we don't need additional error checks here
            logger.info(f"CrewAI kickoff completed. Raw response (first 100 chars): {result[:100]}")
            return result
            
        except AttributeError as e:
            if "'NoneType' object has no attribute" in str(e) and "RedditDataTool" in str(e):
                # Handle specific case of RedditDataTool returning None
                logger.error(f"RedditDataTool returned None: {str(e)}")
                fallback_response = f"""
# {crypto} Sentiment Analysis

## Unable to retrieve sentiment data

I'm sorry, but I couldn't retrieve the latest posts from r/{subreddit} to analyze sentiment. The tool encountered an error.

Please try again later or try a different cryptocurrency/subreddit.
"""
                logger.warning(f"Returning fallback response due to RedditDataTool returning None")
                return fallback_response
            else:
                # Re-raise other AttributeError exceptions
                raise
                
    except Exception as e:
        error_message = f"Error performing sentiment analysis: {str(e)}"
        logger.exception(error_message)
        
        # Provide a more user-friendly error response
        friendly_error = f"""
# {crypto} Sentiment Analysis

## Error occurred during analysis

I encountered an error while trying to analyze sentiment for {crypto} on r/{subreddit}: {str(e)}

Please try again later.
"""
        return friendly_error

  async def stream(self, query: str) -> AsyncIterable[Dict[str, Any]]:
    """Streaming is not supported by CrewAI."""
    raise NotImplementedError("Streaming is not supported by CrewAI.")

class MCPSession:
    """Context manager for MCP server sessions"""
    
    def __init__(self, python_cmd, script_path, session_id=None):
        """Initialize an MCP session with the given parameters"""
        self.python_cmd = python_cmd
        self.script_path = script_path
        self.session_id = session_id or str(uuid.uuid4())
        self.process = None
        self.port = 10101  # Default MCP port
        self.server_ready = False
        self.max_retries = 3
        
    def __enter__(self):
        """Start the MCP server process when entering the context"""
        try:
            # Check if port is already in use
            try:
                # Try to create a socket on the port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', self.port))
                sock.close()
                
                if result == 0:  # Port is open/in use
                    # Try to make a health check request - maybe it's already our server
                    try:
                        response = requests.get(f"http://localhost:{self.port}/health", timeout=1)
                        if response.status_code == 200:
                            logger.info(f"MCP server already running on port {self.port}")
                            self.server_ready = True
                            # In this case, we don't start a new server process
                            return self
                    except requests.RequestException:
                        # If health check fails, it's probably another application
                        raise RuntimeError(f"Port {self.port} is already in use by another application")
            except socket.error:
                # Socket creation failed, unlikely but handle it
                logger.warning(f"Failed to check if port {self.port} is in use")
            
            # Get the script directory and src directory
            script_dir = os.path.dirname(os.path.abspath(self.script_path))
            src_dir = os.path.dirname(script_dir)  # Parent directory of the script dir
                
            # Create the environment with PYTHONPATH properly set up
            env = os.environ.copy()
            
            # Add the src directory to PYTHONPATH so the module can be found
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = f"{src_dir}{os.pathsep}{env['PYTHONPATH']}"
            else:
                env['PYTHONPATH'] = src_dir
                
            # Start the MCP server as a subprocess using the module approach
            cmd = [self.python_cmd, "-m", "mcp_server_reddit"]
            
            # Add enhanced logging
            logger.info(f"Starting MCP server: {' '.join(cmd)}")
            logger.info(f"With PYTHONPATH: {env.get('PYTHONPATH', 'Not set')}")
            logger.info(f"From directory: {src_dir}")
            
            # Start the process from the src directory
            self.process = subprocess.Popen(
                cmd,
                cwd=src_dir,  # Run from src directory for proper module import
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Create a queue for output processing
            output_queue = queue.Queue()
            
            # Start a thread to log server output for debugging and capture into queue
            def log_server_output():
                if self.process is None:
                    return
                    
                for line in self.process.stdout:
                    logger.debug(f"MCP server stdout: {line.strip()}")
                    output_queue.put(("stdout", line.strip()))
                for line in self.process.stderr:
                    logger.warning(f"MCP server stderr: {line.strip()}")
                    output_queue.put(("stderr", line.strip()))
            
            output_thread = threading.Thread(target=log_server_output)
            output_thread.daemon = True
            output_thread.start()
            
            # Wait for the server to become ready with improved detection
            start_time = time.time()
            max_wait_time = 45  # Increased max wait time to 45 seconds for slow systems
            
            logger.info(f"Waiting for MCP server to initialize (max {max_wait_time}s)...")
            
            # Check if the process starts correctly
            time.sleep(0.5)  # Give it a moment to start
            if self.process and self.process.poll() is not None:
                # Process exited immediately - something is wrong
                stderr_output = ""
                stdout_output = ""
                try:
                    while True:
                        try:
                            source, line = output_queue.get(block=False)
                            if source == "stderr":
                                stderr_output += line + "\n"
                            else:
                                stdout_output += line + "\n"
                        except queue.Empty:
                            break
                except Exception:
                    pass
                
                error_msg = f"MCP server process exited immediately with code {self.process.returncode}"
                if stderr_output:
                    error_msg += f"\nStderr: {stderr_output}"
                if stdout_output:
                    error_msg += f"\nStdout: {stdout_output}"
                
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            # Wait for the server to initialize by checking both log messages and connectivity
            while time.time() - start_time < max_wait_time:
                # Check if the process has crashed
                if self.process and self.process.poll() is not None:
                    raise RuntimeError(f"MCP server process exited prematurely with code {self.process.returncode}")
                
                # Try to connect to the server to see if it's running
                try:
                    test_response = requests.get(f"http://localhost:{self.port}/health", timeout=1)
                    if test_response.status_code == 200:
                        logger.info("MCP server is responding to HTTP requests")
                        self.server_ready = True
                        break
                except requests.RequestException:
                    # Server not ready yet, that's expected
                    pass
                
                # Wait before checking again
                time.sleep(0.5)
            
            # If we exited the loop without finding the server ready
            if not self.server_ready:
                # Try one more time with a longer timeout
                try:
                    logger.info("Final attempt to connect to MCP server...")
                    requests.get(f"http://localhost:{self.port}/health", timeout=5)
                    self.server_ready = True
                except requests.RequestException as e:
                    if "Connection refused" in str(e):
                        # Check if the process is still running
                        if self.process and self.process.poll() is None:
                            # Attempt to read any stderr output from the server
                            stderr_output = ""
                            try:
                                while True:
                                    try:
                                        source, line = output_queue.get(block=False)
                                        if source == "stderr":
                                            stderr_output += line + "\n"
                                    except queue.Empty:
                                        break
                            except Exception:
                                pass
                            
                            if stderr_output:
                                logger.error(f"Server stderr output: {stderr_output}")
                            
                        # Give more specific error about port binding
                        raise RuntimeError(f"MCP server failed to bind to port {self.port}. Check if another process is using this port or if the MCP server has permission issues.")
                    raise RuntimeError(f"MCP server did not become ready within {max_wait_time} seconds: {str(e)}")
            
            logger.info("MCP server started successfully")
            return self

        except Exception as e:
            logger.exception(f"Error starting MCP server: {e}")
            if self.process:
                self.process.kill()
                self.process = None
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Terminate the MCP server process when exiting the context"""
        try:
            if self.process:
                logger.info("Shutting down MCP server")
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("MCP server did not terminate gracefully, killing process")
                    self.process.kill()
                    self.process.wait()
                logger.info("MCP server shutdown complete")
        except Exception as e:
            logger.exception(f"Error cleaning up MCP server process: {e}")
    
    def call(self, tool_name, arguments, retry_count=0):
        """Call an MCP tool and return the result"""
        try:
            if not self.server_ready:
                logger.error("Attempted to call a tool but MCP server is not ready")
                return json.dumps({"tool_error": "MCP server is not ready. The server failed to start properly."})
                
            if self.process and self.process.poll() is not None:
                logger.error(f"MCP server process has exited unexpectedly with code {self.process.returncode}")
                return json.dumps({"tool_error": f"MCP server process has exited with code {self.process.returncode}"})
                
            # Build the JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "call_tool",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Make the request to the MCP server
            try:
                logger.info(f"Sending request to MCP server at http://localhost:{self.port} for tool '{tool_name}'")
                # Better request handling with more explicit headers and error management
                response = requests.post(
                    f"http://localhost:{self.port}",
                    json=request,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                # Log response status for debugging
                logger.info(f"MCP server response status: {response.status_code}")
                
                # Check for errors
                if response.status_code != 200:
                    logger.error(f"MCP server returned status code {response.status_code}: {response.text}")
                    # Retry logic for transient errors
                    if retry_count < self.max_retries and 500 <= response.status_code < 600:
                        retry_count += 1
                        wait_time = retry_count * 2  # Exponential backoff
                        logger.warning(f"Retrying request (attempt {retry_count}/{self.max_retries}) after {wait_time}s")
                        time.sleep(wait_time)  # Wait before retrying with increasing backoff
                        return self.call(tool_name, arguments, retry_count)
                    return json.dumps({"tool_error": f"MCP server returned status code {response.status_code}: {response.text[:500]}"})
                
                # Parse the response
                try:
                    result = response.json()
                    logger.info(f"Received JSON response from MCP server")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response: {response.text[:500]}")
                    return json.dumps({"tool_error": f"Invalid JSON response from MCP server: {str(e)}"})
                
                # Check for JSON-RPC errors
                if "error" in result:
                    logger.error(f"MCP server returned error: {result['error']}")
                    return json.dumps({"tool_error": f"MCP server error: {result['error'].get('message', 'Unknown error')}"})
                
                # Extract the text content from the result
                if "result" not in result:
                    logger.error("MCP response missing 'result' field")
                    return json.dumps({"tool_error": "Invalid MCP response format"})
                
                text_contents = []
                for item in result.get("result", []):
                    if item.get("type") == "text":
                        text_contents.append(item.get("text", ""))
                
                # Combine the text contents into a single result
                if text_contents:
                    # If each text content is a JSON string, parse and combine them
                    try:
                        parsed_items = []
                        for item in text_contents:
                            try:
                                parsed_items.append(json.loads(item))
                            except json.JSONDecodeError:
                                # If this item can't be parsed as JSON, include it as a raw string
                                parsed_items.append({"raw_text": item})
                        return parsed_items
                    except Exception as parse_err:
                        logger.warning(f"Error parsing text contents as JSON: {parse_err}")
                        # If parsing fails, just return the raw text
                        return json.dumps(text_contents) if len(text_contents) > 1 else text_contents[0]
                
                # Empty result
                logger.warning("MCP server returned empty result")
                return json.dumps([])
                
            except requests.ConnectionError as conn_err:
                logger.exception(f"Connection error when calling MCP tool: {conn_err}")
                logger.error(f"Connection to http://localhost:{self.port} failed. Check if the server is running.")
                
                # Retry logic for connection errors
                if retry_count < self.max_retries:
                    retry_count += 1
                    wait_time = retry_count * 2  # Exponential backoff
                    logger.warning(f"Retrying request (attempt {retry_count}/{self.max_retries}) after {wait_time}s")
                    time.sleep(wait_time)  # Wait before retrying with increasing backoff
                    return self.call(tool_name, arguments, retry_count)
                
                # Check if the server is still running
                if self.process and self.process.poll() is None:
                    # The process is running but not responding
                    logger.error("MCP server process is running but not responding to HTTP requests")
                else:
                    logger.error("MCP server process has crashed or exited")
                    
                return json.dumps({
                    "tool_error": f"Failed to connect to MCP server at http://localhost:{self.port}. The server may not be running or might be blocked by firewall settings."
                })
                
            except requests.RequestException as req_err:
                logger.exception(f"HTTP request error when calling MCP tool: {req_err}")
                # Retry logic for connection errors
                if retry_count < self.max_retries:
                    retry_count += 1
                    wait_time = retry_count * 2  # Exponential backoff
                    logger.warning(f"Retrying request (attempt {retry_count}/{self.max_retries}) after {wait_time}s")
                    time.sleep(wait_time)  # Wait before retrying with increasing backoff
                    return self.call(tool_name, arguments, retry_count)
                
                # Check if the server is still running
                if self.process and self.process.poll() is None:
                    # The process is running but not responding
                    logger.error("MCP server process is running but not responding")
                else:
                    logger.error("MCP server process has crashed or exited")
                    
                return json.dumps({"tool_error": f"Failed to communicate with MCP server: {str(req_err)}"})
                
        except Exception as e:
            logger.exception(f"Error calling MCP tool: {e}")
            return json.dumps({"tool_error": f"Error calling MCP tool: {str(e)}"})

def check_and_install_dependencies():
    """Check if required dependencies are installed and install them if needed."""
    try:
        import importlib
        
        # List of required packages
        required_packages = {
            'requests': 'requests',
            'contextlib': None,  # Built-in module
            'subprocess': None,  # Built-in module
            'time': None,  # Built-in module
            'json': None,  # Built-in module
            'uuid': None,  # Built-in module
            'os': None,  # Built-in module
            're': None,  # Built-in module
        }
        
        # Check if each package is installed
        for module_name, package_name in required_packages.items():
            try:
                importlib.import_module(module_name)
                logger.info(f"Module {module_name} is already installed.")
            except ImportError:
                if package_name:  # Only try to install if it's not a built-in module
                    logger.warning(f"Module {module_name} is not installed. Installing...")
                    import subprocess
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
                    logger.info(f"Successfully installed {package_name}.")
                else:
                    logger.error(f"Built-in module {module_name} is not available. This should not happen.")
        
        # Explicitly check for ExitStack and AsyncExitStack in contextlib
        try:
            from contextlib import ExitStack, AsyncExitStack
            logger.info("contextlib.ExitStack and AsyncExitStack are available.")
        except ImportError as e:
            logger.error(f"Failed to import ExitStack or AsyncExitStack from contextlib: {str(e)}")
            # For Python versions before 3.10, AsyncExitStack might not be available
            # Let's check just for ExitStack which we absolutely need
            try:
                from contextlib import ExitStack
                logger.info("contextlib.ExitStack is available.")
            except ImportError:
                logger.error("contextlib.ExitStack is not available. This is required for the RedditDataTool.")
                raise

        logger.info("All required dependencies are installed.")
        return True
        
    except Exception as e:
        logger.exception(f"Error checking/installing dependencies: {e}")
        return False

# Run the dependency check when the module is imported
check_and_install_dependencies()
