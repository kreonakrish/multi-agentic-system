"""OpenAI utilities for the multi-agent system."""
import os
from typing import Any
import openai
from app.utils.logger import logger

def get_openai_client() -> Any:
    """Get an initialized OpenAI client.
    
    Returns:
        An initialized OpenAI client instance
    
    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OpenAI API key not found in environment variables")
        raise ValueError("OPENAI_API_KEY environment variable must be set")
    
    # Initialize the client
    openai.api_key = api_key
    
    return openai 