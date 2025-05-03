"""FastAPI Server for the Visualization Agent."""

# --- Start: Add project root to sys.path ---
import sys
import os

# Get the absolute path of the current file (server.py)
current_file_path = os.path.abspath(__file__)
# Get the path of the directory containing this file (visualization_agent/)
current_dir_path = os.path.dirname(current_file_path)
# Get the path of the parent directory (project root: A2A_with_MCP/)
project_root_path = os.path.abspath(os.path.join(current_dir_path, '..'))

# Add the project root to sys.path if it's not already there
if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path)
    print(f"Added project root to sys.path: {project_root_path}")
# --- End: Add project root to sys.path ---

import asyncio
import json
import logging
from typing import Any, Dict, Optional
import time

from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import from the local common module within visualization_agent
from visualization_agent.common.types import JSONRPCRequest
from visualization_agent.common.server import utils

from visualization_agent.agent import VisualizationAgent
from visualization_agent.task_manager import AgentTaskManager

# --- Logging Setup ---
# Moved basicConfig here for centralized setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Request limiting ---
class RateLimiter:
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.clients = {}

    async def check_limit(self, client_id: str) -> bool:
        """Check if the client has exceeded the rate limit."""
        now = time.time()
        
        # Initialize client data if it doesn't exist
        if client_id not in self.clients:
            self.clients[client_id] = []
            
        # Remove requests that are outside the current time window
        self.clients[client_id] = [t for t in self.clients[client_id] if t > now - self.time_window]
            
        # Check if the client has exceeded the maximum number of requests
        if len(self.clients[client_id]) >= self.max_requests:
            return False
            
        # Add the current request timestamp
        self.clients[client_id].append(now)
        return True

# --- Middleware for client identification and rate limiting ---
async def identify_client(request: Request) -> str:
    """Extract and return a client identifier from the request."""
    headers = request.headers
    # Try to extract client ID from headers
    client_id = headers.get("X-Client-ID") or headers.get("User-Agent", "unknown")
    return client_id

rate_limiter = RateLimiter(max_requests=20, time_window=60)  # 20 requests per minute per client

