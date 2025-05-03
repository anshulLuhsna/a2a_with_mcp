"""Visualization Agent using CrewAI.

Generates plots based on descriptions and data, then returns an ID 
for the plot stored in cache.
"""

import base64
import io
import json
import logging
import os
import traceback
from typing import Any, AsyncIterable, Dict, Optional
from uuid import uuid4

import matplotlib.pyplot as plt
from crewai import Agent, Crew, Task, LLM # Import LLM from CrewAI
from crewai.process import Process
from crewai.tools import tool
from dotenv import load_dotenv
# Remove direct GenAI client import if only used for LLM wrapper
# from google.genai import Client as GenAIClient
from pydantic import BaseModel

# Assuming common utils are one level up
import sys
PARENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Import from the local common module within visualization_agent
from visualization_agent.common.utils.in_memory_cache import InMemoryCache

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class PlotData(BaseModel):
    """Model for plot data returned to orchestrator."""
    id: str
    name: str
    mime_type: str
    bytes: str  # Base64 encoded image data


def get_api_key() -> str:
    """Helper method to handle API Key."""
    load_dotenv()
    # Use GOOGLE_API_KEY consistently
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")
    return key


# --- Matplotlib Plotting Tool ---
@tool("PlotGenerationTool")
def generate_plot_tool(plot_description: str, data_json: str, session_id: str) -> str:
    """Generates a plot using Matplotlib based on a description and data provided as a JSON string. Stores the plot and returns its ID."""
    logger.info(f"Generating plot for session {session_id}. Description: {plot_description[:50]}...")

    if not plot_description or not data_json:
        logger.error("Plot description and data JSON cannot be empty.")
        raise ValueError("Plot description and data JSON cannot be empty.")

    cache = InMemoryCache() # Use shared or local cache instance

    try:
        # If the data_json is a string, parse it
        if isinstance(data_json, str):
            data = json.loads(data_json)
        else:
            data = data_json
            
        # --- Plotting Logic with Multiple Data Format Support ---
        labels = None
        values = None
        
        # Try different attribute names that could contain the data
        if "labels" in data and "values" in data:
            labels = data["labels"]
            values = data["values"]
        elif "x_axis_data" in data and "y_axis_data" in data:
            labels = data["x_axis_data"]
            values = data["y_axis_data"]
            
        # Get axis labels if available
        x_label = data.get("xlabel") or data.get("x_axis_label") or "X-Axis"
        y_label = data.get("ylabel") or data.get("y_axis_label") or "Y-Axis"
        title = data.get("title", plot_description[:50])
        
        # If we don't have data, return an error message
        if not labels or not values or len(labels) == 0 or len(values) == 0:
            logger.warning("Invalid or missing data. Using sample data instead.")
            # Generate a sample plot with placeholder data
            labels = ["Sample A", "Sample B", "Sample C", "Sample D", "Sample E"]
            values = [5, 7, 3, 8, 6]
            
        # Create the plot
        plt.figure(figsize=(10, 6))
        plt.bar(labels, values)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.title(title)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save the plot to a BytesIO object
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Convert to base64 for storage
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        # Generate a unique ID for the plot
        plot_id = f"plot_{uuid4().hex}"
        
        # Store in cache
        plot_data = PlotData(
            id=plot_id,
            name=f"{plot_id}.png",
            mime_type="image/png",
            bytes=img_base64
        )
        
        # Get session cache or initialize it
        if not session_id:
            session_id = f"session_{uuid4().hex}"
            logger.warning(f"No session ID provided, generated: {session_id}")
            
        # Store plot in the session cache
        session_data = cache.get(session_id)
        if session_data is None:
            # Session doesn't exist, create it
            cache.set(session_id, {plot_id: plot_data})
        else:
            # Update existing session
            if isinstance(session_data, dict):
                session_data[plot_id] = plot_data
                cache.set(session_id, session_data)
            else:
                # Handle unexpected session data type
                logger.warning(f"Unexpected session data type: {type(session_data)}. Reinitializing session.")
                cache.set(session_id, {plot_id: plot_data})
            
        # Clean up
        plt.close()
        
        logger.info(f"Successfully generated and cached plot with ID: {plot_id}")
        return plot_id
        
    except Exception as e:
        logger.error(f"Error generating plot: {str(e)}")
        logger.error(traceback.format_exc())
        plt.close()  # Ensure figure is closed even on error
        raise ValueError(f"Failed to generate plot: {str(e)}")


