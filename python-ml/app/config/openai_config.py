import os
from openai import OpenAI
from app.utils.logger import logger

def init_openai():
    """Initialize OpenAI client"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            logger.info('OPENAI_API_KEY found in environment')
            return OpenAI(api_key=api_key)
        else:
            logger.error('OPENAI_API_KEY not found in environment')
            raise ValueError('OPENAI_API_KEY not found in environment')
    except Exception as e:
        logger.error(f'Error initializing OpenAI client: {str(e)}')
        raise

def get_openai_client():
    """Get or initialize OpenAI client with proper error handling"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
    return OpenAI(api_key=api_key) 