async def check_rate_limit(client_id: str = Depends(identify_client)):
    """Rate limiting middleware."""
    if not await rate_limiter.check_limit(client_id):
        logger.warning(f"Rate limit exceeded for client {client_id}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    return client_id

# --- Agent and Task Manager Initialization ---
try:
    agent = VisualizationAgent()
    task_manager = AgentTaskManager(agent)
except Exception as e:
    logger.exception("Failed to initialize Agent or Task Manager. Exiting.")
    sys.exit(1) # Exit if core components fail

# --- FastAPI App ---
app = FastAPI(
    title="Visualization Agent",
    description="A2A compliant agent for generating data visualizations.",
    version="1.0.0",
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Load agent info from .well-known/agent.json file ---
def load_agent_info() -> Dict[str, Any]:
    """Load agent info from .well-known/agent.json file."""
    well_known_path = os.path.join(current_dir_path, '.well-known', 'agent.json')
    try:
        if os.path.exists(well_known_path):
            with open(well_known_path, 'r') as f:
                agent_info = json.load(f)
                logger.info(f"Loaded agent info from {well_known_path}")
                return agent_info
        else:
            logger.warning(f"No agent.json file found at {well_known_path}, using default configuration")
    except Exception as e:
        logger.error(f"Error loading agent.json: {e}")
    
    # Default agent info if file not found or invalid
    return {
        "id": "visualization-agent-v1",
        "name": "Data Visualization Agent",
        "description": "Generates plots and charts from data based on descriptions.",
        "capabilities": {
            "requestOutputModes": ["artifact"],
            "requestInputModes": ["text"],
            "supportedContentTypes": VisualizationAgent.SUPPORTED_CONTENT_TYPES,
            "methods": ["tasks/send"],
        },
        "author": "AI Assistant",
        "version": "1.0.0",
        "url": os.getenv("VISUALIZATION_AGENT_URL", "http://localhost:8004"),
        "metadata": {
            "multiClientSupport": True  # Indicate that multiple clients are supported
        },
    }

# Load agent info at startup
AGENT_INFO = load_agent_info()

# Mount .well-known directory if it exists
well_known_dir = os.path.join(current_dir_path, '.well-known')
if os.path.exists(well_known_dir) and os.path.isdir(well_known_dir):
    app.mount("/.well-known", StaticFiles(directory=well_known_dir), name="well-known")

# --- API Endpoints ---

@app.get("/.well-known/agent.json", response_model=Dict[str, Any])
async def get_agent_info():
    """Return agent information."""
    # Reload agent info in case it was updated
    return load_agent_info()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Enhanced health check
    try:
        # Check if task manager is initialized
        if task_manager is None:
            return {"status": "error", "message": "Task manager not initialized"}
        
        # Check if agent is initialized
        if agent is None:
            return {"status": "error", "message": "Agent not initialized"}
            
        return {
            "status": "ok", 
            "uptime": "unknown",  # Could add server uptime monitoring
            "agent_status": "ready",
            "version": AGENT_INFO.get("version", "1.0.0")
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/", dependencies=[Depends(check_rate_limit)])
async def handle_rpc(request: Request, client_id: str = Depends(identify_client)):
    """Handle incoming JSON-RPC requests with rate limiting."""
    try:
        # Log which client is making the request
        logger.info(f"Received request from client: {client_id}")
        
        body = await request.json()
        logger.info(f"Received JSON-RPC request: {body}")
        rpc_request = JSONRPCRequest(**body)
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        error_resp = utils.new_parse_error(req_id=None)
        return JSONResponse(content=error_resp.model_dump(), status_code=400)

    method_name = rpc_request.method
    # Map method name like 'tasks/send' to handler 'on_tasks_send'
    handler_name = f"on_{method_name.replace('/', '_')}"
    handler = getattr(task_manager, handler_name, None)

    if handler and callable(handler):
        try:
            logger.info(f"Routing request to handler: {handler_name}")
            # Await the handler if it's async
            if asyncio.iscoroutinefunction(handler):
                response_data = await handler(rpc_request)
            else:
                # If handler is sync but needs to run async agent code,
                # it might need internal async handling or the handler itself
                # should be async.
                logger.warning(f"Handler {handler_name} is synchronous, potential blocking.")
                response_data = handler(rpc_request)

            # Check if the response is already a JSONRPCResponse or similar structure
            if hasattr(response_data, 'model_dump'):
                 final_response = response_data.model_dump()
            elif isinstance(response_data, dict): # Basic check for dicts
                 final_response = response_data
            else:
                 # Wrap unexpected response types
                 logger.error(f"Handler for {method_name} returned unexpected type: {type(response_data)}")
                 final_response = utils.new_internal_error(rpc_request.id, "Invalid handler response type").model_dump()

            # Ensure response has an ID matching the request if possible
            if isinstance(final_response, dict) and 'id' not in final_response and rpc_request.id is not None:
                final_response['id'] = rpc_request.id

            logger.info(f"Sending response for request ID {rpc_request.id} to client {client_id}: {json.dumps(final_response)[:200]}...") # Log snippet
            return JSONResponse(content=final_response)

        except ValueError as e:
            # Handle ValueError specifically (often from validation or missing parameters)
            logger.exception(f"Validation error in handler {handler_name}: {str(e)}")
            error_resp = utils.new_invalid_params_error(rpc_request.id, str(e))
            return JSONResponse(content=error_resp.model_dump(), status_code=400)
        except AttributeError as e:
            # Handle AttributeError specifically (often from accessing non-existent attributes)
            logger.exception(f"Attribute error in handler {handler_name}: {str(e)}")
            # Fix for the TaskState.ERROR issue
            if "TaskState" in str(e) and "ERROR" in str(e):
                logger.info("Detected TaskState.ERROR issue, using FAILED instead")
                # Create a generic error response as fallback
                task_id = None
                if hasattr(rpc_request, 'params') and rpc_request.params:
                    if isinstance(rpc_request.params, dict) and 'id' in rpc_request.params:
                        task_id = rpc_request.params['id']
                    elif hasattr(rpc_request.params, 'id'):
                        task_id = rpc_request.params.id
                        
                # If we have the task_id, try to update its status directly
                if task_id and task_id in task_manager.tasks:
                    task_manager.tasks[task_id].status = TaskStatus(
                        state=TaskState.FAILED,
                        message=Message(
                            role="assistant", 
                            parts=[TextPart(text=f"Task processing failed: {str(e)}")]
                        )
                    )
                    
                # Return an error response to the client
                error_resp = utils.new_internal_error(rpc_request.id, f"Task processing failed: {str(e)}")
                return JSONResponse(content=error_resp.model_dump(), status_code=500)
            else:
                # For other attribute errors
                error_resp = utils.new_internal_error(rpc_request.id, str(e))
                return JSONResponse(content=error_resp.model_dump(), status_code=500)
        except Exception as e:
            logger.exception(f"Error executing handler {handler_name}")
            error_resp = utils.new_internal_error(rpc_request.id, str(e))
            return JSONResponse(content=error_resp.model_dump(), status_code=500)
    else:
        logger.warning(f"Method not found or handler not callable: {method_name} (Expected handler: {handler_name})")
        error_resp = utils.new_method_not_found_error(rpc_request.id)
        return JSONResponse(content=error_resp.model_dump(), status_code=404)

# --- Uvicorn Runner (Optional - can be run directly) ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8004))
    logger.info(f"Starting Visualization Agent server on port {port}")
    # Use reload=True for development, disable for production
    uvicorn.run("visualization_agent.server:app", host="0.0.0.0", port=port, reload=True) 