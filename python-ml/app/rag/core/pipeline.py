"""
Base RAG pipeline implementation.
"""

from typing import Dict, List, Optional, Any
import logging
import time
import pandas as pd
import requests
from pathlib import Path
import traceback
from datetime import datetime
import json
import copy
import numpy as np

from .config import RAGConfig
from .embeddings import EmbeddingManager
from .vector_store import VectorStoreManager
from ..processing.chunking import DocumentChunker
from ..processing.cleaning import DataCleaner
from ..query.preprocessing import QueryPreprocessor
from ..response.generator import ResponseGenerator
from ..monitoring.metrics import RAGMonitor

# Get module-specific logger
logger = logging.getLogger(__name__)

def _flatten_metadata(metadata: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
    """
    Flatten nested metadata dictionary into a single level with string values.
    
    Args:
        metadata: Nested metadata dictionary
        prefix: Prefix for flattened keys
        
    Returns:
        Flattened metadata dictionary with only simple types
    """
    items = []
    for k, v in metadata.items():
        new_key = f"{prefix}_{k}" if prefix else k
        
        if isinstance(v, (str, int, float, bool)) or v is None:
            items.append((new_key, v))
        elif isinstance(v, dict):
            items.extend(_flatten_metadata(v, new_key).items())
        elif isinstance(v, (list, tuple)):
            # Convert lists to strings
            items.append((new_key, str(v)))
        else:
            # Convert other types to strings
            items.append((new_key, str(v)))
            
    return dict(items)

def _mask_sensitive_data(config_dict: Dict) -> Dict:
    """
    Create a copy of the config dictionary with sensitive data masked.
    
    Args:
        config_dict: Original configuration dictionary
        
    Returns:
        Dictionary with sensitive data masked
    """
    # Create a deep copy to avoid modifying the original
    masked_dict = copy.deepcopy(config_dict)
    
    # Mask OpenAI API key if present
    if 'openai' in masked_dict and 'api_key' in masked_dict['openai']:
        api_key = masked_dict['openai']['api_key']
        if api_key:
            # Keep first 4 and last 4 characters, mask the rest
            masked_dict['openai']['api_key'] = f"{api_key[:4]}...{api_key[-4:]}"
    
    return masked_dict

def _convert_to_json_serializable(obj: Any) -> Any:
    """Convert objects to JSON serializable format."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (list, tuple)):
        return [_convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: _convert_to_json_serializable(value) for key, value in obj.items()}
    return obj

class RAGPipeline:
    """Base RAG pipeline implementation."""
    
    def __init__(self, config: RAGConfig):
        """
        Initialize the RAG pipeline.
        
        Args:
            config: RAG configuration
        """
        try:
            logger.info("[pipeline.py:__init__] Initializing RAG pipeline")
            self.config = config
            
            # Log full configuration with masked sensitive data
            config_dict = self.config.to_dict()
            masked_config = _mask_sensitive_data(config_dict)
            
            logger.info("[pipeline.py:__init__] RAG Pipeline Configuration:")
            logger.info(f"[pipeline.py:__init__] OpenAI Settings:\n{json.dumps(masked_config['openai'], indent=2)}")
            logger.info(f"[pipeline.py:__init__] Embedding Settings:\n{json.dumps(masked_config['embedding'], indent=2)}")
            logger.info(f"[pipeline.py:__init__] FAISS Settings:\n{json.dumps(masked_config['faiss'], indent=2)}")
            logger.info(f"[pipeline.py:__init__] Chunking Settings:\n{json.dumps(masked_config['chunking'], indent=2)}")
            logger.info(f"[pipeline.py:__init__] Query Settings:\n{json.dumps(masked_config['query'], indent=2)}")
            logger.info(f"[pipeline.py:__init__] Processing Settings:\n{json.dumps(masked_config['processing'], indent=2)}")
            logger.info(f"[pipeline.py:__init__] Query Preprocessing Settings:\n{json.dumps(masked_config['query_preprocessing'], indent=2)}")
            logger.info(f"[pipeline.py:__init__] LLM Settings:\n{json.dumps(masked_config['llm'], indent=2)}")
            logger.info(f"[pipeline.py:__init__] Monitoring Settings:\n{json.dumps(masked_config['monitoring'], indent=2)}")
            logger.info(f"[pipeline.py:__init__] Path Settings:\n{json.dumps(masked_config['paths'], indent=2)}")
            
            # Initialize components
            logger.info("[pipeline.py:__init__] Initializing embedding manager")
            self.embedding_manager = EmbeddingManager(
                model_name=config.embedding_model
            )
            
            logger.info("[pipeline.py:__init__] Initializing vector store")
            self.vector_store = VectorStoreManager(
                faiss_index_path=config.faiss_index_path,
                metadata_path=config.metadata_path,
                similarity_metric=config.similarity_metric,
                nprobe=config.nprobe
            )
            
            logger.info("[pipeline.py:__init__] Initializing document chunker")
            self.chunker = DocumentChunker(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap
            )
            
            logger.info("[pipeline.py:__init__] Initializing data cleaner")
            self.cleaner = DataCleaner(
                remove_stopwords=False,  # Keep stopwords for better context
                remove_punctuation=True,
                lowercase=True,
                normalize_whitespace=True
            )
            
            logger.info("[pipeline.py:__init__] Initializing query processor")
            self.query_processor = QueryPreprocessor(
                expand_synonyms=True,
                max_synonyms=3
            )
            
            logger.info("[pipeline.py:__init__] Initializing response generator")
            self.response_generator = ResponseGenerator(
                model=config.llm_model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                api_key=config.openai_api_key
            )
            
            logger.info("[pipeline.py:__init__] Initializing RAG monitor")
            self.monitor = RAGMonitor(
                log_dir=str(config.log_dir),
                enable_detailed_logging=True
            )
            
            # Ensure directories exist
            logger.info("[pipeline.py:__init__] Creating required directories")
            config.data_dir.mkdir(parents=True, exist_ok=True)
            config.cache_dir.mkdir(parents=True, exist_ok=True)
            config.log_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info("[pipeline.py:__init__] RAG pipeline initialization completed")
        except Exception as e:
            logger.error(f"[pipeline.py:__init__] Error initializing RAG pipeline: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _load_data(self, location: Dict[str, str]) -> pd.DataFrame:
        """
        Load data from various sources.
        
        Args:
            location: Dictionary containing location info
            
        Returns:
            Loaded DataFrame
        """
        loc_type = location["type"]
        loc_path = location["location"]
        
        if loc_type == "local_file":
            if not Path(loc_path).exists():
                raise FileNotFoundError(f"File not found: {loc_path}")
                
            # Determine file type from extension
            file_ext = Path(loc_path).suffix.lower()
            
            if file_ext == '.csv':
                return pd.read_csv(loc_path)
            elif file_ext == '.json':
                # Read JSON file
                with open(loc_path, 'r') as f:
                    data = json.load(f)
                # Convert to DataFrame
                if isinstance(data, list):
                    return pd.DataFrame(data)
                elif isinstance(data, dict):
                    return pd.DataFrame([data])
                else:
                    raise ValueError(f"Unsupported JSON structure in {loc_path}")
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
            
        elif loc_type == "url":
            try:
                response = requests.get(loc_path)
                response.raise_for_status()
                
                # Determine content type from URL
                if loc_path.lower().endswith('.json'):
                    data = response.json()
                    if isinstance(data, list):
                        return pd.DataFrame(data)
                    elif isinstance(data, dict):
                        return pd.DataFrame([data])
                    else:
                        raise ValueError(f"Unsupported JSON structure from {loc_path}")
                else:
                    # Default to CSV
                    return pd.read_csv(pd.StringIO(response.text))
                    
            except requests.exceptions.RequestException as e:
                raise Exception(f"Error loading URL data: {str(e)}")
            
        else:
            raise ValueError(f"Unsupported location type: {loc_type}")
    
    def ingest_data(
        self,
        dataset_nm: str,
        metadata: Dict[str, Any],
        location: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Ingest data from various sources into the RAG pipeline.
        
        Args:
            dataset_nm: Name of the dataset
            metadata: Metadata about the dataset
            location: Dictionary containing location info
            
        Returns:
            Dictionary containing ingestion results
        """
        try:
            start_time = time.time()
            logger.info(f"[pipeline.py:ingest_data] Starting data ingestion for dataset: {dataset_nm}")
            logger.info(f"[pipeline.py:ingest_data] Received parameters: dataset_nm={dataset_nm}, metadata={json.dumps(metadata, indent=2)}, location={json.dumps(location, indent=2)}")
            
            # Load data
            logger.info(f"[pipeline.py:ingest_data] Loading data from {location['type']}: {location['location']}")
            df = self._load_data(location)
            logger.info(f"[pipeline.py:ingest_data] Successfully loaded {len(df)} rows")
            
            # Convert DataFrame to text chunks
            documents = []
            chunk_metadata = []
            
            logger.info("[pipeline.py:ingest_data] Processing rows into chunks")
            # Process each row as a document
            for idx, row in df.iterrows():
                logger.debug(f"[pipeline.py:ingest_data] Processing row {idx + 1}/{len(df)}")
                # Convert row to string representation
                doc = row.to_string()
                
                # Clean document
                cleaned_doc = self.cleaner.clean_text(doc)
                
                # Split into chunks
                chunks = self.chunker.chunk_text(cleaned_doc)
                logger.debug(f"[pipeline.py:ingest_data] Created {len(chunks)} chunks from row {idx + 1}")
                
                # Add chunks and metadata
                for chunk_idx, chunk in enumerate(chunks):
                    documents.append(chunk)
                    
                    # Create chunk metadata
                    chunk_meta = metadata.copy()
                    chunk_meta.update({
                        'chunk_index': chunk_idx,
                        'row_index': idx,
                        'dataset_name': dataset_nm
                    })
                    # Flatten metadata to simple types
                    flattened_meta = _flatten_metadata(chunk_meta)
                    chunk_metadata.append(flattened_meta)
            
            # Generate embeddings
            logger.info(f"[pipeline.py:ingest_data] Generating embeddings for {len(documents)} chunks")
            embedding_start = time.time()
            embeddings = self.embedding_manager.batch_generate_embeddings(
                documents,
                batch_size=self.config.embedding_batch_size
            )
            embedding_time = time.time() - embedding_start
            logger.info(f"[pipeline.py:ingest_data] Embeddings generated in {embedding_time:.2f} seconds")
            
            # Store in vector store
            logger.info("[pipeline.py:ingest_data] Storing chunks in vector store")
            vector_store_result = self.vector_store.upsert_documents(
                documents=documents,
                embeddings=embeddings,
                metadata=chunk_metadata
            )
            
            if vector_store_result["status"] != "success":
                error_msg = f"Vector store operation failed: {vector_store_result.get('message', 'Unknown error')}"
                logger.error(f"[pipeline.py:ingest_data] {error_msg}")
                return {
                    'dataset_name': dataset_nm,
                    'total_rows': len(df),
                    'total_chunks': len(documents),
                    'embedding_time': embedding_time,
                    'total_time': time.time() - start_time,
                    'status': 'error',
                    'error': error_msg,
                    'vector_store_details': vector_store_result
                }

            total_time = time.time() - start_time
            
            # Log metrics
            logger.info("[pipeline.py:ingest_data] Logging embedding metrics")
            for chunk, meta in zip(documents, chunk_metadata):
                self.monitor.log_embedding(chunk, embedding_time / len(documents))
            
            results = {
                'dataset_name': dataset_nm,
                'total_rows': len(df),
                'total_chunks': len(documents),
                'embedding_time': embedding_time,
                'total_time': total_time,
                'status': 'success',
                'vector_store_details': vector_store_result
            }
            
            logger.info(f"[pipeline.py:ingest_data] Successfully ingested dataset {dataset_nm}")
            logger.debug(f"[pipeline.py:ingest_data] Ingestion results: {json.dumps(results, indent=2)}")
            return results
            
        except Exception as e:
            error_msg = f"Error ingesting dataset {dataset_nm}: {str(e)}"
            logger.error(f"[pipeline.py:ingest_data] {error_msg}")
            logger.error(traceback.format_exc())
            return {
                'dataset_name': dataset_nm,
                'status': 'error',
                'error': error_msg,
                'total_time': time.time() - start_time
            }
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a query through the RAG pipeline.
        
        Args:
            query: Query string
            
        Returns:
            Dictionary containing query results and response
        """
        try:
            start_time = time.time()
            logger.info(f"[pipeline.py:process_query] Starting query processing: {query}")
            
            # Validate and preprocess query
            logger.info("[pipeline.py:process_query] Validating query")
            query_validation = self.query_processor.validate_query(query)
            if not query_validation["is_valid"]:
                logger.warning(f"[pipeline.py:process_query] Query validation failed: {query_validation.get('reason', 'Unknown reason')}")
                return query_validation
            
            # Process query
            logger.info("[pipeline.py:process_query] Preprocessing query")
            processed_query = self.query_processor.preprocess_query(query)
            query_metadata = self.query_processor.get_query_metadata(processed_query)
            logger.debug(f"[pipeline.py:process_query] Processed query: {processed_query}")
            
            # Generate query embedding
            logger.info(f"[pipeline.py:process_query] Generating embedding for query: {processed_query}")
            query_start = time.time()
            query_embedding = self.embedding_manager.generate_embedding(processed_query)
            query_time = time.time() - query_start
            logger.info(f"[pipeline.py:process_query] Query embedding generated in {query_time:.2f} seconds")
            
            # Query vector store
            logger.info(f"[pipeline.py:process_query] Querying vector store for top {self.config.n_results} results")
            retrieval_start = time.time()
            results = self.vector_store.query(
                query_embedding=query_embedding,
                n_results=self.config.n_results
            )
            retrieval_time = time.time() - retrieval_start
            logger.info(f"[pipeline.py:process_query] Retrieved {len(results)} results in {retrieval_time:.2f} seconds")
            
            # Generate response
            logger.info("[pipeline.py:process_query] Generating response")
            response_start = time.time()
            response = self.response_generator.generate_response(
                query=processed_query,
                retrieved_docs=results,
                task="answer"  # Default to answer task
            )
            response_time = time.time() - response_start
            logger.info(f"[pipeline.py:process_query] Response generated in {response_time:.2f} seconds")
            
            # Calculate total time
            total_time = time.time() - start_time
            
            # Log metrics
            logger.info("[pipeline.py:process_query] Logging metrics")
            self.monitor.log_query(processed_query, query_metadata)
            self.monitor.log_embedding(processed_query, query_time)
            self.monitor.log_retrieval(
                processed_query,
                len(results),
                retrieval_time,
                bool(results)
            )
            self.monitor.log_response(
                processed_query,
                response,
                response_time,
                response.get("metadata", {}).get("success", True)
            )
            
            response["metadata"]["timing"] = {
                "total_time": total_time
            }
            
            final_response = {
                "query": query,
                "processed_query": processed_query,
                "results": _convert_to_json_serializable(results),
                "response": _convert_to_json_serializable(response),
                "metadata": {
                    "query_metadata": query_metadata,
                    "n_results": len(results),
                    "timing": {
                        "query_time": query_time,
                        "retrieval_time": retrieval_time,
                        "response_time": response_time,
                        "total_time": total_time
                    }
                }
            }
            
            logger.info("[pipeline.py:process_query] Query processing completed successfully")
            logger.debug(f"[pipeline.py:process_query] Final response: {json.dumps(_convert_to_json_serializable(final_response), indent=2)}")
            return final_response
            
        except Exception as e:
            logger.error(f"[pipeline.py:process_query] Error processing query: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "response": "I apologize, but I encountered an error processing your query.",
                "metadata": {
                    "error": str(e),
                    "success": False,
                    "timing": {
                        "total_time": 0
                    }
                },
                "results": []
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG pipeline."""
        try:
            logger.info("[pipeline.py:get_stats] Retrieving RAG pipeline statistics")
            stats = {
                "document_count": self.vector_store.count(),
                "embedding_dimension": self.embedding_manager.get_embedding_dim(),
                "config": self.config.to_dict(),
                "metrics": self.monitor.get_metrics_summary()
            }
            logger.debug(f"[pipeline.py:get_stats] Pipeline stats: {json.dumps(stats, indent=2)}")
            return stats
        except Exception as e:
            logger.error(f"[pipeline.py:get_stats] Error getting pipeline stats: {str(e)}")
            logger.error(traceback.format_exc())
            raise 