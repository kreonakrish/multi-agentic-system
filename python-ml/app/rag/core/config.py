"""
Configuration manager for RAG settings.
"""

from typing import Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path
import os

@dataclass
class RAGConfig:
    """Configuration settings for RAG implementation."""
    
    # OpenAI settings
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Embedding settings
    embedding_model: str = "sentence-transformers/all-mpnet-base-v2"
    embedding_batch_size: int = 100
    
    # FAISS settings
    faiss_index_path: str = str(Path(__file__).parent.parent / "data" / "faiss_index")
    metadata_path: str = str(Path(__file__).parent.parent / "data" / "metadata.json")
    similarity_metric: str = "cosine"  # Options: cosine, l2
    nprobe: int = 10  # Number of clusters to probe during search
    
    # Chunking settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Query settings
    n_results: int = 5
    similarity_threshold: float = 0.7
    
    # Processing settings
    max_documents_per_query: int = 10
    remove_stopwords: bool = False
    remove_punctuation: bool = True
    lowercase: bool = True
    normalize_whitespace: bool = True
    
    # Query preprocessing settings
    expand_synonyms: bool = True
    max_synonyms: int = 3
    min_word_length: int = 3
    
    # LLM settings
    llm_model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 500
    
    # Monitoring settings
    enable_detailed_logging: bool = True
    
    # Paths
    data_dir: Path = field(default_factory=lambda: Path("data"))
    cache_dir: Path = field(default_factory=lambda: Path("cache"))
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {
            "openai": {
                "api_key": self.openai_api_key
            },
            "embedding": {
                "model": self.embedding_model,
                "batch_size": self.embedding_batch_size
            },
            "faiss": {
                "index_path": self.faiss_index_path,
                "metadata_path": self.metadata_path,
                "similarity_metric": self.similarity_metric,
                "nprobe": self.nprobe
            },
            "chunking": {
                "size": self.chunk_size,
                "overlap": self.chunk_overlap
            },
            "query": {
                "n_results": self.n_results,
                "similarity_threshold": self.similarity_threshold,
                "max_documents": self.max_documents_per_query
            },
            "processing": {
                "remove_stopwords": self.remove_stopwords,
                "remove_punctuation": self.remove_punctuation,
                "lowercase": self.lowercase,
                "normalize_whitespace": self.normalize_whitespace
            },
            "query_preprocessing": {
                "expand_synonyms": self.expand_synonyms,
                "max_synonyms": self.max_synonyms,
                "min_word_length": self.min_word_length
            },
            "llm": {
                "model": self.llm_model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            },
            "monitoring": {
                "enable_detailed_logging": self.enable_detailed_logging
            },
            "paths": {
                "data": str(self.data_dir),
                "cache": str(self.cache_dir),
                "logs": str(self.log_dir)
            }
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'RAGConfig':
        """Create config from dictionary."""
        return cls(
            # OpenAI settings
            openai_api_key=config_dict["openai"]["api_key"],
            
            # Embedding settings
            embedding_model=config_dict["embedding"]["model"],
            embedding_batch_size=config_dict["embedding"]["batch_size"],
            
            # FAISS settings
            faiss_index_path=config_dict["faiss"]["index_path"],
            metadata_path=config_dict["faiss"]["metadata_path"],
            similarity_metric=config_dict["faiss"]["similarity_metric"],
            nprobe=config_dict["faiss"]["nprobe"],
            
            # Chunking settings
            chunk_size=config_dict["chunking"]["size"],
            chunk_overlap=config_dict["chunking"]["overlap"],
            
            # Query settings
            n_results=config_dict["query"]["n_results"],
            similarity_threshold=config_dict["query"]["similarity_threshold"],
            max_documents_per_query=config_dict["query"]["max_documents"],
            
            # Processing settings
            remove_stopwords=config_dict["processing"]["remove_stopwords"],
            remove_punctuation=config_dict["processing"]["remove_punctuation"],
            lowercase=config_dict["processing"]["lowercase"],
            normalize_whitespace=config_dict["processing"]["normalize_whitespace"],
            
            # Query preprocessing settings
            expand_synonyms=config_dict["query_preprocessing"]["expand_synonyms"],
            max_synonyms=config_dict["query_preprocessing"]["max_synonyms"],
            min_word_length=config_dict["query_preprocessing"]["min_word_length"],
            
            # LLM settings
            llm_model=config_dict["llm"]["model"],
            temperature=config_dict["llm"]["temperature"],
            max_tokens=config_dict["llm"]["max_tokens"],
            
            # Monitoring settings
            enable_detailed_logging=config_dict["monitoring"]["enable_detailed_logging"],
            
            # Paths
            data_dir=Path(config_dict["paths"]["data"]),
            cache_dir=Path(config_dict["paths"]["cache"]),
            log_dir=Path(config_dict["paths"]["logs"])
        ) 