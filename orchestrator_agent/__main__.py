import uvicorn
import os
import sys
import logging

# Configure logging EARLY
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("__main__")
logger.info("--- Orchestrator Agent __main__ starting ---")

# Determine base and parent directory relative to this __main__.py file
# base_dir = os.path.dirname(os.path.abspath(__file__))
# workspace_root = os.path.dirname(base_dir)
# python_dir = os.path.join(workspace_root, "python") # This path seems incorrect

# --- PYTHONPATH Setup --- 
# REMOVED: Dockerfile handles PYTHONPATH via ENV
# logger.info(f"Attempting to add {python_dir} to sys.path")
# if python_dir not in sys.path:
#     sys.path.insert(0, python_dir)
#     logger.info(f"Added python directory ({python_dir}) to sys.path") 

logger.info(f"Current sys.path BEFORE import: {sys.path}") # Log path as seen by this script

try:
    # Use relative import to get the app object from server.py
    logger.info("Importing app from .server")
    from .server import app, host, port
    logger.info("Import successful")
except ImportError as e:
    logger.exception("Failed to import from .server. Check PYTHONPATH set in Dockerfile and file structure.")
    sys.exit(1) # Exit if core import fails


if __name__ == "__main__":
    logger.info(f"Starting server on {host}:{port}")
    try:
        # Run the server using the app object imported from server.py
        uvicorn.run(app, host=host, port=port)
    except Exception as e:
        logger.exception("Uvicorn server failed to run!")
    finally:
        logger.info("--- Orchestrator Agent __main__ finished ---") 