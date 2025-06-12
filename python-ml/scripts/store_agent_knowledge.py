"""Script to store predefined knowledge for agents."""
import sys
from pathlib import Path

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from app.utils.knowledge_manager import KnowledgeManager

def store_agent_knowledge():
    """Store predefined knowledge for Databricks and Nifi agents."""
    knowledge_manager = KnowledgeManager()
    
    # Knowledge for Databricks Agent (ID: 10)
    dbx_knowledge = """You are a Databricks Agent and know Spark very well
If someone asks to create a Databricks pipeline. Just give them below Message:

INSERT INTO METADATA_STEP (step_name, step_type, description, job_config)
VALUES (
    'Load Customer Data',
    'DBX',
    'Ingests customer data from S3 into Delta Lake using a Databricks notebook',
    JSON_OBJECT(
        'notebook_path', '/Shared/IngestCustomerData',
        'cluster_id', 'db-cluster-xyz',
        'parameters', JSON_OBJECT('env', 'prod', 'retries', 3)
    )
);"""

    # Knowledge for Nifi Agent (ID: 11)
    nifi_knowledge = """You are a Apache Nifi Agent and know Nifi very well.
If someone asks to create a Apache Nifi pipeline. Just give them below Message:

INSERT INTO METADATA_STEP (step_name, step_type, description, job_config)
VALUES (
    'Transform Sales Records',
    'NiFi',
    'Processes and transforms sales records with NiFi pipeline',
    JSON_OBJECT(
        'nifi_flow_id', 'abc123-nifi-flow',
        'input_port', 'SalesInput',
        'output_port', 'TransformedSales',
        'schedule', '0 */15 * * * *'
    )
);"""

    # Store knowledge for Databricks Agent
    result_dbx = knowledge_manager.store_predefined_knowledge(
        agent_id=10,
        knowledge_text=dbx_knowledge,
        confidence=1.0
    )
    print(f"Stored Databricks knowledge: {result_dbx}")

    # Store knowledge for Nifi Agent
    result_nifi = knowledge_manager.store_predefined_knowledge(
        agent_id=11,
        knowledge_text=nifi_knowledge,
        confidence=1.0
    )
    print(f"Stored Nifi knowledge: {result_nifi}")

if __name__ == "__main__":
    store_agent_knowledge() 