# --- Visualization Agent Definition ---
class VisualizationAgent:
    """Visualization Agent that creates plots and charts based on user data."""
    
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain", "image/png"]
    
    def __init__(self):
        """Initialize the agent with the appropriate LLM and tools."""
        api_key = get_api_key()
        self.model = LLM(
            model="gemini/gemini-2.0-flash", 
            api_key=api_key
        )
        
        self.data_visualization_agent = Agent(
            role="Data Visualization Specialist",
            goal="Create accurate and insightful visualizations from data",
            backstory=(
                "You are an expert in data visualization with extensive experience in translating "
                "raw data into clear, informative plots and charts. Your visualizations help people "
                "understand complex information at a glance."
            ),
            verbose=False,
            allow_delegation=False,
            tools=[generate_plot_tool],
            llm=self.model
        )
        
        self.visualization_task = Task(
            description=(
                "Receive a plot description: '{plot_description}' and data: '{data_json}'. "
                "Analyze the request and use the 'Plot Generation Tool' to create the visualization. "
                "Provide the tool with the description, the data JSON, and the session ID: '{session_id}'."
            ),
            expected_output="The ID of the generated plot",
            agent=self.data_visualization_agent
        )
        
        self.plot_crew = Crew(
            agents=[self.data_visualization_agent],
            tasks=[self.visualization_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Initialize cache for testing
        self.cache = InMemoryCache()
    
    def invoke(self, plot_description: str, data_json: str, session_id: str) -> str:
        """Kicks off CrewAI to generate the plot and returns the plot ID."""
        if not session_id:
             session_id = f"session_{uuid4().hex}" # Ensure session ID exists
             logger.warning(f"No session ID provided, generated: {session_id}")

        inputs = {
            "plot_description": plot_description,
            "data_json": data_json,
            "session_id": session_id
        }
        logger.info(f"Invoking plot crew with inputs: {str(inputs)[:200]}...")

        try:
            # CrewAI kickoff returns the result of the last task
            result = self.plot_crew.kickoff(inputs=inputs)
            logger.info(f"Plot crew finished. Result (expecting plot ID): {result}")
            
            # Extract the plot ID from the result object or string
            plot_id = None
            if hasattr(result, 'raw'):
                plot_id = result.raw
            else:
                plot_id = str(result)
                
            # Verify the plot exists in cache
            if not self.plot_exists(session_id, plot_id):
                logger.warning(f"Plot ID {plot_id} not found in cache. Generating fallback...")
                # If not found, try to generate it directly using the tool
                return generate_plot_tool(plot_description, data_json, session_id)
                
            logger.info(f"Successfully extracted and verified plot ID: {plot_id}")
            return plot_id
            
        except Exception as e:
            logger.error(f"Error invoking plot crew: {str(e)}")
            logger.error(traceback.format_exc())
            # Try to generate directly instead
            try:
                logger.info("Attempting direct plot generation as fallback...")
                return generate_plot_tool(plot_description, data_json, session_id)
            except Exception as direct_error:
                logger.error(f"Direct plot generation also failed: {str(direct_error)}")
                raise ValueError(f"Failed to generate plot: {str(e)}")
    
    async def stream(self, query: str) -> AsyncIterable[Dict[str, Any]]:
        """Streaming is not supported by this agent."""
        raise NotImplementedError("Streaming is not supported by this agent.")
    
    def plot_exists(self, session_id: str, plot_id: str) -> bool:
        """Check if a plot exists in the cache."""
        cache = InMemoryCache()
        session_data = cache.get(session_id)
        if session_data and isinstance(session_data, dict):
            return plot_id in session_data
        return False
    
    def get_plot_data(self, session_id: str, plot_id: str) -> Optional[PlotData]:
        """Return PlotData for a given plot ID. Helper method for the task manager."""
        if not session_id or not plot_id:
            logger.error("Session ID and Plot ID cannot be empty")
            return None
            
        try:
            cache = InMemoryCache()
            session_data = cache.get(session_id)
            
            if not session_data:
                logger.error(f"No session data found for session ID: {session_id}")
                return None
                
            if not isinstance(session_data, dict):
                logger.error(f"Session data is not a dictionary: {type(session_data)}")
                return None
                
            if plot_id not in session_data:
                logger.error(f"Plot ID {plot_id} not found in session {session_id}")
                logger.debug(f"Available plot IDs: {list(session_data.keys())}")
                return None
                
            plot_data = session_data[plot_id]
            if not isinstance(plot_data, PlotData):
                logger.error(f"Plot data is not a PlotData object: {type(plot_data)}")
                # Try to convert it to a PlotData object if it's a dict
                if isinstance(plot_data, dict):
                    try:
                        return PlotData(**plot_data)
                    except Exception as e:
                        logger.error(f"Failed to convert dict to PlotData: {str(e)}")
                return None
                
            return plot_data
        except Exception as e:
            logger.error(f"Error retrieving plot with ID {plot_id} for session {session_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return None 