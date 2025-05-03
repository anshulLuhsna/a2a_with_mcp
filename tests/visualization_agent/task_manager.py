"""Visualization Agent Task Manager."""

import json
import logging
import traceback
from typing import AsyncIterable, Any, Dict

from pydantic import BaseModel, Field

# Assuming agent and common types are available
# Adjust imports based on final project structure
import sys
import os
import asyncio # Import needed for lock
from typing import Any # Import needed for fallback definition

PARENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Import from the local common module within visualization_agent
from visualization_agent.common.server.task_manager import InMemoryTaskManager
from visualization_agent.common.server import utils
from visualization_agent.common.types import (
    Artifact,
    FileContent,
    FilePart,
    JSONRPCResponse,
    JSONRPCRequest,
    SendTaskRequest,
    SendTaskResponse,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
    Task,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TextPart,
    Message
)

from visualization_agent.agent import VisualizationAgent, PlotData # Import agent

logger = logging.getLogger(__name__)
# BasicConfig removed, assuming setup in server.py or main entry point
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- Input Validation Model ---
class PlotRequestInput(BaseModel):
    plot_description: str = Field(..., description="Natural language description of the plot needed.")
    data_json: str = Field(..., description="Data for the plot, formatted as a JSON string.")


class AgentTaskManager(InMemoryTaskManager):
    """Visualization Agent Task Manager."""

    def __init__(self, agent: VisualizationAgent):
        super().__init__()
        self.agent = agent

    async def _stream_generator(
        self, request: SendTaskRequest
    ) -> AsyncIterable[SendTaskResponse]:
        raise NotImplementedError("Streaming not supported by CrewAI agent")

    async def on_send_task(
        self, request: SendTaskRequest | JSONRPCRequest
    ) -> SendTaskResponse | AsyncIterable[SendTaskResponse]:
        # Handle params as dict or object
        params = request.params
        accepted_modes = None
        
        # Handle both dict and object cases for params
        if isinstance(params, dict):
            accepted_modes = params.get("acceptedOutputModes")
        elif hasattr(params, "acceptedOutputModes"):
            accepted_modes = params.acceptedOutputModes
        
        if accepted_modes is not None and not utils.are_modalities_compatible(
            accepted_modes,
            VisualizationAgent.SUPPORTED_CONTENT_TYPES,
        ):
            logger.warning(
                "Unsupported output mode. Received %s, Support %s",
                accepted_modes,
                VisualizationAgent.SUPPORTED_CONTENT_TYPES,
            )
            return utils.new_incompatible_types_error(request.id)

        # Extract task_id for logging
        task_id = params.get("id") if isinstance(params, dict) else params.id
        logger.info(f"Processing task: {task_id}")
        
        await self.upsert_task(params)
        
        # Normal invocation
        return await self._invoke(request)

    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
        # Streaming not supported by underlying agent
        return utils.new_method_not_found_error(request.id)

    async def _invoke(self, request: SendTaskRequest | JSONRPCRequest) -> SendTaskResponse:
        # Handle params as dict or object
        params = request.params
        task_id = None
        session_id = None
        message = None
        
        # Handle both dict and object cases for params
        if isinstance(params, dict):
            task_id = params.get("id")
            session_id = params.get("sessionId")
            message = params.get("message")
        else:
            task_id = params.id
            session_id = params.sessionId
            message = params.message
            
        logger.info(f"Invoking task manager for task: {task_id} with session: {session_id}")

        # Initialize plot_id and error_message variables
        plot_id = None
        error_message = None

        try:
            # Extract user input (plot description and data)
            user_input = self._extract_text_from_message(message)
                
            if not user_input:
                logger.error(f"No text input found in message for task {task_id}")
                error_message = "No text input found in message"
                raise ValueError(error_message)
                
            # Parse the user input as JSON or as direct text
            try:
                # Check if input is direct text first (from UI) or JSON (from Orchestrator)
                if user_input.strip().startswith('{'):
                    # Try to parse as JSON
                    request_data = json.loads(user_input)
                    
                    plot_description = None
                    data_json = None
                    
                    # Check if this is coming from the orchestrator with specific format
                    if "plot_description" in request_data and "data_json" in request_data:
                        plot_description = request_data.get("plot_description")
                        # The data_json might be a string or already parsed JSON
                        data_json_value = request_data.get("data_json")
                        if isinstance(data_json_value, str):
                            data_json = data_json_value
                        else:
                            data_json = json.dumps(data_json_value)
                    # Or if it matches the expected parameters directly
                    elif "data_type" in request_data and "parameters" in request_data:
                        params = request_data.get("parameters", {})
                        data_type = request_data.get("data_type", "bar_chart")
                        
                        # Extract params for visualization
                        x_axis_data = params.get("x_axis_data", [])
                        y_axis_data = params.get("y_axis_data", [])
                        x_axis_label = params.get("x_axis_label", "X-Axis")
                        y_axis_label = params.get("y_axis_label", "Y-Axis")
                        title = params.get("title", "Visualization")
                        
                        # Format plot description
                        plot_description = f"Generate a {data_type} titled '{title}' with {x_axis_label} and {y_axis_label}"
                        
                        # Create data json
                        data_json = json.dumps({
                            "labels": x_axis_data,
                            "values": y_axis_data,
                            "xlabel": x_axis_label,
                            "ylabel": y_axis_label,
                            "title": title
                        })
                else:
                    # Handle direct text input from UI
                    # Parse the free-form text to extract visualization requirements
                    logger.info(f"Processing direct text input: {user_input[:100]}...")
                    
                    # Very simple parsing logic for demonstration
                    lines = user_input.strip().split('\n')
                    plot_description = lines[0] if lines else "Generate a visualization"
                    
                    # Extract chart type (default to bar chart)
                    chart_type = "bar_chart"
                    if "bar graph" in user_input.lower() or "bar chart" in user_input.lower():
                        chart_type = "bar_chart"
                    elif "line graph" in user_input.lower() or "line chart" in user_input.lower():
                        chart_type = "line_chart"
                    elif "pie chart" in user_input.lower():
                        chart_type = "pie_chart"
                    
                    # Extract labels and values
                    labels = []
                    values = []
                    
                    # Simple text parsing - look for patterns that might indicate data
                    # This is a very basic implementation - in production you'd want more robust parsing
                    for line in lines:
                        if ":" in line and any(c.isdigit() for c in line):
                            parts = line.split(":", 1)
                            if len(parts) == 2:
                                label = parts[0].strip()
                                try:
                                    value = float(parts[1].strip())
                                    labels.append(label)
                                    values.append(value)
                                except ValueError:
                                    pass
                    
                    # If no values were extracted, use some defaults
                    if not labels or not values:
                        labels = ["Category A", "Category B", "Category C"]
                        values = [100, 200, 300]
                    
                    # Extract title if mentioned
                    title = "Visualization"
                    for line in lines:
                        if "title" in line.lower() and ":" in line:
                            title = line.split(":", 1)[1].strip().strip('"').strip("'")
                            break
                    
                    # Extract axis labels if mentioned
                    x_axis_label = "X-Axis"
                    y_axis_label = "Y-Axis"
                    
                    if "x-axis" in user_input.lower() or "x axis" in user_input.lower():
                        for line in lines:
                            if ("x-axis" in line.lower() or "x axis" in line.lower()) and ":" in line:
                                x_axis_label = line.split(":", 1)[1].strip().strip('"').strip("'")
                                break
                    
                    if "y-axis" in user_input.lower() or "y axis" in user_input.lower():
                        for line in lines:
                            if ("y-axis" in line.lower() or "y axis" in line.lower()) and ":" in line:
                                y_axis_label = line.split(":", 1)[1].strip().strip('"').strip("'")
                                break
                    
                    # Create data json
                    data_json = json.dumps({
                        "labels": labels,
                        "values": values,
                        "xlabel": x_axis_label,
                        "ylabel": y_axis_label,
                        "title": title,
                        "x_axis_data": labels,
                        "y_axis_data": values,
                        "x_axis_label": x_axis_label,
                        "y_axis_label": y_axis_label
                    })
                    
                    # Update plot_description to be more specific
                    plot_description = f"Generate a {chart_type} showing {y_axis_label} for different {x_axis_label}"
                    
                if not plot_description or not data_json:
                    logger.error(f"Missing required parameters for task {task_id}")
                    error_message = "Missing required parameters: plot_description and data_json"
                    raise ValueError(error_message)
                    
                logger.info(f"Parsed input for task {task_id}: desc=\"{plot_description[:50]}...\", data=\"{data_json[:50]}...\"")
                
                # Update task status to working
                async with self.lock:
                    task = self.tasks.get(task_id)
                    if task:
                        task.status = TaskStatus(state=TaskState.WORKING)
                        logger.info(f"Updating task {task_id} status to WORKING")
                
                # Invoke the agent with the parsed parameters
                plot_id = self.agent.invoke(
                    plot_description=plot_description,
                    data_json=data_json,
                    session_id=session_id
                )
                
                logger.info(f"Agent invoke completed for task {task_id}. Plot ID: {plot_id}")
                
                # Directly extract the plot ID if it's returned as a string
                if isinstance(plot_id, str):
                    logger.info(f"Extracted plot ID directly: {plot_id}")
                else:
                    logger.error(f"Unexpected plot_id type: {type(plot_id)}")
                    error_message = f"Unexpected plot_id type: {type(plot_id)}"
                    raise ValueError(error_message)
                
                # Get plot data from the agent
                plot_data = self.agent.get_plot_data(session_id, plot_id)
                if not plot_data:
                    logger.error(f"Failed to get plot data for ID {plot_id}")
                    error_message = f"Failed to get plot data for ID {plot_id}"
                    raise ValueError(error_message)
                
                # Create file part with the image data
                file_part = FilePart(
                    file=FileContent(
                        bytes=plot_data.bytes,
                        mimeType=plot_data.mime_type,
                        name=plot_data.name
                    )
                )
                
                # Create artifact with the file part
                artifact = Artifact(
                    name=f"plot_{plot_id}.png",
                    description=f"Visualization: {plot_description[:50]}...",
                    parts=[file_part]
                )
                
                # Update the task with the artifact
                async with self.lock:
                    task = self.tasks[task_id]
                    task.artifacts = [artifact]
                    task.status = TaskStatus(state=TaskState.COMPLETED)
                
                logger.info(f"Task {task_id} completed successfully with plot artifact.")
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON input: {e}")
                error_message = f"Invalid JSON input: {e}"
                raise ValueError(error_message)
                
        except Exception as e:
            logger.error(f"Error invoking agent: {e}")
            logger.error(traceback.format_exc())
            error_message = f"Error processing visualization request: {str(e)}"
            
            # Update task status to error
            async with self.lock:
                task = self.tasks.get(task_id)
                if task:
                    task.status = TaskStatus(
                        state=TaskState.FAILED,  # Changed from ERROR to FAILED
                        message=Message(role="assistant", parts=[TextPart(text=error_message)])
                    )
            
            # Return error response
            return SendTaskResponse(
                id=request.id,
                error={"code": -32603, "message": error_message}
            )
        
        # Update final status
        logger.info(f"Updating final status for task {task_id} to {TaskState.COMPLETED}")
        
        # Return the completed task
        return SendTaskResponse(id=request.id, result=self.tasks[task_id])

    def _extract_text_from_message(self, message) -> str:
        """Extract text content from message in different formats."""
        if not message:
            return ""
            
        # Handle Dict format
        if isinstance(message, dict):
            if "parts" in message:
                for part in message["parts"]:
                    if isinstance(part, dict) and "text" in part:
                        return part["text"]
                    elif isinstance(part, dict) and "type" in part and part["type"] == "text" and "text" in part:
                        return part["text"]
            # Direct message text (for simple UI clients)
            elif "text" in message:
                return message["text"]
        # Handle Object format
        elif hasattr(message, "parts") and message.parts:
            for part in message.parts:
                if hasattr(part, "text") and part.text:
                    return part.text
                elif hasattr(part, "type") and part.type == "text" and hasattr(part, "text"):
                    return part.text
        # Direct string input
        elif isinstance(message, str):
            return message
                    
        return ""

    # Ensure _update_store exists or use base implementation
    async def _update_store(
      self, task_id: str, status: TaskStatus, artifacts: list[Artifact] | None
    ) -> Task:
        async with self.lock:
            try:
                # Assume self.tasks is the dict holding Task objects
                task = self.tasks[task_id]
            except KeyError as exc:
                logger.error(f"Task {task_id} not found for updating the task")
                raise ValueError(f"Task {task_id} not found") from exc

            task.status = status

            # Append message to history if message tracking exists
            if status.message is not None and hasattr(self, 'task_messages') and task_id in self.task_messages:
                 self.task_messages[task_id].append(status.message)
                 task.history = self.task_messages[task_id] # Assuming history is tracked this way

            if artifacts is not None:
                if task.artifacts is None:
                    task.artifacts = []
                task.artifacts.extend(artifacts)

            # Update the task in the main dictionary
            self.tasks[task_id] = task
            return task 

    # Add an alias method to handle the tasks/send JSON-RPC method
    async def on_tasks_send(
        self, request: JSONRPCRequest
    ) -> SendTaskResponse | AsyncIterable[SendTaskResponse]:
        """Alias for on_send_task to handle method name mismatch."""
        logger.info(f"Received request via tasks/send, delegating to on_send_task")
        return await self.on_send_task(request) 

    async def upsert_task(self, params):
        """
        Create or update a task with the given params.
        Handles both dictionary and TaskSendParams object formats.
        """
        # Create a Task object that will be returned
        task_id = None
        session_id = None
        message = None
        
        # Handle both dict and object cases for params
        if isinstance(params, dict):
            task_id = params.get("id")
            session_id = params.get("sessionId")
            message = params.get("message")
        else:
            task_id = params.id
            session_id = params.sessionId
            message = params.message
            
        if not task_id:
            raise ValueError("Task ID is required")
            
        async with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = TaskStatus(state=TaskState.WORKING)
            else:
                self.tasks[task_id] = Task(
                    id=task_id,
                    status=TaskStatus(state=TaskState.WORKING),
                    sessionId=session_id,
                )
                # Initialize task_messages if necessary
                if not hasattr(self, 'task_messages'):
                    self.task_messages = {}
                self.task_messages[task_id] = [message] if message else []
        
        return self.tasks[task_id] 