import os
import openai
from app.utils.logger import logger

def init_openai():
    """Initialize OpenAI client"""
    try:
        if os.getenv('OPENAI_API_KEY'):
            logger.info('OPENAI_API_KEY found in environment')
            openai.api_key = os.getenv('OPENAI_API_KEY')  # Set the API key directly
        else:
            logger.error('OPENAI_API_KEY not found in environment')
            raise ValueError('OPENAI_API_KEY not found in environment')
    except Exception as e:
        logger.error(f'Error initializing OpenAI client: {str(e)}')
        raise

def get_openai_client():
    """Get or initialize OpenAI client with proper error handling"""
    if not openai.api_key:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        openai.api_key = api_key
    return openai 