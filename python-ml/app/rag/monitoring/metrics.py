"""
Monitoring utilities for tracking RAG performance and usage.
"""

from typing import Dict, List, Any, Optional
import time
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class RAGMonitor:
    """Handles monitoring and metrics collection for RAG system."""
    
    def __init__(
        self,
        log_dir: Optional[str] = None,
        enable_detailed_logging: bool = True
    ):
        """
        Initialize the monitor.
        
        Args:
            log_dir: Directory for storing logs
            enable_detailed_logging: Whether to log detailed metrics
        """
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.enable_detailed_logging = enable_detailed_logging
        
        # Initialize metrics
        self.reset_metrics()
    
    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics = {
            "queries": [],
            "embeddings": {
                "count": 0,
                "total_time": 0,
                "average_time": 0
            },
            "retrievals": {
                "count": 0,
                "total_time": 0,
                "average_time": 0,
                "hit_rate": 0
            },
            "responses": {
                "count": 0,
                "total_time": 0,
                "average_time": 0,
                "success_rate": 0
            }
        }
    
    def log_query(
        self,
        query: str,
        metadata: Dict[str, Any]
    ):
        """
        Log query metrics.
        
        Args:
            query: Query text
            metadata: Query metadata
        """
        timestamp = datetime.now().isoformat()
        
        query_log = {
            "timestamp": timestamp,
            "query": query,
            "metadata": metadata
        }
        
        self.metrics["queries"].append(query_log)
        
        if self.enable_detailed_logging:
            log_file = self.log_dir / f"queries_{datetime.now():%Y%m%d}.jsonl"
            with open(log_file, "a") as f:
                f.write(json.dumps(query_log) + "\n")
    
    def log_embedding(
        self,
        text: str,
        embedding_time: float
    ):
        """
        Log embedding metrics.
        
        Args:
            text: Text that was embedded
            embedding_time: Time taken for embedding
        """
        self.metrics["embeddings"]["count"] += 1
        self.metrics["embeddings"]["total_time"] += embedding_time
        self.metrics["embeddings"]["average_time"] = (
            self.metrics["embeddings"]["total_time"] /
            self.metrics["embeddings"]["count"]
        )
        
        if self.enable_detailed_logging:
            log_file = self.log_dir / f"embeddings_{datetime.now():%Y%m%d}.jsonl"
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "text_length": len(text),
                "embedding_time": embedding_time
            }
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
    
    def log_retrieval(
        self,
        query: str,
        num_results: int,
        retrieval_time: float,
        is_hit: bool
    ):
        """
        Log retrieval metrics.
        
        Args:
            query: Query text
            num_results: Number of results retrieved
            retrieval_time: Time taken for retrieval
            is_hit: Whether relevant results were found
        """
        self.metrics["retrievals"]["count"] += 1
        self.metrics["retrievals"]["total_time"] += retrieval_time
        self.metrics["retrievals"]["average_time"] = (
            self.metrics["retrievals"]["total_time"] /
            self.metrics["retrievals"]["count"]
        )
        
        # Update hit rate
        total_hits = sum(1 for q in self.metrics["queries"] if q.get("is_hit", False))
        self.metrics["retrievals"]["hit_rate"] = total_hits / self.metrics["retrievals"]["count"]
        
        if self.enable_detailed_logging:
            log_file = self.log_dir / f"retrievals_{datetime.now():%Y%m%d}.jsonl"
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "num_results": num_results,
                "retrieval_time": retrieval_time,
                "is_hit": is_hit
            }
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
    
    def log_response(
        self,
        query: str,
        response: Dict[str, Any],
        response_time: float,
        is_success: bool
    ):
        """
        Log response metrics.
        
        Args:
            query: Query text
            response: Generated response
            response_time: Time taken for response generation
            is_success: Whether response generation was successful
        """
        self.metrics["responses"]["count"] += 1
        self.metrics["responses"]["total_time"] += response_time
        self.metrics["responses"]["average_time"] = (
            self.metrics["responses"]["total_time"] /
            self.metrics["responses"]["count"]
        )
        
        # Update success rate
        total_successes = sum(1 for q in self.metrics["queries"] if q.get("is_success", False))
        self.metrics["responses"]["success_rate"] = total_successes / self.metrics["responses"]["count"]
        
        if self.enable_detailed_logging:
            log_file = self.log_dir / f"responses_{datetime.now():%Y%m%d}.jsonl"
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "response_length": len(response["response"]),
                "response_time": response_time,
                "is_success": is_success,
                "metadata": response.get("metadata", {})
            }
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of all metrics.
        
        Returns:
            Dictionary containing metrics summary
        """
        return {
            "total_queries": len(self.metrics["queries"]),
            "embeddings": {
                "total": self.metrics["embeddings"]["count"],
                "average_time": round(self.metrics["embeddings"]["average_time"], 3)
            },
            "retrievals": {
                "total": self.metrics["retrievals"]["count"],
                "average_time": round(self.metrics["retrievals"]["average_time"], 3),
                "hit_rate": round(self.metrics["retrievals"]["hit_rate"], 2)
            },
            "responses": {
                "total": self.metrics["responses"]["count"],
                "average_time": round(self.metrics["responses"]["average_time"], 3),
                "success_rate": round(self.metrics["responses"]["success_rate"], 2)
            }
        }
    
    def export_metrics(
        self,
        format: str = "json",
        output_file: Optional[str] = None
    ) -> Optional[str]:
        """
        Export metrics to file.
        
        Args:
            format: Export format ('json' or 'jsonl')
            output_file: Output file path
            
        Returns:
            Path to exported file if successful
        """
        if not output_file:
            output_file = self.log_dir / f"metrics_export_{datetime.now():%Y%m%d_%H%M%S}.{format}"
        
        try:
            metrics_data = {
                "timestamp": datetime.now().isoformat(),
                "summary": self.get_metrics_summary(),
                "detailed": self.metrics
            }
            
            with open(output_file, "w") as f:
                if format == "json":
                    json.dump(metrics_data, f, indent=2)
                else:  # jsonl
                    for key, value in metrics_data.items():
                        f.write(json.dumps({key: value}) + "\n")
            
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {str(e)}")
            return None 