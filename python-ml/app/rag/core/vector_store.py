"""
Vector store manager for handling FAISS operations.
"""

from typing import Dict, List, Optional, Any
import faiss
import numpy as np
import logging
import json
import os
from pathlib import Path
import uuid
import warnings
import platform

logger = logging.getLogger(__name__)

def _check_faiss_capabilities():
    """Check and log FAISS capabilities on the current system."""
    capabilities = []
    
    # Check CPU features
    if hasattr(faiss, 'has_avx512'):
        if faiss.has_avx512():
            capabilities.append("AVX512")
    if hasattr(faiss, 'has_avx2'):
        if faiss.has_avx2():
            capabilities.append("AVX2")
    
    # Log capabilities
    if capabilities:
        logger.info(f"[vector_store.py] FAISS running with CPU features: {', '.join(capabilities)}")
    else:
        logger.info("[vector_store.py] FAISS running with basic CPU support")
    
    # Log system info
    logger.info(f"[vector_store.py] System: {platform.system()} {platform.machine()}")
    logger.info(f"[vector_store.py] FAISS version: {faiss.__version__}")

class VectorStoreManager:
    """Manages interactions with FAISS vector store."""
    
    def __init__(
        self,
        faiss_index_path: str,
        metadata_path: str,
        similarity_metric: str = "cosine",
        nprobe: int = 10
    ):
        """
        Initialize the vector store manager.
        
        Args:
            faiss_index_path: Path to store/load FAISS index
            metadata_path: Path to store/load metadata
            similarity_metric: Similarity metric to use ('cosine' or 'l2')
            nprobe: Number of clusters to probe during search
        """
        try:
            # Check FAISS capabilities
            _check_faiss_capabilities()
            
            # Suppress FAISS warnings about CPU features
            warnings.filterwarnings('ignore', category=UserWarning, module='faiss')
            
            self.faiss_index_path = faiss_index_path
            self.metadata_path = metadata_path
            self.similarity_metric = similarity_metric
            self.nprobe = nprobe
            
            logger.info(f"[vector_store.py] Initializing vector store with settings:")
            logger.info(f"[vector_store.py] - Index path: {faiss_index_path}")
            logger.info(f"[vector_store.py] - Metadata path: {metadata_path}")
            logger.info(f"[vector_store.py] - Similarity metric: {similarity_metric}")
            logger.info(f"[vector_store.py] - nprobe: {nprobe}")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(faiss_index_path), exist_ok=True)
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
            
            # Initialize metadata storage
            self.metadata = {}
            self.load_metadata()
            
            # Initialize or load FAISS index
            self.index = None
            self.dimension = None
            
            # Try to load existing index
            if os.path.exists(self.faiss_index_path):
                try:
                    logger.info(f"[vector_store.py] Loading existing FAISS index from {self.faiss_index_path}")
                    self.index = faiss.read_index(self.faiss_index_path)
                    if hasattr(self.index, 'ntotal'):
                        logger.info(f"[vector_store.py] Loaded index with {self.index.ntotal} vectors")
                        if hasattr(self.index, 'd'):
                            self.dimension = self.index.d
                            logger.info(f"[vector_store.py] Index dimension: {self.dimension}")
                except Exception as e:
                    logger.warning(f"[vector_store.py] Could not load existing index, will create new one. Error: {str(e)}")
                    self.index = None
            
        except Exception as e:
            logger.error(f"[vector_store.py] Error initializing vector store: {str(e)}")
            raise
            
    def _initialize_index(self, dimension: int):
        """Initialize FAISS index with given dimension."""
        try:
            if self.similarity_metric == "cosine":
                # For cosine similarity, we need to normalize vectors
                self.index = faiss.IndexFlatIP(dimension)  # Inner product for normalized vectors
            else:
                # For L2 distance
                self.index = faiss.IndexFlatL2(dimension)
                
            self.dimension = dimension
            logger.info(f"Initialized new FAISS index with dimension {dimension}")
            
        except Exception as e:
            logger.error(f"Error initializing FAISS index: {str(e)}")
            raise
        
    def load_metadata(self):
        """Load metadata from disk if it exists."""
        try:
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'r') as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded metadata for {len(self.metadata)} documents")
        except Exception as e:
            logger.error(f"Error loading metadata: {str(e)}")
            self.metadata = {}
            
    def save_metadata(self):
        """Save metadata to disk."""
        try:
            with open(self.metadata_path, 'w') as f:
                json.dump(self.metadata, f)
            logger.info(f"Saved metadata for {len(self.metadata)} documents")
        except Exception as e:
            logger.error(f"Error saving metadata: {str(e)}")
            
    def upsert_documents(
        self,
        documents: List[str],
        embeddings: np.ndarray,
        metadata: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Add or update documents in the vector store.
        
        Args:
            documents: List of document texts
            embeddings: Document embeddings as numpy array
            metadata: List of metadata dictionaries for each document
            ids: Optional list of document IDs
            
        Returns:
            Dictionary containing operation status and details
        """
        try:
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in range(len(documents))]
                
            # Initialize index if not done yet
            if self.index is None:
                self._initialize_index(embeddings.shape[1])
                
            # Normalize vectors if using cosine similarity
            if self.similarity_metric == "cosine":
                faiss.normalize_L2(embeddings)
                
            # Add vectors to FAISS index
            self.index.add(embeddings)
            
            # Store metadata and documents
            for doc_id, doc, meta in zip(ids, documents, metadata):
                self.metadata[doc_id] = {
                    "content": doc,
                    "metadata": meta
                }
                
            # Save metadata to disk
            self.save_metadata()
            
            # Save FAISS index
            faiss.write_index(self.index, self.faiss_index_path)
            
            logger.info(f"Successfully upserted {len(documents)} documents")
            
            return {
                "status": "success",
                "message": f"Successfully upserted {len(documents)} documents",
                "document_count": len(documents),
                "index_size": self.index.ntotal if self.index else 0,
                "metadata_count": len(self.metadata)
            }
            
        except Exception as e:
            error_msg = f"Error upserting documents: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "error": str(e),
                "document_count": 0,
                "index_size": self.index.ntotal if self.index else 0,
                "metadata_count": len(self.metadata)
            }
            
    def query(
        self,
        query_embedding: np.ndarray,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        include_distances: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Query the vector store for similar documents.
        
        Args:
            query_embedding: Query embedding as numpy array
            n_results: Number of results to return
            where: Optional metadata filters
            include_metadata: Whether to include metadata in results
            include_distances: Whether to include similarity scores
            
        Returns:
            List of dictionaries containing query results
        """
        try:
            if self.index is None or self.index.ntotal == 0:
                logger.warning("No documents in index")
                return []
                
            # Reshape query if needed
            if len(query_embedding.shape) == 1:
                query_embedding = query_embedding.reshape(1, -1)
                
            # Normalize query if using cosine similarity
            if self.similarity_metric == "cosine":
                faiss.normalize_L2(query_embedding)
                
            # Set number of clusters to probe
            if hasattr(self.index, 'nprobe'):
                self.index.nprobe = self.nprobe
                
            # Search in FAISS
            distances, indices = self.index.search(query_embedding, n_results)
            
            # Format results
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx == -1:  # FAISS returns -1 for not enough results
                    continue
                    
                doc_id = list(self.metadata.keys())[idx]
                doc_data = self.metadata[doc_id]
                
                result = {
                    "content": doc_data["content"],
                    "id": doc_id
                }
                
                if include_metadata:
                    result["metadata"] = doc_data["metadata"]
                    
                if include_distances:
                    if self.similarity_metric == "cosine":
                        # Convert distance to similarity score (cosine similarity)
                        result["similarity"] = 1 - distance/2
                    else:
                        # Convert L2 distance to similarity score
                        result["similarity"] = 1 / (1 + distance)
                        
                results.append(result)
                
            logger.info(f"Found {len(results)} relevant documents")
            return results
            
        except Exception as e:
            logger.error(f"Error querying vector store: {str(e)}")
            return []
            
    def count(self) -> int:
        """Get the number of documents in the store."""
        return len(self.metadata)
        
    def peek(
        self,
        limit: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get a sample of documents from the store.
        
        Args:
            limit: Maximum number of documents to return
            where: Optional metadata filters
            
        Returns:
            List of documents
        """
        try:
            # Get all document IDs
            doc_ids = list(self.metadata.keys())
            
            # Apply metadata filters if provided
            if where:
                doc_ids = [
                    doc_id for doc_id in doc_ids
                    if all(
                        self.metadata[doc_id]["metadata"].get(k) == v
                        for k, v in where.items()
                    )
                ]
                
            # Limit number of results
            doc_ids = doc_ids[:limit]
            
            # Format results
            results = []
            for doc_id in doc_ids:
                doc_data = self.metadata[doc_id]
                results.append({
                    "content": doc_data["content"],
                    "id": doc_id,
                    "metadata": doc_data["metadata"]
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Error peeking documents: {str(e)}")
            return [] 