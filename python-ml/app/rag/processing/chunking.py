"""
Document chunking utilities for splitting text into manageable pieces.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import json

class DocumentChunker:
    """Handles splitting documents into chunks for processing."""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separator: str = "\n"
    ):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Target size of each chunk
            chunk_overlap: Number of characters to overlap between chunks
            separator: Character to use for splitting text
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
            
        # Split text into sentences/paragraphs
        segments = text.split(self.separator)
        chunks = []
        current_chunk = []
        current_size = 0
        
        for segment in segments:
            segment_size = len(segment)
            
            if current_size + segment_size <= self.chunk_size:
                current_chunk.append(segment)
                current_size += segment_size
            else:
                # Save current chunk
                if current_chunk:
                    chunks.append(self.separator.join(current_chunk))
                
                # Start new chunk with overlap
                overlap_size = 0
                overlap_chunks = []
                
                for prev_segment in reversed(current_chunk):
                    if overlap_size + len(prev_segment) <= self.chunk_overlap:
                        overlap_chunks.insert(0, prev_segment)
                        overlap_size += len(prev_segment)
                    else:
                        break
                
                current_chunk = overlap_chunks + [segment]
                current_size = sum(len(s) for s in current_chunk)
        
        # Add final chunk
        if current_chunk:
            chunks.append(self.separator.join(current_chunk))
        
        return chunks
    
    def chunk_structured_data(
        self,
        data: Any,
        strategy: str = "row"
    ) -> List[Dict[str, Any]]:
        """
        Split structured data (JSON, CSV, etc.) into chunks.
        
        Args:
            data: Data to split (DataFrame or dict)
            strategy: Chunking strategy ('row' or 'column')
            
        Returns:
            List of data chunks
        """
        if isinstance(data, pd.DataFrame):
            if strategy == "row":
                chunks = []
                for i in range(0, len(data), self.chunk_size):
                    chunk = data.iloc[i:i + self.chunk_size].to_dict('records')
                    chunks.extend(chunk)
                return chunks
            else:
                # Column-wise chunking
                return [data.to_dict('records')]
        
        elif isinstance(data, (dict, list)):
            if isinstance(data, dict):
                data = [data]
            
            chunks = []
            current_chunk = []
            
            for item in data:
                if len(current_chunk) >= self.chunk_size:
                    chunks.append(current_chunk)
                    current_chunk = []
                current_chunk.append(item)
            
            if current_chunk:
                chunks.append(current_chunk)
            
            return chunks
        
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
    
    def get_chunk_metadata(self, chunk: str, index: int) -> Dict[str, Any]:
        """
        Generate metadata for a chunk.
        
        Args:
            chunk: Text chunk
            index: Chunk index
            
        Returns:
            Dictionary of metadata
        """
        return {
            "chunk_index": index,
            "chunk_size": len(chunk),
            "chunk_tokens": len(chunk.split()),  # Simple token count
            "chunk_type": "text"
        } 