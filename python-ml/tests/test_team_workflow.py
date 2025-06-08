import unittest
import json
import requests
from datetime import datetime
from app.utils.logger import logger
from app.utils.db import get_db_connection, safe_close_connection

API_BASE_URL = "http://localhost:5000/api/ml"

class TestTeamWorkflow(unittest.TestCase):
    """Test cases for team workflow execution"""
    
    def setUp(self):
        """Set up test environment"""
        self.conn = get_db_connection()
        self.cursor = self.conn.cursor(dictionary=True)
        
        # Create test team
        self.cursor.execute("""
            INSERT INTO teams (name) VALUES ('Test Team')
        """)
        self.team_id = self.cursor.lastrowid
        
        # Create test agents with different priorities
        self.agents = [
            {
                "name": "High Priority Agent",
                "description": "Agent with highest priority",
                "priority": 1,
                "accuracy_rate": 95,
                "success_rate": 90
            },
            {
                "name": "Medium Priority Agent",
                "description": "Agent with medium priority",
                "priority": 2,
                "accuracy_rate": 85,
                "success_rate": 80
            },
            {
                "name": "Low Priority Agent",
                "description": "Agent with lowest priority",
                "priority": 3,
                "accuracy_rate": 75,
                "success_rate": 70
            }
        ]
        
        self.agent_ids = []
        for agent in self.agents:
            # Create agent
            self.cursor.execute("""
                INSERT INTO agents (name, description)
                VALUES (%s, %s)
            """, (agent["name"], agent["description"]))
            agent_id = self.cursor.lastrowid
            self.agent_ids.append(agent_id)
            
            # Add agent to team with metrics
            self.cursor.execute("""
                INSERT INTO team_agents 
                (team_id, agent_id, priority, accuracy, success)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                self.team_id,
                agent_id,
                agent["priority"],
                agent["accuracy_rate"],
                agent["success_rate"]
            ))
        
        self.conn.commit()
    
    def tearDown(self):
        """Clean up test data"""
        try:
            # Delete test data
            self.cursor.execute("DELETE FROM team_agents WHERE team_id = %s", (self.team_id,))
            if self.agent_ids:
                placeholders = ', '.join(['%s'] * len(self.agent_ids))
                self.cursor.execute(f"DELETE FROM agents WHERE id IN ({placeholders})", self.agent_ids)
            self.cursor.execute("DELETE FROM teams WHERE id = %s", (self.team_id,))
            self.conn.commit()
        finally:
            safe_close_connection(self.conn, self.cursor)
    
    def test_workflow_execution(self):
        """Test complete workflow execution"""
        # Prepare test data
        task_data = {
            "team_config": {
                "team_id": self.team_id
            },
            "task": {
                "task_description": "can you show me NFL favorite team data.",
                "requirements": {
                    "min_accuracy": 0.85,
                    "max_time": 300,
                    "output_format": "text",
                    "context": {
                        "user_id": "user-1",
                        "session_id": 77,
                        "conversation_history": []
                    }
                }
            }
        }
        
        # Execute team task
        response = requests.post(
            f"{API_BASE_URL}/team/execute",
            json=task_data
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("correlation_id", data)
        self.assertIn("workflow_id", data)
        self.assertIn("response", data)
        
        # Verify workflow record
        self.cursor.execute("""
            SELECT * FROM workflows WHERE id = %s
        """, (data["workflow_id"],))
        workflow = self.cursor.fetchone()
        self.assertIsNotNone(workflow)
        self.assertEqual(workflow["status"], "completed")
        
        # Verify workflow steps
        self.cursor.execute("""
            SELECT * FROM workflow_steps 
            WHERE workflow_id = %s
            ORDER BY id
        """, (data["workflow_id"],))
        steps = self.cursor.fetchall()
        self.assertEqual(len(steps), len(self.agents))
        
        # Verify steps are completed in priority order
        for step, agent in zip(steps, sorted(self.agents, key=lambda x: x["priority"])):
            self.assertEqual(step["status"], "completed")
            self.assertIsNotNone(step["tool_responses"])
            
        # Verify response contains data from all agents
        response_data = data["response"]
        self.assertIn("message", response_data)
        self.assertIn("data", response_data)
        self.assertIn("tool_results", response_data)

if __name__ == '__main__':
    unittest.main() 