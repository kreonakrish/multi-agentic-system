"""
Embeddings manager for handling document and query embeddings using sentence-transformers.
"""

from typing import List, Union
from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingManager:
    """Manages the generation of embeddings for documents and queries."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        """
        Initialize the embedding manager.
        
        Args:
            model_name: Name of the sentence-transformer model to use
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            Numpy array containing the embedding
        """
        return self.model.encode(text, convert_to_numpy=True)
    
    def batch_generate_embeddings(
        self, 
        texts: List[str], 
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to generate embeddings for
            batch_size: Number of texts to process at once
            
        Returns:
            Numpy array containing the embeddings
        """
        return self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True
        )
    
    def get_embedding_dim(self) -> int:
        """
        Get the dimensionality of the embeddings.
        
        Returns:
            Dimension of the embedding vectors
        """
        return self.model.get_sentence_embedding_dimension() 