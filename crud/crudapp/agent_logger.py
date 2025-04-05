# crudapp/agent_logger.py
import logging
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent # Adjust if your structure differs

LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True) # Create logs directory if it doesn't exist

AGENT_LOG_FILE = LOG_DIR / 'agent.log'

def setup_agent_logger():
    """Sets up the logger for agent actions."""
    logger = logging.getLogger('agent_logger')
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers if called multiple times
    if not logger.handlers:
        # Create a file handler
        handler = logging.FileHandler(AGENT_LOG_FILE)
        handler.setLevel(logging.INFO)

        # Create a logging format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        # Add the handlers to the logger
        logger.addHandler(handler)

    return logger

# Initialize the logger when this module is imported
agent_logger = setup_agent_logger()

# Example usage (will be used in agent.py and views.py)
# from .agent_logger import agent_logger
# agent_logger.info("This is an info message.")
# agent_logger.warning("This is a warning message.")
# agent_logger.error("This is an error message.")