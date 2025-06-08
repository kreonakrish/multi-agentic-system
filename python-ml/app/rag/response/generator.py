"""
Response generation utilities for LLM-based response generation.
"""

from typing import List, Dict, Any, Optional
import json
import logging
import traceback
from openai import OpenAI, OpenAIError

logger = logging.getLogger(__name__)

class ResponseGenerator:
    """Handles LLM-based response generation."""
    
    def __init__(
        self,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 500,
        api_key: Optional[str] = None
    ):
        """
        Initialize the generator.
        
        Args:
            model: OpenAI model to use
            temperature: Temperature for response generation
            max_tokens: Maximum tokens in response
            api_key: OpenAI API key
        """
        try:
            self.model = model
            self.temperature = temperature
            self.max_tokens = max_tokens
            self.client = OpenAI(api_key=api_key) if api_key else OpenAI()
        except Exception as e:
            logger.error(f"Error initializing ResponseGenerator: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def format_context(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]]
    ) -> str:
        """
        Format retrieved documents into context string.
        
        Args:
            query: Original query
            retrieved_docs: List of retrieved documents
            
        Returns:
            Formatted context string
        """
        try:
            context = f"Query: {query}\n\nRelevant Information:\n"
            
            for i, doc in enumerate(retrieved_docs, 1):
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})
                source = metadata.get("source", "unknown")
                
                context += f"\n{i}. From {source}:\n{content}\n"
            
            return context
        except Exception as e:
            logger.error(f"Error formatting context: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def generate_prompt(
        self,
        query: str,
        context: str,
        task: str = "answer"
    ) -> List[Dict[str, str]]:
        """
        Generate prompt for the LLM.
        
        Args:
            query: Original query
            context: Formatted context
            task: Task type (answer, summarize, analyze)
            
        Returns:
            List of message dictionaries
        """
        try:
            system_prompts = {
                "answer": "You are a helpful assistant. Answer the question using only the provided context. If you cannot answer from the context, say so.",
                "summarize": "You are a helpful assistant. Summarize the key points from the provided context that are relevant to the query.",
                "analyze": "You are a helpful assistant. Analyze the information in the context to answer the query, providing specific details and examples."
            }
            
            return [
                {"role": "system", "content": system_prompts.get(task, system_prompts["answer"])},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
            ]
        except Exception as e:
            logger.error(f"Error generating prompt: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def generate_response(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        task: str = "answer"
    ) -> Dict[str, Any]:
        """
        Generate response using the LLM.
        
        Args:
            query: Original query
            retrieved_docs: List of retrieved documents
            task: Task type
            
        Returns:
            Dictionary containing response and metadata
        """
        try:
            # Format context and generate prompt
            context = self.format_context(query, retrieved_docs)
            messages = self.generate_prompt(query, context, task)
            
            try:
                # Get LLM response
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
                # Extract response text
                response_text = response.choices[0].message.content
                
                return {
                    "response": response_text,
                    "metadata": {
                        "model": self.model,
                        "temperature": self.temperature,
                        "task": task,
                        "context_docs": len(retrieved_docs),
                        "finish_reason": response.choices[0].finish_reason,
                        "success": True
                    }
                }
                
            except OpenAIError as e:
                logger.error(f"OpenAI API error: {str(e)}")
                logger.error(traceback.format_exc())
                return {
                    "response": "I apologize, but I encountered an error with the language model. Please try again later.",
                    "metadata": {
                        "error": str(e),
                        "error_type": "openai_api_error",
                        "success": False
                    }
                }
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "response": "I apologize, but I encountered an error generating the response.",
                "metadata": {
                    "error": str(e),
                    "error_type": "general_error",
                    "success": False
                }
            }
    
    def validate_response(
        self,
        response: Dict[str, Any],
        query: str,
        context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate generated response.
        
        Args:
            response: Generated response
            query: Original query
            context: Retrieved documents
            
        Returns:
            Dictionary with validation results
        """
        try:
            validation_prompt = [
                {
                    "role": "system",
                    "content": "You are a response validator. Check if the response accurately answers the query using only the provided context."
                },
                {
                    "role": "user",
                    "content": f"""
                    Query: {query}
                    
                    Context: {json.dumps(context, indent=2)}
                    
                    Response: {response['response']}
                    
                    Validate this response for:
                    1. Accuracy (uses only provided context)
                    2. Completeness (addresses all aspects of query)
                    3. Relevance (focuses on the query)
                    """
                }
            ]
            
            try:
                validation = self.client.chat.completions.create(
                    model=self.model,
                    messages=validation_prompt,
                    temperature=0.3,  # Lower temperature for validation
                    max_tokens=200
                )
                
                return {
                    "is_valid": True,
                    "validation_feedback": validation.choices[0].message.content,
                    "metadata": response["metadata"]
                }
                
            except OpenAIError as e:
                logger.error(f"OpenAI API error during validation: {str(e)}")
                logger.error(traceback.format_exc())
                return {
                    "is_valid": False,
                    "validation_feedback": f"Error during validation: OpenAI API error - {str(e)}",
                    "metadata": response["metadata"]
                }
                
        except Exception as e:
            logger.error(f"Error validating response: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "is_valid": False,
                "validation_feedback": f"Error during validation: {str(e)}",
                "metadata": response["metadata"]
            } 