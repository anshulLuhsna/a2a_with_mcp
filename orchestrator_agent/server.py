import json
import logging
import os
import sys
import uuid
from typing import Any, Dict, List, Optional, AsyncGenerator

# Remove external path dependency
# sys.path.append('/home/anshul/Desktop/A2A/A2A/samples/python')

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from mcp.server.fastmcp import FastMCP

# Use local imports instead of external path
from common.server import A2AServer
from common.types import (
    AgentCard, 
    AgentCapabilities, 
    AgentSkill
)
# Remove this import and use the one from task_manager
# from common.utils.push_notification_auth import PushNotificationSenderAuth

# Use relative imports for modules within the same package
from .agent import process_request
from .task_manager import OrchestratorTaskManager, PushNotificationSenderAuth
from .mcp_server import mcp  # Import mcp from mcp_server.py instead of agent.py

# Configure logging
# Moved basicConfig here to ensure it's set before any logging happens
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("orchestrator.server") # More specific logger name

logger.info("--- Orchestrator Server module loading --- ")

try:
    from .mcp_server import mcp
    logger.info("Imported mcp from .mcp_server successful")
except ImportError as e:
    logger.exception("Failed to import mcp from .mcp_server")
    mcp = None # Set to None if import fails

# Define agent capabilities and skills
capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
skills = [
    AgentSkill(
        id="task_decomposition",
        name="Task Decomposition",
        description="Ability to break down complex tasks into manageable subtasks"
    ),
    AgentSkill(
        id="agent_delegation",
        name="Agent Delegation",
        description="Ability to assign tasks to appropriate specialized agents"
    ),
    AgentSkill(
        id="workflow_management",
        name="Workflow Management",
        description="Ability to coordinate and track progress across multiple agents"
    ),
    AgentSkill(
        id="result_integration",
        name="Result Integration",
        description="Ability to compile and integrate results from multiple agents"
    )
]

# Create FastAPI app
logger.info("Creating main FastAPI app instance")
app = FastAPI(title="Orchestrator Agent", description="A2A-compliant Orchestrator Agent")

# Add CORS middleware
logger.info("Adding CORS middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up push notification sender auth
logger.info("Setting up PushNotificationSenderAuth")
notification_sender_auth = PushNotificationSenderAuth()
notification_sender_auth.generate_jwk()

def create_server(host="localhost", port=8000):
    logger.info(f"--- create_server called with host={host}, port={port} ---")
    agent_card = AgentCard(
        name="Orchestrator Agent",
        description="Agent that breaks down user tasks and delegates them to specialized agents",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        capabilities=capabilities,
        skills=skills,
        defaultInputModes=["text", "text/plain"],
        defaultOutputModes=["text", "text/plain"],
    )
    logger.info("AgentCard created")
    task_manager = OrchestratorTaskManager(notification_sender_auth)
    logger.info("OrchestratorTaskManager created")
    server = A2AServer(
        agent_card=agent_card,
        task_manager=task_manager,
        host=host,
        port=port,
    )
    logger.info("A2AServer created")
    server.app.add_route(
        "/.well-known/jwks.json",
        notification_sender_auth.handle_jwks_endpoint,
        methods=["GET"]
    )
    logger.info("Added JWKs endpoint to A2AServer app")
    logger.info(f"--- create_server finished ---")
    return server

# Get port from environment variable or use default
port = int(os.environ.get("PORT", 8000))
host = os.environ.get("HOST", "0.0.0.0")

logger.info(f"Creating A2AServer instance for {host}:{port}")
server = create_server(host, port)

if mcp:
    logger.info(f"Attempting to mount MCP server (type: {type(mcp)}) at /mcp")
    try:
        mcp_app = mcp.sse_app() # Get the app to mount
        app.mount("/mcp", mcp_app)
        logger.info("Successfully mounted MCP server at /mcp")
    except Exception as e:
        logger.exception("!!! FAILED to mount MCP server !!!")
else:
    logger.warning("MCP server instance not available, skipping mount.")

logger.info("Attempting to mount A2A server at /")
try:
    app.mount("/", server.app)
    logger.info("Successfully mounted A2A server at /")
except Exception as e:
    logger.exception("!!! FAILED to mount A2A server !!!")

# Log all registered routes AFTER mounting
logger.info("--- Registered Routes START ---")
for route in app.routes:
    # Check if it's a Mount object
    if hasattr(route, 'path') and hasattr(route, 'name') and hasattr(route, 'app'):
        logger.info(f"Mount Path: {route.path}, Name: {route.name}, App Type: {type(route.app)}")
        # Log sub-routes within the mounted app if possible
        if hasattr(route.app, 'routes'):
             for sub_route in route.app.routes:
                 logger.info(f"  -> Sub-Route: Path={getattr(sub_route, 'path', '?')}, Name={getattr(sub_route, 'name', '?')}, Methods={getattr(sub_route, 'methods', '?')}")
    # Check if it's a standard APIRoute
    elif hasattr(route, 'path') and hasattr(route, 'methods'):
        logger.info(f"Route: Path={route.path}, Methods={route.methods}, Name={getattr(route, 'name', '?')}")
    else:
        logger.info(f"Route: {route} (Type: {type(route)}) ")
logger.info("--- Registered Routes END ---")

@app.get("/.well-known/agent.json")
async def agent_manifest():
    logger.info("GET /.well-known/agent.json called")
    try:
        with open(os.path.join(os.path.dirname(__file__), ".well-known/agent.json"), "r") as f:
            return Response(content=f.read(), media_type="application/json")
    except FileNotFoundError:
        logger.error("Agent manifest file not found!")
        raise HTTPException(status_code=404, detail="Agent manifest not found")

logger.info("--- Orchestrator Server module loaded successfully ---")

# Removed the if __name__ == "__main__" block as startup is now handled by __main__.py
# logger.info(f"Starting server on {host}:{port}")
# 
# # Run the server
# uvicorn.run(app, host=host, port=port) 