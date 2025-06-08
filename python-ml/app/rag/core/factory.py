"""
Factory for creating RAG pipeline instances.
"""

from typing import Dict, Optional, Union
from pathlib import Path

from .config import RAGConfig
from .pipeline import RAGPipeline

class RAGFactory:
    """Factory for creating RAG pipeline instances with different configurations."""
    
    @staticmethod
    def create_pipeline(
        config: Optional[Union[RAGConfig, Dict, str]] = None,
        **kwargs
    ) -> RAGPipeline:
        """
        Create a RAG pipeline instance.
        
        Args:
            config: Configuration for the pipeline. Can be:
                   - RAGConfig instance
                   - Dictionary of configuration values
                   - Path to JSON configuration file
                   - None (use defaults)
            **kwargs: Override specific configuration values
            
        Returns:
            Configured RAGPipeline instance
        """
        if config is None:
            # Use default configuration
            pipeline_config = RAGConfig()
        elif isinstance(config, RAGConfig):
            # Use provided RAGConfig instance
            pipeline_config = config
        elif isinstance(config, dict):
            # Create from dictionary
            pipeline_config = RAGConfig.from_dict(config)
        elif isinstance(config, (str, Path)):
            # Load from JSON file
            import json
            with open(config) as f:
                config_dict = json.load(f)
            pipeline_config = RAGConfig.from_dict(config_dict)
        else:
            raise ValueError(f"Unsupported config type: {type(config)}")
        
        # Override with any provided kwargs
        for key, value in kwargs.items():
            if hasattr(pipeline_config, key):
                setattr(pipeline_config, key, value)
            else:
                raise ValueError(f"Unknown configuration parameter: {key}")
        
        return RAGPipeline(pipeline_config)
    
    @staticmethod
    def create_default_pipeline() -> RAGPipeline:
        """Create a pipeline with default configuration."""
        return RAGFactory.create_pipeline()
    
    @staticmethod
    def create_minimal_pipeline() -> RAGPipeline:
        """Create a pipeline with minimal configuration for lightweight usage."""
        return RAGFactory.create_pipeline(
            llm_model="gpt-3.5-turbo",  # Use smaller model
            chunk_size=250,  # Smaller chunks
            chunk_overlap=25,
            max_documents_per_query=5,
            enable_detailed_logging=False,
            expand_synonyms=False  # Disable expensive operations
        )
    
    @staticmethod
    def create_comprehensive_pipeline() -> RAGPipeline:
        """Create a pipeline with comprehensive configuration for best results."""
        return RAGFactory.create_pipeline(
            llm_model="gpt-4",  # Use most capable model
            chunk_size=1000,  # Larger chunks for more context
            chunk_overlap=100,
            max_documents_per_query=20,
            enable_detailed_logging=True,
            expand_synonyms=True,
            max_synonyms=5,
            temperature=0.5  # More focused responses
        )
    
    @staticmethod
    def create_fast_pipeline() -> RAGPipeline:
        """Create a pipeline optimized for speed."""
        return RAGFactory.create_pipeline(
            llm_model="gpt-3.5-turbo",
            chunk_size=500,
            chunk_overlap=0,  # No overlap for faster processing
            max_documents_per_query=3,
            enable_detailed_logging=False,
            expand_synonyms=False,
            embedding_batch_size=64  # Larger batches for faster processing
        )
    
    @staticmethod
    def create_accurate_pipeline() -> RAGPipeline:
        """Create a pipeline optimized for accuracy."""
        return RAGFactory.create_pipeline(
            llm_model="gpt-4",
            chunk_size=750,
            chunk_overlap=150,  # More overlap for better context
            max_documents_per_query=15,
            enable_detailed_logging=True,
            expand_synonyms=True,
            max_synonyms=7,
            temperature=0.3,  # Lower temperature for more focused responses
            similarity_threshold=0.8  # Higher threshold for better matches
        ) 