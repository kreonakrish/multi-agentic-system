import unittest
import json
import mysql.connector
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime
import logging

# Create mock responses for OpenAI
mock_code_response = Mock()
mock_code_response.choices = [
    Mock(message=Mock(content="Here's a Databricks PySpark code example with unit tests:\n\ndef test_spark_code():\n    assert spark_function() == expected_result"))
]
mock_code_response.model = "gpt-4"

mock_validation_response = Mock()
mock_validation_response.choices = [
    Mock(message=Mock(content='{"valid": true, "reason": "Response includes proper unit tests"}'))
]
mock_validation_response.model = "gpt-4"

# Mock the OpenAI class
class MockOpenAI:
    def __init__(self, api_key=None):
        self.chat = MagicMock()
        self.chat.completions = MagicMock()
        self.chat.completions.create = MagicMock(return_value=mock_code_response)

# Patch OpenAI before importing app
with patch('openai.OpenAI', MockOpenAI):
    from app import Agent, Tool, create_tool, initialize_agent_from_db

class MockDBXTool(Tool):
    def __init__(self):
        super().__init__(
            tool_id=1,
            tool_name="DBX Tool",
            hostname="databricks.example.com",
            username="test_user",
            password="test_pass",
            auth_method="token"
        )
    
    def execute(self, command):
        return {
            "status": "success",
            "tool_responses": [{
                "tool_name": "DBX Tool",
                "status": "success",
                "message": "DBX Tool was used to process the request",
                "tool_specific": {
                    "dbx_operation": "code_generation",
                    "status": "success",
                    "message": "DBX Tool was used to process the request"
                }
            }]
        }

    def get_default_response(self, command):
        return {
            "status": "success",
            "tool_responses": [{
                "tool_name": "DBX Tool",
                "status": "success",
                "message": "DBX Tool was used to process the request",
                "tool_specific": {
                    "dbx_operation": "code_generation",
                    "status": "success",
                    "message": "DBX Tool was used to process the request"
                }
            }]
        }

class TestAgentFunctionality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger(__name__)

        # Mock database connection
        cls.db_config = {
            'host': 'localhost',
            'user': 'test_user',
            'password': 'test_pass',
            'database': 'test_db'
        }

    def setUp(self):
        """Set up test cases"""
        self.agent = Agent(
            agent_id=1,
            name="Test Databricks Agent",
            memory_type="SHORT_TERM_MEMORY",
            foundation_model="gpt-4",
            team_id=1
        )
        
        # Initialize memories list
        self.agent.memories = []
        
        # Add DBX Tool to agent
        self.dbx_tool = MockDBXTool()
        self.agent.add_tool(self.dbx_tool)

    def test_agent_initialization(self):
        """Test if agent is initialized correctly"""
        self.assertEqual(self.agent.name, "Test Databricks Agent")
        self.assertEqual(self.agent.memory_type, "SHORT_TERM_MEMORY")
        self.assertEqual(self.agent.foundation_model, "gpt-4")
        self.assertEqual(len(self.agent.tools), 1)
        self.assertEqual(self.agent.tools[0].tool_name, "DBX Tool")

    @patch('app.connection_pool')
    def test_agent_memory_creation(self, mock_pool):
        """Test agent memory creation and retrieval"""
        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock memory data
        memory_data = {
            'id': 1,
            'agent_id': 1,
            'memory_type': 'SHORT_TERM_MEMORY',
            'start_prompt': 'You are a Databricks Agent and know Spark very well',
            'end_prompt': 'Have a Unit Test to verify your code',
            'context': 'Apache Spark & Databricks best practices',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_cursor.fetchone.return_value = memory_data
        
        # Test memory loading
        self.agent.memories = []  # Reset memories
        self.agent.memories.append(memory_data)  # Add mock memory
        
        self.assertEqual(len(self.agent.memories), 1)
        self.assertEqual(self.agent.memories[0]['memory_type'], 'SHORT_TERM_MEMORY')
        self.assertEqual(
            self.agent.memories[0]['start_prompt'],
            'You are a Databricks Agent and know Spark very well'
        )

    def test_llm_processing(self):
        """Test LLM processing of agent tasks"""
        # Test message formatting
        messages = self.agent.format_messages_for_llm(
            "How to build a python based databricks spark code?",
            "Apache Spark & Databricks best practices"
        )
        
        self.assertTrue(any("Databricks Agent" in msg['content'] for msg in messages))
        self.assertTrue(any("Apache Spark & Databricks best practices" in msg['content'] for msg in messages))
        
        # Test LLM processing
        response = self.agent.process_with_llm(messages)
        self.assertEqual(response['status'], 'success')
        self.assertTrue('response' in response)

    def test_tool_execution(self):
        """Test execution of DBX Tool"""
        command = "How to build a python based databricks spark code?"
        
        # Mock the process_with_llm method
        with patch.object(self.agent, 'process_with_llm') as mock_process:
            mock_process.return_value = {
                'status': 'success',
                'response': 'Here is a sample Databricks code',
                'model_used': 'gpt-4'
            }
            
            # Test tool execution
            result = self.dbx_tool.execute(command)
            
            self.assertEqual(result['status'], 'success')
            self.assertTrue('tool_responses' in result)
            self.assertEqual(len(result['tool_responses']), 1)
            self.assertEqual(result['tool_responses'][0]['tool_name'], 'DBX Tool')

    @patch('app.connection_pool')
    def test_end_to_end_workflow(self, mock_pool):
        """Test complete workflow from task input to response"""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock memory data
        memory_data = {
            'id': 1,
            'agent_id': 1,
            'memory_type': 'SHORT_TERM_MEMORY',
            'start_prompt': 'You are a Databricks Agent and know Spark very well',
            'end_prompt': 'Have a Unit Test to verify your code',
            'context': 'Apache Spark & Databricks best practices'
        }
        mock_cursor.fetchone.return_value = memory_data
        
        # Use the current agent for testing
        self.agent.memories = [memory_data]
        result = self.agent.execute_with_tools("How to build a python based databricks spark code?")
        
        self.assertEqual(result['status'], 'success')
        self.assertTrue('tool_responses' in result)
        self.assertTrue('validation_results' in result)
        self.assertEqual(self.agent.memory_type, 'SHORT_TERM_MEMORY')

    def test_validation_with_end_prompt(self):
        """Test validation of response against end prompt"""
        # Create a new mock OpenAI instance for this test
        mock_validation_only = Mock()
        mock_validation_only.chat = MagicMock()
        mock_validation_only.chat.completions = MagicMock()
        mock_validation_only.chat.completions.create = MagicMock(return_value=mock_validation_response)
        
        with patch('app.client', mock_validation_only):
            # Mock a response that should include unit tests
            mock_response = """
            def test_spark_code():
                # Test case implementation
                assert spark_function() == expected_result
            """
            
            # Test validation
            validation = self.agent.validate_response_with_llm(
                mock_response,
                "Have a Unit Test to verify your code"
            )
            
            self.assertEqual(validation['status'], 'success')
            self.assertTrue(validation['valid'])

if __name__ == '__main__':
    unittest.main() 