"""
Test cases for RAG pipeline implementation.
"""

import unittest
from unittest.mock import patch, MagicMock
import logging
from datetime import datetime
import pandas as pd
import requests
from pathlib import Path
import os
import traceback
import json

logger = logging.getLogger(__name__)

from ..rag.core.config import RAGConfig
from ..rag.core.factory import RAGFactory
from ..rag.core.pipeline import RAGPipeline

class MockResponse:
    """Mock OpenAI API response."""
    def __init__(self, content="This is a mock response"):
        self.choices = [
            MagicMock(
                message=MagicMock(content=content),
                finish_reason="stop"
            )
        ]

class MyRagSystem:
    """Test RAG system implementation."""
    
    def __init__(self):
        """Initialize the RAG system."""
        try:
            config = RAGConfig()
            config.openai_api_key = os.getenv("OPENAI_API_KEY", "dummy_key")
            self.rag_pipeline = RAGFactory.create_pipeline(config)
        except Exception as e:
            logger.error(f"Error initializing RAG system: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def ingest_dataset(self, tool_nm: str, dataset_nm: str, dataset_loc: dict):
        """
        Ingest a dataset into the RAG pipeline.
        
        Args:
            tool_nm: Name of the tool providing the dataset
            dataset_nm: Name of the dataset
            dataset_loc: Dictionary containing dataset location info
        """
        try:
            # Create metadata
            metadata = {
                'source': tool_nm,
                'dataset_nm': dataset_nm,
                'dataset_location': dataset_loc['location'],
                'location_type': dataset_loc['type'],
                'timestamp': datetime.now().isoformat(),
            }
            
            # Pass to pipeline for ingestion
            self.rag_pipeline.ingest_data(
                dataset_nm,
                metadata=metadata,
                location=dataset_loc
            )
        except Exception as e:
            logger.error(f"Error ingesting dataset {dataset_nm}: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def execute(self, user_query: str) -> dict:
        """
        Execute a query against the RAG pipeline.
        
        Args:
            user_query: User's query string
            
        Returns:
            Query results
        """
        try:
            return self.rag_pipeline.process_query(user_query)
        except Exception as e:
            logger.error(f"Error executing query '{user_query}': {str(e)}")
            logger.error(traceback.format_exc())
            raise

class TestRagPipeline(unittest.TestCase):
    """Test cases for RAG pipeline."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        try:
            # Create test data directory
            cls.test_data_dir = Path("test_data")
            cls.test_data_dir.mkdir(exist_ok=True)
            
            # Create sample NFL stats
            cls.create_sample_nfl_data()
        except Exception as e:
            logger.error(f"Error in setUpClass: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    @classmethod
    def create_sample_nfl_data(cls):
        """Create sample NFL data for testing."""
        try:
            nfl_data = {
                'team': ['Patriots', 'Rams', 'Chiefs', 'Packers'],
                'wins': [10, 12, 14, 13],
                'losses': [7, 5, 3, 4],
                'points_scored': [350, 420, 480, 450],
                'points_allowed': [300, 350, 320, 330]
            }
            df = pd.DataFrame(nfl_data)
            
            # Save local copy
            cls.local_file = cls.test_data_dir / "nfl_stats.csv"
            df.to_csv(cls.local_file, index=False)
        except Exception as e:
            logger.error(f"Error creating sample NFL data: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def setUp(self):
        """Set up test cases."""
        try:
            logger.info("Setting up test case...")
            self.mock_openai_patcher = patch('openai.OpenAI')
            self.mock_openai = self.mock_openai_patcher.start()
            
            # Configure mock OpenAI client
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = MockResponse(
                "Based on the provided data, the Kansas City Chiefs have the most wins with 14 wins in the season."
            )
            self.mock_openai.return_value = mock_client
            
            config = RAGConfig()
            config.openai_api_key = "mock_key"
            self.system = MyRagSystem()
            self.test_query = "do you have nfl favorite team data"
            logger.info("Test case setup complete")
        except Exception as e:
            logger.error(f"Error in setUp: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def tearDown(self):
        """Clean up after each test."""
        try:
            logger.info("Cleaning up after test")
            self.mock_openai_patcher.stop()
        except Exception as e:
            logger.error(f"Error in tearDown: {str(e)}")
            logger.error(traceback.format_exc())
    
    def test_local_file_ingestion(self):
        """Test ingesting data from local file."""
        try:
            logger.info("Starting local file ingestion test")
            dataset_loc = {
                "location": str(self.local_file),
                "type": "local_file"
            }
            
            # Test ingestion
            self.system.ingest_dataset("GitHubTool", "nfl_stats", dataset_loc)
            
            # Test query
            result = self.system.execute(self.test_query)
            
            # Verify response
            self.assertIsNotNone(result)
            self.assertIn("response", result)
            self.assertTrue(len(result.get("results", [])) > 0)
            logger.info("Local file ingestion test completed successfully")
        except Exception as e:
            logger.error(f"Error in test_local_file_ingestion: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def test_url_ingestion(self):
        """Test ingesting data from URL."""
        try:
            logger.info("Starting URL ingestion test")
            # For testing, we'll use a mock URL
            dataset_loc = {
                "location": "https://example.com/nfl_stats.csv",
                "type": "url"
            }
            
            try:
                self.system.ingest_dataset("GitHubTool", "nfl_stats_web", dataset_loc)
                result = self.system.execute(self.test_query)
                
                self.assertIsNotNone(result)
                self.assertIn("response", result)
                logger.info("URL ingestion test completed successfully")
                
            except requests.exceptions.RequestException:
                # Skip test if URL is not accessible
                logger.warning("Skipping URL ingestion test - URL not accessible")
                self.skipTest("URL not accessible")
        except Exception as e:
            logger.error(f"Error in test_url_ingestion: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def test_query_processing(self):
        """Test query processing functionality."""
        try:
            logger.info("Starting query processing test")
            # First ingest local data
            dataset_loc = {
                "location": str(self.local_file),
                "type": "local_file"
            }
            logger.info("Ingesting test dataset...")
            self.system.ingest_dataset("GitHubTool", "nfl_stats", dataset_loc)
            
            # Test various queries
            queries = [
                "which team has the most wins?",
                "what is the average points scored?",
                "show me the team statistics"
            ]
            
            for query in queries:
                logger.info(f"Testing query: {query}")
                result = self.system.execute(query)
                logger.info(f"Query result: {json.dumps(result, indent=2)}")
                
                # Verify response structure
                self.assertIsNotNone(result)
                self.assertIn("response", result)
                self.assertIn("metadata", result)
                
                # Verify timing information
                self.assertIn("timing", result["metadata"])
                self.assertGreater(result["metadata"]["timing"]["total_time"], 0)
            
            logger.info("Query processing test completed successfully")
        except Exception as e:
            logger.error(f"Error in test_query_processing: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def test_error_handling(self):
        """Test error handling in pipeline."""
        try:
            logger.info("Starting error handling test")
            # Test with invalid file location
            dataset_loc = {
                "location": "nonexistent.csv",
                "type": "local_file"
            }
            
            with self.assertRaises(Exception):
                self.system.ingest_dataset("GitHubTool", "invalid_data", dataset_loc)
            
            # Test with invalid URL
            dataset_loc = {
                "location": "https://invalid.url/data.csv",
                "type": "url"
            }
            
            with self.assertRaises(Exception):
                self.system.ingest_dataset("GitHubTool", "invalid_url_data", dataset_loc)
            
            logger.info("Error handling test completed successfully")
        except Exception as e:
            logger.error(f"Error in test_error_handling: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def test_metadata_handling(self):
        """Test metadata handling in pipeline."""
        try:
            logger.info("Starting metadata handling test")
            dataset_loc = {
                "location": str(self.local_file),
                "type": "local_file"
            }
            
            logger.info("Ingesting dataset with metadata...")
            # Ingest with metadata
            self.system.ingest_dataset("GitHubTool", "nfl_stats_meta", dataset_loc)
            
            logger.info("Executing test query...")
            # Query and verify metadata
            result = self.system.execute(self.test_query)
            logger.info(f"Query result: {json.dumps(result, indent=2)}")
            
            logger.info("Verifying metadata structure...")
            self.assertIn("metadata", result)
            self.assertIn("query_metadata", result["metadata"])
            
            # Verify source tracking
            results = result.get("results", [])
            for doc in results:
                self.assertIn("metadata", doc)
                self.assertEqual(doc["metadata"]["source"], "GitHubTool")
            
            logger.info("Metadata handling test completed successfully")
        except Exception as e:
            logger.error(f"Error in test_metadata_handling: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        try:
            logger.info("Final cleanup after all tests")
            # Add any final cleanup code here
        except Exception as e:
            logger.error(f"Error in tearDownClass: {str(e)}")
            logger.error(traceback.format_exc())

if __name__ == '__main__':
    unittest.main() 